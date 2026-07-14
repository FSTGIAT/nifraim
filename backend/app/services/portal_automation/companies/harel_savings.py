"""Harel (הראל) — agents-portal PRODUCTION (מוצרי צבירה) → גמל + מגוון.

Same report as `harel_commissions` ("ריכוז תשלומי עמלות"), same login/OTP/nav, but
drills the **מוצרי צבירה** column instead of נפרעים. The drill ends in a per-managing-
company breakdown (גמל, מגוון); clicking each company's value opens a NEW TAB with a
bar-excel export. These accumulation files are reshaped into the production format with
distinct `company_source` ("הראל גמל", "הראל מגוון") so they coexist in the unified
production view.

Per operator: loop ALL accounts in the מספר-חשבון dropdown and merge each managing-
company's rows ACROSS accounts → exactly two files (one per company). Always drill the
LATEST month (top summary row; `_M2_*` = latest-month column in the modals).

Drill (per account):
  Drill 0  td[data_colid="Schum_Mutzarim_Finnasim"].cell_action   (latest-month צבירה)
  Drill 1  td[data_colid="_M2_Schum_2"].cell_action               (latest month in modal 1)
  Modal 2  per-company rows (גמל/מגוון); click each value → new tab → bar-excel
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from app.services.portal_automation.companies._harel_report import _HarelReportPortal

if TYPE_CHECKING:
    from playwright.async_api import Page

_MONTHS_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני",
    7: "יולי", 8: "אוגוסט", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}

# Source-column candidates (the צבירה export layout is discovered live).
_ID_CANDIDATES = [
    "ת.ז", "ת.ז.", "תז", "תעודת זהות", "מספר זהות", "מס זהות", "מס. זהות",
    "ת.ז עמית", "תז עמית", "ת.ז מבוטח", "תז מבוטח", "ת.ז בעל פוליסה", "זהות",
]
_NAME_CANDIDATES = ["שם מבוטח", "שם בעל הפוליסה", "שם עמית", "שם לקוח", "שם מלא", "שם"]
# NOTE: accumulation is the balance "יתרת סגירה" — NOT "צבירה/צבירה פרט/דמי ניהול"
# (that's a category label, not a number), so bare "צבירה" is intentionally excluded.
_ACCUM_CANDIDATES = [
    "יתרת סגירה", "יתרת צבירה", "צבירה כוללת", "ערך צבירה", "יתרת סוף חודש",
    'סה"כ צבירה', "סך צבירה", "יתרה",
]
# Accumulation reports have no premium/deposit AMOUNT column; avoid bare "הפקדה"/
# "פרמיה" which loose-match date columns (e.g. "תאריך הפקדה ראשונה").
_PREMIUM_CANDIDATES = ['סה"כ פרמיה', "פרמיה משולמת", "פרמיה חודשית", "סכום הפקדה", "הפקדה חודשית"]
_PRODUCT_CANDIDATES = ["סוג קופה", "סוג תוכנית", "סוג מוצר", "מוצר", "שם מוצר", "שם קופה", "ענף"]
_POLICY_CANDIDATES = [
    "מספר פוליסה", "מס' פוליסה", "פוליסה", "מספר חשבון", "מספר קופה", "מס' קופה",
    "מספר חשבון/פוליסה", "מס חשבון",
]


def _company_label_from_row(row_text: str) -> str | None:
    """Extract the חברה-מנהלת label from a modal-2 row (`גמל 6 6`,
    `קרן השתלמות 74 74`). Returns None for non-company rows: the agent rows
    still visible behind modal 2 (`61826 סוכן 1,824 …`), totals (`1,824 1,824`
    — no Hebrew token), and סה"כ rows."""
    toks = (row_text or "").split()
    label_toks: list[str] = []
    for t in toks:
        if any("֐" <= ch <= "׿" for ch in t):
            label_toks.append(t)
        elif label_toks:
            break
    label = " ".join(label_toks).strip()
    if not label or "סוכן" in label or label.startswith("סה"):
        return None
    return label


def _pick(columns, candidates):
    cset = {str(c).strip(): c for c in columns}
    for cand in candidates:
        if cand in cset:
            return cset[cand]
    for cand in candidates:
        for c in columns:
            if cand in str(c):
                return c
    return None


def _find_header_row(raw_path: Path) -> int:
    probe = pd.read_excel(raw_path, header=None, nrows=20, dtype=str)
    for i in range(len(probe)):
        cells = [str(c).strip() for c in probe.iloc[i].tolist()]
        if _pick(cells, _ID_CANDIDATES) and (
            _pick(cells, _ACCUM_CANDIDATES) or _pick(cells, _PREMIUM_CANDIDATES)
        ):
            return i
    return 0


def _split_name(full: str):
    full = (full or "").strip()
    if not full:
        return "", ""
    parts = full.split(None, 1)
    return (parts[0], "") if len(parts) == 1 else (parts[0], parts[1])


def _cell(series, i):
    v = series.iloc[i]
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v


def _period_label(month_mm_yyyy: str | None) -> str:
    """'05/2026' / '04-2026' → Hebrew 'חודש שנה'; falls back to current month."""
    if month_mm_yyyy:
        m = (re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{4})", month_mm_yyyy)
             or re.search(r"(\d{4})\s*[/\-.]\s*(\d{1,2})", month_mm_yyyy)
             or re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{2})", month_mm_yyyy))
        if m:
            a, b = m.group(1), m.group(2)
            if len(a) == 4:
                yyyy, mm = int(a), int(b)
            else:
                mm, yyyy = int(a), (int(b) if len(b) == 4 else 2000 + int(b))
            if 1 <= mm <= 12:
                return f"{_MONTHS_HE[mm]} {yyyy}"
    now = datetime.utcnow()
    return f"{_MONTHS_HE[now.month]} {now.year}"


def _period_from_df(df) -> str | None:
    """Derive the period from the export's 'חודש עיבוד' column (e.g. '04-2026')."""
    for col in df.columns:
        if "חודש עיבוד" in str(col):
            vals = df[col].dropna().astype(str)
            if len(vals):
                m = (re.search(r"\d{1,2}\s*[/\-.]\s*\d{4}", vals.iloc[0])
                     or re.search(r"\d{4}\s*[/\-.]\s*\d{1,2}", vals.iloc[0]))
                if m:
                    return _period_label(m.group(0))
            break
    return None


def _extract_production_rows(raw_path: Path, company_source: str, run_id: str, scr_root: Path,
                             account: str = ""):
    """Read a downloaded צבירה export and return normalized production-row dicts.

    `account` is the source מספר-חשבון for these rows (an agency login has 2+);
    it's stamped per-row so the merged production file / download export can show
    WHICH account each client came from (QA 2026-07-07 — 'did 061826 download?')."""
    header_row = _find_header_row(raw_path)
    df = pd.read_excel(raw_path, header=header_row, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    id_col = _pick(cols, _ID_CANDIDATES)
    name_col = _pick(cols, _NAME_CANDIDATES)
    accum_col = _pick(cols, _ACCUM_CANDIDATES)
    prem_col = _pick(cols, _PREMIUM_CANDIDATES)
    prod_col = _pick(cols, _PRODUCT_CANDIDATES)
    policy_col = _pick(cols, _POLICY_CANDIDATES)

    try:
        (scr_root / f"{run_id}_{company_source}_columns.txt").write_text(
            "HEADER ROW: %d\nSOURCE COLUMNS:\n%s\n\nMAPPING:\n"
            "  id=%s name=%s accumulation=%s premium=%s product=%s policy=%s\n"
            % (header_row, "\n".join(f"  - {c}" for c in cols),
               id_col, name_col, accum_col, prem_col, prod_col, policy_col),
            encoding="utf-8",
        )
    except Exception:
        pass

    if not id_col:
        raise RuntimeError(
            f"{company_source}: no id column among {cols} "
            f"(see {run_id}_{company_source}_columns.txt) — extend _ID_CANDIDATES"
        )

    # company_source is "הראל <label>" with a dynamic label (גמל/מגוון/פנסיה/…).
    default_prod = company_source.replace("הראל", "").strip() or "מגוון"
    rows = []
    for i in range(len(df)):
        idv = df[id_col].iloc[i]
        if idv is None or (isinstance(idv, float) and pd.isna(idv)):
            continue
        id_str = str(idv).strip()
        if not id_str or id_str.lower() in ("nan", "none"):
            continue
        first, last = _split_name(str(df[name_col].iloc[i]) if name_col else "")
        rows.append({
            "יצרן": company_source,
            "סוג מוצר": _cell(df[prod_col], i) if prod_col else default_prod,
            "מוצר": _cell(df[prod_col], i) if prod_col else default_prod,
            "מס' חשבון/פוליסה": _cell(df[policy_col], i) if policy_col else None,
            "מספר ת.ז": id_str,
            "שם פרטי לקוח": first,
            "שם משפחה לקוח": last,
            'סה"כ פרמיה': _cell(df[prem_col], i) if prem_col else None,
            "צבירה": _cell(df[accum_col], i) if accum_col else None,
            "סטטוס מוצר": "פעיל",
            "תאריך הצטרפות למוצר": None,
            "מספר סוכן": None,
            "מספר חשבון": account or None,
        })
    return rows


def _write_production_xlsx(rows, company_source: str, period_label: str, download_dir: Path) -> Path:
    out_df = pd.DataFrame(rows, columns=[
        "יצרן", "סוג מוצר", "מוצר", "מס' חשבון/פוליסה", "מספר ת.ז",
        "שם פרטי לקוח", "שם משפחה לקוח", 'סה"כ פרמיה', "צבירה",
        "סטטוס מוצר", "תאריך הצטרפות למוצר", "מספר סוכן", "מספר חשבון",
    ])
    out_path = download_dir / f"{company_source} - פרודוקציה ({period_label}).xlsx"
    out_df.to_excel(out_path, index=False)
    return out_path


class HarelSavingsPortal(_HarelReportPortal):
    portal_kind = "harel_savings"
    company_label = "הראל — מוצרי צבירה (פרודוקציה)"
    # The consolidated Harel batch credential: ONE agents-portal login downloads
    # both production (מוצרי צבירה) and נפרעים (ריכוז תשלומי עמלות). HarelPortal
    # sets include_in_batch=False (legacy safe vault) — re-enable it here.
    include_in_batch = True

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        self.report_password = None
        from app.services.portal_automation.runner import (
            SCREENSHOT_ROOT,
            _worker_note,
            logger as _logger,
        )

        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        frame = await self._open_report(page, run_id)
        await self._dump_frame(page, run_id, "sv_1_report", frame)

        accounts = await self._list_accounts(page, frame)
        if not accounts:
            accounts = [""]  # single default account
        _logger.info("harel_savings: accounts=%s", accounts)

        # Accumulate rows per managing-company ACROSS all accounts → 2 files.
        company_rows: dict[str, list] = {}
        period_label: str | None = None
        raw_idx = 0

        for ai, acct in enumerate(accounts):
            if acct:
                if not await self._select_account(page, frame, acct):
                    # A failed switch means the report still shows the PREVIOUS
                    # account — drilling now would double-count its rows into
                    # this account's slot. Skip loudly instead.
                    _logger.warning("harel_savings: acct %s — account select failed, skipping", acct)
                    try:
                        _worker_note(f"harel_savings: acct {acct} SELECT FAILED — skipped")
                    except Exception:
                        pass
                    frame = await self._open_report(page, run_id)
                    continue
            frame = await self._run_filter(page, frame)
            await self._dump_frame(page, run_id, f"sv_2_filtered_{ai}", frame)

            ctx = page.context

            async def _export_from_popup(popup, comp_label: str, uniq: str):
                """Poll the popup's frames for a visible bar-excel (the report
                loads async), then expect_download on the click. Dumps all frames
                on failure. Returns the saved raw path or None."""
                try:
                    await popup.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                found = None
                for _ in range(50):  # up to ~25s for the report to render
                    for fr in [popup.main_frame, *popup.frames]:
                        try:
                            loc = fr.locator("button.bar-excel, [title='הדפס תצורת אקסל']")
                            cnt = await loc.count()
                            for k in range(cnt):
                                if await loc.nth(k).is_visible():
                                    found = (fr, loc)
                                    break
                        except Exception:
                            continue
                        if found:
                            break
                    if found:
                        break
                    await asyncio.sleep(0.5)
                if not found:
                    try:
                        await self._dump_all_frames(
                            popup, SCREENSHOT_ROOT / f"{run_id}_sv_6_no_excel_{comp_label}_{uniq}.png"
                        )
                    except Exception:
                        pass
                    _logger.warning("harel_savings: no bar-excel in popup for הראל %s", comp_label)
                    return None
                fr, loc = found
                raw_path = download_dir / f"_raw_{comp_label}_{uniq}.xls"
                try:
                    async with popup.expect_download(timeout=30000) as dl:
                        if not await self._vis_click_last(loc):
                            raise RuntimeError("excel-click-failed")
                    download = await dl.value
                    sug = (download.suggested_filename or "").lower()
                    if sug.endswith(".xlsx"):
                        raw_path = raw_path.with_suffix(".xlsx")
                    await download.save_as(str(raw_path))
                    return raw_path
                except Exception as e:
                    _logger.warning("harel_savings: download failed for הראל %s: %s", comp_label, e)
                    return None

            async def _drill0_savings(fr, tag: str):
                """Click the latest-month מוצרי צבירה cell → agent-breakdown
                modal 1. Returns the re-acquired frame or None."""
                if not await self._vis_click_first(
                    fr.locator('td[data_colid="Schum_Mutzarim_Finnasim"].cell_action')
                ):
                    await self._dump_frame(page, run_id, f"sv_3_no_drill0_{tag}", fr)
                    return None
                await page.wait_for_timeout(2500)
                fr = await self._get_frame(page) or fr
                await self._dump_frame(page, run_id, f"sv_3_modal1_{tag}", fr)
                return fr

            def _agent_rows(cells: list[dict]) -> list[dict]:
                """Modal-1 rows are one per AGENT (`61826 סוכן 1,824 …`); an
                agency account lists several. The bottom total row has no
                'סוכן' token. Falls back to the first visible cell when the
                shape drifts, preserving the legacy single-drill behavior."""
                agents = [c for c in cells if "סוכן" in (c.get("row") or "")]
                return agents or cells[:1]

            _before = {k: len(v) for k, v in company_rows.items()}

            f0 = await _drill0_savings(frame, str(ai))
            if f0 is None:
                _logger.warning("harel_savings: acct %s — מוצרי צבירה cell not found", acct)
                try:
                    _worker_note(f"harel_savings: acct {acct or 'default'} drill0 FAILED (מוצרי צבירה cell)")
                except Exception:
                    pass
                frame = await self._open_report(page, run_id)
                continue
            frame = f0

            # Modal 1 — enumerate ALL agent rows (never just .first: an agency
            # account has several agents; QA measured the missing share).
            agent_cells = _agent_rows(await self._visible_drill_cells(frame, "_M2_Schum_2"))
            if not agent_cells:
                _logger.warning("harel_savings: acct %s — _M2_Schum_2 (modal1) not found", acct)
                try:
                    _worker_note(f"harel_savings: acct {acct or 'default'} drill1 FAILED (_M2_Schum_2)")
                except Exception:
                    pass
                await self._dump_frame(page, run_id, f"sv_4_no_drill1_{ai}", frame)
                frame = await self._open_report(page, run_id)
                continue
            try:
                _worker_note(f"harel_savings: acct {acct or 'default'} agents={len(agent_cells)}")
            except Exception:
                pass

            for gi in range(len(agent_cells)):
                if gi > 0:
                    # Fresh drill for the next agent — modal state after the
                    # previous agent's popups is unreliable.
                    frame = await self._open_report(page, run_id)
                    if acct and not await self._select_account(page, frame, acct):
                        _logger.warning("harel_savings: acct %s — reselect failed (agent %d)", acct, gi)
                        break
                    frame = await self._run_filter(page, frame)
                    f0 = await _drill0_savings(frame, f"{ai}_{gi}")
                    if f0 is None:
                        continue
                    frame = f0
                    cur = _agent_rows(await self._visible_drill_cells(frame, "_M2_Schum_2"))
                    if gi < len(cur):
                        agent_cells[gi] = cur[gi]

                # Drill 1 — THIS agent's latest-month cell → modal 2. The period
                # is the DRILLED month (the _M2 column's data-title, e.g.
                # "05/2026") — NOT the lagging חודש עיבוד processing month.
                acell = frame.locator('td[data_colid="_M2_Schum_2"].cell_action').nth(
                    agent_cells[gi]["nth"]
                )
                try:
                    await acell.click(timeout=5000, force=True)
                except Exception as e:
                    _logger.warning("harel_savings: acct %s agent %d — modal1 click failed: %s", acct, gi, e)
                    continue
                await page.wait_for_timeout(2500)
                frame = await self._get_frame(page) or frame
                await self._dump_frame(page, run_id, f"sv_5_modal2_{ai}_{gi}", frame)

                # Modal 2 — enumerate ALL חברה-מנהלת rows dynamically (גמל,
                # מגוון, פנסיה, …) instead of a hardcoded pair; the label filter
                # drops the total row and the modal-1 agent rows behind it.
                comps: list[tuple[str, dict]] = []
                for c in await self._visible_drill_cells(frame, "_M2_Schum_2"):
                    label = _company_label_from_row(c.get("row") or "")
                    if label:
                        comps.append((label, c))
                if not comps:
                    _logger.warning("harel_savings: acct %s agent %d — no company rows in modal2", acct, gi)
                    try:
                        _worker_note(f"harel_savings: acct {acct or 'default'} agent {gi} — modal2 empty")
                    except Exception:
                        pass
                    continue

                for comp_label, cinfo in comps:
                    company_source = f"הראל {comp_label}"
                    if period_label is None and cinfo.get("title"):
                        if re.search(r"\d{1,2}\s*[/\-.]\s*\d{2,4}", cinfo["title"]):
                            period_label = _period_label(cinfo["title"])
                    cell = frame.locator('td[data_colid="_M2_Schum_2"].cell_action').nth(
                        cinfo["nth"]
                    )
                    popup = None
                    try:
                        async with ctx.expect_page(timeout=8000) as pp:
                            await cell.click(timeout=5000, force=True)
                        popup = await pp.value
                    except Exception:
                        _logger.warning("harel_savings: no popup for %s", company_source)
                        continue
                    raw_path = await _export_from_popup(popup, comp_label, f"{ai}_{gi}")
                    if raw_path:
                        try:
                            rows = _extract_production_rows(raw_path, company_source, run_id, SCREENSHOT_ROOT, account=acct or "")
                            company_rows.setdefault(company_source, []).extend(rows)
                            _logger.info("harel_savings: %s acct %s → +%d rows", company_source, acct, len(rows))
                        except Exception as e:
                            _logger.warning("harel_savings: reshape failed for %s: %s", company_source, e)
                    try:
                        await popup.close()
                    except Exception:
                        pass
                    frame = await self._get_frame(page) or frame

            # Per-account coverage note → Railway WORKER-LOG, so a silently
            # missing account/company is visible without pulling worker dumps.
            try:
                added = {
                    k: len(v) - _before.get(k, 0)
                    for k, v in company_rows.items()
                    if len(v) - _before.get(k, 0)
                }
                _worker_note(
                    f"harel_savings: acct {acct or 'default'} → "
                    + (", ".join(f"{k} +{n}" for k, n in added.items()) or "no rows")
                )
            except Exception:
                pass

            # Return to the report params for the next account.
            frame = await self._open_report(page, run_id)

        # Write one production file per managing-company (merged across accounts).
        period_label = period_label or _period_label(None)
        out_paths: list[Path] = []
        for company_source, rows in company_rows.items():
            if not rows:
                continue
            try:
                p = _write_production_xlsx(rows, company_source, period_label, download_dir)
                out_paths.append(p)
                _logger.info("harel_savings: wrote %s (%d rows)", p.name, len(rows))
            except Exception as e:
                _logger.warning("harel_savings: write failed for %s: %s", company_source, e)
                self.partial_errors.append(f"פרודוקציה {company_source}: {str(e)[:120]}")

        results = list(out_paths)
        if not out_paths:
            _logger.warning("harel: no production files produced; continuing to נפרעים")
            self.partial_errors.append("פרודוקציה: לא הופקו קבצים")

        # ── Also grab נפרעים from the SAME authenticated agents-portal session ──
        # One Harel login → both production (מוצרי צבירה) AND נפרעים (ריכוז תשלומי
        # עמלות). harel_commissions.download_reports re-navigates to the report
        # itself (hangup recovery + goto), so calling it on this already-
        # authenticated page works WITHOUT a second login/OTP. Tolerate failure.
        try:
            from app.services.portal_automation.companies.harel_commissions import (
                HarelCommissionsPortal,
            )
            nif_files = await HarelCommissionsPortal().download_reports(
                page, download_dir, username=username
            )
            results.extend(nif_files or [])
            _logger.info(
                "harel: also downloaded נפרעים → %s",
                [p.name for p in (nif_files or [])],
            )
        except Exception as e:
            _logger.warning("harel: נפרעים grab failed (production still returned): %s", e)
            # Folded leg — losing it silently drops ALL Harel נפרעים from the
            # merged file (harel_commissions never runs standalone in a batch).
            self.partial_errors.append(f"נפרעים: {str(e)[:120]}")

        if not results:
            raise RuntimeError(
                f"harel: לא הופקו קבצים (פרודוקציה+נפרעים). בדוק דאמפים תחת {run_id}_*"
            )
        return results
