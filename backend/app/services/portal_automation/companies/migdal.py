"""Migdal (מגדל) agent portal — login, OTP, download commission report.

The Migdal Safes System uses a Google-style email-first login (email page
→ password page → SMS OTP page) and an SPA dashboard whose left-nav often
hides the reports section behind a hamburger toggle.

When a run fails, the runner saves three artifacts under
`data/portal_screenshots/<run_id>.{png,html,txt}`. The `.txt` lists every
visible link/button — use it to extend the candidate-selector lists below
without re-running the live portal.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://mfte.migdal.co.il/#/"


class MigdalPortal(BasePortalAutomation):
    portal_kind = "migdal"
    company_label = "מגדל"

    async def login(self, page: "Page", username: str, password: str) -> None:
        # Migdal Safes System uses a 2-step email-first login (Google-style):
        # email page → Next → password page → Sign in → OTP page.
        await page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)

        # Step 1: username
        await self._wait_visible(page, "input#email")
        await page.fill("input#email", username)
        # The "Next" / "המשך" label depends on UI language; match either.
        await page.click("button:has-text('Next'), button:has-text('המשך')")

        # Step 2: password (note: input type=text + custom show/hide, not type=password)
        await self._wait_visible(page, "input#password", timeout=15000)
        await page.fill("input#password", password)
        await page.click("button:has-text('Sign in'), button:has-text('כניסה')")

        # Step 3: OTP page — input#otp, "Sign in" button (verified against live portal).
        await self._wait_visible(page, "input#otp", timeout=20000)

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill("input#otp", otp)
        await page.click("button:has-text('Sign in'), button:has-text('כניסה')")
        # Migdal Safes System is an SPA — `networkidle` settles before the
        # hash route flips off /tfa, so dumping/clicking here would still
        # see the OTP page DOM. Wait for the URL to actually leave /tfa.
        try:
            await page.wait_for_url(
                lambda u: "/tfa" not in u, timeout=20000
            )
        except Exception:
            # URL never changed — let download_reports dump current state
            # for diagnosis instead of hanging here.
            pass
        await page.wait_for_load_state("networkidle", timeout=10000)

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        # Migdal commission reports are typically not password-protected; leave None
        # so msoffcrypto isn't tried unnecessarily.
        self.report_password = None

        # Always dump the post-OTP landing page next to the run's screenshot so
        # we have evidence the next time selectors drift. `download_dir.name`
        # is the run_id (see runner.DOWNLOAD_ROOT / str(run.id)), so this
        # produces a unique debug stem per run.
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        debug_base = SCREENSHOT_ROOT / f"{run_id}_post_otp.png"
        await self._safe_screenshot(page, debug_base)
        await self._dump_page_state(page, debug_base)

        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "migdal_commission.xlsx"

        # Fallback path: many SPA portals serve files via XHR (Content-Disposition
        # never reaches Playwright's expect_download). Attach a response listener
        # BEFORE any click so we capture the bytes regardless of how Migdal
        # delivers them. The listener fills `xhr_capture` if it sees an Excel
        # response; we check it after the click flow finishes.
        xhr_capture: dict = {"bytes": None, "url": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel = (
                    "spreadsheetml" in ct
                    or "vnd.ms-excel" in ct
                    or "octet-stream" in ct and (".xlsx" in url or ".xls" in url or "frommigdal" in url)
                    or ".xlsx" in url
                    or ".xls" in url and "/css" not in url
                    or "frommigdal" in url
                    or ".xlsx" in cd
                    or ".xls" in cd
                )
                if is_excel and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:  # skip tiny preflight responses
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
            except Exception:
                pass

        page.on("response", _on_response)

        # Some accounts land on a dashboard with a nav menu instead of the file
        # vault directly. Try to navigate to "my files / reports / downloads"
        # first; harmless no-op if we're already on the vault page.
        nav_candidates = [
            "a:has-text('הקבצים שלי')",
            "a:has-text('הקבצים')",
            "a:has-text('קבצים')",
            "a:has-text('הורדות')",
            "a:has-text('דוחות')",
            "a:has-text('Safes')",
            "a:has-text('My Files')",
            "button:has-text('הקבצים שלי')",
            "[role='link']:has-text('קבצים')",
        ]
        await self._click_first_visible(page, nav_candidates, timeout=4000)

        # The "Migdal Safes System" landing page is a file-vault — files for
        # the agent are listed by name like `{USERNAME}_FROMMIGDAL_<index>`.
        # Build the precise file selector when we know the username; fall back
        # to a generic _FROMMIGDAL match otherwise.
        user_upper = (username or "").strip().upper()
        file_candidates: list[str] = []
        if user_upper:
            file_candidates.extend([
                f"a:has-text('{user_upper}_FROMMIGDAL')",
                f"button:has-text('{user_upper}_FROMMIGDAL')",
                f"[role='link']:has-text('{user_upper}_FROMMIGDAL')",
                f"tr:has-text('{user_upper}_FROMMIGDAL')",
                f"li:has-text('{user_upper}_FROMMIGDAL')",
                f"div[role='row']:has-text('{user_upper}_FROMMIGDAL')",
            ])
        file_candidates.extend([
            "a:has-text('_FROMMIGDAL')",
            "button:has-text('_FROMMIGDAL')",
            "[role='link']:has-text('_FROMMIGDAL')",
            "tr:has-text('_FROMMIGDAL')",
            "li:has-text('_FROMMIGDAL')",
            "a:has-text('FROMMIGDAL')",
            # Last resort: any row mentioning Excel-like extensions
            "tr:has-text('.xlsx')",
            "a:has-text('.xlsx')",
        ])

        # Trigger download via expect_download wrapped around the click flow.
        # On some accounts the file-row click already triggers the download;
        # on others a toolbar Download button is needed. Either way the
        # response listener above also captures XHR-served files as a fallback.
        download_candidates = [
            "button:has-text('Download')",
            "button:has-text('הורד')",
            "button:has-text('הורדה')",
            "a:has-text('Download')",
            "a:has-text('הורד')",
            "[aria-label='Download']",
            "[aria-label='הורדה']",
            "button:has-text('יצוא')",
            "button:has-text('יצוא לאקסל')",
            "a:has-text('Excel')",
            "a:has-text('XLSX')",
            "[role='button']:has-text('Download')",
            "[title*='Download']",
            "[title*='הורד']",
        ]

        clicked_file: str | None = None
        download = None
        try:
            async with page.expect_download(timeout=45000) as dl_info:
                clicked_file = await self._click_first_visible(page, file_candidates, timeout=15000)
                if not clicked_file:
                    # No file row found — raise inside expect_download so the
                    # context exits cleanly; we'll re-raise with detail below.
                    raise RuntimeError("file-row-not-found")
                # Migdal uses Kiteworks PDN where _FROMMIGDAL rows are
                # actually folders ("1 item"). Clicking navigates into
                # /folder/{uuid}. Capture the page state mid-flight so we
                # know what's inside without needing a second debug run.
                import asyncio as _asyncio
                try:
                    await page.wait_for_load_state("networkidle", timeout=4000)
                except Exception:
                    pass
                inner_dump = SCREENSHOT_ROOT / f"{run_id}_after_row_click.png"
                await self._safe_screenshot(page, inner_dump)
                await self._dump_page_state(page, inner_dump)

                # Two-level pattern: now we should be INSIDE the folder.
                # Try the same FROMMIGDAL pattern again (the inner file may
                # share the prefix), plus generic Excel/file selectors.
                inner_candidates: list[str] = []
                if user_upper:
                    inner_candidates.extend([
                        f"a:has-text('{user_upper}_FROMMIGDAL')",
                        f"tr:has-text('{user_upper}_FROMMIGDAL')",
                    ])
                inner_candidates.extend([
                    "a:has-text('_FROMMIGDAL')",
                    "tr:has-text('_FROMMIGDAL')",
                    "a:has-text('.xlsx')",
                    "a:has-text('.xls')",
                    "a:has-text('.csv')",
                    "tr:has-text('.xlsx')",
                    "tr:has-text('.xls')",
                ])
                await self._click_first_visible(page, inner_candidates, timeout=6000)

                # Capture again after the inner click — this is where the
                # download button (or download itself) should appear.
                try:
                    await page.wait_for_load_state("networkidle", timeout=4000)
                except Exception:
                    pass
                inner2_dump = SCREENSHOT_ROOT / f"{run_id}_after_inner_click.png"
                await self._safe_screenshot(page, inner2_dump)
                await self._dump_page_state(page, inner2_dump)

                # Kiteworks shows a kebab `⋮` per row with Download in the
                # dropdown — try that pattern too (most reliable for OneDrive-
                # /SharePoint-like UIs).
                kebab_candidates = [
                    "button[aria-label*='options' i]",
                    "button[aria-label*='actions' i]",
                    "button[aria-label*='more' i]",
                    "button[title*='options' i]",
                    "button[title*='actions' i]",
                    "[role='button'][aria-haspopup='menu']",
                ]
                await self._click_first_visible(page, kebab_candidates, timeout=4000)

                # If a menu opened, click Download inside it.
                menu_download_candidates = [
                    "li:has-text('Download')",
                    "[role='menuitem']:has-text('Download')",
                    "li:has-text('הורד')",
                    "[role='menuitem']:has-text('הורד')",
                    "li:has-text('הורדה')",
                    "a:has-text('Download')",
                ]
                await self._click_first_visible(page, menu_download_candidates, timeout=4000)

                # Final fallback: original toolbar Download buttons.
                await self._click_first_visible(page, download_candidates, timeout=4000)
            download = await dl_info.value
            await download.save_as(str(target))
        except Exception as native_err:
            # Native download didn't fire — fall back to XHR capture. Wait a
            # short grace period for the response listener to fill the buffer.
            import asyncio
            for _ in range(20):  # 20 * 0.5s = 10s grace
                if xhr_capture["bytes"]:
                    break
                await asyncio.sleep(0.5)

            if xhr_capture["bytes"]:
                target.write_bytes(xhr_capture["bytes"])
            else:
                visible_hint = debug_base.with_suffix(".txt").name
                file_status = (
                    f"לא נמצא קובץ של הסוכן (חיפש {len(file_candidates)} מועמדים, כולל "
                    f"{user_upper}_FROMMIGDAL)"
                    if str(native_err) == "file-row-not-found"
                    else f"קובץ נלחץ ({clicked_file}) אבל לא הופעלה הורדה"
                )
                raise RuntimeError(
                    f"{file_status} ב-{page.url}. "
                    f"בדוק רשימת אלמנטים גלויים ב-{visible_hint}: {native_err}"
                )
        finally:
            page.remove_listener("response", _on_response)

        downloaded: list[Path] = [target]

        # ─── Best-effort production (Mimshak) ZIP download ──────────────
        # Migdal's production-export ("מבנה אחיד" / Mimshak) lives on a
        # separate menu we haven't mapped yet. Attempt common navigation
        # paths and dump page state so the first run produces evidence we
        # can refine selectors from. NEVER fail the whole run on this step
        # — the commission file is the main deliverable; production is a
        # bonus today and will become reliable as we tune selectors.
        try:
            production_path = await self._try_download_mimshak(page, download_dir, run_id)
            if production_path:
                downloaded.append(production_path)
                from app.services.portal_automation.runner import logger as _runner_logger
                _runner_logger.info(
                    "Migdal: also downloaded production ZIP %s", production_path.name
                )
        except Exception as e:
            # Diagnostics already dumped inside the helper. Log + move on.
            from app.services.portal_automation.runner import logger as _runner_logger
            _runner_logger.warning(
                "Migdal production-export attempt failed (run %s): %s. "
                "Until Mimshak menu selectors are mapped, manually upload the "
                "LIFE*.zip file from Migdal — it ingests via the same pipeline.",
                run_id, e,
            )

        return downloaded

    async def _try_download_mimshak(
        self,
        page: "Page",
        download_dir: Path,
        run_id: str,
    ) -> Path | None:
        """Attempt to navigate to Migdal's Mimshak/production-export menu and
        download the ZIP. Returns the saved path, or None if the menu wasn't
        found (no exception raised — production is best-effort today).

        Dumps page state to `<run_id>_prod_*.{png,html,txt}` at each
        checkpoint so we can refine selectors from real evidence after the
        first run that gets this far.
        """
        from app.services.portal_automation.runner import SCREENSHOT_ROOT

        # Checkpoint 0: where we are before any navigation
        dump_pre = SCREENSHOT_ROOT / f"{run_id}_prod_0_pre.png"
        await self._safe_screenshot(page, dump_pre)
        await self._dump_page_state(page, dump_pre)

        # Try clicking common navigation items that might lead to Mimshak.
        # Hebrew + English variants; specific → generic order.
        nav_candidates = [
            "a:has-text('מבנה אחיד')",
            "a:has-text('מימשק')",
            "a:has-text('Mimshak')",
            "a:has-text('ייצוא ייצור')",
            "a:has-text('ייצוא')",
            "a:has-text('הפקות')",
            "a:has-text('דוחות')",
            "button:has-text('מבנה אחיד')",
            "button:has-text('Mimshak')",
            "[role='link']:has-text('מבנה אחיד')",
        ]
        nav_clicked = await self._click_first_visible(page, nav_candidates, timeout=6000)
        if not nav_clicked:
            # No nav match — leave a dump so the operator can see what menu items
            # actually exist, and abort silently.
            return None

        try:
            await page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass

        # Checkpoint 1: after navigation
        dump_nav = SCREENSHOT_ROOT / f"{run_id}_prod_1_after_nav.png"
        await self._safe_screenshot(page, dump_nav)
        await self._dump_page_state(page, dump_nav)

        # Try to trigger the ZIP download. Same pattern as commission —
        # expect_download wrapping a click on common download triggers.
        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "migdal_production.zip"
        download_candidates = [
            "button:has-text('הורד ZIP')",
            "button:has-text('הורד קובץ')",
            "button:has-text('Download')",
            "a:has-text('Download')",
            "a:has-text('הורד')",
            "button:has-text('הורד')",
            "button:has-text('הורדה')",
            "button:has-text('יצוא')",
            "a:has-text('.zip')",
            "[aria-label*='Download']",
        ]
        try:
            async with page.expect_download(timeout=30000) as dl_info:
                clicked = await self._click_first_visible(
                    page, download_candidates, timeout=8000
                )
                if not clicked:
                    raise RuntimeError("no-download-trigger-visible")
            download = await dl_info.value
            await download.save_as(str(target))

            # Checkpoint 2: after successful download
            dump_done = SCREENSHOT_ROOT / f"{run_id}_prod_2_downloaded.png"
            await self._safe_screenshot(page, dump_done)
            return target
        except Exception as e:
            # Dump so we can see what the menu looks like and refine selectors.
            dump_fail = SCREENSHOT_ROOT / f"{run_id}_prod_2_failed.png"
            await self._safe_screenshot(page, dump_fail)
            await self._dump_page_state(page, dump_fail)
            raise

    async def change_contact_phone(self, page: "Page", new_phone: str) -> None:
        # Selectors are first-pass placeholders. Re-record with playwright codegen.
        await page.click("a:has-text('פרופיל'), a:has-text('פרטים אישיים'), a:has-text('הגדרות')")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await self._wait_visible(page, "input[name='phone'], input[name='mobile'], input[name='cellphone']")
        await page.fill("input[name='phone'], input[name='mobile'], input[name='cellphone']", new_phone)
        await page.click("button:has-text('שמור'), button:has-text('עדכן')")
        # Migdal verifies the change by texting the OLD phone — wait for the OTP entry to appear.
        await self._wait_visible(
            page,
            "input[name='otp'], input[autocomplete='one-time-code'], input[name='code']",
            timeout=20000,
        )

    async def confirm_contact_phone_change(self, page: "Page", otp: str) -> None:
        await page.fill(
            "input[name='otp'], input[autocomplete='one-time-code'], input[name='code']",
            otp,
        )
        await page.click("button[type='submit'], button:has-text('אישור'), button:has-text('המשך')")
        await page.wait_for_load_state("networkidle", timeout=15000)
