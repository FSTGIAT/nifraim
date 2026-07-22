"""אנליסט (Analyst) agent portal — login, OTP, commission (נפרעים) download.

Login (https://agent.analyst.co.il/auth/login) is an Angular Material SPA. The
operator logs in with **תעודת זהות (ID)** + **טלפון נייד (phone)**, clicks
"שלחו לי קוד", and the portal SMS-OTPs that phone. Structurally this is Yelin's
twin, so this plugin mirrors ``yelin.py``.

Credential convention:  ``username = "<id>"`` (ת"ז 040336281),
                        ``password = "<phone>"`` (0504302306).

Flow (operator):
  login (ת"ז + phone → "שלחו לי קוד") → OTP (6 mat-input boxes → "כניסה")
  → הפקת דוחות → report-type "עמלות סוכנים" → date range → "הפק דוח" → xlsx.

Date rule (keyed on the 20th of the month — analyst publishes ~20 days late):
  day >= 20 → previous month;  day < 20 → two months back.
  range = [first-of-target-month, first-of-next-month].

The exact date-picker DOM is not yet known (SPA) — login/submit_otp/download use
broad candidate-selector lists and dump ``<run_id>_*.{png,html,txt}`` aggressively.
Refine selectors from the FIRST live run's `.txt` dumps — re-running costs an OTP.

The downloaded עמלות Excel format is confirmed against a real sample on the first
run; if `detect_format` misses it, add an `analyst_nifraim` signature to
`hebrew_mappings.py` + a parser branch, and add `"analyst_nifraim"` to
`_COMMISSION_FORMATS` in `parser_service.py` (else the run-all batch drops it).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from playwright.async_api import Page

PORTAL_URL = "https://agent.analyst.co.il/auth/login"


class AnalystPortal(BasePortalAutomation):
    portal_kind = "analyst"
    company_label = "אנליסט"
    # Ship OUT of the run-all batch until a single-run e2e is green — a half-working
    # new plugin must not break kiko's whole batch. Flip to True after verification.
    include_in_batch = False
    # MUST be Edge. Analyst's login is captcha-gated (`GetConfiguration` returns
    # `isCaptchaActive: true`) and it refuses automated Chrome. Measured
    # 2026-07-20, same machine/minute/profile/flow, fields verifiably filled in
    # both cases:
    #     msedge -> 200 {"isError":false,"guid":"…"}  -> OTP screen, SMS sent
    #     chrome -> 400 "Recaptcha validation failed"  -> no SMS at all
    # That is exactly the live failure: kiko's worker defaults to Chrome (it heads
    # the launch ladder), the login POST was rejected, no SMS was ever sent, and
    # the run then waited 5 minutes for a code nobody had issued. Same finding as
    # meitav — see ARCHITECTURE §4c, "the browser brand is part of the score".
    browser_channel = "msedge"
    # Captcha-gated, so it needs the same treatment as Mor/Meitav — and for the
    # same measured reason. The dev-box run that reached the OTP screen was
    # HEADED, on a real browser, with a fresh profile. Without these three flags
    # the worker launched analyst HEADLESS through the shared-browser path,
    # where a captcha refuses the login no matter which channel is picked.
    # `headed` also keeps it on the local worker (a headless Railway container
    # cannot open a desktop browser at all).
    headed = True
    native_fingerprint = True
    use_persistent_profile = True
    needs_residential_proxy = False

    def _split(self, username: str, password: str) -> tuple[str, str]:
        """username='<id>', password='<phone>'. Digit-strip both; pad the Israeli
        ת"ז to 9 and the mobile to 10 (operator may drop a leading zero)."""
        id_no = re.sub(r"\D", "", username or "")
        phone = re.sub(r"\D", "", password or "")
        if len(id_no) == 8:
            id_no = "0" + id_no
        if len(phone) == 9 and not phone.startswith("0"):
            phone = "0" + phone
        return id_no, phone

    @staticmethod
    def _target_months(today: date) -> list[tuple[int, int]]:
        """Ordered (year, month) candidates to try. Primary per the 20th rule, then
        one/two months further back as a self-heal if the primary month is empty
        (late publish). day>=20 → previous month; day<20 → two months back."""
        back = 1 if today.day >= 20 else 2

        def shift(months_back: int) -> tuple[int, int]:
            m = today.month - months_back
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            return y, m

        return [shift(back), shift(back + 1), shift(back + 2)]

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        id_no, phone = self._split(username, password)

        # Watch the LOGIN POST itself. The OTP screen appearing is the success
        # signal, but its ABSENCE used to be silent: the old code fell through
        # with "no clear transition — let the runner await OTP", so a rejected
        # login became a five-minute wait for a code that was never sent, and
        # the run was reported at stage=otp as though login had worked.
        #
        # The DOM check alone cannot see this. Chrome's rejection was a network
        # 400 ("Recaptcha validation failed") with NO toast and no mat-error —
        # the page simply stayed on the form. Only the response says what
        # happened, so capture it and let the server's own words end the run.
        srv: dict = {"status": None, "body": "", "seen": False}

        async def _on_resp(resp):
            try:
                if resp.request.method != "POST" or "Authorization/Login" not in resp.url:
                    return
                srv["seen"] = True
                srv["status"] = resp.status
                try:
                    srv["body"] = (await resp.text())[:300]
                except Exception:
                    pass
            except Exception:
                pass

        page.on("response", _on_resp)

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        land = SCREENSHOT_ROOT / "analyst_login.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # MOVE THE MOUSE LIKE A PERSON before clicking anything.
        #
        # `page.click()` teleports the cursor: the pointer is at (0,0) one moment
        # and inside the field the next, with no path between. reCAPTCHA
        # Enterprise scores interaction telemetry, and a session that produces
        # keystrokes with literally NO pointer movement is a strong bot signal.
        #
        # This is the difference that matters here, and it was measured the right
        # way round: a HUMAN logging in on this same machine, same IP, same Edge
        # reaches the OTP screen reliably, while the automation is refused
        # intermittently. So the account and the IP are not penalised and the
        # score is not "burned" — the automated SESSION is being judged on its
        # own, and the one thing it never produced was a mouse path.
        #
        # Deliberately cheap: a short glide to each control plus a small dwell.
        # No synthetic "warm-up" browsing (that was disabled for Mor on
        # evidence); this only makes the real interaction look like one.
        async def _glide_click(sel: str) -> None:
            """Plain click — deliberately NOT a synthetic mouse path.

            This used to glide the pointer over 6 eased steps before clicking, on
            the hypothesis that "keystrokes with no pointer movement" looked like
            a bot. That hypothesis was never measured, and the evidence now runs
            against it. Same portal, same credentials, same Edge, same minute:

                plain page.click()      -> 200 + OTP SMS sent      (dev box)
                6-step synthetic glide  -> 400 "Recaptcha validation failed"
                                           (agent's worker, cold profile, Edge)

            A perfectly linear path with fixed 45/57/69ms dwells is arguably a
            STRONGER bot signal than a normal click, which already dispatches
            real mousedown/mouseup. Playwright's click is what was proven to
            pass, so that is what ships. Do not re-add the glide without a
            measurement showing it helps.
            """
            await page.click(sel)

        # Angular Material: matinput controls stay ng-pristine/ng-invalid under
        # page.fill(), keeping the submit disabled — drive real KEYSTROKES.
        async def _type(selectors: list[str], val: str, label: str) -> bool:
            for sel in selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=4000)
                except Exception:
                    continue
                try:
                    await _glide_click(sel)
                    await page.fill(sel, "")
                    await page.keyboard.type(val, delay=70)
                    cur = await page.input_value(sel)
                    if cur != val:  # retry once if a char dropped
                        await page.fill(sel, "")
                        await page.click(sel)
                        await page.keyboard.type(val, delay=90)
                    logger.info("אנליסט: filled %s via %s", label, sel)
                    return True
                except Exception:
                    continue
            return False

        # ת"ז — the DOM paste shows a matinput with mat-label "תעודת זהות".
        id_ok = await _type([
            "input[formcontrolname*='identity' i]",
            "input[formcontrolname*='tz' i]",
            "input[aria-label*='זהות']",
            "input[placeholder*='זהות']",
            "input[maxlength='9']",
        ], id_no, "ת\"ז")

        # phone — matinput inputmode="tel" aria-label="טלפון נייד" maxlength=10.
        phone_ok = await _type([
            "input[inputmode='tel']",
            "input[aria-label*='טלפון']",
            "input[formcontrolname*='phone' i]",
            "input[placeholder*='טלפון']",
            "input[maxlength='10']",
        ], phone, "טלפון")

        if not (id_ok and phone_ok):
            raise RuntimeError(
                "אנליסט: לא נמצאו שדות ת\"ז/טלפון בטופס ההתחברות — בדוק analyst_login.txt/html"
            )

        # A short settle before submitting. No synthetic pointer wiggle — see
        # _glide_click: the manufactured mouse path correlated with the captcha
        # rejection, while a plain click passed.
        await page.wait_for_timeout(700)

        # "שלחו לי קוד" → fires the SMS (otp_since is anchored by the runner BEFORE
        # login(), so a code that arrives now is caught).
        clicked = await self._click_first_visible(page, [
            "button[type='submit']:has-text('שלחו לי קוד')",
            "button:has-text('שלחו לי קוד')",
            "button:has-text('שלחו קוד')",
            "button:has-text('שלח קוד')",
            "button[type='submit']:not([disabled])",
        ], timeout=10000)
        if not clicked:
            raise RuntimeError(
                "אנליסט: כפתור 'שלחו לי קוד' לא נמצא/מושבת (טופס לא תקין) — בדוק analyst_login.txt"
            )

        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "analyst_after_send.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

        # Wait for the OTP screen (segmented boxes) OR an error toast — fail fast.
        otp_sel = "input[maxlength='1']"
        for _ in range(60):  # ~30s
            try:
                boxes = page.locator(f"{otp_sel}:visible")
                if await boxes.count() and await boxes.first.is_visible():
                    return
            except Exception:
                pass
            try:
                err = await page.evaluate(
                    """() => [...document.querySelectorAll('mat-error,.error,.toast,.alert,[class*=error i]')]
                        .map(e => (e.innerText||'').trim()).filter(Boolean).join(' | ').slice(0,300)"""
                )
            except Exception:
                err = ""
            if err and any(w in err for w in ("שגוי", "שגיא", "לא נמצא", "נסה")):
                raise RuntimeError(f"אנליסט: הכניסה נדחתה — {err}")
            # The server's answer beats the DOM: a captcha rejection paints
            # nothing at all, so without this the loop just times out quietly.
            if srv["seen"] and srv["status"] and srv["status"] >= 400:
                break
            await page.wait_for_timeout(500)

        # FAIL LOUDLY. Falling through to the runner's OTP wait after a rejected
        # login costs five minutes and then blames the phone — "לא התקבל קוד OTP",
        # pointing the agent at their SMS app when the code was never requested.
        if srv["seen"] and srv["status"] and srv["status"] >= 400:
            _b = (srv["body"] or "").strip()
            _hint = ""
            if "ecaptcha" in _b or "aptcha" in _b:
                # Name the cause from the FACT of which browser ran, not from an
                # assumption. The first version of this hint always said "use
                # Edge, not Chrome" — and then fired on a run that WAS on Edge
                # (persistent browser=msedge), sending the reader back to a
                # question already settled. `browser_label` is stamped by the
                # runner with what actually launched.
                _bl = getattr(self, "browser_label", "") or "unknown"
                if _bl in ("msedge", "chrome-exe", "chrome"):
                    _real = "msedge" in _bl
                else:
                    _real = False
                if not _real:
                    _hint = (f" רץ על דפדפן '{_bl}' — אנליסט דוחה כל דפדפן שאינו Edge. "
                             "ודא ש-Edge מותקן במחשב (browser_channel='msedge').")
                else:
                    # Edge WAS used, so the browser is not the story. On a
                    # score-gated portal the usual cause is repeated attempts:
                    # each rejection lowers the score, and it recovers with quiet
                    # (the Mor precedent, ARCHITECTURE §4c).
                    _hint = (" רץ על Edge כנדרש, ולכן זו אינה בעיית דפדפן — "
                             "ככל הנראה ניקוד ה-captcha ירד עקב ניסיונות חוזרים. "
                             "המתן 20-30 דקות ונסה פעם אחת בלבד.")
            raise RuntimeError(
                f"אנליסט: שרת האנליסט דחה את הכניסה ({srv['status']}: {_b[:120]}) — "
                f"לא נשלחה הודעת SMS.{_hint}"
            )
        if not srv["seen"]:
            raise RuntimeError(
                "אנליסט: בקשת הכניסה כלל לא נשלחה (לא נצפתה קריאת Authorization/Login) — "
                "ייתכן שהטופס לא מולא או שהכפתור לא נלחץ. בדוק analyst_after_send.txt/html"
            )
        # OTP screen never painted but the server accepted — let the runner await
        # the code; submit_otp re-detects the boxes.

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")[:6]

        filled = False
        # Segmented single-char boxes. `:visible` EXCLUDES the hidden
        # autocomplete="one-time-code" maxlength=6 catcher (it isn't maxlength=1
        # and isn't visible), so we type only into the six real boxes.
        #
        # TYPE THE WHOLE CODE INTO THE FIRST BOX and let the component's own
        # auto-advance place the digits — the way a person enters it.
        #
        # The previous version clicked EACH box and typed one digit into it. That
        # desynchronises against auto-advance: the component moves focus after a
        # character, so the next click/fill lands on a box the component has
        # already moved past, and digits shift or vanish. Measured live
        # 2026-07-20 — code 775439 produced boxes `0 0 4 3 9 _`, with the last
        # box still `ng-pristine` (never typed into). The run then sat on
        # /auth/otp while download_reports scraped the OTP page, and reported a
        # date-picker problem that did not exist.
        async def _read_boxes(loc) -> str:
            try:
                return "".join([(await loc.nth(i).input_value()) or ""
                                for i in range(await loc.count())])
            except Exception:
                return ""

        try:
            boxes = page.locator("input[maxlength='1']:visible")
            n = await boxes.count()
            if 0 < n <= len(digits) + 2:
                await boxes.first.click()
                try:
                    await boxes.first.fill("")
                except Exception:
                    pass
                await page.keyboard.type(digits, delay=90)
                await page.wait_for_timeout(300)
                got = await _read_boxes(boxes)
                if got != digits:
                    # Fallback: set each box directly, no clicking and no
                    # keystrokes, so focus movement cannot reorder anything.
                    logger.warning("אנליסט: OTP autotype gave %r, retrying per-box", got)
                    for i in range(min(n, len(digits))):
                        try:
                            await boxes.nth(i).fill(digits[i])
                        except Exception:
                            pass
                    await page.wait_for_timeout(300)
                    got = await _read_boxes(boxes)
                # NEVER submit a code we can see is wrong — a rejected OTP can
                # burn the one the insurer issued.
                if got != digits:
                    raise RuntimeError(
                        f"אנליסט: לא ניתן להזין את קוד ה-OTP בתיבות "
                        f"(התקבל {len(got)} ספרות במקום {len(digits)}) — "
                        "ייתכן שינוי ברכיב ה-OTP."
                    )
                logger.info("אנליסט: OTP entered into %d boxes, verified", n)
                filled = True
        except RuntimeError:
            raise
        except Exception:
            pass
        # Fallback: a single OTP input (e.g. the hidden one-time-code catcher).
        if not filled:
            for sel in (
                "input[autocomplete='one-time-code']",
                "input[formcontrolname*='otp' i]",
                "input[name*='otp' i]",
                "input[inputmode='numeric']",
            ):
                try:
                    await page.wait_for_selector(sel, state="attached", timeout=3000)
                    await page.click(sel)
                    await page.keyboard.type(digits, delay=70)
                    filled = True
                    break
                except Exception:
                    continue

        await page.wait_for_timeout(400)
        # "כניסה" — the OTP submit lives inside the OTP <form>. Scope to the form so
        # a background submit button isn't clicked instead (the Mor lesson).
        # Scoped to the OTP form so it can't hit the login form's own submit button
        # behind it (the Mor lesson). NO bare `button:has-text('כניסה')` /
        # `button[type=submit]` fallbacks — those could match the still-mounted login
        # view's "שלחו לי קוד" submit and silently no-op the OTP.
        clicked = await self._click_first_visible(page, [
            "form button.btn-submit[type='submit']",
            "form button[type='submit']:has-text('כניסה')",
            "button.btn-submit:has-text('כניסה')",
        ], timeout=6000)
        if not clicked:
            try:
                await page.keyboard.press("Enter")
            except Exception:
                pass

        # Accepted ⇒ leaves the whole AUTH flow. Test for that, not for "login".
        #
        # This used to wait for `"login" not in url` — but the OTP screen lives at
        # **/auth/otp**, which contains no "login", so the predicate was already
        # true the moment it was evaluated. `left_login` came back True on a code
        # that had not been accepted, and the run walked into download_reports
        # still sitting on the OTP page. Measured live 2026-07-20: the failure
        # surfaced as "לא ירד קובץ נפרעים תקין — check nav_3_dates.txt", pointing
        # at a date picker that had never been reached, while the DOM snapshot
        # showed `url: /auth/otp` and six OTP boxes.
        #
        # Anything under /auth/ is still the login flow: /auth/login, /auth/otp,
        # and any future step. Leaving that subtree is the real success signal.
        left_login = False
        try:
            await page.wait_for_url(
                lambda u: "/auth/" not in (u or "").lower(), timeout=25000
            )
            left_login = True
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "analyst_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("אנליסט: לא נמצא שדה OTP — בדוק analyst_after_send.txt")
        # Still on the login route with the OTP boxes present ⇒ the code was rejected.
        if not left_login:
            try:
                still_otp = bool(await page.locator("input[maxlength='1']:visible").count())
            except Exception:
                still_otp = False
            if still_otp:
                raise RuntimeError(
                    "אנליסט: קוד ה-OTP נדחה (עדיין במסך הקוד) — בדוק analyst_post_otp.txt"
                )

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        self.report_password = None
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        async def ck(tag: str):
            p = SCREENSHOT_ROOT / f"{run_id}_{tag}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        # DISMISS THE POST-LOGIN ANNOUNCEMENT MODAL.
        #
        # Analyst opens the lobby with a "סוכן יקר" notice (phone-support hours)
        # over the page, closed by a "סגירה" button. Its backdrop intercepts
        # pointer events, so the right-hand menu — which IS rendered and visible
        # behind it — cannot be clicked. That is the whole reason the run never
        # left /lobby: `_click_first_visible` correctly reported the menu item as
        # unclickable (`clicked=None`), and page.goto('/reports') bounced back
        # because the route is guarded and only in-app navigation satisfies it.
        #
        # The evidence was already in an earlier dump — `btn: ["", "יציאה",
        # "סגירה"]` — and "סגירה" is this dialog's close button. It read as page
        # furniture until a screenshot showed the dialog.
        #
        # Same shape as mor.py's announcement modal, so the same belt-and-braces:
        # click the close button, press Escape, then tear any overlay out of the
        # DOM. Every step is a no-op when no modal is present.
        await page.wait_for_timeout(2000)
        for _ in range(3):
            try:
                btn = page.locator(
                    "button:has-text('סגירה'), button:has-text('סגור'), "
                    "mat-dialog-container button, .cdk-overlay-container button"
                ).first
                if not await btn.count():
                    break
                if await btn.is_visible():
                    await btn.click(timeout=3000)
                    logger.info("אנליסט: dismissed post-login modal")
                    await page.wait_for_timeout(700)
                else:
                    break
            except Exception:
                break
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)
        except Exception:
            pass
        # Guaranteed dismissal: remove any Material overlay/backdrop still up.
        # It is only an announcement, so tearing it down client-side is safe.
        try:
            removed = await page.evaluate(
                """() => {
                    // Remove the DIALOG and its BACKDROP only.
                    //
                    // NEVER match `[class*=overlay]` here: that also matches
                    // `.cdk-overlay-container`, the single host Angular Material
                    // renders EVERY overlay into — including mat-select panels.
                    // Deleting it leaves the page looking fine while every
                    // dropdown silently opens with no options: measured live,
                    // `mat-select[aria-label="בחירת סוג דוח"]` reported
                    // aria-expanded=true while `mat-option` count was 0, so the
                    // report type could never be chosen. Killing the modal
                    // cannot be allowed to break the form behind it.
                    const sel = 'mat-dialog-container, .cdk-overlay-backdrop, '
                              + '.modal-backdrop';
                    const n = document.querySelectorAll(sel).length;
                    document.querySelectorAll(sel).forEach(e => e.remove());
                    // Empty panes left behind by the dialog are safe to drop;
                    // panes that still hold content are somebody's live UI.
                    document.querySelectorAll('.cdk-overlay-pane').forEach(p => {
                        if (!p.querySelector('mat-select-panel, .mat-mdc-select-panel, '
                                             + 'mat-option, [role=listbox]')) p.remove();
                    });
                    document.body.classList.remove('cdk-global-scrollblock');
                    document.body.style.overflow = '';
                    return n;
                }"""
            )
            if removed:
                logger.info("אנליסט: removed %d leftover overlay node(s)", removed)
        except Exception:
            pass
        await page.wait_for_timeout(600)
        await ck("nav_0_home")

        # 1) Navigate to הפקת דוחות — BY HREF, and then VERIFY we arrived.
        #
        # The live lobby DOM (2026-07-21) gives the routes outright:
        #   דף הבית לסוכן -> /lobby        חשבונות עמיתים -> /customer-accounts
        #   הפקת דוחות    -> /reports      הודעות        -> /messages
        # so "הפקת דוחות" is an <a href="/reports">, not a button or a span.
        #
        # Two failures compounded before this. The click result was DISCARDED —
        # `await self._click_first_visible(...)` with no `if not clicked:` — so a
        # missed nav was silent; and every later step then ran against /lobby.
        # The report-type select was never found, the date pickers never opened
        # (`DATEPICKER {"open": false, "cells": []}`), and the run finally blamed
        # the date screen. Every one of those was a downstream symptom of never
        # having left the lobby.
        # Order follows the OPERATOR'S recorded procedure, which names the exact
        # element: "מצד ימין יש תפריט, לוחצים על 'הפקת דוחות'" with
        #     <span class="font-h8-regular">הפקת דוחות</span>
        # so the documented span leads. Clicking what a person clicks is also the
        # safer route on an Angular SPA: the target route can depend on state a
        # guard/resolver sets up during navigation, which a raw URL jump skips.
        _clicked = await self._click_first_visible(page, [
            "span.font-h8-regular:has-text('הפקת דוחות')",
            "span:has-text('הפקת דוחות')",
            "[role='menuitem']:has-text('הפקת דוחות')",
            "li:has-text('הפקת דוחות')",
            "a:has-text('הפקת דוחות')",
            "a[href='/reports']",
        ], timeout=12000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        # The menu item exists in the DOM but is not CLICKABLE — `clicked=None`
        # with the anchors present in the snapshot means the right-hand menu is
        # collapsed/zero-size, so Playwright's visibility check rejects it.
        # Dispatch the click in-page instead: that runs Angular's routerLink
        # exactly as a user's click would, without needing the element painted.
        # (A raw page.goto does NOT substitute — measured 2026-07-21, /reports
        # redirected straight back to /lobby, so the route is guarded and only
        # in-app navigation satisfies it.)
        if "/reports" not in (page.url or ""):
            try:
                did = await page.evaluate(
                    """() => {
                        const els = [...document.querySelectorAll('a,[routerlink],span,li')];
                        const hit = els.find(e =>
                            (e.textContent || '').trim() === 'הפקת דוחות'
                            || (e.getAttribute && (e.getAttribute('href') || '') === '/reports'));
                        if (!hit) return 'no-element';
                        // Click the anchor if the text sits inside one.
                        const a = hit.closest('a') || hit;
                        a.click();
                        return 'clicked:' + (a.tagName || '?');
                    }"""
                )
                logger.info("אנליסט: in-page nav dispatch → %s", did)
                await page.wait_for_timeout(2500)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
            except Exception as _e:
                logger.warning("אנליסט: in-page nav dispatch failed: %s", _e)

        # If the menu is collapsed, open it and retry the documented span. The
        # lobby exposes one unnamed button alongside יציאה/סגירה — the likely
        # toggle — so try the generic openers before giving up.
        if "/reports" not in (page.url or ""):
            for _t in ("button[aria-label*='תפריט']", "button.menu-toggle",
                       "button:has(mat-icon)", "mat-icon:has-text('menu')",
                       "button:not(:has-text('יציאה')):not(:has-text('סגירה'))"):
                try:
                    loc = page.locator(_t).first
                    if await loc.count():
                        await loc.click(timeout=2500)
                        await page.wait_for_timeout(900)
                        _again = await self._click_first_visible(page, [
                            "span.font-h8-regular:has-text('הפקת דוחות')",
                            "a[href='/reports']",
                        ], timeout=4000)
                        if _again and "/reports" in (page.url or ""):
                            logger.info("אנליסט: menu opened via %s", _t)
                            break
                except Exception:
                    continue
            await page.wait_for_timeout(1200)

        if "/reports" not in (page.url or ""):
            logger.warning("אנליסט: still at %s after nav click (clicked=%s) — "
                           "falling back to goto /reports (the CLICK should be fixed)",
                           page.url, _clicked)
            try:
                from app.services.portal_automation.runner import _worker_note
                _worker_note(f"analyst: menu click did not navigate (clicked={_clicked}, "
                             f"url={page.url}) — using goto fallback")
            except Exception:
                pass
            try:
                await page.goto("https://agent.analyst.co.il/reports",
                                wait_until="domcontentloaded", timeout=30000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
            except Exception as _e:
                logger.warning("אנליסט: goto /reports failed: %s", _e)

        await ck("nav_1_reports")

        # Do NOT continue on the lobby. Everything downstream reads a form that
        # only exists on /reports, so proceeding just manufactures a misleading
        # error three steps later.
        if "/reports" not in (page.url or ""):
            try:
                # Say WHY the menu could not be clicked, not merely that it
                # wasn't. Geometry + computed style distinguishes the candidates:
                # a collapsed/zero-size sidebar, an off-screen drawer, a
                # display:none menu, or an overlay eating the click. Also list
                # every button with its class/aria so the unnamed one (the likely
                # toggle) can be identified by name next time.
                probe = await page.evaluate(
                    """() => {
                        const links = [...document.querySelectorAll('a,[routerlink],span')]
                          .filter(e => (e.textContent || '').trim() === 'הפקת דוחות'
                                    || (e.getAttribute && e.getAttribute('href') === '/reports'))
                          .slice(0, 4).map(e => {
                            const r = e.getBoundingClientRect();
                            const s = getComputedStyle(e);
                            return {tag: e.tagName, href: e.getAttribute('href') || '',
                                    w: Math.round(r.width), h: Math.round(r.height),
                                    x: Math.round(r.x), y: Math.round(r.y),
                                    disp: s.display, vis: s.visibility, op: s.opacity,
                                    off: !!e.offsetParent};
                          });
                        return {
                            url: location.href, links,
                            buttons: [...document.querySelectorAll('button')].slice(0, 10).map(b => ({
                                t: (b.innerText || '').trim().slice(0, 14),
                                cls: (b.className || '').slice(0, 40),
                                aria: b.getAttribute('aria-label') || ''})),
                            drawers: [...document.querySelectorAll(
                                'mat-sidenav,mat-drawer,nav,aside,[class*=menu],[class*=sidebar]')]
                                .slice(0, 6).map(d => ({c: (d.className || '').slice(0, 40),
                                    w: Math.round(d.getBoundingClientRect().width)})),
                        };
                    }"""
                )
                from app.services.portal_automation.runner import _worker_note
                import json as _json
                _worker_note("analyst NAV FAILED — "
                             + _json.dumps(probe, ensure_ascii=False)[:1800])
            except Exception:
                try:
                    from app.services.portal_automation.runner import _worker_note
                    _worker_note(f"analyst NAV FAILED — still at {page.url}")
                except Exception:
                    pass
            raise RuntimeError(
                f"אנליסט: לא הצלחנו לעבור למסך 'הפקת דוחות' (נשארנו ב-{page.url}) — "
                "בדוק את תפריט הניווט בדף הלובי."
            )

        # 2) Report-type mat-select → "עמלות סוכנים".
        await self._click_first_visible(page, [
            "mat-select[aria-label*='סוג דוח']",
            "mat-select[aria-label*='בחירת סוג']",
            "mat-select",
        ], timeout=10000)
        await page.wait_for_timeout(600)
        await self._click_first_visible(page, [
            "mat-option:has-text('עמלות סוכנים')",
            "mat-option .mdc-list-item__primary-text:has-text('עמלות סוכנים')",
            "[role='option']:has-text('עמלות סוכנים')",
        ], timeout=8000)
        await page.wait_for_timeout(600)
        await ck("nav_2_report_type")

        # 2b) AGENT select → "כל הסוכנים". A SECOND mat-select that this plugin
        #     never touched. The operator's recorded procedure lists it right
        #     after the report type ("בחלונית סוכנים בוחרים 'כל הסוכנים'"), and
        #     the live /lobby DOM showed it as `aria-label="בחירת סוכן"` sitting
        #     at "כל הסוכנים". Leaving it unset can scope the report to nothing.
        #     Best-effort: if it is already on "כל הסוכנים" this is a no-op.
        try:
            _agent_sel = page.locator(
                "mat-select[aria-label*='סוכן'], mat-select[aria-label*='בחירת סוכן']"
            ).first
            if await _agent_sel.count():
                await _agent_sel.click(timeout=6000)
                await page.wait_for_timeout(600)
                _all = page.locator(
                    "mat-option:has-text('כל הסוכנים'), [role='option']:has-text('כל הסוכנים')"
                ).first
                if await _all.count():
                    await _all.click(timeout=5000)
                    logger.info("אנליסט: agent select → כל הסוכנים")
                else:
                    await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
        except Exception as _e:
            logger.warning("אנליסט: agent select step skipped: %s", _e)
        await ck("nav_2b_agent")

        # 3) Date range. The pickers are READONLY — they must be driven through
        #    the calendar dialog, never typed into.
        target = None
        chosen_ym: tuple[int, int] | None = None
        range_confirmed = False

        _HE_MONTHS = ("ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                      "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר")

        async def _pick_day(aria: str, yy: int, mm: int, day: int) -> bool:
            """Set ONE readonly date field by driving its calendar dialog.

            Every selector here comes from the live DOM (observed 2026-07-22 on
            the real /reports page), not from inference:

              * the input is `readonly` with `data-mat-calendar="mat-datepicker-N"`,
                so CLICKING IT DOES NOTHING — the calendar opens from the
                `mat-datepicker-toggle` button beside it. That single fact is why
                the previous implementation logged "no calendar" every time.
              * the calendar is a DAY view: cells carry
                `aria-label="1 בינואר 2026"`, and the header button reads
                "ינו׳ 2026".
              * the fields arrive PRE-FILLED (מחודש=1.1.2026, עד חודש=30.6.2026),
                so a run that fails to set them still exports — silently, over the
                portal's own default range rather than the month we asked for.

            Navigation reads the first cell's aria-label to learn which month is
            displayed, then steps next/prev exactly the required number of times —
            no reliance on the abbreviated header text.
            """
            di = page.locator(f"input[aria-label='{aria}']").first
            if not await di.count():
                logger.warning("אנליסט: date field %s not found", aria)
                return False
            # The toggle sits inside the same mat-form-field as the input.
            tog = page.locator(
                f"mat-form-field:has(input[aria-label='{aria}']) mat-datepicker-toggle button"
            ).first
            if not await tog.count():
                tog = page.locator("mat-datepicker-toggle button").first
            try:
                await tog.click(timeout=6000)
                await page.wait_for_timeout(800)
            except Exception as e:
                logger.warning("אנליסט: %s toggle click failed: %s", aria, e)
                return False

            cal = page.locator(".mat-datepicker-content, mat-calendar").first
            try:
                await cal.wait_for(state="visible", timeout=6000)
            except Exception:
                logger.warning("אנליסט: %s calendar did not open", aria)
                return False

            want = f"{day} ב{_HE_MONTHS[mm - 1]} {yy}"
            for _ in range(30):
                cell = page.locator(f".mat-calendar-body-cell[aria-label='{want}']").first
                if await cell.count():
                    await cell.click(timeout=3000)
                    await page.wait_for_timeout(600)
                    break
                # Which month is on screen? Read it off the first cell.
                try:
                    first = await page.locator(
                        ".mat-calendar-body-cell").first.get_attribute("aria-label")
                except Exception:
                    first = None
                cur = None
                if first:
                    for idx, nm in enumerate(_HE_MONTHS, start=1):
                        if f"ב{nm} " in first:
                            try:
                                cur = (int(first.strip().split()[-1]), idx)
                            except Exception:
                                cur = None
                            break
                if not cur:
                    break
                delta = (yy * 12 + mm) - (cur[0] * 12 + cur[1])
                if delta == 0:
                    break
                nav = (".mat-calendar-next-button" if delta > 0
                       else ".mat-calendar-previous-button")
                try:
                    await page.locator(nav).first.click(timeout=2500)
                    await page.wait_for_timeout(350)
                except Exception:
                    break

            got = (await di.input_value()) or ""
            # Live format is d.m.yyyy ("1.1.2026"); accept / as a separator too.
            norm = "." + got.replace("/", ".").strip() + "."
            ok = bool(got) and str(yy) in got and f".{mm}." in norm
            logger.info("אנליסט: %s → %d.%d.%d ⇒ %r (ok=%s)", aria, day, mm, yy, got, ok)
            return ok

        async def _pick_month(aria: str, yy: int, mm: int, want_last: bool = False) -> bool:
            """Drive ONE readonly month picker through its calendar dialog.

            The operator's recorded DOM settles what these fields are:

                <input matinput readonly="true" aria-label="מחודש"
                       class="… mat-datepicker-input …" id="mat-input-8"
                       aria-haspopup="dialog" data-mat-calendar="mat-datepicker-0">
                <input … aria-label="עד חודש" … data-mat-calendar="mat-datepicker-1">

            `readonly="true"` is the whole story: the previous implementation did
            `click → fill("") → keyboard.type("01/06/2026")`, which CANNOT put a
            value into a readonly input. The range was therefore never applied,
            the portal exported its own default period, and the run reported
            "date range not confirmed" without anyone realising typing was
            impossible in principle. They are month pickers (labels are
            "מחודש"/"עד חודש" — FROM-MONTH / TO-MONTH), opened as a dialog via
            aria-haspopup, so the month must be CLICKED in the calendar.

            Returns True only when the input reads back the requested month+year.
            """
            di = page.locator(f"input[aria-label='{aria}']").first
            if not await di.count():
                return False
            try:
                await di.click(timeout=6000)          # opens mat-datepicker
                await page.wait_for_timeout(700)
            except Exception:
                return False

            cal = page.locator(".mat-datepicker-content, mat-calendar").first
            try:
                await cal.wait_for(state="visible", timeout=6000)
            except Exception:
                return False

            # Walk to the right YEAR. The period button shows the current view's
            # label; prev/next step a year at a time in the month view.
            for _ in range(14):
                try:
                    label = (await page.locator(
                        ".mat-calendar-period-button").first.inner_text(timeout=2000)) or ""
                except Exception:
                    label = ""
                if str(yy) in label:
                    break
                nav = ".mat-calendar-previous-button" if str(yy) < label else \
                      ".mat-calendar-next-button"
                # Fall back to 'previous' when the label carries no year at all.
                if not re.search(r"\d{4}", label):
                    nav = ".mat-calendar-previous-button"
                try:
                    await page.locator(nav).first.click(timeout=2500)
                    await page.wait_for_timeout(350)
                except Exception:
                    break

            # Click the month cell. Cells carry the Hebrew month name (or its
            # abbreviation) as text/aria-label.
            name = _HE_MONTHS[mm - 1]
            for sel in (f".mat-calendar-body-cell[aria-label*='{name}']",
                        f"[role='gridcell']:has-text('{name}')",
                        f".mat-calendar-body-cell:has-text('{name[:3]}')"):
                try:
                    cell = page.locator(sel).first
                    if await cell.count():
                        await cell.click(timeout=3000)
                        await page.wait_for_timeout(600)
                        break
                except Exception:
                    continue

            # A DAY may still be required after the month view. Which day matters:
            # the recorded procedure uses 01/06/26 → 30/06/26, i.e. the FIRST day
            # for "מחודש" and the LAST day for "עד חודש". Taking the first cell
            # for both (the earlier behaviour) would ask for 01/06 → 01/06 and
            # report a single day instead of the month.
            try:
                if await cal.is_visible():
                    cells = page.locator(
                        ".mat-calendar-body-cell:not(.mat-calendar-body-disabled)")
                    n = await cells.count()
                    if n:
                        c = cells.nth(n - 1) if want_last else cells.first
                        await c.click(timeout=2500)
                        await page.wait_for_timeout(500)
            except Exception:
                pass

            try:
                got = re.sub(r"\D", "", (await di.input_value()) or "")
            except Exception:
                got = ""
            # Accept 06/2026 or 06/26 — compare month+year, ignoring the day.
            ok = bool(got) and f"{mm:02d}" in got and (str(yy) in got or str(yy)[-2:] in got)
            logger.info("אנליסט: %s → %02d/%d ⇒ %r (ok=%s)", aria, mm, yy, got, ok)
            return ok

        async def _set_range(yy: int, mm: int) -> bool:
            """Both ends of the range are the SAME month.

            The recorded procedure says "בוחרים את החודש האחרון לדוגמה:
            30/06/26 - 01/06/26" — i.e. the whole of June, expressed as a
            FROM-MONTH / TO-MONTH pair. The old code sent `d_to` as the FIRST of
            the NEXT month (01/07/2026), which on a month picker is a different,
            wrong month.
            """
            # Day range over the whole target month: 1 -> last. The live fields
            # read "1.1.2026" / "30.6.2026", i.e. d.m.yyyy days, matching the
            # operator's "01/06/26 - 30/06/26".
            import calendar as _cal
            _last_day = _cal.monthrange(yy, mm)[1]
            ok_from = await _pick_day("מחודש", yy, mm, 1)
            ok_to = await _pick_day("עד חודש", yy, mm, _last_day)
            if not (ok_from and ok_to):
                # Report the calendar's own DOM once, so a miss here is fixable
                # without another blind run.
                try:
                    snap = await page.evaluate(
                        """() => ({
                            open: !!document.querySelector('.mat-datepicker-content'),
                            period: (document.querySelector('.mat-calendar-period-button')
                                     ||{}).innerText || '',
                            cells: [...document.querySelectorAll('.mat-calendar-body-cell')]
                                    .slice(0, 18).map(c => (c.getAttribute('aria-label')
                                     || c.innerText || '').trim()),
                            vals: [...document.querySelectorAll('input.mat-datepicker-input')]
                                    .map(i => ({a: i.getAttribute('aria-label'), v: i.value})),
                        })"""
                    )
                    from app.services.portal_automation.runner import _worker_note
                    import json as _json
                    _worker_note("analyst DATEPICKER — "
                                 + _json.dumps(snap, ensure_ascii=False)[:1200])
                except Exception:
                    pass
            return ok_from and ok_to

        async def _produce_download(out_path: Path) -> Path | None:
            """Click 'הפק דוח' and capture a native download OR XHR bytes — but only
            accept bytes that are actually an Excel file (magic-byte checked), so an
            HTML/JSON error page or a stray octet-stream blob can't be saved as a
            fake report."""
            xhr = {"bytes": None, "url": None}

            async def on_resp(resp):
                try:
                    if xhr["bytes"] is not None:
                        return
                    ct = (resp.headers.get("content-type") or "").lower()
                    cd = (resp.headers.get("content-disposition") or "").lower()
                    url = resp.url.lower()
                    is_sheet = any(x in (ct + cd + url) for x in (
                        "spreadsheet", "vnd.ms-excel", ".xlsx", ".xls", "excel"))
                    is_attach = "octet-stream" in ct and "attachment" in cd
                    if is_sheet or is_attach:
                        body = await resp.body()
                        if body and len(body) > 1024 and self._is_excel_bytes(body):
                            xhr["bytes"] = body
                            xhr["url"] = resp.url
                except Exception:
                    pass
            page.on("response", on_resp)
            got = None
            try:
                async with page.expect_download(timeout=30000) as dl:
                    clicked = await self._click_first_visible(page, [
                        "button[aria-label='הפק דוח']",
                        "button:has-text('הפק דוח')",
                        "button:has-text('הפקת דוח')",
                        "button[type='submit']:has-text('הפק')",
                    ], timeout=12000)
                    if not clicked:
                        raise RuntimeError("no-produce-trigger")
                d = await dl.value
                await d.save_as(str(out_path))
                if self._is_excel_file(out_path):
                    got = out_path
                else:
                    logger.warning("אנליסט: downloaded file is not valid Excel: %s", out_path.name)
            except Exception as native_err:
                import asyncio
                for _ in range(20):
                    if xhr["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr["bytes"]:
                    out_path.write_bytes(xhr["bytes"])
                    got = out_path
                else:
                    logger.warning("אנליסט: no valid download this attempt: %s", native_err)
            finally:
                page.remove_listener("response", on_resp)
            return got

        for (yy, mm) in self._target_months(date.today()):
            # A month RANGE with both ends on the same month — the pickers are
            # labelled מחודש / עד חודש, so "June" is expressed as June→June, not
            # June→July. (The old code sent the 1st of the NEXT month as the end,
            # which on a month picker selects the wrong month outright.)
            logger.info("אנליסט: trying report month %02d/%d", mm, yy)
            applied = await _set_range(yy, mm)
            await ck("nav_3_dates")

            # Encode the month in the filename ONLY when we confirmed the range
            # applied — otherwise the portal used its own default range and a
            # month-stamped name would mislabel it (detect_period_month is
            # filename-first). Neutral name → period is read from the content.
            out = download_dir / (f"אנליסט עמלות {mm:02d}-{yy}.xlsx" if applied
                                  else "אנליסט עמלות.xlsx")
            got = await _produce_download(out)

            if got and self._looks_nonempty(got):
                target, chosen_ym, range_confirmed = got, (yy, mm), applied
                break
            await ck("nav_3_empty_retry")
            # Walk back ONLY when we confirmed the range applied and the month was
            # empty. If the range never applied, retrying just re-downloads the same
            # default file under different names — take one diagnostic result and stop.
            if not applied:
                if got:  # a file came down; we just couldn't prove which month
                    target, chosen_ym, range_confirmed = got, (yy, mm), False
                break

        await ck("nav_4_after_export")
        if not target:
            # SHIP THE DOM, not a filename. `ck()` writes png/html/txt to the
            # WORKER's disk and `logger` writes the worker's local file — on an
            # agent's PC both are unreachable, so "בדוק …_nav_3_dates.txt" asks
            # for evidence nobody can retrieve without sitting at that machine.
            # This stage's whole problem is that its date-picker DOM was never
            # observed; a run that fails without reporting what it saw teaches
            # nothing and costs an OTP. Post a compact snapshot to the worker log
            # (Railway) so the selectors can be fixed from one failure.
            try:
                snap = await page.evaluate(
                    """() => ({
                        url: location.href,
                        sel: [...document.querySelectorAll('mat-select')].map(s => ({
                            a: s.getAttribute('aria-label') || '',
                            t: (s.innerText || '').trim().slice(0, 30)})),
                        // Capped: a form screen can carry a dozen inputs and
                        // crowd the links/text out of the note's length budget.
                        inp: [...document.querySelectorAll('input')]
                              .filter(e => e.offsetParent).slice(0, 12).map(e => ({
                                i: e.id, a: e.getAttribute('aria-label') || '',
                                p: e.placeholder || '', v: (e.value || '').slice(0, 12),
                                c: (e.className || '').slice(0, 35)})),
                        btn: [...document.querySelectorAll('button')]
                              .filter(e => e.offsetParent)
                              .map(b => ((b.innerText || '').trim().slice(0, 22)
                                         + (b.disabled ? '[off]' : ''))),
                        opt: [...document.querySelectorAll('mat-option,[role=option]')]
                              .map(o => (o.innerText || '').trim().slice(0, 26)),
                        // Links and page text. Their absence is why the first
                        // snapshot could not explain /lobby: it showed an
                        // agent-selection mat-select and two buttons, with no
                        // way to tell what the screen wanted next. On an SPA the
                        // route forward is usually an <a>, a nav item or a card
                        // — none of which are <button>.
                        a: [...document.querySelectorAll('a,[role=menuitem],mat-list-item,.nav-item')]
                            .filter(e => e.offsetParent)
                            .map(e => ((e.innerText || '').trim().slice(0, 24)
                                       + (e.getAttribute('href') ? '->' + e.getAttribute('href').slice(0, 28) : '')))
                            .filter(Boolean).slice(0, 25),
                        txt: (document.body.innerText || '')
                              .replace(/\\s*\\n+\\s*/g, ' | ').slice(0, 400),
                    })"""
                )
                from app.services.portal_automation.runner import _worker_note
                import json as _json
                _worker_note(
                    "analyst DOWNLOAD FAILED — dom: "
                    + _json.dumps(snap, ensure_ascii=False)[:2600]
                )
            except Exception as _e:
                try:
                    from app.services.portal_automation.runner import _worker_note
                    _worker_note(f"analyst DOWNLOAD FAILED — dom snapshot failed: {_e}")
                except Exception:
                    pass
            raise RuntimeError(
                f"אנליסט: לא ירד קובץ נפרעים תקין — בדוק "
                f"{run_id}_nav_2_report_type.txt / _nav_3_dates.txt / _nav_4_after_export.txt"
            )
        if not range_confirmed:
            msg = ("אנליסט: טווח התאריכים לא אומת (ריצה אבחונית) — הקובץ נשמר בשם ניטרלי "
                   "וזיהוי החודש נעשה מהתוכן. אמת את בורר התאריכים מ-nav_3_dates.txt")
            logger.warning(msg)
            self.partial_errors.append(msg)
        logger.info("אנליסט: downloaded %s (range_confirmed=%s)", target.name, range_confirmed)
        return [target]

    @staticmethod
    def _is_excel_bytes(b: bytes) -> bool:
        """True iff the bytes start with an Excel magic number: PK zip (.xlsx) or
        OLE2 (.xls). An HTML/JSON/text error page fails both."""
        return b[:4] == b"PK\x03\x04" or b[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    @staticmethod
    def _is_excel_file(path: Path) -> bool:
        try:
            return AnalystPortal._is_excel_bytes(path.read_bytes()[:8])
        except Exception:
            return False

    @staticmethod
    def _looks_nonempty(path: Path) -> bool:
        """Guard against ingesting an empty month OR an error-page blob as success.
        Magic-byte gate first (real .xlsx = PK zip, .xls = OLE2); anything else
        (HTML/JSON error page) is rejected so the walk-back keeps trying. For a valid
        xlsx, prefer a real row count but fall back to worksheet presence so a
        quirky-but-valid export (missing <dimension>) isn't falsely called empty."""
        try:
            head = path.read_bytes()[:8]
        except Exception:
            return False
        if head[:4] == b"PK\x03\x04":
            try:
                from openpyxl import load_workbook
                wb = load_workbook(str(path), read_only=True)
                ws = wb.active
                rows = ws.max_row
                wb.close()
                if rows is not None:
                    return rows > 1  # definitive count — trust it (header-only ⇒ empty)
                # rows is None → <dimension> missing; fall through to the zip check.
            except Exception:
                pass  # couldn't read as a workbook → fall through to the zip check
            try:
                import zipfile
                with zipfile.ZipFile(str(path)) as z:
                    return any(
                        n.startswith("xl/worksheets/") and z.getinfo(n).file_size > 400
                        for n in z.namelist()
                    )
            except Exception:
                return False
        if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return True  # legacy .xls (OLE2) — real Excel binary; let the parser read it
        return False  # not an Excel file (HTML/JSON/text)
