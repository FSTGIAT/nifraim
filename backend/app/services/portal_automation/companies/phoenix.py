"""Phoenix (הפניקס) agent portal — login, OTP, download commission report.

NOTE: Selectors below are best-effort placeholders based on the typical layout
of Israeli insurance agent portals. They WILL need adjustment after the first
real run — re-record with `playwright codegen` against the live portal and
update the selectors. Screenshots-on-failure are saved to
`backend/data/portal_screenshots/<run_id>.png` to make this debugging easy.

The Phoenix commission report is a password-protected `.xls` — the plugin
sets `self.report_password` so the runner forwards it to `parse_excel`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://agents.fnx.co.il/login"


class PhoenixPortal(BasePortalAutomation):
    portal_kind = "phoenix"
    company_label = "הפניקס"

    async def login(self, page: "Page", username: str, password: str) -> None:
        await page.goto(PORTAL_URL, wait_until="domcontentloaded")
        await self._wait_visible(page, "input[name='username'], input#username")
        await page.fill("input[name='username'], input#username", username)
        await page.fill("input[name='password'], input#password", password)
        # Submit
        await page.click("button[type='submit'], button:has-text('כניסה')")
        # Wait for OTP input to appear (varies by portal)
        await self._wait_visible(page, "input[name='otp'], input[autocomplete='one-time-code']", timeout=20000)

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill("input[name='otp'], input[autocomplete='one-time-code']", otp)
        await page.click("button[type='submit'], button:has-text('אישור'), button:has-text('המשך')")
        # Wait for the dashboard to settle
        await page.wait_for_load_state("networkidle", timeout=20000)

    async def download_reports(self, page: "Page", download_dir: Path) -> list[Path]:
        # Phoenix's report password is the user's ID number; for MVP we hardcode
        # a placeholder — operators must override per-credential via category_hint
        # or extend the schema. Setting None lets parse_excel try without first.
        self.report_password = None

        # Navigate to commission report. Real selectors require live recording.
        await page.click("a:has-text('דוחות'), a:has-text('עמלות')")
        await page.wait_for_load_state("networkidle", timeout=15000)

        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "phoenix_commission.xls"

        async with page.expect_download() as dl_info:
            await page.click("button:has-text('הורד'), a:has-text('Excel')")
        download = await dl_info.value
        await download.save_as(str(target))
        return [target]
