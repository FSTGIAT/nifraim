"""Hachshara (הכשרה) agent portal — login, OTP, download נפרעים (commission) report.

F5 BIG-IP APM at `agents-login.hcsra.co.il/my.policy`. Shares the APM login
form with Phoenix, Clal, Migdal-APM (see `_apm_helpers.py`).

Operator nav (live): right menu → **דוחות** → scroll to **עמלות** → open the
**בסט אינווסט** (Best Invest) window/חלונית → pick the agent (**הכל**) → pick
**חודש עיבוד** → **הורד ל excel**.

The חודש עיבוד step is not optional. Skipping it exports every client the agent
has ever had instead of the ones still under them that month, and the result is
a well-formed file that passes every downstream check — so the export is also
verified against the month before it is accepted (`verify_processing_month`).
The Best-Invest step may open a NEW TAB (handled via context.expect_page, same
pattern as Clal's infobay). Downloaded file = `hachshara_nifraim` format
(company_source=הכשרה, commission) — no parser changes.

Selectors are best-effort against the operator's described path; refine from the
`<run_id>_<step>.txt` dumps after the first live run.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation, reporting_months

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://agents-login.hcsra.co.il/my.policy"

# הכשרה publishes a processing month on the 21st of the following month, so the
# newest PUBLISHED month is two back before the 21st and one back on/after it:
#   run 14/09/2026 -> חודש עיבוד 07/2026      run 21/09/2026 -> 08/2026
CYCLE_CUTOFF_DAY = 21

# The column the export carries the processing month in. Live files spell it with
# a TRAILING SPACE ("תאריך עיבוד ") and hold strings like "01/2026", so match on a
# stripped substring, never on equality.
PROCESSING_MONTH_COL = "תאריך עיבוד"

_HEB_MONTHS = (
    "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
)


def _cell_month(val) -> tuple[int, int] | None:
    """(year, month) out of one תאריך עיבוד cell, or None if unreadable.

    Live files hold the string "MM/YYYY"; openpyxl can also hand back a real
    datetime, and other exports of the same report use "DD/MM/YYYY".
    """
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.year, val.month
    text = str(val).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None

    # ISO-ish "2026-01" / "2026-01-15" -> year first
    m = re.match(r"^(\d{4})[-/.](\d{1,2})(?:[-/.]\d{1,2})?$", text)
    if m:
        y, mm = int(m.group(1)), int(m.group(2))
        return (y, mm) if 1 <= mm <= 12 else None

    # "MM/YYYY", "MM-YYYY", "DD/MM/YYYY"
    parts = [p for p in re.split(r"[-/.\s]+", text) if p.isdigit()]
    if len(parts) == 2:
        mm, y = int(parts[0]), int(parts[1])
    elif len(parts) == 3:
        mm, y = int(parts[1]), int(parts[2])
    else:
        return None
    if y < 100:
        y += 2000
    return (y, mm) if 1 <= mm <= 12 and 1900 < y < 2200 else None


def verify_processing_month(df, year: int, month: int) -> tuple[bool, str]:
    """Is this export really ONE processing month, and the one we asked for?

    Returns (ok, reason). `reason` is a Hebrew operator-facing message when not ok.

    This is the guard for the bug that made it necessary (2026-09): with no month
    selected, the report exports EVERY client the agent has ever had instead of
    the ones still under them that month, and it sails through every other check
    - the 1 KB size gate, the column-name signature, record_count, the runner.
    Kept a pure function over a DataFrame so it is testable without a portal.
    """
    col = next(
        (c for c in df.columns if PROCESSING_MONTH_COL in str(c).strip()), None
    )
    if col is None:
        return False, (
            f"בקובץ אין עמודת '{PROCESSING_MONTH_COL}' - "
            f"נמצאו: {', '.join(str(c).strip() for c in list(df.columns)[:12])}"
        )

    seen: dict[tuple[int, int], int] = {}
    unreadable = 0
    for val in df[col].tolist():
        ym = _cell_month(val)
        if ym is None:
            unreadable += 1
        else:
            seen[ym] = seen.get(ym, 0) + 1

    total = sum(seen.values())
    if total == 0:
        return False, (
            "הקובץ שהתקבל ריק - אין אף שורת נתונים עם תאריך עיבוד "
            f"(שורות בקובץ: {len(df)}, לא ניתן לפענח: {unreadable})"
        )

    want = (year, month)
    others = {ym: n for ym, n in seen.items() if ym != want}
    if others:
        got = ", ".join(
            f"{m:02d}/{y} ({n} שורות)"
            for (y, m), n in sorted(others.items(), reverse=True)[:6]
        )
        return False, (
            f"הדוח לא סונן לחודש {month:02d}/{year} - הקובץ מכיל גם: {got}. "
            "זה הסימן ש'חודש עיבוד' לא נבחר בפועל והדוח החזיר את כל הלקוחות "
            "שהיו אי פעם אצל הסוכן."
        )
    return True, ""



class HachsharaPortal(BasePortalAutomation):
    portal_kind = "hachshara"
    company_label = "הכשרה"
    # Run headed: the נפרעים report is an Angular-Material page whose autocomplete
    # ("הכל") + "הורד ל excel" force-click were verified headed on the local
    # worker (like Mor). Flip to False only after a headless live-verify.
    headed = True

    async def login(self, page: "Page", username: str, password: str) -> None:
        # Hachshara wants the 9-digit username (leading-zero padded): 40336281 →
        # 040336281. Without the 0 the F5 form accepts the POST but login fails
        # (no OTP is sent → the OTP screen never appears).
        username = (username or "").strip()
        if len(username) == 8 and not username.startswith("0"):
            username = "0" + username

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1500)

        # F5 BIG-IP stale-session recovery. Two screens block the logon form:
        #   1. errorcode-19 bounce (my.logout.php3?errorcode=19).
        #   2. "זמן החיבור פג תוקף" interstitial — seen when re-running within ~30
        #      min: the prior F5 session is STILL ALIVE. Its only control is a
        #      **"חיבור חדש"** link (href="/").
        # CRITICAL: the expiry page ALSO renders `input#text` — the SAME selector
        # as Hachshara's OTP field — so naively waiting for the OTP input is a FALSE
        # positive: we'd report login-OK and then sit on awaiting_otp for a code the
        # insurer never sent (the login was never actually submitted). The reliable
        # cure for a live stale session is to CLEAR COOKIES (kills the F5 session) so
        # a clean logon form is served, then re-enter credentials. We also verify we
        # truly LEFT the expiry screen before trusting the OTP field.
        async def _blocked():
            try:
                body = (await page.inner_text("body"))[:1500]
            except Exception:
                body = ""
            expired = any(t in body for t in ("זמן החיבור", "פג תוקף", "פג זמן", "החיבור פג"))
            return expired or "errorcode" in page.url or "logout" in page.url

        for _ in range(5):
            has_user = await page.locator("input[name='username']").count()
            if has_user and not await _blocked():
                break
            # Kill the stale session so the logon form (not the expiry screen) loads,
            # click any recovery link, then reload PORTAL_URL fresh.
            try:
                await page.context.clear_cookies()
            except Exception:
                pass
            await self._click_first_visible(page, [
                "a:has-text('חיבור חדש')", "a:has-text('חיבור מחדש')",
                "button:has-text('חיבור מחדש')", "a:has-text('התחבר מחדש')",
                "a:has-text('לחץ כאן')", "input[value*='חיבור']",
            ], timeout=4000)
            try:
                await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)

        # Fill + submit ourselves (the shared apm_login_submit's normal click on
        # the submit input TIMES OUT here — the `input[type=submit]` value=התחברות
        # is present+visible but not click-actionable, it's covered). Submit via
        # Enter in the password field (canonical F5 POST form), force-click fallback.
        async def _fill_and_submit():
            await self._wait_visible(page, "input[name='username']", timeout=15000)
            await page.fill("input[name='username']", username)
            await page.fill("input[name='password']", password)
            try:
                await page.press("input[name='password']", "Enter")
            except Exception:
                pass
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            if await page.locator("input[name='username']").count():
                try:
                    await page.click("input[type='submit']", force=True, timeout=4000)
                except Exception:
                    pass

        await _fill_and_submit()

        # If the submit landed back on the expiry/errorcode screen, the login didn't
        # take (stale session) — clear cookies and redo it ONCE on a fresh form.
        if await _blocked():
            try:
                await page.context.clear_cookies()
            except Exception:
                pass
            await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1500)
            await _fill_and_submit()

        await self._wait_visible(page, self._OTP_SEL, timeout=20000)
        # Guard against the false positive: the expiry page carries input#text too.
        # If we're still on it, fail fast + clearly instead of a misleading 5-min
        # "no OTP" timeout (the code was never sent).
        if await _blocked():
            raise RuntimeError(
                "הכשרה: נותרנו במסך 'זמן החיבור פג תוקף' אחרי התחברות — הסשן הישן לא נוקה "
                "(לא נשלח OTP). נסו שוב בעוד מספר דקות."
            )

    # Hachshara's OTP input is name="text"/id="text" ("קוד חד פעמי"), NOT the usual
    # otp/code/answer names. Keep the others as fallbacks.
    _OTP_SEL = (
        "input#text, input[name='text'], input[name='otp'], "
        "input[autocomplete='one-time-code'], input[name='code'], input[name='answer']"
    )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(self._OTP_SEL, otp)
        # Same F5 form: the submit input isn't click-actionable → press Enter in the
        # OTP field, force-click fallback.
        try:
            await page.press(self._OTP_SEL, "Enter")
        except Exception:
            pass
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        if await page.locator(self._OTP_SEL).count():
            try:
                await page.click("input[type='submit']", force=True, timeout=4000)
            except Exception:
                pass
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        # Detect a rejected OTP fast (don't proceed to the nav on a not-logged-in
        # page). The F5 re-renders the OTP screen with "שם המשתמש או הסיסמא שגויים"
        # — usually a STALE/expired code: the phone's SMS forwarder batched an old
        # OTP (Doze) and it was consumed instead of the current one. Reinstall the
        # immediate-forward APK + disable battery optimization (see sms_forward_immediate).
        try:
            body = (await page.inner_text("body"))[:1500]
        except Exception:
            body = ""
        if "שגוי" in body or "נסה שנית" in body or "נסה שוב" in body:
            raise RuntimeError(
                "Hachshara: קוד ה-OTP נדחה (\"שם המשתמש או הסיסמא שגויים\") — ככל "
                "הנראה קוד ישן/פג תוקף שהועבר ב-batch. ודא שאפליקציית Nifraim SMS "
                "מעבירה כל SMS מיידית (התקן מחדש את ה-APK + בטל אופטימיזציית סוללה)."
            )

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        self.report_password = None

        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)
        # Provisional name. The month is stamped on only AFTER the file is
        # verified to contain it (see the rename below) - `detect_period_month`
        # reads the filename FIRST, so a month in the name must be a statement
        # about the contents, never about what we asked for.
        target = download_dir / "הכשרה נפרעים.xlsx"

        async def ck(tag: str):
            p = SCREENSHOT_ROOT / f"{run_id}_{tag}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        # Excel XHR sniffer — fallback if the "הורד ל excel" button streams the
        # bytes via XHR instead of a native browser download.
        xhr_capture: dict = {"bytes": None, "url": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel = (
                    "spreadsheetml" in ct or "vnd.ms-excel" in ct
                    or "octet-stream" in ct
                    or ".xlsx" in url or ".xlsx" in cd or ".xls" in cd
                )
                if is_excel and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
            except Exception:
                pass

        page.on("response", _on_response)
        await ck("post_otp")

        # ── Navigation: verified hops, not fire-and-forget ────────────────
        # Live failure 2026-07-24 (batch 3c0b055f): the SPA booted slowly after
        # OTP, every _click_first_visible timed out SILENTLY, and the run died
        # much later at "no-download-trigger-visible" with url = the site ROOT —
        # blaming the wrong step. Each hop below verifies the URL actually
        # advanced, retries, and fails loudly AT THAT STEP. Re-verified live
        # 2026-07-24: the flow itself is unchanged (menu → /reports → tile →
        # report form → הכל → הורד ל excel), but the report id changed (66→152),
        # so match /reports/<digits>, never a fixed id.
        import re as _re

        # 0) slow-boot gate: wait for the sidebar to actually render
        try:
            await page.wait_for_selector(
                "span:has-text('דוחות'), a:has-text('דוחות')",
                state="visible", timeout=45000,
            )
        except Exception:
            await ck("nav0_spa_not_ready")
            raise RuntimeError(
                f"Hachshara: התפריט לא נטען אחרי ההתחברות ({page.url}) — "
                f"בדוק {run_id}_nav0_spa_not_ready.txt"
            )

        # 1) right menu → דוחות — must land on /reports
        for _ in range(3):
            await self._click_first_visible(page, [
                "span:has-text('דוחות')", "a:has-text('דוחות')",
                "button:has-text('דוחות')", "*:has-text('דוחות'):visible",
            ], timeout=10000)
            try:
                await page.wait_for_url(lambda u: "/reports" in (u or ""), timeout=8000)
                break
            except Exception:
                await page.wait_for_timeout(1500)
        await ck("nav1_dohot")
        if "/reports" not in (page.url or ""):
            raise RuntimeError(
                f"Hachshara: הקליק על 'דוחות' לא ניווט (עדיין ב-{page.url}) — "
                f"בדוק {run_id}_nav1_dohot.txt"
            )

        # 2) עמלות section header — its tiles render below the fold, scroll to it
        for sel in ("h5:has-text('עמלות')", "*:has-text('עמלות'):visible"):
            loc = page.locator(sel).first
            try:
                if await loc.count():
                    await loc.scroll_into_view_if_needed(timeout=2500)
                    break
            except Exception:
                continue
        await self._click_first_visible(page, [
            "h5:has-text('עמלות')", "a:has-text('עמלות')", "*:has-text('עמלות'):visible",
        ], timeout=8000)
        await page.wait_for_timeout(1200)
        await ck("nav2_amlot")

        # 3) "בסט אינווסט-עמלות נפרעים" tile — must land on /reports/<id>
        for _ in range(2):
            await self._click_first_visible(page, [
                "p:has-text('בסט אינווסט'):has-text('נפרעים')",
                "p:has-text('בסט אינווסט')",
                "*:has-text('בסט אינווסט'):visible",
                "a:has-text('נפרעים')",
            ], timeout=8000)
            try:
                await page.wait_for_url(
                    lambda u: bool(_re.search(r"/reports/\d+", u or "")), timeout=10000)
                break
            except Exception:
                await page.wait_for_timeout(1500)
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await ck("nav3_nifraim")
        if not _re.search(r"/reports/\d+", page.url or ""):
            raise RuntimeError(
                f"Hachshara: אריח 'בסט אינווסט-עמלות נפרעים' לא נפתח (עדיין ב-{page.url}) — "
                f"בדוק {run_id}_nav2_amlot.txt / _nav3_nifraim.txt"
            )

        # 3b) the report form renders lazily (measured ~8s+ live 2026-07-24) —
        # wait for the agent autocomplete / excel button before touching it.
        try:
            await page.wait_for_selector(
                "#mat-input-0, input[placeholder*='פיננסי סוכן'], "
                "button:has-text('הורד ל excel'), i.mdi-microsoft-excel",
                state="visible", timeout=60000,
            )
        except Exception:
            await ck("nav3b_form_not_rendered")
            raise RuntimeError(
                f"Hachshara: טופס הדוח לא נטען ב-{page.url} — "
                f"בדוק {run_id}_nav3b_form_not_rendered.txt"
            )
        await page.wait_for_timeout(1000)

        # 4) agent financial-number autocomplete (#mat-input-0, placeholder
        #    "בחר מספר פיננסי סוכן") → pick the **הכל** (ALL) option. WITHOUT this
        #    the grid stays empty and only the column headers export.
        agent = page.locator(
            "#mat-input-0, input[placeholder*='פיננסי סוכן'], input[placeholder*='בחר מספר']"
        ).first
        try:
            await agent.click()
            await page.wait_for_timeout(1000)
            picked = await self._click_first_visible(page, [
                "mat-option:has-text('הכל')", "[role='option']:has-text('הכל')",
                ".mat-option:has-text('הכל')",
            ], timeout=5000)
            if not picked:
                await agent.press("ArrowDown")
                await page.wait_for_timeout(600)
                await self._click_first_visible(page, [
                    "mat-option:has-text('הכל')", "mat-option", "[role='option']",
                ], timeout=4000)
            # Close the mat-autocomplete panel — its cdk-overlay backdrop otherwise
            # intercepts the subsequent "הורד ל excel" click (the observed "selects
            # הכל but never presses download" bug). Then let the grid load.
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        await ck("nav4_agent_all")

        # 4b) חודש עיבוד (processing month) — THE step this flow was missing.
        #
        # Without it the report exports EVERY client the agent has ever had
        # rather than the ones still under them that month (live 2026-09-14), and
        # nothing downstream notices: the file is well-formed, the columns match
        # the signature, and the run reports success. kikohib's count had drifted
        # 350 → 356 → 362 across runs, which is what an accumulating
        # all-clients-ever export looks like.
        #
        # 🚫 NEVER "pick the newest option" here. Unlike Altshuler's
        # `_select_mat_last` (altshuler.py:570), whose dropdowns only list months
        # that HAVE data, this list offers a month before its cycle has published
        # it: on 14/09/2026 it shows 08/2026, but the 21/09 cycle has not run, so
        # the correct choice is 07/2026. Taking the last option downloads a thin
        # or empty report that still looks like a successful run. Compute the
        # month, then step BACKWARD only.
        candidates = reporting_months(date.today(), CYCLE_CUTOFF_DAY)
        picked_month: tuple[int, int] | None = None

        month_input = page.locator(
            "input[placeholder*='חודש עיבוד'], input[aria-label*='חודש עיבוד']"
        ).first
        # Anchored on the placeholder, never on #mat-input-N: those ids are
        # positional (the live field is #mat-input-14) and shift as the form grows.
        if not await month_input.count():
            await ck("nav4b_month_field_missing")
            raise RuntimeError(
                f"Hachshara: לא נמצא שדה 'חודש עיבוד' בטופס ({page.url}) — "
                f"בדוק {run_id}_nav4b_month_field_missing.txt"
            )

        # The agent picker above ends its Escape INSIDE a bare `except: pass`, so a
        # failure there leaves the cdk-overlay backdrop up — and it would swallow
        # this field's click exactly the way it swallows the export button. Clear
        # it unconditionally rather than inheriting that step's luck.
        for _ in range(3):
            if not await page.locator(".cdk-overlay-backdrop").count():
                break
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)

        async def _month_options():
            """Locator for THIS field's options, never the whole page.

            `mat-option` is page-global: if another panel is open (the agent
            autocomplete) its financial numbers are digit strings too, and a
            digits-only comparison could match one by coincidence — clicking the
            wrong list and reporting "did not stick". Angular Material points the
            input at its own panel via aria-owns/aria-controls, so use that.
            """
            for attr in ("aria-owns", "aria-controls"):
                try:
                    panel_id = await month_input.get_attribute(attr)
                except Exception:
                    panel_id = None
                if panel_id:
                    pid = panel_id.split()[0]
                    loc = page.locator(f"#{pid} mat-option, #{pid} [role='option']")
                    if await loc.count():
                        return loc
            # Fallback: the visible overlay pane (only one is open at a time here).
            loc = page.locator(
                ".cdk-overlay-pane:visible mat-option, .cdk-overlay-pane:visible [role='option']"
            )
            return loc if await loc.count() else page.locator("mat-option, [role='option']")

        options = page.locator("mat-option, [role='option']")  # rebound per open

        async def _open_panel() -> list[str]:
            """Open the dropdown and return its option labels, top to bottom."""
            nonlocal options
            await month_input.click()
            await page.wait_for_timeout(1200)
            options = await _month_options()
            if not await options.count():
                await month_input.press("ArrowDown")
                await page.wait_for_timeout(800)
                options = await _month_options()
            out: list[str] = []
            for i in range(await options.count()):
                try:
                    out.append(((await options.nth(i).inner_text()) or "").strip())
                except Exception:
                    out.append("")
            return out

        def _match(labels: list[str], want: tuple[int, int]) -> int | None:
            """Index of the option meaning (year, month), or None.

            Compares on digits only, so 07/2026, 07-2026, 072026 and 07.2026 all
            match; Hebrew month names ("יולי 2026") are matched separately.
            """
            y, m = want
            numeric = {f"{m:02d}{y}", f"{m}{y}", f"{y}{m:02d}"}
            for idx, text in enumerate(labels):
                if re.sub(r"\D", "", text) in numeric:
                    return idx
                if _HEB_MONTHS[m] and f"{_HEB_MONTHS[m]} {y}" in text:
                    return idx
            return None

        def _applied_is(value: str, want: tuple[int, int]) -> bool:
            y, m = want
            if re.sub(r"\D", "", value) in {f"{m:02d}{y}", f"{m}{y}", f"{y}{m:02d}"}:
                return True
            return bool(_HEB_MONTHS[m]) and _HEB_MONTHS[m] in value

        # Re-open the panel for every candidate: clicking an option CLOSES it, so
        # a second attempt against the first attempt's locators would click a
        # detached node and look like a silent miss.
        labels: list[str] = []
        for want in candidates:
            labels = await _open_panel()
            if want is candidates[0]:
                # Log every option once. The label format is only known from live
                # runs, and this line is the evidence that a NEWER month was on
                # offer and was deliberately skipped.
                print(f"[hachshara] חודש עיבוד options ({len(labels)}): {labels}")
            idx = _match(labels, want)
            if idx is None:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                print(f"[hachshara] {want[1]:02d}/{want[0]} not in the list — stepping back")
                continue
            await options.nth(idx).click()
            await page.wait_for_timeout(600)
            # Read the value back — a click landing is not the same as the widget
            # accepting it.
            applied = ((await month_input.input_value()) or "").strip()
            if _applied_is(applied, want):
                picked_month = want
                print(f"[hachshara] חודש עיבוד selected: {applied!r} → {want}")
                break
            print(f"[hachshara] click on {want} did not stick (field reads {applied!r})")

        # Close the mat-autocomplete panel before clicking export — the cdk-overlay
        # backdrop otherwise swallows the "הורד ל excel" click (same bug the agent
        # picker above already pays for).
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(2500)
        await ck("nav4b_month")

        if picked_month is None:
            raise RuntimeError(
                f"Hachshara: לא הצלחתי לבחור 'חודש עיבוד'. ציפיתי לאחד מ-"
                f"{', '.join(f'{m:02d}/{y}' for y, m in candidates)} אך האפשרויות "
                f"היו: {labels or '(ריק)'} — בדוק {run_id}_nav4b_month.txt. "
                "לא מורידים דוח ללא חודש: הוא יחזיר את כל הלקוחות שהיו אי פעם "
                "אצל הסוכן וייראה כהצלחה."
            )

        # 5) download — button "הורד ל excel" (<i class="mdi mdi-microsoft-excel">).
        #    This Angular page covers elements, so FORCE-click the exact button;
        #    native download + XHR fallback.
        async def _click_excel() -> bool:
            for sel in (
                "button:has-text('הורד ל excel')",
                "button.btn-outline-ele:has(i.mdi-microsoft-excel)",
                "button:has(i.mdi-microsoft-excel)",
                "i.mdi-microsoft-excel",
                "button:has-text('ייצוא לאקסל')", "button:has-text('יצוא לאקסל')",
            ):
                loc = page.locator(sel).first
                try:
                    if await loc.count():
                        await loc.scroll_into_view_if_needed(timeout=2000)
                        await loc.click(force=True, timeout=4000)
                        return True
                except Exception:
                    continue
            return False

        try:
            async with page.expect_download(timeout=30000) as dl_info:
                if not await _click_excel():
                    raise RuntimeError("no-download-trigger-visible")
            download = await dl_info.value
            await download.save_as(str(target))
        except Exception as native_err:
            for _ in range(24):
                if xhr_capture["bytes"]:
                    break
                await asyncio.sleep(0.5)
            if xhr_capture["bytes"]:
                target.write_bytes(xhr_capture["bytes"])
            else:
                await ck("nav5_no_download")
                raise RuntimeError(
                    f"Hachshara: לא נמצא טריגר הורדה ב-{page.url}. בדוק "
                    f"{run_id}_nav4_agent_all.txt / _nav5_no_download.txt: {native_err}"
                )
        finally:
            try:
                page.remove_listener("response", _on_response)
            except Exception:
                pass

        await ck("nav5_after_export")

        # 6) Verify what actually ARRIVED, then name the file after it.
        #
        # The month hop reading its value back only proves the widget accepted a
        # click — not that the grid re-filtered. This form exports from a single
        # button with no "הפק דוח" to confirm a regenerate, so the contents are
        # the only real evidence. Fail here rather than ingest: an unfiltered
        # export is exactly the bug, and it looks like success at every layer.
        yyyy, mm = picked_month
        try:
            import pandas as pd

            df = pd.read_excel(target)
        except Exception as read_err:
            await ck("nav6_unreadable")
            raise RuntimeError(
                f"Hachshara: הקובץ שהתקבל לא נקרא ({target.name}) — "
                f"בדוק {run_id}_nav6_unreadable.txt: {read_err}"
            )

        ok, reason = verify_processing_month(df, yyyy, mm)
        if not ok:
            await ck("nav6_wrong_month")
            raise RuntimeError(
                f"Hachshara: {reason} — בדוק {run_id}_nav4b_month.txt / "
                f"{run_id}_nav6_wrong_month.txt"
            )

        # Only now is the month a fact about the contents. Note this renames the
        # DOWNLOADED FILE only — run_id (download_dir.name) keeps driving the dump
        # prefixes, so the file names quoted in the errors above still resolve.
        stamped = download_dir / f"הכשרה נפרעים {mm:02d}-{yyyy}.xlsx"
        target.replace(stamped)
        print(
            f"[hachshara] verified {len(df)} rows, all תאריך עיבוד = "
            f"{mm:02d}/{yyyy} → {stamped.name}"
        )
        return [stamped]
