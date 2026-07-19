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

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        land = SCREENSHOT_ROOT / "analyst_login.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # Angular Material: matinput controls stay ng-pristine/ng-invalid under
        # page.fill(), keeping the submit disabled — drive real KEYSTROKES.
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
        await page.wait_for_timeout(400)

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
            await page.wait_for_timeout(500)
        # No clear transition — let the runner await OTP; submit_otp re-detects.

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")[:6]

        filled = False
        # Segmented single-char boxes. `:visible` EXCLUDES the hidden
        # autocomplete="one-time-code" maxlength=6 catcher (it isn't maxlength=1
        # and isn't visible), so we type only into the six real boxes.
        try:
            boxes = page.locator("input[maxlength='1']:visible")
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

        # Accepted ⇒ leaves /auth/login (SPA may keep a base path). VERIFY the
        # transition — a rejected/expired code otherwise returns silently and the
        # failure surfaces later as a confusing "nav link not found".
        left_login = False
        try:
            await page.wait_for_url(
                lambda u: "login" not in (u or "").lower(), timeout=25000
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

        # A transient post-login message may overlay the UI — let it clear.
        await page.wait_for_timeout(2500)
        await ck("nav_0_home")

        # 1) Navigate to הפקת דוחות.
        await self._click_first_visible(page, [
            "a:has-text('הפקת דוחות')",
            "button:has-text('הפקת דוחות')",
            "[role='menuitem']:has-text('הפקת דוחות')",
            "span:has-text('הפקת דוחות')",
            "li:has-text('הפקת דוחות')",
            "a:has-text('דוחות')",
        ], timeout=12000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        await ck("nav_1_reports")

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

        # 3) Date range per the 20th rule, with a self-heal walk-back. The actual
        #    date-picker DOM is unknown — this fills any date-ish inputs it finds and
        #    dumps state so the selectors can be finalized from nav_2_report_type.txt.
        target = None
        chosen_ym: tuple[int, int] | None = None
        range_confirmed = False

        async def _set_range(d_from: str, d_to: str) -> bool:
            """Best-effort fill of the from/to date inputs, then READ BACK to confirm
            it took. Angular mat-datepicker frequently reparses/ignores raw typed
            text, so a blind fill is not proof. Returns True only when the from-field
            actually carries the target month+year."""
            date_inputs = page.locator(
                "input[matinput][type='text']:visible, input.mat-datepicker-input:visible, "
                "input[placeholder*='תאריך']:visible, input[aria-label*='תאריך']:visible"
            )
            try:
                cnt = await date_inputs.count()
            except Exception:
                cnt = 0
            if cnt == 0:
                return False
            pairs = [(0, d_from), (1, d_to)] if cnt >= 2 else [(0, d_from)]
            for idx, val in pairs:
                try:
                    di = date_inputs.nth(idx)
                    await di.click()
                    await di.fill("")
                    await page.keyboard.type(val, delay=60)
                except Exception:
                    return False
            try:
                await page.keyboard.press("Tab")
            except Exception:
                pass
            await page.wait_for_timeout(400)
            try:
                got0 = re.sub(r"\D", "", (await date_inputs.nth(0).input_value()) or "")
            except Exception:
                got0 = ""
            want = re.sub(r"\D", "", d_from)  # e.g. 01062026
            # Compare the month+year core (formats differ: 01/06/2026 vs 1.6.26).
            return bool(got0) and (want[-6:] in got0 or got0[-6:] in want)

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
            nm, ny = (mm % 12) + 1, yy + (1 if mm == 12 else 0)
            d_from = f"01/{mm:02d}/{yy}"
            d_to = f"01/{nm:02d}/{ny}"
            logger.info("אנליסט: trying report range %s → %s", d_from, d_to)
            applied = await _set_range(d_from, d_to)
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
