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
    # Keep out of the run-all batch until live-verified (nav selectors are
    # best-effort until the first real run). Flip to True after verification.
    include_in_batch = False

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

        # Fields have dynamic Kendo ids → select by placeholder substring.
        await self._wait_visible(page, "input[placeholder*='רשיון']", timeout=20000)
        await page.fill("input[placeholder*='רשיון']", license_no)
        await page.fill("input[placeholder*='זהות']", id_no)
        await page.fill("input[placeholder*='טלפון']", phone)
        await page.wait_for_timeout(400)

        await self._click_first_visible(page, [
            "button:has-text('כניסה')",
            "input[type='submit']",
            "button[type='submit']",
        ], timeout=8000)

        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        post = SCREENSHOT_ROOT / f"mor_login_{safe}_post_submit.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

        # Wait for the SMS-OTP field (selectors unknown until first live run —
        # broad set; refine from mor_login_*_post_submit.txt).
        await self._wait_visible(
            page,
            (
                "input[autocomplete='one-time-code'], "
                "input[name*='otp' i], input[id*='otp' i], "
                "input[placeholder*='קוד'], input[placeholder*='סיסמ'], "
                "input[name*='code' i], input[id*='code' i], "
                "input[inputmode='numeric']"
            ),
            timeout=25000,
        )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")
        otp_sel = (
            "input[autocomplete='one-time-code'], "
            "input[name*='otp' i], input[id*='otp' i], "
            "input[placeholder*='קוד'], input[placeholder*='סיסמ'], "
            "input[name*='code' i], input[inputmode='numeric']"
        )
        filled = False
        try:
            await page.fill(otp_sel, digits, timeout=4000)
            filled = True
        except Exception:
            try:
                await page.click(otp_sel, timeout=3000)
                await page.keyboard.type(digits, delay=50)
                filled = True
            except Exception:
                pass
        await page.wait_for_timeout(400)
        await self._click_first_visible(page, [
            "button:has-text('אישור')",
            "button:has-text('כניסה')",
            "button:has-text('המשך')",
            "input[type='submit']",
            "button[type='submit']",
        ], timeout=6000)
        try:
            await page.wait_for_url(lambda u: "login" not in (u or "").lower(), timeout=20000)
        except Exception:
            pass
        post = SCREENSHOT_ROOT / "mor_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("Mor: לא נמצא שדה OTP — בדוק mor_login_*_post_submit.txt")

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

        # 1) Right-menu → "חישוב עמלות".
        await self._click_first_visible(page, [
            "a:has-text('חישוב עמלות')",
            "span:has-text('חישוב עמלות')",
            "*:has-text('חישוב עמלות')",
            "a:has-text('עמלות')",
        ], timeout=12000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
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
