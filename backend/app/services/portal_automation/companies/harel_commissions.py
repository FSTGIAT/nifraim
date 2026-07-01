"""Harel (הראל) — agents-portal commission report "ריכוז תשלומי עמלות".

Distinct from the `harel` plugin (which logs in a SECOND time to the
harelsafe.co.il vault and pulls CP862 fixed-width files). This plugin stays on
the agents portal after APM+OTP and exports the clean **נפרעים** Excel from the
life/health commissions report — the same file shape as the manually-uploaded
`הראל נפרעים חיים ובריאות *.xlsx`, parsed by the existing `harel_nifraim` format.

Login + OTP are inherited from `HarelPortal` through `_HarelReportPortal`.
Shared nav helpers (_open_report, _run_filter, _vis_click_first, _vis_click_last,
_dump_frame, _get_frame) all live in `_harel_report._HarelReportPortal`.

include_in_batch=False — this plugin runs alphabetically BEFORE harel_savings.
Both hit the same F5 APM endpoint; F5 allows only ONE APM session per user at a
time, so a standalone batch entry collides with harel_savings's login ('access
policy already in progress'), causing harel_savings to land on the wrong host and
never find the intellisys iframe. harel_savings already downloads both production
(מוצרי צבירה) AND this נפרעים report in a single login by calling
HarelCommissionsPortal().download_reports() on its authenticated page after the
production drills are done. Manual single-runs are unaffected.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.companies._harel_report import _HarelReportPortal

if TYPE_CHECKING:
    from playwright.async_api import Page


# The agent's first account (operator-provided). The "מספר - חשבון" param
# usually defaults to this; we still try to select it explicitly.
# TODO: promote to a per-credential field when a second account is needed.
ACCOUNT_NUMBER = "113061826"


class HarelCommissionsPortal(_HarelReportPortal):
    portal_kind = "harel_commissions"
    company_label = "הראל — ריכוז תשלומי עמלות"
    # F5-APM single-session constraint — see module docstring.
    include_in_batch = False

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        self.report_password = None
        from app.services.portal_automation.runner import logger as _logger

        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 1: hangup recovery + navigate to the report + wait for frame ──
        # _open_report handles: hangup.php3 loop, goto REPORT_PATH, 40s iframe
        # poll (3 strategies), and a last-resort full re-navigation if the BI
        # frame is still absent after the first paint.
        frame = await self._open_report(page, run_id)
        await self._dump_frame(page, run_id, "1_report", frame)

        # ── Step 2: ensure "מספר - חשבון" param is the target account ──
        # _select_account is a no-op when the account is already selected.
        await self._select_account(page, frame, ACCOUNT_NUMBER)
        await self._dump_frame(page, run_id, "2_account", frame)

        # ── Step 3: click "סנן מידע" and wait until Schum_* cells render ──
        # _run_filter polls up to 25 s for td.cell_action[data_colid^="Schum"]
        # to appear — the Intellisys BI grid builds via document.write AFTER
        # networkidle and a plain 3-second sleep races it too often.
        frame = await self._run_filter(page, frame)
        await self._dump_frame(page, run_id, "3_filtered", frame)

        # ── XHR fallback listener for the Excel export ──
        # Attached to original_page before the popup may replace `page` below.
        original_page = page
        xhr_capture: dict = {"bytes": None, "url": None, "filename": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel = (
                    "spreadsheetml" in ct
                    or "vnd.ms-excel" in ct
                    or "octet-stream" in ct
                    or ".xlsx" in url
                    or ".xls" in cd
                    or ".xlsx" in cd
                )
                if is_excel and xhr_capture["bytes"] is None:
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

        original_page.on("response", _on_response)

        try:
            # ── Step 4: two-step drill summary → agent breakdown → per-policy ──
            async def _has_detail(fr) -> bool:
                """True once per-policy columns (מבוטח/פוליסה/ענף/חודש עיבוד) appear."""
                for s in (
                    'th:has-text("מבוטח")', 'td[data-title*="מבוטח"]',
                    'th:has-text("מספר פוליסה")', 'th:has-text("סוג פוליסה")',
                    'th:has-text("ענף")', 'th:has-text("חודש עיבוד")',
                    'th:has-text("שם מבוטח")',
                ):
                    try:
                        if await fr.locator(s).count() > 0:
                            return True
                    except Exception:
                        continue
                return False

            # Drill 0 — summary נפרעים cell → agent-breakdown modal.
            drill0_ok = False
            for sel in (
                'td[data_colid="Schum_Nifraim"].cell_action',
                'td[data-title="נפרעים"].cell_action',
            ):
                if await self._vis_click_first(frame.locator(sel)):
                    drill0_ok = True
                    break
            if not drill0_ok:
                await self._dump_frame(page, run_id, "4_no_drill0", frame)
                raise RuntimeError(
                    f"לא נמצאה תא Schum_Nifraim לקידוח בדוח. "
                    f"בדוק {run_id}_3_filtered.cells.txt ו-{run_id}_4_no_drill0.cells.txt"
                )
            await page.wait_for_timeout(3000)
            frame = await self._get_frame(page) or frame
            await self._dump_frame(page, run_id, "4_drill0", frame)

            # Drill 1 — clicking the underlined month link `_inset_1__M2_Schum`
            # opens the per-policy detail. Every in-place click (plain/forced/JS)
            # left the modal DOM unchanged, which fits the link opening a NEW
            # browser tab. Capture that popup if it appears; otherwise fall back
            # to detecting an in-frame detail.
            if not await _has_detail(frame):
                ctx = page.context
                popup = None
                for method in ("force_click", "js_td", "force_dblclick"):
                    cell = frame.locator('td[headers="_inset_1__M2_Schum"]').first
                    try:
                        if await cell.count() == 0:
                            cell = frame.locator(
                                'td[data_colid="_M2_Schum"].cell_action'
                            ).first
                    except Exception:
                        pass
                    try:
                        async with ctx.expect_page(timeout=5000) as pp:
                            if method == "js_td":
                                await cell.evaluate("e => e.click()")
                            elif method == "force_dblclick":
                                await cell.dblclick(timeout=4000, force=True)
                            else:
                                await cell.click(timeout=4000, force=True)
                        popup = await pp.value
                        break
                    except Exception:
                        # No popup for this method — maybe it drilled in-place.
                        await page.wait_for_timeout(2000)
                        frame = await self._get_frame(page) or frame
                        if await _has_detail(frame):
                            break
                if popup is not None:
                    _logger.info("Harel-commissions: drill 1 opened a popup window")
                    try:
                        await popup.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    await popup.wait_for_timeout(2500)
                    page = popup  # export operates on the popup tab
                    frame = await self._get_frame(page) or popup.main_frame
                    await self._dump_frame(page, run_id, "4_detail_popup", frame)
                else:
                    await self._dump_frame(page, run_id, "4_drill1_nopopup", frame)
                    _logger.warning(
                        "Harel-commissions: drill 1 — no popup, no in-frame detail"
                    )

            # ── Step 5: export via the bar-excel button (inside the frame) ──
            # Use _vis_click_last — there are 3 bar-excel buttons in the nested
            # grids; the deepest (correct) one is appended last in the DOM.
            target = download_dir / "הראל נפרעים חיים ובריאות.xlsx"
            # The report toolbar (bar-excel) renders a beat AFTER the grid loads.
            # A batch run can reach here before it exists → intermittent
            # "no-excel-button" (works on a slower manual run, fails in the batch).
            # Wait for the toolbar button to actually appear before exporting.
            try:
                await frame.locator(
                    "button.bar-excel, [title='הדפס תצורת אקסל']"
                ).last.wait_for(state="visible", timeout=15000)
            except Exception:
                _logger.warning(
                    "Harel-commissions: bar-excel toolbar not visible after 15s; "
                    "attempting export anyway"
                )
            try:
                async with page.expect_download(timeout=30000) as dl_info:
                    ok = False
                    for sel in (
                        "button.bar-excel",
                        '[title="הדפס תצורת אקסל"]',
                    ):
                        if await self._vis_click_last(frame.locator(sel)):
                            ok = True
                            break
                    if not ok:
                        raise RuntimeError("no-excel-button")
                download = await dl_info.value
                # The portal suggests a generic "New Excel.xls" — preserve our
                # meaningful base name, just keep the real extension.
                suggested = (download.suggested_filename or "").strip().lower()
                if suggested.endswith(".xls"):
                    target = target.with_suffix(".xls")
                await download.save_as(str(target))
            except Exception as native_err:
                for _ in range(20):  # 10 s grace for XHR
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    sug = (xhr_capture["filename"] or "").strip().lower()
                    if sug.endswith(".xls"):
                        target = target.with_suffix(".xls")
                    target.write_bytes(xhr_capture["bytes"])
                else:
                    await self._dump_frame(page, run_id, "5_export_failed", frame)
                    raise RuntimeError(
                        f"לא הצלחנו להוריד אקסל מדוח עמלות הראל. "
                        f"בדוק {run_id}_5_export_failed.html "
                        f"ו-{run_id}_3_filtered.html: {native_err}"
                    )
        finally:
            try:
                original_page.remove_listener("response", _on_response)
            except Exception:
                pass

        _logger.info(
            "Harel-commissions: downloaded %s (%d bytes)",
            target.name,
            target.stat().st_size,
        )
        return [target]
