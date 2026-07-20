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


async def _retry_file_op(fn, *, attempts: int = 4, delay: float = 0.6):
    """Call fn() and retry on PermissionError/OSError (covers Windows WinError 32
    file-lock errors that antivirus or Playwright's temp-file move can trigger).

    fn may be:
      - a plain sync callable  → result = fn()
      - a callable returning a coroutine → result = await fn()

    Back-off: delay * (attempt+1) seconds between retries (0.6 s, 1.2 s, 1.8 s …).
    Raises the last exception if all attempts fail.
    """
    import asyncio as _asyncio
    import inspect as _inspect

    last_err: BaseException = RuntimeError("no attempts made")
    for i in range(attempts):
        try:
            result = fn()
            if _inspect.isawaitable(result):
                result = await result
            return result
        except (PermissionError, OSError) as e:
            last_err = e
            if i < attempts - 1:
                await _asyncio.sleep(delay * (i + 1))
    raise last_err


class MigdalPortal(BasePortalAutomation):
    portal_kind = "migdal"
    company_label = "מגדל — כספת (ייצור)"
    # Downloaded on this same login (see download_reports) — mirror our
    # outcome onto its credential so its card is not stuck at "ממתין".
    folds = ('migdal_apm',)
    # Migdal answers Railway's datacenter IP directly (proven live 2026-06-26),
    # so skip the IL residential proxy — avoids its latency/cost. The apmaccess
    # נפרעים leg shares this context. See memory `railway_ip_geoblocked_insurers`.
    needs_residential_proxy = False

    async def login(self, page: "Page", username: str, password: str) -> None:
        # The consolidated Migdal credential may carry TWO logins joined by `|`:
        # `<mfte_user>|<apm_user>` / `<mfte_pw>|<apm_pw>` (the production Safes
        # vault vs the apmaccess נפרעים portal). Use the FIRST part here for the
        # mfte login; download_reports() uses the second for apmaccess. No `|` →
        # the same value is used for both.
        username = username.split("|")[0].strip()
        password = password.split("|")[0].strip()
        # Migdal Safes System uses a 2-step email-first login (Google-style):
        # email page → Next → password page → Sign in → OTP page.
        await page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)

        # Step 1: username. The Next button reads "הבא" (verified live
        # 2026-06-20) and is disabled until the email field is filled; the
        # English/המשך variants are kept only as language-fallbacks.
        await self._wait_visible(page, "input#email")
        await page.fill("input#email", username)
        await page.click(
            "button:has-text('הבא'), button:has-text('Next'), button:has-text('המשך')"
        )

        # Step 2: password (input type=text + custom show/hide, not type=password).
        # The submit button reads "התחבר" (verified live 2026-06-20).
        await self._wait_visible(page, "input#password", timeout=15000)
        await page.fill("input#password", password)
        await page.click(
            "button:has-text('התחבר'), button:has-text('Sign in'), button:has-text('כניסה')"
        )

        # Step 3: OTP page — input#otp, "Sign in" button (verified against live portal).
        await self._wait_visible(page, "input#otp", timeout=20000)

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill("input#otp", otp)
        # OTP submit reuses the password-page button label ("התחבר"); keep the
        # other labels as fallbacks in case the OTP page differs.
        await page.click(
            "button:has-text('התחבר'), button:has-text('Sign in'), button:has-text('כניסה')"
        )
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
        password: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        # Migdal Safes vault contents are NOT password-protected.
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
        # Provisional name — we sniff the real bytes after download and
        # rename to `.zip` once we see the Mimshak ZIP magic header.
        target = download_dir / "migdal_safes.xlsx"

        # XHR capture fallback — some Kiteworks endpoints serve via XHR with
        # `responseType: 'blob'` so the native expect_download never fires.
        # Listener attached BEFORE any clicks. Re-checked after the flow.
        xhr_capture: dict = {"bytes": None, "url": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel_or_zip = (
                    "spreadsheetml" in ct
                    or "vnd.ms-excel" in ct
                    or "zip" in ct
                    or "octet-stream" in ct
                    or ".xlsx" in url
                    or ".zip" in url
                    or ".xls" in url and "/css" not in url
                    or "frommigdal" in url
                    or ".xlsx" in cd
                    or ".zip" in cd
                )
                if is_excel_or_zip and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
            except Exception:
                pass

        page.on("response", _on_response)

        # ─── Explicit Kiteworks navigation per operator's flow ────────────
        # Per QA: post-OTP → ALL FILES → first FROMMIGDAL folder → Root → LIFE
        # → download. Each step keys off the `font-bold` label class Kiteworks
        # uses for both folder rows and breadcrumbs.
        user_upper = (username or "").strip().upper()

        async def _checkpoint(stem: str) -> Path:
            """Snapshot + DOM dump under <run_id>_<stem>.{png,html,txt}."""
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)
            return p

        async def _click_step(label: str, selectors: list[str], timeout: int = 8000) -> str | None:
            """Click the first matching selector, wait for navigation to
            settle, dump checkpoint, return the matched selector (or None)."""
            sel = await self._click_first_visible(page, selectors, timeout=timeout)
            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except Exception:
                pass
            await _checkpoint(f"nav_{label}")
            return sel

        try:
            # Step 1: ensure we're at the ALL FILES root. Best-effort —
            # post-OTP often lands here already, in which case the click is
            # a no-op. The label is inside a `font-bold` div per the UI.
            await _click_step("1_all_files", [
                'text="ALL FILES"',
                'div.font-bold:has-text("ALL FILES")',
                '[class*="font-bold"]:has-text("ALL FILES")',
                'a:has-text("ALL FILES")',
                'button:has-text("ALL FILES")',
            ], timeout=4000)

            # Step 2: click the first FROMMIGDAL folder row.
            from_migdal_selectors: list[str] = []
            if user_upper:
                from_migdal_selectors.extend([
                    f'text="{user_upper}_FROMMIGDAL_01"',
                    f'div.font-bold:has-text("{user_upper}_FROMMIGDAL")',
                    f'a:has-text("{user_upper}_FROMMIGDAL")',
                    f'tr:has-text("{user_upper}_FROMMIGDAL")',
                ])
            from_migdal_selectors.extend([
                'div.font-bold:has-text("_FROMMIGDAL")',
                '[class*="font-bold"]:has-text("_FROMMIGDAL")',
                'a:has-text("_FROMMIGDAL")',
                'tr:has-text("_FROMMIGDAL")',
                'li:has-text("_FROMMIGDAL")',
            ])
            clicked_frommigdal = await _click_step(
                "2_frommigdal", from_migdal_selectors, timeout=12000
            )
            if not clicked_frommigdal:
                raise RuntimeError(
                    f"לא נמצא תיקיית {user_upper or 'AGENT'}_FROMMIGDAL ב-{page.url}"
                )

            # Step 3: click "Root" subfolder.
            clicked_root = await _click_step("3_root", [
                'text="Root"',
                'div.font-bold:has-text("Root")',
                '[class*="font-bold"]:has-text("Root")',
                'a:has-text("Root")',
                'tr:has-text("Root")',
            ], timeout=10000)
            if not clicked_root:
                raise RuntimeError(f"לא נמצאה תיקיית Root ב-{page.url}")

            # Step 4: discover subfolders at Root level. Folder rows render
            # as `<a>` tags inside Kiteworks file-list (operator-confirmed
            # via run a0a3c225's nav_3_root_no_match.txt). Wait briefly for
            # the SPA's async list render — earlier dumps were captured too
            # fast and showed only the breadcrumb.
            import asyncio as _asyncio
            for _ in range(12):  # up to 6s waiting for content to render
                first_pass = await page.evaluate("""
                    () => [...document.querySelectorAll('a')]
                        .map(a => (a.textContent || '').trim())
                        .filter(t => t)
                """)
                # Look for non-breadcrumb folder candidates
                if any(t not in {"Tracked Activity", "Root", "ALL FILES"}
                       and "_FROMMIGDAL_" not in t.upper()
                       and len(t) > 1
                       for t in first_pass):
                    break
                await _asyncio.sleep(0.5)

            EXCLUDED = {
                "Tracked Activity",
                "Skip to main content",
                "ALL FILES",
                "Root",
                "Migdal Safes System",
                "Sign in",
                "English",
                "Resend",
            }
            root_subfolders: list[str] = await page.evaluate(
                """(excluded) => {
                    const skip = new Set(excluded);
                    const seen = new Set();
                    const out = [];
                    for (const a of document.querySelectorAll('a')) {
                        const t = (a.textContent || '').trim();
                        if (!t || skip.has(t)) continue;
                        if (t.toUpperCase().includes('_FROMMIGDAL_')) continue;  // breadcrumb of parent
                        if (seen.has(t)) continue;
                        seen.add(t);
                        out.push(t);
                    }
                    return out;
                }""",
                list(EXCLUDED),
            )

            from app.services.portal_automation.runner import logger as _logger

            if not root_subfolders:
                await _checkpoint("3_root_no_match")
                raise RuntimeError(
                    f"לא נמצאו תיקיות מוצר תחת Root ב-{page.url}. "
                    f"בדוק {run_id}_nav_3_root_no_match.txt"
                )

            _logger.info(
                "Migdal: discovered %d Root subfolders: %s",
                len(root_subfolders), root_subfolders,
            )

            # Helpers for download flow (used per subfolder)
            download_candidates = [
                'button:has-text("Download")',
                'button:has-text("הורד")',
                'button:has-text("הורדה")',
                'a:has-text("Download")',
                '[aria-label="Download"]',
                '[aria-label="הורדה"]',
                '[title*="Download"]',
                '[title*="הורד"]',
                'button[aria-label*="download" i]',
                '[role="button"]:has-text("Download")',
            ]
            select_all_candidates = [
                'input[type="checkbox"][aria-label*="select all" i]',
                'th input[type="checkbox"]',
                'button[aria-label*="select all" i]',
                'input[type="checkbox"][aria-label*="הכל" i]',
            ]

            async def _download_current_folder(label: str) -> Path:
                """Download whatever the currently-open folder contains as a
                ZIP. Saves to download_dir/migdal_<label>.zip. Falls back to
                the XHR capture if expect_download doesn't fire."""
                out = download_dir / f"migdal_{label}.zip"
                nonlocal xhr_capture
                # Reset XHR buffer between subfolders so we don't reuse the
                # previous one's bytes for the next folder.
                xhr_capture = {"bytes": None, "url": None}
                # Pre-unlink stale destination so a lingering Windows file-
                # handle from a previous run doesn't cause WinError 32 when
                # save_as tries to overwrite it.
                if out.exists():
                    await _retry_file_op(lambda: out.unlink(missing_ok=True))
                try:
                    async with page.expect_download(timeout=45000) as dl_info:
                        direct = await self._click_first_visible(
                            page, download_candidates, timeout=4000
                        )
                        if not direct:
                            await self._click_first_visible(
                                page, select_all_candidates, timeout=2500
                            )
                            await self._click_first_visible(
                                page, download_candidates, timeout=4000
                            )
                    download = await dl_info.value
                    # Retry on WinError 32: Playwright moves the temp download
                    # file into place and AV/Explorer can briefly lock it.
                    await _retry_file_op(lambda: download.save_as(str(out)))
                except Exception as native_err:
                    import asyncio
                    for _ in range(20):
                        if xhr_capture["bytes"]:
                            break
                        await asyncio.sleep(0.5)
                    if xhr_capture["bytes"]:
                        # XHR path: same WinError 32 guard for the fallback write.
                        await _retry_file_op(
                            lambda: out.write_bytes(xhr_capture["bytes"])
                        )
                    else:
                        raise RuntimeError(
                            f"הורדה לא הופעלה ב-{label} ({page.url}): {native_err}"
                        )
                return out

            # Step 5: iterate every Root subfolder. For each: click in,
            # download, navigate back to Root for the next iteration.
            downloaded_zips: list[Path] = []
            for idx, folder_name in enumerate(root_subfolders, start=1):
                clicked = await _click_step(f"5_{idx}_{folder_name}", [
                    f'text="{folder_name}"',
                    f'div.font-bold:has-text("{folder_name}")',
                    f'a:has-text("{folder_name}")',
                ], timeout=10000)
                if not clicked:
                    _logger.warning(
                        "Migdal: couldn't enter subfolder %r — skipping", folder_name,
                    )
                    continue
                try:
                    zip_path = await _download_current_folder(folder_name.lower())
                    downloaded_zips.append(zip_path)
                    _logger.info(
                        "Migdal: downloaded %s → %s (%d bytes)",
                        folder_name, zip_path.name, zip_path.stat().st_size,
                    )
                except Exception as e:
                    _logger.warning(
                        "Migdal: download failed for %s: %s", folder_name, e,
                    )

                # Return to Root for the next iteration (or end of loop).
                # The "Root" breadcrumb link is always present at the top of
                # the folder view inside any Root/<subfolder> page.
                await _click_step(f"5_{idx}_back", [
                    'a:has-text("Root"):not(:has-text("/"))',
                    'text="Root"',
                ], timeout=6000)

            if not downloaded_zips:
                raise RuntimeError(
                    f"לא הצלחנו להוריד אף תיקיה מ-Root ({len(root_subfolders)} ניסיונות)"
                )

            # Step 6: merge all downloaded Mimshak bundles into one xlsx
            # with a clean Hebrew filename for the production tab.
            from app.services.mimshak import merge_mimshak_zips_to_xlsx
            # Each zip was just written; on Windows a transient AV/Explorer
            # handle can still block read_bytes — retry per file.
            zip_bytes_list = [
                await _retry_file_op(lambda p=p: p.read_bytes())
                for p in downloaded_zips
            ]

            # Build the display filename from the latest period found in any
            # DAT filename inside the bundles. Pattern: `...INP\d{3}YYYYMMDD\d+.DAT`
            import re, zipfile, io
            latest_yyyymmdd = ""
            for zb in zip_bytes_list:
                try:
                    with zipfile.ZipFile(io.BytesIO(zb)) as zf:
                        for n in zf.namelist():
                            m = re.search(r'INP\d{3}(\d{8})', n.upper())
                            if m and m.group(1) > latest_yyyymmdd:
                                latest_yyyymmdd = m.group(1)
                except Exception:
                    pass

            HEBREW_MONTHS = ['', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                             'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
            if latest_yyyymmdd and len(latest_yyyymmdd) == 8:
                yyyy = latest_yyyymmdd[:4]
                mm = int(latest_yyyymmdd[4:6])
                period_label = f"{HEBREW_MONTHS[mm]} {yyyy}"
            else:
                from datetime import datetime as _dt
                now = _dt.utcnow()
                period_label = f"{HEBREW_MONTHS[now.month]} {now.year}"

            merged_xlsx = download_dir / f"מגדל - ייצור ({period_label}).xlsx"
            # Pre-unlink stale merged file before writing so openpyxl / the OS
            # doesn't hit WinError 32 on an already-open xlsx from a prior run.
            if merged_xlsx.exists():
                await _retry_file_op(lambda: merged_xlsx.unlink(missing_ok=True))
            await _retry_file_op(
                lambda: merge_mimshak_zips_to_xlsx(zip_bytes_list, merged_xlsx)
            )
            _logger.info(
                "Migdal: merged %d bundle(s) → %s",
                len(downloaded_zips), merged_xlsx.name,
            )
            target = merged_xlsx
        finally:
            page.remove_listener("response", _on_response)

        # `target` is now the merged synthetic xlsx produced by
        # merge_mimshak_zips_to_xlsx — a real Excel file. No magic-byte
        # rename needed (and would be wrong: xlsx itself starts with PK).
        results: list[Path] = [target]

        # ── Also grab נפרעים from the apmaccess APM portal (SECOND login) ──
        # mfte (production) and apmaccess (נפרעים) are different sites with their
        # own SMS OTP, so this needs a 2nd OTP via the runner's otp_provider.
        # One Migdal credential drives both (creds from the `|`-split, or the
        # same value if no delimiter). Best-effort — production is still returned.
        if otp_provider is not None and password is not None:
            apm_page = None
            try:
                from app.services.portal_automation.companies.migdal_apm import (
                    MigdalApmPortal,
                )
                from app.services.portal_automation.runner import logger as _logger
                apm_user = (username or "").split("|")[-1].strip()
                apm_pw = (password or "").split("|")[-1].strip()
                apm = MigdalApmPortal()
                apm_page = await page.context.new_page()
                # login() goes to apmaccess + submits creds → triggers the 2nd SMS
                # and waits for the OTP field.
                await apm.login(apm_page, apm_user, apm_pw)
                otp2 = await otp_provider()            # runner waits for the 2nd code
                await apm.submit_otp(apm_page, otp2)
                nif_files = await apm.download_reports(
                    apm_page, download_dir, username=apm_user
                )
                results.extend(nif_files or [])
                _logger.info(
                    "migdal: also downloaded apmaccess נפרעים → %s",
                    [f.name for f in (nif_files or [])],
                )
            except Exception as e:
                from app.services.portal_automation.runner import logger as _logger
                _logger.warning(
                    "migdal: apmaccess נפרעים grab failed (production still returned): %s", e
                )
                # Folded leg — surface on the run/batch so the merged נפרעים
                # isn't quietly missing Migdal (the standalone migdal_apm cred
                # may not exist for every user).
                self.partial_errors.append(f"נפרעים (apmaccess): {str(e)[:120]}")
            finally:
                if apm_page is not None:
                    try:
                        await apm_page.close()
                    except Exception:
                        pass

        return results

    # Legacy helper kept for the change_contact_phone flow only — the main
    # download_reports above now navigates ALL FILES → FROMMIGDAL → Root →
    # LIFE explicitly, so this best-effort Mimshak-menu probe is no longer
    # called from the happy path. Left for reference / future re-use.
    async def _try_download_mimshak(
        self,
        page: "Page",
        download_dir: Path,
        run_id: str,
    ) -> Path | None:
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
