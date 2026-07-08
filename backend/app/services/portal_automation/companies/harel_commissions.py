"""Harel (הראל) — agents-portal commission report "ריכוז תשלומי עמלות".

Distinct from the `harel` plugin (which logs in a SECOND time to the
harelsafe.co.il vault and pulls CP862 fixed-width files). This plugin stays on
the agents portal after APM+OTP and exports the clean **נפרעים** Excel from the
life/health commissions report — the same file shape as the manually-uploaded
`הראל נפרעים חיים ובריאות *.xlsx`, parsed by the existing `harel_nifraim` format.

Login + OTP are inherited from `HarelPortal` through `_HarelReportPortal`.
Shared nav helpers (_open_report, _run_filter, _vis_click_first, _vis_click_last,
_dump_frame, _get_frame, _visible_drill_cells) live in `_harel_report`.

Coverage is fully dynamic — NOTHING here hardcodes an account or agent number:
  • the מספר-חשבון dropdown is enumerated LIVE per run (`_list_accounts`) and the
    drill runs once per account (users have 1..N accounts);
  • inside each account, modal 1 lists one row PER AGENT (an agency account has
    several) — every agent row's month value is drilled and exported, not just
    the first (QA 2026-07-06: first-row-only left a measurable נפרעים gap).
Each (account, agent) pair produces its own distinctly-named file — the upload
replace-key is (user, filename, category), so names must differ to coexist.

include_in_batch=False — this plugin runs alphabetically BEFORE harel_savings.
Both hit the same F5 APM endpoint; F5 allows only ONE APM session per user at a
time, so a standalone batch entry collides with harel_savings's login ('access
policy already in progress'). harel_savings downloads both production (מוצרי
צבירה) AND this נפרעים report in a single login by calling
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


def _agent_number_from_row(row_text: str) -> str | None:
    """Pull the agent number out of a modal row like `61826 סוכן 1,824 1,824`.
    Amounts carry thousands-commas so plain digit tokens of sane length are the
    agent id; month tokens (05/2026) don't isdigit()."""
    for tok in (row_text or "").split():
        if tok.isdigit() and 3 <= len(tok) <= 7:
            return tok
    return None


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
        from app.services.portal_automation.runner import logger as _logger, _worker_note

        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 1: hangup recovery + navigate to the report + wait for frame ──
        frame = await self._open_report(page, run_id)
        await self._dump_frame(page, run_id, "1_report", frame)

        # ── Step 2: enumerate ALL accounts in the מספר-חשבון dropdown ──
        accounts = await self._list_accounts(page, frame)
        if not accounts:
            accounts = [""]  # single default account (drill whatever is selected)
        _logger.info("Harel-commissions: accounts=%s", accounts)

        files: list[Path] = []
        errors: list[str] = []
        for ai, acct in enumerate(accounts):
            try:
                got = await self._download_nifraim_for_account(
                    page, frame, acct, ai, download_dir, run_id
                )
                files.extend(got)
            except Exception as e:
                errors.append(f"{acct or 'default'}: {e}")
                _logger.warning(
                    "Harel-commissions: acct %s failed: %s", acct or "default", e
                )
                try:
                    _worker_note(f"harel_commissions: acct {acct or 'default'} FAILED: {e}")
                except Exception:
                    pass
            # Reset drill state for the next account (fresh report page).
            if ai < len(accounts) - 1:
                frame = await self._open_report(page, run_id)

        if not files:
            raise RuntimeError(
                "לא הצלחנו להוריד אקסל נפרעים מאף חשבון בהראל "
                f"({len(accounts)} חשבונות; שגיאות: {'; '.join(errors) or '—'}). "
                f"בדוק דאמפים תחת {run_id}_*"
            )
        return files

    async def _prep_account(self, page: "Page", frame, acct: str, tag: str, run_id: str):
        """Select the account (verified) and run סנן מידע; returns the filtered frame."""
        if acct:
            if not await self._select_account(page, frame, acct):
                raise RuntimeError(f"בחירת חשבון {acct} נכשלה")
        frame = await self._run_filter(page, frame)
        await self._dump_frame(page, run_id, f"3_filtered_{tag}", frame)
        return frame

    async def _drill0(self, page: "Page", frame, tag: str, run_id: str, acct: str):
        """Click the summary נפרעים cell → agent-breakdown modal (modal 1)."""
        drill0_ok = False
        for sel in (
            'td[data_colid="Schum_Nifraim"].cell_action',
            'td[data-title="נפרעים"].cell_action',
        ):
            if await self._vis_click_first(frame.locator(sel)):
                drill0_ok = True
                break
        if not drill0_ok:
            await self._dump_frame(page, run_id, f"4_no_drill0_{tag}", frame)
            raise RuntimeError(
                f"לא נמצאה תא Schum_Nifraim לקידוח בדוח (חשבון {acct or 'default'}). "
                f"בדוק {run_id}_3_filtered_{tag}.cells.txt"
            )
        await page.wait_for_timeout(3000)
        frame = await self._get_frame(page) or frame
        await self._dump_frame(page, run_id, f"4_drill0_{tag}", frame)
        return frame

    async def _download_nifraim_for_account(
        self,
        page: "Page",
        frame,
        acct: str,
        ai: int,
        download_dir: Path,
        run_id: str,
    ) -> list[Path]:
        """Export the נפרעים detail Excel for EVERY agent row in this account's
        breakdown modal. Modal 1 lists one row per agent (agencies have several);
        each row's month value drills to its own per-policy detail → its own
        file. Re-drills from the report between agents so every agent starts
        from a clean modal."""
        from app.services.portal_automation.runner import logger as _logger, _worker_note

        tag = acct or "default"
        frame = await self._prep_account(page, frame, acct, str(ai), run_id)
        frame = await self._drill0(page, frame, str(ai), run_id, acct)

        agents = await self._visible_drill_cells(frame, "_M2_Schum")
        if not agents:
            # Fall back to the legacy single-first behavior (cell shape drifted);
            # _export_agent_detail handles cell=None by using the old selectors.
            agents = [None]
        multi = len(agents) > 1
        _logger.info(
            "Harel-commissions: acct %s — %d agent row(s): %s",
            tag, len(agents),
            [(_agent_number_from_row(a["row"]) if a else "?") for a in agents],
        )
        try:
            _worker_note(f"harel_commissions: acct {tag} agents={len(agents)}")
        except Exception:
            pass

        saved: list[Path] = []
        for k in range(len(agents)):
            if k > 0:
                # Fresh drill for the next agent — modal state after an export is
                # unreliable (popup/in-frame drill may have replaced the grid).
                frame = await self._open_report(page, run_id)
                frame = await self._prep_account(page, frame, acct, f"{ai}_{k}", run_id)
                frame = await self._drill0(page, frame, f"{ai}_{k}", run_id, acct)
                cur = await self._visible_drill_cells(frame, "_M2_Schum")
                if k < len(cur):
                    agents[k] = cur[k]
            info = agents[k]
            agent_no = _agent_number_from_row(info["row"]) if info else None
            try:
                p = await self._export_agent_detail(
                    page, frame, acct, agent_no if multi else None,
                    info, f"{ai}_{k}", download_dir, run_id,
                )
                if p:
                    saved.append(p)
                    try:
                        _worker_note(
                            f"harel_commissions: acct {tag}"
                            + (f" סוכן {agent_no}" if multi and agent_no else "")
                            + f" → {p.name}"
                        )
                    except Exception:
                        pass
            except Exception as e:
                _logger.warning(
                    "Harel-commissions: acct %s agent %s export failed: %s",
                    tag, agent_no or k, e,
                )
                try:
                    _worker_note(
                        f"harel_commissions: acct {tag} agent {agent_no or k} FAILED: {e}"
                    )
                except Exception:
                    pass
        return saved

    async def _export_agent_detail(
        self,
        page: "Page",
        frame,
        acct: str,
        agent_no: str | None,
        cell_info: dict | None,
        tag: str,
        download_dir: Path,
        run_id: str,
    ) -> Path | None:
        """Drill ONE agent row's month link (popup or in-frame) and export the
        per-policy detail via bar-excel, with the XHR capture fallback."""
        from app.services.portal_automation.runner import logger as _logger

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
        popup = None
        month_title = (cell_info or {}).get("title") or None

        try:
            async def _has_detail(fr) -> bool:
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

            def _month_cell():
                """Locator for THIS agent's month cell (by absolute nth from the
                enumeration); legacy first-row selectors when enumeration failed."""
                if cell_info is not None:
                    return frame.locator(
                        'td[data_colid="_M2_Schum"].cell_action'
                    ).nth(cell_info["nth"])
                legacy = frame.locator('td[headers="_inset_1__M2_Schum"]').first
                return legacy

            if not await _has_detail(frame):
                ctx = page.context
                for method in ("force_click", "js_td", "force_dblclick"):
                    cell = _month_cell()
                    try:
                        if cell_info is None and await cell.count() == 0:
                            cell = frame.locator(
                                'td[data_colid="_M2_Schum"].cell_action'
                            ).first
                    except Exception:
                        pass
                    if month_title is None:
                        try:
                            month_title = await cell.get_attribute("data-title")
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
                    _logger.info("Harel-commissions: drill 1 opened a popup (%s)", tag)
                    try:
                        await popup.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    await popup.wait_for_timeout(2500)
                    page = popup  # export operates on the popup tab
                    frame = await self._get_frame(page) or popup.main_frame
                    await self._dump_frame(page, run_id, f"4_detail_popup_{tag}", frame)
                else:
                    await self._dump_frame(page, run_id, f"4_drill1_nopopup_{tag}", frame)
                    _logger.warning(
                        "Harel-commissions: drill 1 — no popup, no in-frame detail (%s)",
                        tag,
                    )

            # Hebrew month in the filename → correct period_month at ingest.
            # Only added when the captured data-title actually looks like a
            # month (MM/YYYY) — _period_label falls back to "now" otherwise,
            # which could stamp a wrong month.
            month_suffix = ""
            if month_title and re.search(r"\d{1,2}\s*[/\-.]\s*\d{2,4}", month_title):
                from app.services.portal_automation.companies.harel_savings import (
                    _period_label,
                )
                month_suffix = f" ({_period_label(month_title)})"
            parts = ["הראל נפרעים חיים ובריאות"]
            if acct:
                parts.append(f"- {acct}")
            if agent_no:
                parts.append(f"סוכן {agent_no}")
            base_name = " ".join(parts) + f"{month_suffix}.xlsx"
            target = download_dir / base_name

            # The report toolbar (bar-excel) renders a beat AFTER the grid loads.
            try:
                await frame.locator(
                    "button.bar-excel, [title='הדפס תצורת אקסל']"
                ).last.wait_for(state="visible", timeout=15000)
            except Exception:
                _logger.warning(
                    "Harel-commissions: bar-excel toolbar not visible after 15s "
                    "(%s); attempting export anyway", tag,
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
                    await self._dump_frame(page, run_id, f"5_export_failed_{tag}", frame)
                    raise RuntimeError(
                        f"לא הצלחנו להוריד אקסל מדוח עמלות הראל ({tag}). "
                        f"בדוק {run_id}_5_export_failed_{tag}.html: {native_err}"
                    )
        finally:
            try:
                original_page.remove_listener("response", _on_response)
            except Exception:
                pass
            # Close the drill popup so the NEXT agent/account starts from the
            # original page (leaking tabs confuses frame acquisition).
            if popup is not None:
                try:
                    await popup.close()
                except Exception:
                    pass

        _logger.info(
            "Harel-commissions: downloaded %s (%d bytes) [%s]",
            target.name,
            target.stat().st_size,
            tag,
        )
        return target
