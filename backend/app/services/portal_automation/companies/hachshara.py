"""Hachshara (הכשרה) agent portal — login, OTP, download commission report.

F5 BIG-IP APM at `agents-login.hcsra.co.il/my.policy`. Shares the APM login
form with Phoenix, Clal, Migdal-APM (see `_apm_helpers.py`).

Selectors below are scaffolds. Refine from `<run_id>_post_otp.txt` after
first live run.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation._apm_helpers import apm_login_submit

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://agents-login.hcsra.co.il/my.policy"


class HachsharaPortal(BasePortalAutomation):
    portal_kind = "hachshara"
    company_label = "הכשרה"

    async def login(self, page: "Page", username: str, password: str) -> None:
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await apm_login_submit(page, username, password)
        await self._wait_visible(
            page,
            "input[name='otp'], input[autocomplete='one-time-code'], input[name='code'], input[name='answer']",
            timeout=20000,
        )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(
            "input[name='otp'], input[autocomplete='one-time-code'], input[name='code'], input[name='answer']",
            otp,
        )
        for sel in (
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('כניסה')",
            "button:has-text('המשך')",
            "button:has-text('אישור')",
            "button:has-text('Logon')",
        ):
            try:
                await page.click(sel, timeout=2500)
                break
            except Exception:
                continue
        await page.wait_for_load_state("networkidle", timeout=20000)

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
        debug_base = SCREENSHOT_ROOT / f"{run_id}_post_otp.png"
        await self._safe_screenshot(page, debug_base)
        await self._dump_page_state(page, debug_base)

        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "hachshara_commission.xlsx"

        nav_candidates = [
            "a:has-text('דוח עמלות')",
            "a:has-text('דוחות עמלות')",
            "a:has-text('עמלות')",
            "a:has-text('נפרעים')",
            "a:has-text('דוחות')",
            "button:has-text('עמלות')",
            "[role='link']:has-text('עמלות')",
        ]
        await self._click_first_visible(page, nav_candidates, timeout=8000)

        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        mid_dump = SCREENSHOT_ROOT / f"{run_id}_after_nav.png"
        await self._safe_screenshot(page, mid_dump)
        await self._dump_page_state(page, mid_dump)

        xhr_capture: dict = {"bytes": None, "url": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel = (
                    "spreadsheetml" in ct
                    or "vnd.ms-excel" in ct
                    or ".xlsx" in url
                    or ".xlsx" in cd
                    or ".xls" in cd
                )
                if is_excel and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
            except Exception:
                pass

        page.on("response", _on_response)

        download_candidates = [
            "button:has-text('הורד')",
            "button:has-text('הורדה')",
            "button:has-text('יצוא לאקסל')",
            "button:has-text('יצוא')",
            "a:has-text('Excel')",
            "a:has-text('XLSX')",
            "[title*='הורד']",
            "[aria-label*='Download']",
            "button:has-text('Download')",
        ]

        try:
            async with page.expect_download(timeout=30000) as dl_info:
                clicked = await self._click_first_visible(
                    page, download_candidates, timeout=12000
                )
                if not clicked:
                    raise RuntimeError("no-download-trigger-visible")
            download = await dl_info.value
            await download.save_as(str(target))
        except Exception as native_err:
            import asyncio
            for _ in range(20):
                if xhr_capture["bytes"]:
                    break
                await asyncio.sleep(0.5)
            if xhr_capture["bytes"]:
                target.write_bytes(xhr_capture["bytes"])
            else:
                visible_hint = mid_dump.with_suffix(".txt").name
                raise RuntimeError(
                    f"לא נמצא טריגר הורדה ב-{page.url}. בדוק רשימת אלמנטים גלויים "
                    f"ב-{visible_hint}: {native_err}"
                )
        finally:
            page.remove_listener("response", _on_response)

        return [target]
