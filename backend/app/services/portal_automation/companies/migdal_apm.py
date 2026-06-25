"""Migdal — אזור סוכנים (APM) — login, OTP, download נפרעים commission report.

This is the F5 BIG-IP APM-fronted "agent area" portal — separate from the
Safes vault (`mfte.migdal.co.il`) which is handled by `migdal.py`. Distinct
`portal_kind` so the user can store distinct credentials for each.

Login flow:
    1. page.goto(PORTAL_URL) → F5 logon form
    2. apm_login_submit(page, username, password) → submits the F5 form
    3. Wait for OTP input → submit_otp() fills + submits
    4. download_reports() navigates to the נפרעים report and downloads

Selectors below are scaffolds — they're recorded against the standard F5
APM markup, but the post-login report-section nav needs live codegen
against the real portal. First run will dump `<run_id>.{png,html,txt}` so
we can refine without re-running.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation._apm_helpers import apm_login_submit

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://apmaccess.migdal.co.il/my.policy"

# The agent's owner ID (תז בעלים). The "משולמים בעלים" report lists owners; clicking
# this row scopes the export to the agent's full book — the same value appears on
# every exported row (it's the agent, not a client).
# TODO: promote to a per-credential field if a second agent ever uses this portal.
OWNER_ID = "40336281"


class MigdalApmPortal(BasePortalAutomation):
    portal_kind = "migdal_apm"
    company_label = "מגדל — אזור סוכנים (עמלות)"
    # Folded into the consolidated `migdal` plugin, which downloads the mfte
    # production then logs into apmaccess (2nd OTP via the runner's otp_provider)
    # for this נפרעים report. Still runnable as a manual single run.
    include_in_batch = False

    async def login(self, page: "Page", username: str, password: str) -> None:
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # F5 APM bot gate: the first hit bounces to my.logout.php3?errorcode=19.
        # The recovery link's href is a (literal, server-templated) session token
        # "https://apmaccess.migdal.co.il/[SESSION_RESTART_URL]"; navigating to it
        # restarts the session and serves the real logon form. We navigate by href
        # rather than click because the page has TWO "לחץ כאן" links — the other is
        # a remote-support link to lpsplatformp.migdal.co.il. Loop in case it
        # bounces more than once.
        for _ in range(4):
            if "errorcode" not in page.url and "logout" not in page.url:
                break
            restart = await page.evaluate(
                """() => {
                    const as = Array.from(document.querySelectorAll('a'));
                    let m = as.find(a => (a.href||'').includes('apmaccess.migdal.co.il')
                                         && (a.href||'').includes('SESSION_RESTART'));
                    if (!m) m = as.find(a => (a.innerText||'').trim() === 'לחץ כאן'
                                             && (a.href||'').includes('apmaccess.migdal.co.il'));
                    return m ? m.href : null;
                }"""
            )
            if not restart:
                break
            await page.goto(restart, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

        await apm_login_submit(page, username, password)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        # Dump the post-credential page so the OTP-field selector can be refined
        # from the artifact without re-running the live portal.
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        dump = SCREENSHOT_ROOT / "migdal_apm_otp_page.png"
        await self._safe_screenshot(page, dump)
        await self._dump_page_state(page, dump)
        # F5 reuses the same form id (input_2) for the OTP step; cover that plus
        # the generic one-time-code names.
        await self._wait_visible(page, self.OTP_FIELD, timeout=20000)

    # F5 APM OTP field — input_2 is reused for the code; placeholder/name variants
    # cover the other portals' markup.
    OTP_FIELD = (
        "input[name='otp'], input[autocomplete='one-time-code'], input[name='code'], "
        "input[name='answer'], input[placeholder*='קוד'], input#input_2, input[name='password']"
    )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(self.OTP_FIELD, otp)
        # Standard F5 OTP-page submit
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
        # Commission/נפרעים reports here are typically not password-protected.
        self.report_password = None

        # Dump the post-OTP landing page so the first real run gives us
        # the visible menu items to refine selectors against.
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        debug_base = SCREENSHOT_ROOT / f"{run_id}_post_otp.png"
        await self._safe_screenshot(page, debug_base)
        await self._dump_page_state(page, debug_base)

        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "migdal_apm_commission.xlsx"

        # --- Navigation: כלים → משולמים בעלים → owner row → ייצוא לאקסל ---
        # Selectors are best-effort against the live markup; refine from the
        # `_post_otp.txt` / `_after_nav.txt` dumps after the first live run.

        # Step 1: open the כלים (Tools) menu.
        await self._click_first_visible(
            page,
            [
                "a:has-text('כלים')",
                "button:has-text('כלים')",
                "[role='menuitem']:has-text('כלים')",
                "span:has-text('כלים')",
                "text=כלים",
            ],
            timeout=12000,
        )
        try:
            await page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass

        # Step 2: open the "משולמים בעלים" report (likely a submenu item).
        await self._click_first_visible(
            page,
            [
                "a:has-text('משולמים בעלים')",
                "[role='menuitem']:has-text('משולמים בעלים')",
                "button:has-text('משולמים בעלים')",
                "span:has-text('משולמים בעלים')",
                "text=משולמים בעלים",
            ],
            timeout=12000,
        )

        # Step 3: wait for the owners grid to populate ("wait secs" per the flow).
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        # Step 4: click the owner row (תז בעלים == OWNER_ID). Fall back to the
        # first data row if the specific id isn't matched.
        owner_clicked = await self._click_first_visible(
            page,
            [
                f"tr:has-text('{OWNER_ID}')",
                f"td:has-text('{OWNER_ID}')",
                f"[role='row']:has-text('{OWNER_ID}')",
            ],
            timeout=8000,
        )
        if not owner_clicked:
            for sel in (
                "table tbody tr",
                "tr.x-grid-row",
                "[role='row']:not(:first-child)",
            ):
                try:
                    await page.click(sel, timeout=2500)
                    owner_clicked = sel
                    break
                except Exception:
                    continue

        # Step 5: wait for the report grid to render for the selected owner.
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # Capture state just before the download trigger — helpful for refining
        # the export-button selector without re-running the live portal.
        mid_dump = SCREENSHOT_ROOT / f"{run_id}_after_nav.png"
        await self._safe_screenshot(page, mid_dump)
        await self._dump_page_state(page, mid_dump)

        # XHR fallback — some F5-fronted SPAs deliver the file via XHR, not
        # Content-Disposition. Listener attached BEFORE the click flow.
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
                    or ".xls" in cd
                    or ".xlsx" in cd
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
            "button:has-text('ייצוא לאקסל')",
            "a:has-text('ייצוא לאקסל')",
            "button:has-text('יצוא לאקסל')",
            "a:has-text('יצוא לאקסל')",
            "[title*='ייצוא לאקסל']",
            "[title*='יצוא לאקסל']",
            "button:has-text('הורד')",
            "button:has-text('הורדה')",
            "a:has-text('Excel')",
            "a:has-text('XLSX')",
            "a:has-text('הורד')",
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
            for _ in range(20):  # 10s grace for XHR
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

        # Rename with the report's Hebrew month so detect_period_month (filename-first)
        # resolves correctly. The parser maps חודש תחילת ביטוח → sign_date (policy
        # inception year, e.g. 2011), which would otherwise mislead period detection.
        final = self._rename_with_period(target)
        return [final]

    @staticmethod
    def _rename_with_period(path: Path) -> Path:
        """Rename a Migdal נפרעים export to 'מגדל נפרעים <חודש> <שנה>.xlsx' using the
        report month (from the 'לחודש' column, falling back to latest 'תאריך תשלום').
        Returns the original path unchanged if the month can't be determined."""
        try:
            import pandas as pd
            from app.services.parser_service import _HE_MONTH_TO_INT

            int_to_he = {v: k for k, v in _HE_MONTH_TO_INT.items()}
            df = pd.read_excel(path)

            month = year = None
            # Prefer the explicit "לחודש" column (MM/YYYY).
            for col in df.columns:
                if str(col).strip() == "לחודש":
                    vals = df[col].dropna().astype(str)
                    if len(vals):
                        m = re.search(r"(\d{1,2})\s*[/.\-]\s*(\d{4})", vals.iloc[0])
                        if m:
                            month, year = int(m.group(1)), int(m.group(2))
                    break
            # Fallback: latest payment date (תאריך תשלום).
            if month is None:
                for col in df.columns:
                    if "תאריך תשלום" in str(col):
                        dts = pd.to_datetime(df[col], dayfirst=True, errors="coerce").dropna()
                        if len(dts):
                            month, year = int(dts.max().month), int(dts.max().year)
                        break

            if month and year and month in int_to_he:
                new_path = path.with_name(f"מגדל נפרעים {int_to_he[month]} {year}.xlsx")
                path.rename(new_path)
                return new_path
        except Exception:
            pass
        return path
