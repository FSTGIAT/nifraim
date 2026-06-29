"""מור (Mor) agent portal — נפרעים / commission download.

Login (https://join.more.co.il/agentsportal/agents/login) asks for THREE fields:
מס' רשיון (license) + תעודת זהות (ID) + טלפון (phone). It then SMS-OTPs the phone.
Credential convention: ``username = "<license>|<id>"`` and ``password = "<phone>"``.

Flow (operator): right-menu → חישוב עמלות → pick the month → download to Excel.
The downloaded Excel is the existing ``nifraim`` format (company_source=מור,
commission), so no parser changes are needed.
"""
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page

PORTAL_URL = "https://join.more.co.il/agentsportal/agents/login"


class MorPortal(BasePortalAutomation):
    portal_kind = "mor"
    company_label = "מור"
    # In the run-all batch. Mor's reCAPTCHA Enterprise gate only passes on the
    # Windows LOCAL WORKER (real desktop Chrome + IL IP) — never headless/Linux
    # Railway — so the batch must defer this credential to the worker.
    include_in_batch = True
    # Mor's login is gated by reCAPTCHA *Enterprise* (score-based). The server
    # returns HTTP 400 ("אירעה שגיאה") whenever Google scores the browser as a
    # bot. Proven live: headless + the runner's UA override → 400; headed +
    # native fingerprint + a persistent profile → 201 Success → OTP modal. So
    # Mor must run on the LOCAL WORKER (headed desktop session, real IL IP) —
    # never the headless Railway container. See memory `portal_mor`.
    headed = True
    native_fingerprint = True
    use_persistent_profile = True
    # Run on the worker's OWN residential IL IP — a Bright Data datacenter proxy
    # IP would sink the reCAPTCHA Enterprise score. (Also a no-op unless a proxy
    # env is set, but we never want one routed here.)
    needs_residential_proxy = False

    def _split(self, username: str, password: str) -> tuple[str, str, str]:
        """username='<license>|<id>', password='<phone>'. Falls back to
        license==id when no pipe (operator often has them equal)."""
        parts = (username or "").split("|")
        license_no = parts[0].strip()
        id_no = parts[1].strip() if len(parts) > 1 else license_no
        phone = (password or "").strip()
        return license_no, id_no, phone

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        license_no, id_no, phone = self._split(username, password)

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=40000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        safe = re.sub(r"[^A-Za-z0-9_]", "_", license_no)[:32] or "anon"
        land = SCREENSHOT_ROOT / f"mor_login_{safe}.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # Angular reactive form + Kendo inputs: page.fill() leaves the controls
        # ng-pristine/ng-invalid so the submit button stays disabled. Real
        # KEYSTROKES are required to drive Angular's validation. The ת"ז field
        # needs 9 digits and the phone 10 — pad a leading zero when the stored
        # value drops it (operator stores 40336281 / 504302306).
        # Mor's server wants the 9-digit forms (with the leading 0) for BOTH the
        # license and the ת"ז, and the 10-digit phone — even though the client
        # form validates the shorter forms (server returns "אירעה שגיאה").
        if len(license_no) == 8 and not license_no.startswith("0"):
            license_no = "0" + license_no
        if len(id_no) == 8 and not id_no.startswith("0"):
            id_no = "0" + id_no
        if len(phone) == 9 and not phone.startswith("0"):
            phone = "0" + phone

        async def _type(sel: str, val: str):
            await self._wait_visible(page, sel, timeout=15000)
            await page.click(sel)
            await page.keyboard.type(val, delay=70)
            cur = await page.input_value(sel)
            if cur != val:  # retry once if a char dropped
                await page.fill(sel, "")
                await page.click(sel)
                await page.keyboard.type(val, delay=90)

        await _type("input[formcontrolname='licenseId']", license_no)
        await _type("input[formcontrolname='identity']", id_no)
        await _type("input[placeholder*='טלפון']", phone)
        await page.keyboard.press("Tab")

        # Kendo/Angular validate asynchronously — WAIT for the submit button to
        # actually enable before clicking (a premature click hits the disabled
        # button and no-ops, leaving us stuck on the login form).
        try:
            await page.wait_for_selector(
                "button[type='submit']:not([disabled])", state="attached", timeout=12000
            )
        except Exception:
            err = await page.evaluate(
                "() => [...document.querySelectorAll('.k-tooltip, [id^=kendo-error]')]"
                ".map(e => e.innerText.trim()).filter(Boolean).join(' | ')"
            )
            raise RuntimeError(f"Mor: כפתור הכניסה נשאר מושבת (טופס לא תקין). שגיאות: {err or 'אין'}")
        await page.click("button[type='submit']:not([disabled])")

        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        post = SCREENSHOT_ROOT / f"mor_login_{safe}_post_submit.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

        # After submit Mor either opens the OTP MODAL (#otpInput,
        # formcontrolname="otpCode", maxlength 6) or shows "אירעה שגיאה"
        # (rejected credentials / rate-limit). Race the two so we fail fast with
        # a clear message instead of a blind OTP-field timeout.
        otp_sel = "#otpInput, input[formcontrolname='otpCode']"
        deadline = 30
        for _ in range(deadline * 2):
            if await page.locator(otp_sel).count() and await page.locator(otp_sel).first.is_visible():
                return
            try:
                err = page.locator("text=אירעה שגיאה")
                if await err.count() and await err.first.is_visible():
                    raise RuntimeError(
                        "Mor: הכניסה נדחתה (אירעה שגיאה) — בדוק מס' רשיון/ת\"ז/טלפון "
                        "או המתן דקות (חסימת ניסיונות חוזרים)."
                    )
            except RuntimeError:
                raise
            except Exception:
                pass
            await page.wait_for_timeout(500)
        raise RuntimeError("Mor: מודאל ה-OTP לא נפתח תוך 30 שניות")

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")[:6]
        otp_sel = "#otpInput, input[formcontrolname='otpCode']"
        filled = False
        try:
            await self._wait_visible(page, otp_sel, timeout=8000)
            await page.click(otp_sel)
            await page.keyboard.type(digits, delay=70)  # Angular needs keystrokes
            filled = True
        except Exception:
            try:
                await page.fill(otp_sel, digits, timeout=3000)
                filled = True
            except Exception:
                pass
        await page.wait_for_timeout(400)
        # CRITICAL: the OTP submit button lives inside the <app-otp> dialog, but
        # the LOGIN form BEHIND the modal ALSO has a `type=submit` "כניסה" button
        # that appears FIRST in the DOM. A bare `button:has-text('כניסה')` clicks
        # that background button → the OTP is never submitted and the modal just
        # sits there (no error). Scope the click to the dialog; fall back to
        # pressing Enter inside the OTP field.
        clicked = await self._click_first_visible(page, [
            "app-otp button[type='submit']",
            ".k-dialog-content button[type='submit']",
            "app-otp button:has-text('כניסה')",
        ], timeout=6000)
        if not clicked:
            try:
                await page.focus(otp_sel)
                await page.keyboard.press("Enter")
            except Exception:
                pass
        # Accepted ⇒ the OTP dialog detaches (the SPA keeps the URL on
        # /agents/login, so don't gate on the URL).
        try:
            await page.wait_for_selector("app-otp", state="detached", timeout=20000)
        except Exception:
            pass
        post = SCREENSHOT_ROOT / "mor_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("Mor: לא נמצא שדה OTP — בדוק mor_login_*_post_submit.txt")
        # If the OTP dialog is still open, the code was rejected (or the click
        # missed) — fail with the on-screen error instead of silently navigating
        # download_reports against the login page.
        if await page.locator("#otpInput").count() and await page.locator("#otpInput").first.is_visible():
            err = await page.evaluate(
                "() => {const e=document.querySelector('.erroronbatt');return e?e.innerText.trim():'';}"
            )
            raise RuntimeError(
                f"Mor: קוד ה-OTP לא התקבל (מודאל ה-OTP עדיין פתוח). {('שגיאה: '+err) if err else ''}"
            )

    async def download_reports(self, page: "Page", download_dir: Path, **kwargs) -> list[Path]:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)
        self.report_password = None

        async def ck(tag):
            p = SCREENSHOT_ROOT / f"{run_id}_{tag}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        await ck("nav_0_home")

        # 1) Right side-menu (Kendo drawer) → "תגמול" — the commission/נפרעים
        #    report. Live DOM: <li kendodraweritem aria-label="תגמול"
        #    class="k-drawer-item tagmul" data-kendo-drawer-index="8">. NOTE the
        #    label is "תגמול" (compensation), NOT "חישוב עמלות"; "חישוב תגמול"
        #    (index 9) is a DIFFERENT item — match aria-label exactly so we don't
        #    hit it. Click the <li>; fall back to its inner k-item-text span.
        await self._click_first_visible(page, [
            "li[aria-label='תגמול']",
            "li.k-drawer-item.tagmul",
            "li[data-kendo-drawer-index='8']",
            "li[aria-label='תגמול'] span.k-item-text",
        ], timeout=12000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        await ck("nav_1_commissions")

        # 2) Download to Excel (latest month default; refine selection after the
        #    first live run from nav_1_commissions.txt).
        target = download_dir / "מור נפרעים.xlsx"
        xhr = {"bytes": None}

        async def on_resp(resp):
            try:
                cd = resp.headers.get("content-disposition") or ""
                ct = resp.headers.get("content-type") or ""
                if any(x in (cd + ct).lower() for x in ("spreadsheet", ".xlsx", ".xls", "excel", "octet-stream")):
                    b = await resp.body()
                    if b and len(b) > 1024 and xhr["bytes"] is None:
                        xhr["bytes"] = b
            except Exception:
                pass
        page.on("response", on_resp)

        got = None
        try:
            async with page.expect_download(timeout=20000) as dl:
                await self._click_first_visible(page, [
                    "button:has-text('ייצוא לאקסל')",
                    "a:has-text('ייצוא לאקסל')",
                    "button:has-text('אקסל')",
                    "*:has-text('ייצוא')",
                    "button:has-text('הורד')",
                    "[title*='Excel' i]",
                    "img[src*='excel' i]",
                ], timeout=12000)
            d = await dl.value
            await d.save_as(str(target))
            got = target
        except Exception:
            if xhr["bytes"]:
                target.write_bytes(xhr["bytes"])
                got = target

        await ck("nav_2_after_export")
        if not got:
            raise RuntimeError(f"Mor: לא ירד קובץ — בדוק {run_id}_nav_1_commissions.txt / _nav_2_after_export.txt")
        return [got]
