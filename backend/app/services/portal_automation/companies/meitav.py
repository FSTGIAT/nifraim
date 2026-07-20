"""מיטב דש (Meitav Dash) agent portal — login, OTP, commission download.

Login (https://customers.meitav.co.il/v2/login/LoginAgent) is an Angular SPA.
The operator logs in with **ת.ז (ID)** + **מספר פלאפון (phone)**; the portal then
SMS-OTPs that phone.

Credential convention:  ``username = "<id>"`` (ת"ז 40336281),
                        ``password = "<phone>"`` (פלאפון 504302306 → 0504302306).

Flow (operator):  right-side menu → **דוח עמלות לסוכן** → download to Excel. (There
is no separate "נפרעים" report — this agent-commission report IS the נפרעים data.)

The exact SPA selectors aren't knowable from the static HTML, so login/submit_otp/
download_reports use broad candidate-selector lists and dump
``<run_id>_*.{png,html,txt}`` aggressively. Refine the selectors from the FIRST
live run's `.txt` dumps (visible inputs / links / buttons) — re-running costs an
OTP, so fix selectors before the next run.

The downloaded דוח עמלות לסוכן format is confirmed against a real sample on the
first run; if `detect_format` misses it, add a `meitav` signature to
`hebrew_mappings.py` (company_source=מיטב דש). No parser change until then.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from playwright.async_api import Page

PORTAL_URL = "https://customers.meitav.co.il/v2/login/LoginAgent"


class MeitavPortal(BasePortalAutomation):
    portal_kind = "meitav"
    company_label = "מיטב דש"
    # Live-verified end-to-end 2026-06-29 (reCAPTCHA→OTP→report-builder→download→
    # meitav_nifraim parse, 9 records, May-2026). In the run-all batch. Runs on the
    # LOCAL WORKER (headed, warm profile) — reCAPTCHA blocks headless/Railway.
    include_in_batch = True
    # Login is gated by reCAPTCHA (grecaptcha on the page). Headless + UA-override
    # scored as a bot → server returns "נסה שנית" on a perfectly valid form. Same
    # cure as Mor: headed + native fingerprint + a persistent profile (reputation
    # survives across runs). Runs on the LOCAL WORKER (real desktop + IL IP).
    headed = True
    native_fingerprint = True
    use_persistent_profile = True
    needs_residential_proxy = False
    # MUST be Edge. Meitav's reCAPTCHA Enterprise refuses automated Chrome and
    # accepts automated Edge — measured 2026-07-20 twice each, same machine, same
    # minute, same fresh profile, same flow:
    #     msedge -> 200 {"actionTarget":"LoginCode","isFailed":false} + OTP screen
    #     chrome -> 401 {"message":"gCaptcha error"}  → the agent sees "נסה שנית"
    # The server names the cause itself, so this is not inference. The worker was
    # picking Chrome simply because it heads the default ladder, which is why
    # meitav failed on kiko's PC all day while the identical flow passed here.
    # Mor accepts both channels, hence a per-plugin preference and not a global
    # reorder. A PC without Edge still falls through the ladder.
    browser_channel = "msedge"

    def _split(self, username: str, password: str) -> tuple[str, str, str]:
        """username='<id>', password='<phone>'. Returns (id9, prefix3, local7).
        The Meitav form splits the mobile into a `prefixPhone` <select> (050…058)
        + a 7-digit `phoneNumber` input. ת"ז padded to 9; phone normalised to 10
        (operator stores 40336281 / 504302306, dropping the leading zero)."""
        id_no = re.sub(r"\D", "", username or "")
        phone = re.sub(r"\D", "", password or "")
        if len(id_no) == 8:
            id_no = "0" + id_no
        if len(phone) == 9 and not phone.startswith("0"):
            phone = "0" + phone        # 504302306 → 0504302306
        prefix = phone[:3]             # 050
        local7 = phone[3:][-7:]        # 4302306
        return id_no, prefix, local7


    async def _probe_recaptcha(self, page, label: str) -> str:
        """Is Google's reCAPTCHA ENTERPRISE script alive on THIS machine?

        Meitav loads `recaptcha/enterprise.js?render=6LehTw…` (sitekey also in the
        page as `globalParam.reCaptchaClient`). Enterprise puts its API at
        **`grecaptcha.enterprise.*`** — `grecaptcha.execute` is NOT defined.

        The previous version of this method checked `window.grecaptcha.execute`
        and read a `g-recaptcha-response` element, i.e. Mor's v3/v2 shape. Both
        readings are wrong here, and measurably so: reproduced locally against
        the real page on 2026-07-20 —

            has_grecaptcha=True  has_enterprise=True  plain_execute=False  tok=2148

        so the old probe reported `execute_ready=False` on a perfectly healthy
        page and then appended a user-facing line telling the agent their
        antivirus was blocking Google. That message was never once true. A
        diagnostic that manufactures its own false finding is worse than none —
        it sent real debugging effort at an imaginary firewall.

        Deliberately does NOT call `execute()`. Minting a token here would add a
        second 'login' assessment moments before the page's own on a
        SCORE-GATED portal — the diagnostic would be perturbing what it
        measures. Readiness alone answers "can this machine reach Google", which
        is the only question worth asking before the submit.

        Also reports `navigator.webdriver`: runner.py now clears it for every
        plugin, so anything other than False means the launch flags did not take
        effect on this machine. Never fails the run.
        """
        try:
            info = await page.evaluate(
                """() => {
                    const srcs = [...document.querySelectorAll('script[src]')]
                        .map(e => e.src).filter(u => u.includes('recaptcha'));
                    let key = '';
                    for (const u of srcs) {
                        const m = u.match(/[?&]render=([^&]+)/);
                        if (m && m[1] !== 'explicit') { key = m[1]; break; }
                    }
                    return {
                        scripts: srcs.length,
                        loaded: typeof window.grecaptcha !== 'undefined',
                        // Enterprise API surface — the one this portal uses.
                        ready: !!(window.grecaptcha && window.grecaptcha.enterprise
                                  && window.grecaptcha.enterprise.execute),
                        key: key,
                        wd: navigator.webdriver,
                    };
                }"""
            )
        except Exception as e:
            return f"probe failed: {e}"
        msg = (f"{label}: recaptcha ENTERPRISE scripts={info['scripts']} "
               f"loaded={info['loaded']} enterprise_ready={info['ready']} "
               f"sitekey={info['key'][:12] or 'NONE'} webdriver={info.get('wd')}")
        try:
            from app.services.portal_automation.runner import _worker_note
            _worker_note(msg)
        except Exception:
            pass
        # Claim a blocked machine ONLY when the script genuinely is not there.
        # `ready == False` alone must never trigger this: that is exactly the
        # false positive the old probe shipped.
        if not info["loaded"] and info["scripts"] == 0:
            self.partial_errors.append(
                f"{label}: סקריפט reCAPTCHA לא נטען כלל — ייתכן חסימה של google.com/recaptcha "
                "במחשב (אנטי-וירוס/פיירוול/DNS)."
            )
        return msg

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        id_no, prefix, local7 = self._split(username, password)

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        # WAIT FOR THE FORM TO HYDRATE — do not type into a screen Angular has
        # not painted. `domcontentloaded` returns before AngularJS bootstraps,
        # the networkidle wait above is swallowed, and the old code then slept a
        # fixed 2500ms and hoped. Total budget for the SPA was ~2.5s plus 4s on
        # the first selector; a slower bootstrap left the inputs absent and the
        # run died at the `לא נמצאו שדות ת"ז/טלפון` raise below — which reads
        # like a selector/DOM change but is really a race we lost. Live
        # 2026-07-20: two failures on a portal that is otherwise ~19% flaky, and
        # I twice blamed unrelated causes (a batch reorder, then Mor's reCAPTCHA)
        # before reading this. Same principle as ARCHITECTURE §11: never type
        # into a screen the host has not painted; poll for the pixels, don't
        # guess at the timing.
        _FORM_READY = (
            "input[name='identity'], input[placeholder*='תעודת זהות'], "
            "input[placeholder*='זהות']"
        )
        try:
            await page.wait_for_selector(_FORM_READY, state="visible", timeout=30000)
        except Exception:
            # Not fatal on its own — the selector ladder below still gets its
            # own attempts, and Meitav may legitimately rename a field. But say
            # so, so the failure is not misread as a DOM change again.
            self.partial_errors.append(
                "מיטב: טופס ההתחברות לא נצבע תוך 30 שניות — ייתכן טעינה איטית או שינוי בדף"
            )
            logger.warning("מיטב: login form did not hydrate within 30s at %s", page.url)
        # Small settle for Angular to attach its validators to the painted DOM.
        await page.wait_for_timeout(800)

        land = SCREENSHOT_ROOT / "meitav_login.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # Drive REAL keystrokes so Angular validation enables the submit button.
        async def _type(selectors: list[str], val: str, label: str) -> bool:
            for sel in selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=4000)
                except Exception:
                    continue
                try:
                    await page.click(sel)
                    await page.fill(sel, "")
                    await page.keyboard.type(val, delay=70)
                    cur = await page.input_value(sel)
                    if cur != val:  # retry once if a char dropped
                        await page.fill(sel, "")
                        await page.click(sel)
                        await page.keyboard.type(val, delay=90)
                    logger.info("מיטב: filled %s via %s", label, sel)
                    return True
                except Exception:
                    continue
            return False

        # Live DOM (run 6af823cb): AngularJS form `loginAgent` —
        #   input[name="identity"]   ת"ז (maxlength 9, ng-pattern digits)
        #   select[name="prefixPhone"] phone prefix (050…058)
        #   input[name="phoneNumber"]  7-digit local number (ng-pattern /^\d{7}$/)
        #   button#submit "אישור" ng-click=makeLogin(), ng-disabled until valid.
        id_ok = await _type([
            "input[name='identity']",
            "input[placeholder*='תעודת זהות']",
            "input[placeholder*='זהות']",
        ], id_no, "ת\"ז")

        # Phone prefix is a real <select> — pick the option by value (050…).
        prefix_ok = False
        for sel in ("select[name='prefixPhone']", "select[ng-model='prefixPhone']"):
            try:
                await page.select_option(sel, prefix, timeout=4000)
                prefix_ok = True
                logger.info("מיטב: prefix %s via %s", prefix, sel)
                break
            except Exception:
                continue

        phone_ok = await _type([
            "input[name='phoneNumber']",
            "input[ng-model='phoneNumber']",
            "input[placeholder*='טלפון']",
        ], local7, "טלפון")

        if not (id_ok and phone_ok):
            raise RuntimeError(
                "מיטב: לא נמצאו שדות ת\"ז/טלפון בטופס ההתחברות — בדוק meitav_login.txt/html"
            )
        if not prefix_ok:
            logger.warning("מיטב: לא נבחר קידומת טלפון — ייתכן שכפתור האישור יישאר מושבת")
        await self._probe_recaptcha(page, "meitav")

        # Blur so AngularJS ng-blur validation runs and enables #submit.
        try:
            await page.keyboard.press("Tab")
        except Exception:
            pass
        await page.wait_for_timeout(600)

        clicked = await self._click_first_visible(page, [
            "button#submit:not([disabled])",
            "button[ng-click='makeLogin()']:not([disabled])",
            "button:has-text('אישור'):not([disabled])",
            "button[type='submit']:not([disabled])",
        ], timeout=10000)
        if not clicked:
            # Capture why the button is still disabled (which ng field is invalid).
            try:
                state = await page.evaluate(
                    """() => {const b=document.querySelector('#submit');
                        return b ? {disabled:b.disabled, text:(b.innerText||'').trim()} : null;}"""
                )
            except Exception:
                state = None
            raise RuntimeError(
                f"מיטב: כפתור 'אישור' לא נמצא או מושבת ({state}) — בדוק meitav_login.txt"
            )

        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "meitav_after_send.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

        # Wait for the OTP screen (a short numeric field or a segmented group) OR
        # an error toast, so we fail fast on bad creds.
        otp_sel = (
            "input[formcontrolname*='otp' i], input[name*='otp' i], "
            "input[formcontrolname*='code' i], input[name*='code' i], "
            "input[autocomplete='one-time-code'], input[placeholder*='קוד'], "
            "input[type='tel'][maxlength='1']"
        )
        # NOTE: AngularJS keeps validation-message templates in the DOM always
        # (toggled via ng-hide → display:none). An earlier version matched their
        # TEXT regardless of visibility and false-aborted a perfectly valid login
        # (run 7f3f688b: all fields ng-valid, yet "ת"ז שגוי" hidden text matched).
        # Only treat a VISIBLE error (offsetParent !== null) as a real rejection.
        for _ in range(60):  # ~30s
            try:
                if await page.locator(otp_sel).count() and \
                        await page.locator(otp_sel).first.is_visible():
                    return
            except Exception:
                pass
            try:
                err = await page.evaluate(
                    """() => [...document.querySelectorAll('.error,.toast,.alert,[class*=error i],[class*=Error]')]
                        .filter(e => e.offsetParent !== null && e.getClientRects().length)
                        .map(e => (e.innerText||'').trim()).filter(Boolean).join(' | ').slice(0,300)"""
                )
            except Exception:
                err = ""
            if err and any(w in err for w in ("שגוי", "שגיא", "לא נמצא", "נסה", "נדח")):
                raise RuntimeError(f"מיטב: הכניסה נדחתה — {err}")
            await page.wait_for_timeout(500)
        # Didn't clearly transition — let the runner await OTP anyway; submit_otp
        # re-detects the field. The dump above is the diagnostic.

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")

        filled = False
        # Case A: segmented single-char boxes.
        try:
            boxes = page.locator("input[type='tel'][maxlength='1']:visible, "
                                 "input[maxlength='1']:visible")
            n = await boxes.count()
            if 0 < n <= len(digits) + 2:
                for i in range(min(n, len(digits))):
                    b = boxes.nth(i)
                    await b.click()
                    await b.fill("")
                    await page.keyboard.type(digits[i], delay=60)
                filled = True
        except Exception:
            pass
        # Case B: a single OTP input.
        if not filled:
            for sel in (
                "input[formcontrolname*='otp' i]",
                "input[name*='otp' i]",
                "input[formcontrolname*='code' i]",
                "input[name*='code' i]",
                "input[autocomplete='one-time-code']",
                "input[placeholder*='קוד']",
            ):
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=3000)
                    await page.click(sel)
                    await page.keyboard.type(digits, delay=70)
                    filled = True
                    break
                except Exception:
                    continue

        await page.wait_for_timeout(400)
        await self._click_first_visible(page, [
            "button:has-text('אישור')",
            "button:has-text('כניסה')",
            "button:has-text('התחבר')",
            "button:has-text('המשך')",
            "button:has-text('כניסה למערכת')",
            "button[type='submit']:not([disabled])",
            "input[type='submit']",
        ], timeout=6000)

        try:
            await page.wait_for_url(
                lambda u: "login" not in (u or "").lower(), timeout=25000
            )
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "meitav_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("מיטב: לא נמצא שדה OTP — בדוק meitav_after_send.txt")

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

        await ck("nav_0_home")

        # 1) Right-side menu → "דוח עמלות לסוכן חדש" (live label carries "חדש";
        #    lands on …/agent/mainagent/agentamlot, title "מיטב - עמלות סוכנים").
        await self._click_first_visible(page, [
            "a:has-text('דוח עמלות לסוכן חדש')",
            "a:has-text('דוח עמלות לסוכן')",
            "[role='menuitem']:has-text('דוח עמלות לסוכן')",
            "li:has-text('דוח עמלות לסוכן')",
            "a:has-text('עמלות לסוכן')",
            "a:has-text('דוח עמלות')",
            "*:has-text('דוח עמלות לסוכן')",
        ], timeout=15000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(1800)
        await ck("nav_1_report")

        # 1.5) The עמלות page is a React/MUI report-BUILDER with FOUR required-ish
        #      controls then a "הצג דוחות" <div> that GENERATES the report:
        #        #selectedAgent   (Autocomplete) — בחר סוכן
        #        #selectReportType (MUI Select)  — בחר סוג דוח
        #        #selectedYear     (MUI Select)  — בחר שנה
        #        #selectedMonth    (MUI Select)  — בחר חודש
        #      The export only appears after the grid renders. We LOG every option
        #      so one run reveals them all.
        async def _open_and_options(trigger_sel: str) -> list[str]:
            """Open a MUI Select/Autocomplete and return its visible option texts."""
            try:
                await page.click(trigger_sel, timeout=4000)
            except Exception:
                return []
            await page.wait_for_timeout(700)
            try:
                opts = page.locator("li[role='option']:visible, "
                                    ".MuiAutocomplete-option:visible, "
                                    "ul[role='listbox'] li:visible")
                n = await opts.count()
                texts = []
                for i in range(min(n, 60)):
                    try:
                        texts.append((await opts.nth(i).inner_text()).strip())
                    except Exception:
                        pass
                return texts
            except Exception:
                return []

        async def _pick(trigger_sel: str, label: str, prefer: list[str] | None,
                        pick_last: bool = False) -> None:
            opts = await _open_and_options(trigger_sel)
            logger.warning("מיטב [%s] options: %s", label, opts[:30])
            if not opts:
                return
            idx = 0
            if prefer:
                for i, t in enumerate(opts):
                    if any(p in t for p in prefer):
                        idx = i
                        break
                else:
                    idx = len(opts) - 1 if pick_last else 0
            elif pick_last:
                idx = len(opts) - 1
            cell = page.locator("li[role='option']:visible, .MuiAutocomplete-option:visible, "
                                "ul[role='listbox'] li:visible").nth(idx)
            try:
                await cell.click(timeout=4000)
            except Exception:
                await page.keyboard.press("Enter")
            await page.wait_for_timeout(600)

        # agent: the autocomplete filters by NAME, not the ת"ז (typing 40336281 →
        # "No options"). Open it empty first; if it shows options, pick the first
        # (the agent's own name). Otherwise scrape the agent name from the page
        # header ("ערב טוב <NAME>, ת.ז. …") and type it to narrow.
        async def _agent_options():
            o = page.locator("li[role='option']:visible, .MuiAutocomplete-option:visible")
            return o, await o.count()
        try:
            await page.click("#selectedAgent", timeout=4000)
            await page.fill("#selectedAgent", "")
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(900)
            o, n = await _agent_options()
            if not n:
                # Scrape the logged-in agent's name and type it.
                name = await page.evaluate(
                    r"""() => {const t=document.body.innerText;
                        const m=t.match(/(?:ערב טוב|בוקר טוב|צהריים טובים|לילה טוב|שלום)\s+([^,|]+?)\s*,?\s*ת\.?ז/);
                        return m ? m[1].trim() : '';}"""
                )
                logger.warning("מיטב: agent name scraped = %r", name)
                # The option reorders the name + prefixes an agent code
                # ("(2-11225) -משה היב כהן"), so type only the FIRST word (a stable
                # substring) to filter rather than the full reordered string.
                first_word = name.split()[0] if name else ""
                if first_word:
                    await page.click("#selectedAgent")
                    await page.fill("#selectedAgent", "")
                    await page.keyboard.type(first_word, delay=90)
                    await page.wait_for_timeout(1200)
                    o, n = await _agent_options()
            if n:
                await o.first.click()
                logger.warning("מיטב: agent selected (%d options)", n)
            else:
                logger.warning("מיטב: agent dropdown still empty — בדוק nav_1a_filled")
        except Exception as e:
            logger.warning("מיטב: agent select failed: %s", e)
        await page.wait_for_timeout(700)

        # report type: CONFIRMED = "נפרעים חודשי גמל והשתלמות" (operator). Prefer the
        # most specific match first, then looser נפרעים/עמלות fallbacks.
        await _pick("#selectReportType", "סוג דוח",
                    prefer=["נפרעים חודשי גמל", "גמל והשתלמות", "נפרעים", "נפרע",
                            "עמלות", "עמלה"], pick_last=False)
        # year + month: the latest reported period (operator picks last).
        await _pick("#selectedYear", "שנה", prefer=None, pick_last=True)
        await _pick("#selectedMonth", "חודש", prefer=None, pick_last=True)
        await ck("nav_1a_filled")

        # Click "הצג דוחות" (a bare <div>) — exact-text leaf click.
        shown = False
        for sel in ("div:text-is('הצג דוחות')", "button:text-is('הצג דוחות')",
                    "*:text-is('הצג דוחות')", "div:has-text('הצג דוחות')",
                    "button:has-text('הצג')"):
            try:
                loc = page.locator(sel).last
                if await loc.count() and await loc.is_visible():
                    await loc.click(timeout=4000)
                    shown = True
                    break
            except Exception:
                continue
        if not shown:
            logger.warning("מיטב: לא נמצא 'הצג דוחות' — בדוק nav_1a_filled.txt")
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)
        await ck("nav_1b_shown")

        # 2) Export to Excel — native download OR XHR bytes capture.
        target = download_dir / "מיטב דש עמלות לסוכן.xlsx"
        xhr = {"bytes": None, "url": None}

        async def on_resp(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                if any(x in (ct + cd + url) for x in (
                    "spreadsheet", "vnd.ms-excel", ".xlsx", ".xls", "excel", "octet-stream",
                )) and xhr["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr["bytes"] = body
                        xhr["url"] = resp.url
            except Exception:
                pass
        page.on("response", on_resp)

        got = None
        try:
            async with page.expect_download(timeout=30000) as dl:
                clicked = await self._click_first_visible(page, [
                    # CONFIRMED export trigger (operator-supplied DOM): a bare
                    # <div class="resDownload">להורדת הקובץ</div> that appears once
                    # "הצג דוחות" renders the report.
                    "div.resDownload",
                    "div:has-text('להורדת הקובץ')",
                    ".resDownload",
                    "*:text-is('להורדת הקובץ')",
                    "button:has-text('ייצוא לאקסל')",
                    "a:has-text('ייצוא לאקסל')",
                    "button:has-text('יצוא לאקסל')",
                    "button:has-text('הורד לאקסל')",
                    "button:has-text('ייצוא לאקס')",
                    "button:has-text('הורדה לאקסל')",
                    "button:has-text('אקסל')",
                    "a:has-text('אקסל')",
                    "button:has-text('ייצוא')",
                    "button:has-text('הורדה')",
                    "button:has-text('הורד')",
                    "[title*='אקסל']",
                    "[title*='Excel' i]",
                    "[aria-label*='אקסל']",
                    "[aria-label*='ייצוא']",
                    "img[src*='excel' i]",
                    "img[src*='xls' i]",
                    "[class*='excel' i]",
                    "mat-icon:has-text('file_download')",
                ], timeout=12000)
                if not clicked:
                    raise RuntimeError("no-export-trigger")
            d = await dl.value
            await d.save_as(str(target))
            got = target
        except Exception as native_err:
            import asyncio
            for _ in range(20):
                if xhr["bytes"]:
                    break
                await asyncio.sleep(0.5)
            if xhr["bytes"]:
                target.write_bytes(xhr["bytes"])
                got = target
            else:
                await ck("nav_2_no_download")
                raise RuntimeError(
                    f"מיטב: לא ירד קובץ מ-{page.url}. בדוק {run_id}_nav_1_report.txt / "
                    f"_nav_2_no_download.txt : {native_err}"
                )
        finally:
            page.remove_listener("response", on_resp)

        await ck("nav_2_after_export")
        if not got:
            raise RuntimeError(
                f"מיטב: לא ירד קובץ — בדוק {run_id}_nav_1_report.txt / _nav_2_after_export.txt"
            )
        return [got]
