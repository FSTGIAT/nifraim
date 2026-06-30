"""Menora (מנורה) נפרעים / commission download — agent paid-commission report.

Sibling of `menora.py` (which downloads PRODUCTION rows from the same vault).
This plugin grabs the **"דוח נפרעים לסוכן"** report instead — Menora's two
report families live behind the same login/OTP, so we split them into two
portal kinds the same way Migdal does (`migdal` ייצור vs `migdal_apm` עמלות).

Login + SMS-OTP are identical to production, so `login` / `submit_otp` are
inherited from `MenoraPortal` unchanged. Only `download_reports` differs:

Flow (operator-provided 2026-06-15):
    1..3  same as production: username + phone → 6-digit OTP → /agents-site/
          → click the `כספות - AgentFilesMaster` tile (may open a popup).
    4. Click the **"דוח נפרעים לסוכן"** item.
    5. Click its download-arrow icon — a 24x24 SVG whose path is
       `m12 16 4-5h-3V4h-2v7H8z` — and save the file.

The downloaded `.xlsx` carries the standard Menora commission column signature
(`מספר ת.ז מבוטח/עמית` + `שם סוג עמלה`), so `detect_format()` returns `menora`
→ category `commission` → auto-compare vs. production. No parser changes needed.

As with production, failures (and successes) drop
`data/portal_screenshots/<run_id>_nav_*.{png,html,txt}` so selectors can be
refined from real evidence.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.companies.menora import MenoraPortal

if TYPE_CHECKING:
    from playwright.async_api import Page


# Per-row download-arrow icon path in the AgentFilesMaster vault grid. Lives
# inside a `<div style="cursor: pointer">` cell — one per row.
DOWNLOAD_ICON_PATH = "m12 16 4-5h-3V4h-2v7H8z"
# The vault labels the report "דוח ניפרעים לסוכן" (note the extra yod —
# נ־י־פ־ר־ע־י־ם). Its filename carries an `_NS` code; the sibling reports are
# `_CS` (דוח צבירות) and `_YS` (דוח יעדים), which we must NOT download.
NIFRAIM_MARKERS = ("ניפרעים", "נפרעים")
SKIP_MARKERS = ("צבירות", "יעדים")


class MenoraNifraimPortal(MenoraPortal):
    """Menora commission (נפרעים) download. Inherits login + submit_otp."""

    portal_kind = "menora_nifraim"
    company_label = "מנורה — נפרעים"
    # Folded into the consolidated `menora` plugin: the menora production run calls
    # MenoraNifraimPortal()._download_nifraim_row() in the SAME authenticated session,
    # so one Menora login yields both production and this נפרעים report. Running standalone
    # in the batch forces a redundant second login with no resent OTP → the OTP-input
    # selector never appears → 25s login timeout. Manual single-runs are unaffected.
    include_in_batch = False

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        """Standalone נפרעים run: open the כספות vault, then grab the נפרעים row."""
        self.report_password = None

        from app.services.portal_automation.runner import (
            SCREENSHOT_ROOT,
            logger as _logger,
        )

        run_id = download_dir.name
        debug_base = SCREENSHOT_ROOT / f"{run_id}_post_otp.png"
        await self._safe_screenshot(page, debug_base)
        await self._dump_page_state(page, debug_base)
        download_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 1: confirm we landed on agents-site after OTP ──
        if "/agents-site" not in page.url:
            p = SCREENSHOT_ROOT / f"{run_id}_0_not_on_agents_site.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)
            raise RuntimeError(
                f"OTP submit לא ניווט ל-/agents-site/ — נשארנו על {page.url}. "
                f"בדוק {run_id}_0_not_on_agents_site.txt"
            )

        # ── Step 2: open the כספות vault tile (may open in a popup) ──
        vault_page = await open_menora_vault(self, page, run_id)

        # ── Steps 3-4: download the נפרעים row from the open vault ──
        path = await self._download_nifraim_row(vault_page, download_dir, run_id)
        return [path]

    async def _download_nifraim_row(
        self, page: "Page", download_dir: Path, run_id: str
    ) -> Path:
        """Download the latest 'דוח ניפרעים לסוכן' from an ALREADY-OPEN Menora
        vault `page`. Self-contained (own XHR listener) so it works both for the
        standalone run and when called by the consolidated `menora` production
        run after its bundle download (same vault popup)."""
        from app.services.portal_automation.runner import (
            SCREENSHOT_ROOT,
            logger as _logger,
        )
        download_dir.mkdir(parents=True, exist_ok=True)

        async def _checkpoint(stem: str) -> Path:
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)
            return p

        # ── XHR fallback (some Menora endpoints stream via axios blob) ──
        xhr_capture: dict = {"bytes": None, "url": None, "filename": None}

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
                    or (".xls" in url and "/css" not in url)
                    or ".xlsx" in cd
                    or ".zip" in cd
                    or ".xls" in cd
                )
                if is_excel_or_zip and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
                        m = re.search(
                            r"filename\*?=(?:UTF-8'')?\"?([^\";\r\n]+)",
                            resp.headers.get("content-disposition") or "",
                            re.IGNORECASE,
                        )
                        if m:
                            xhr_capture["filename"] = m.group(1).strip()
            except Exception:
                pass

        page.on("response", _on_response)
        try:
            # ── Step 3: find the latest "דוח ניפרעים לסוכן" row ──
            await asyncio.sleep(1.5)
            for _ in range(12):
                cnt = await page.evaluate(
                    "() => document.querySelectorAll('input[type=\"checkbox\"][id^=\"rowcheck\"]').length"
                )
                if cnt:
                    break
                await asyncio.sleep(0.5)

            all_rows: list[dict] = await page.evaluate(
                """
                () => {
                    const out = [];
                    document.querySelectorAll('input[type="checkbox"][id^="rowcheck"]').forEach((cb) => {
                        const m = (cb.id || '').match(/rowcheck(\\d+)/);
                        if (!m) return;
                        const row = cb.closest('tr') || cb.parentElement;
                        const label = (row?.innerText || row?.textContent || '')
                                        .trim().replace(/\\s+/g, ' ');
                        out.push({ idx: parseInt(m[1], 10), id: cb.id, label });
                    });
                    return out;
                }
                """
            )

            def _is_nifraim(label: str) -> bool:
                hay = label.replace("_", " ")
                if any(s in hay for s in SKIP_MARKERS):
                    return False
                return any(m in hay for m in NIFRAIM_MARKERS)

            nifraim_rows = [r for r in all_rows if _is_nifraim(r["label"])]
            _logger.info(
                "Menora נפרעים: %d vault rows, %d match נפרעים filter",
                len(all_rows), len(nifraim_rows),
            )
            if not nifraim_rows:
                await _checkpoint("2_nifraim_no_match")
                raise RuntimeError(
                    f"לא נמצא דוח 'ניפרעים לסוכן' בכספת מנורה ב-{page.url} "
                    f"({len(all_rows)} שורות). בדוק {run_id}_2_nifraim_no_match.txt"
                )

            target = nifraim_rows[0]  # newest first
            _logger.info("Menora נפרעים: selected row %s — %s",
                         target["id"], target["label"][:80])
            await _checkpoint("2_nifraim_found")

            fallback_out = download_dir / "מנורה דוח ניפרעים לסוכן.zip"

            # ── Step 4: click THAT row's download-arrow icon, capture file ──
            xhr_capture.update({"bytes": None, "url": None, "filename": None})
            row_loc = page.locator(f'tr:has(#{target["id"]})')
            icon_in_row = [
                f'div[style*="cursor: pointer"]:has(svg path[d="{DOWNLOAD_ICON_PATH}"])',
                f'div:has(> svg path[d="{DOWNLOAD_ICON_PATH}"])',
                f'svg:has(path[d="{DOWNLOAD_ICON_PATH}"])',
                f'path[d="{DOWNLOAD_ICON_PATH}"]',
            ]

            async def _click_row_icon() -> bool:
                for sel in icon_in_row:
                    loc = row_loc.locator(sel).first
                    try:
                        await loc.wait_for(state="visible", timeout=3000)
                    except Exception:
                        continue
                    try:
                        await loc.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
                    try:
                        await loc.click(timeout=5000, force=True)
                        return True
                    except Exception:
                        continue
                return False

            final_path: Path | None = None
            try:
                async with page.expect_download(timeout=90000) as dl_info:
                    if not await _click_row_icon():
                        raise RuntimeError("no-row-download-icon-clicked")
                download = await dl_info.value
                suggested = (download.suggested_filename or "").strip()
                final_path = download_dir / (suggested or fallback_out.name)
                await download.save_as(str(final_path))
            except Exception as native_err:
                for _ in range(30):
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    suggested = (xhr_capture["filename"] or "").strip()
                    final_path = download_dir / (suggested or fallback_out.name)
                    final_path.write_bytes(xhr_capture["bytes"])
                else:
                    final_path = await self._fallback_checkbox_download(
                        page, download_dir, xhr_capture, _checkpoint, run_id
                    )
                    if final_path is None:
                        await _checkpoint("4_download_failed")
                        raise RuntimeError(
                            f"הורדת דוח נפרעים לא הופעלה בכספת מנורה ({page.url}). "
                            f"בדוק {run_id}_nav_4_download_failed.txt: {native_err}"
                        )

            await _checkpoint("4_downloaded")
            _logger.info(
                "Menora נפרעים: download → %s (%d bytes)",
                final_path.name, final_path.stat().st_size,
            )

            # Keep the server filename (carries the report date); only rename if
            # it lacks a נפרעים/עמלות marker so detect_format routes commission.
            name = final_path.name
            markers = NIFRAIM_MARKERS + ("עמלות",)
            if not any(m in name for m in markers):
                ext = final_path.suffix or ".zip"
                renamed = download_dir / f"מנורה דוח ניפרעים לסוכן{ext}"
                if renamed != final_path and not renamed.exists():
                    final_path.rename(renamed)
                    final_path = renamed

            return final_path
        finally:
            try:
                page.remove_listener("response", _on_response)
            except Exception:
                pass

    async def _fallback_checkbox_download(
        self,
        page: "Page",
        download_dir: Path,
        xhr_capture: dict,
        checkpoint,
        run_id: str,
    ) -> Path | None:
        """Fallback: the production-style #rowcheck grid, inverted to tick the
        נפרעים/עמלות rows and bundle them into a ZIP. Returns the saved path or
        None if no commission row matched / no download fired."""
        from app.services.portal_automation.runner import logger as _logger

        for _ in range(12):
            cnt = await page.evaluate(
                "() => document.querySelectorAll('input[type=\"checkbox\"][id^=\"rowcheck\"]').length"
            )
            if cnt:
                break
            await asyncio.sleep(0.5)

        all_rows: list[dict] = await page.evaluate(
            """
            () => {
                const out = [];
                document.querySelectorAll('input[type="checkbox"][id^="rowcheck"]').forEach((cb) => {
                    const m = (cb.id || '').match(/rowcheck(\\d+)/);
                    if (!m) return;
                    const row = cb.closest('tr') || cb.parentElement;
                    const label = (row?.innerText || row?.textContent || '')
                                    .trim().replace(/\\s+/g, ' ');
                    out.push({ id: cb.id, label });
                });
                return out;
            }
            """
        )

        def _is_nifraim(label: str) -> bool:
            hay = label.replace("_", " ")
            if any(s in hay for s in SKIP_MARKERS):
                return False
            return any(m in hay for m in NIFRAIM_MARKERS)

        matches = [r for r in all_rows if _is_nifraim(r["label"])]
        _logger.info(
            "Menora נפרעים fallback: %d rows, %d match נפרעים filter",
            len(all_rows), len(matches),
        )
        if not matches:
            return None
        # Tick only the latest (newest-first) — avoid re-pulling old months.
        wanted = matches[:1]

        for r in wanted:
            try:
                await page.check(f"#{r['id']}", timeout=4000)
            except Exception:
                try:
                    await page.click(f"#{r['id']}", timeout=2500)
                except Exception:
                    pass
        await checkpoint("3_fallback_rows_checked")

        xhr_capture.update({"bytes": None, "url": None, "filename": None})
        # Single row → prefer the individual "הורד קבצים" (the bundled
        # "מכווץ" button would nest our already-zipped file in another ZIP).
        zip_button_selectors = [
            'button.button_DocTable:has-text("הורד קבצים")',
            'button:has-text("הורד קבצים")',
            'button.button_DocTable:has-text("הורד קבצים מכווץ")',
            'button:has-text("הורד קבצים מכווץ")',
        ]
        fallback_out = download_dir / "מנורה דוח ניפרעים לסוכן.zip"
        try:
            async with page.expect_download(timeout=90000) as dl_info:
                sel = await self._click_first_visible(
                    page, zip_button_selectors, timeout=8000
                )
                if not sel:
                    raise RuntimeError("no-zip-button-visible")
            download = await dl_info.value
            suggested = (download.suggested_filename or "").strip()
            out = download_dir / (suggested or fallback_out.name)
            await download.save_as(str(out))
            return out
        except Exception:
            for _ in range(30):
                if xhr_capture["bytes"]:
                    break
                await asyncio.sleep(0.5)
            if xhr_capture["bytes"]:
                suggested = (xhr_capture["filename"] or "").strip()
                out = download_dir / (suggested or fallback_out.name)
                out.write_bytes(xhr_capture["bytes"])
                return out
        return None
