"""Phoenix נפרעים גמל → unified production file (UI download).

Sibling of `phoenix_nifraim` (חא"ט ובריאות). Same agentportal Angular SPA, same
inherited login + OTP, but a DIFFERENT report and a DIFFERENT download trigger:

    עמלות  →  עמלות נפרעים והפרשי סוכנויות גמל  →  (wait)  →  "להורדת דוח אקסל"

The גמל report's column layout differs from the חא"ט one and isn't known up
front, so the transform **auto-discovers** id / name / premium / accumulation /
product columns from a candidate list (and logs every source column to an
artifact so the mapping can be tightened).

Routing: reshaped into the production signature and ingested as production with
**company_source = "הפניקס גמל"** — a distinct company from the חא"ט file's
"הפניקס" so the per-company production replacement doesn't deactivate one when the
other is ingested; both coexist in the unified production view. See
[phoenix_nifraim] and [unified_production_per_month].
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from app.services.portal_automation.companies.phoenix_nifraim import (
    PhoenixNifraimPortal,
    _split_name,
    _period_label,
    _cell,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

GEMEL_COMPANY = "הפניקס גמל"

# Candidate source headers (גמל layout unknown up front — match the first present).
_ID_CANDIDATES = [
    "תז העמית", "ת.ז עמית", "ת.ז. עמית", "תז עמית", "תז המבוטח", "ת.ז מבוטח",
    "תעודת זהות", "מספר זהות", "מס זהות", "מס. זהות", "ת.ז", "ת.ז.", "זהות",
]
_NAME_CANDIDATES = ["שם העמית", "שם המבוטח", "שם מלא", "שם הלקוח", "שם"]
_PREMIUM_CANDIDATES = [
    'סה"כ פרמיה', "פרמיה", "פרמיה משולמת", "הפקדה", "הפקדה חודשית",
    "סכום הפקדה", "פרמיה חודשית",
]
_ACCUM_CANDIDATES = [
    "צבירה", "יתרת סוף חודש", "יתרה", "צבירה כוללת", "ערך צבירה", "יתרת צבירה",
]
_PRODUCT_CANDIDATES = ["סוג מוצר", "מוצר", "סוג קופה", "שם מוצר", "שם קופה", "ענף"]
_POLICY_CANDIDATES = [
    "מספר פוליסה", "מס' פוליסה", "מספר חשבון", "מספר קופה", "מס' קופה",
    "מספר חשבון/פוליסה", "מס חשבון",
]


class PhoenixNifraimGemelPortal(PhoenixNifraimPortal):
    portal_kind = "phoenix_nifraim_gemel"
    company_label = "הפניקס גמל"
    # login / submit_otp / OTP_FIELD inherited (via PhoenixNifraimPortal → PhoenixPortal).
    # Excluded from the batch: phoenix_nifraim now downloads BOTH the חא"ט and the
    # גמל reports in a single login (see PhoenixNifraimPortal.download_reports), so
    # running this separately would burn a second Phoenix OTP for the same data.
    # Still registered for manual single-run use.
    include_in_batch = False

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        """Single-run path: one login → just the גמל report.

        In the "run all" batch this report is also downloaded by the consolidated
        phoenix_nifraim plugin (same login as the חא"ט report), so this plugin is
        marked `include_in_batch = False` and only runs on an explicit manual
        single run."""
        self.report_password = None
        download_dir.mkdir(parents=True, exist_ok=True)

        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name

        # Dismiss any post-login modal, then download the גמל report.
        await page.wait_for_timeout(2000)
        await self._click_first_visible(
            page,
            [
                "button:has-text('סגור')",
                "button:has-text('אישור')",
                "button:has-text('הבנתי')",
                ".modal-close",
                "[aria-label='Close']",
                "[aria-label='סגור']",
            ],
            timeout=4000,
        )
        p = SCREENSHOT_ROOT / f"{run_id}_gm_0_post_otp.png"
        await self._safe_screenshot(page, p)
        await self._dump_page_state(page, p)
        root_url = page.url

        return [await download_gemel_report(self, page, download_dir, run_id, root_url)]


# ── Report download helper (shared by the consolidated + single-run flows) ─────

async def download_gemel_report(
    plugin, root_page: "Page", download_dir: Path, run_id: str, root_url: str,
    as_commission: bool = False,
) -> Path:
    """Download the נפרעים גמל report.

    `as_commission=False` (default, manual single-run): reshape to the production
    schema. `as_commission=True` (consolidated batch run): keep the RAW report —
    it natively detects as commission (company הפניקס) → lands on the נפרעים side.
    Operates from the SPA dashboard `root_page` (modal already dismissed); a
    report tab is closed afterwards. Raises (with artifacts) on failure."""
    from app.services.portal_automation.runner import SCREENSHOT_ROOT
    from app.services.portal_automation.companies.phoenix_nifraim import ensure_dashboard

    async def _checkpoint(pg: "Page", stem: str) -> None:
        p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
        await plugin._safe_screenshot(pg, p)
        await plugin._dump_page_state(pg, p)

    def _fail(stem: str, msg: str) -> "RuntimeError":
        return RuntimeError(f"{msg} (see {run_id}_{stem}.{{png,html,txt}})")

    await ensure_dashboard(plugin, root_page, root_url)

    # Step 1: expand the "עמלות" accordion and reveal the גמל report link.
    # Uniquely matched by נפרעים + גמל (the חא"ט reports lack גמל; the "הפרשי"/
    # "היקף" reports lack נפרעים).
    gemel_link = root_page.locator("a:has-text('נפרעים'):has-text('גמל')").first
    amlot_header = root_page.get_by_text("עמלות", exact=True).first
    expanded = False
    for _ in range(3):
        try:
            if await gemel_link.is_visible():
                expanded = True
                break
        except Exception:
            pass
        try:
            await amlot_header.click(timeout=5000)
        except Exception:
            pass
        await root_page.wait_for_timeout(1200)
    if not expanded:
        try:
            expanded = await gemel_link.is_visible()
        except Exception:
            expanded = False
    await _checkpoint(root_page, "gm_1_amlot")
    if not expanded:
        await _checkpoint(root_page, "gm_1_amlot_no_match")
        raise _fail(
            "gm_1_amlot_no_match",
            "Phoenix גמל: could not expand 'עמלות' to reveal the גמל link",
        )

    # Step 2: click the גמל report link (same-tab or new-tab).
    pages_before = set(root_page.context.pages)
    try:
        await gemel_link.click(timeout=8000)
    except Exception:
        await _checkpoint(root_page, "gm_2_gemel_no_match")
        raise _fail("gm_2_gemel_no_match", "Phoenix גמל: גמל link click failed")
    await root_page.wait_for_timeout(2500)
    new_pages = [pg for pg in root_page.context.pages if pg not in pages_before]
    report_page = new_pages[-1] if new_pages else root_page
    opened_new_tab = report_page is not root_page
    if opened_new_tab:
        try:
            await report_page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass

    page = report_page  # all download steps operate on the report view
    try:
        # Let the גמל report render — the operator notes it needs a few seconds
        # before the "להורדת דוח אקסל" button is ready.
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(5000)
        await _checkpoint(page, "gm_2_gemel")

        # Step 3: click "להורדת דוח אקסל" and capture the export. The export is
        # NOT a Playwright-catchable download (native expect_download timed out at
        # 90s in earlier runs), so we record EVERY response during the click
        # window, dump them for diagnosis, and capture the bytes of the response
        # that looks like the xlsx file (broad heuristic, not just content-type).
        responses_log: list[str] = []
        file_capture: dict = {"bytes": None, "url": None, "best_len": 0}

        def _looks_like_file(ct: str, cd: str, url: str) -> bool:
            return (
                "spreadsheet" in ct or "excel" in ct or "octet-stream" in ct
                or "zip" in ct or "csv" in ct or "attachment" in cd
                or any(url.endswith(e) for e in (".xlsx", ".xls", ".csv", ".zip"))
                or any(k in url for k in ("export", "excel", "toexcel", "download", "/report"))
            )

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url
                lu = url.lower()
                clen = resp.headers.get("content-length") or "?"
                responses_log.append(f"{resp.status} len={clen} ct={ct} cd={cd[:60]} {url[:160]}")
                if _looks_like_file(ct, cd, lu):
                    body = await resp.body()
                    # keep the largest non-html candidate (the xlsx is binary/large)
                    if body and len(body) > file_capture["best_len"] and b"<html" not in body[:200].lower():
                        file_capture["bytes"] = body
                        file_capture["url"] = url
                        file_capture["best_len"] = len(body)
            except Exception:
                pass

        raw_path = download_dir / "phoenix_gemel_raw.xlsx"
        download_selectors = [
            "fnx-client-table-export-to-excel img[src*='excel.svg']",
            "fnx-client-table-export-to-excel button",
            "button:has(img[src*='excel.svg']):has-text('להורדת')",
            "button:has-text('להורדת דוח אקסל')",
            "a:has-text('להורדת דוח אקסל')",
            "img[src*='excel.svg']",
        ]
        try:
            await page.wait_for_selector("text=להורדת דוח אקסל", state="visible", timeout=15000)
        except Exception:
            pass

        ctx_dl: dict = {"obj": None}
        def _on_ctx_download(d):
            if ctx_dl["obj"] is None:
                ctx_dl["obj"] = d
        page.context.on("download", _on_ctx_download)
        page.on("response", _on_response)
        try:
            # The "להורדת דוח אקסל" button carries aria-haspopup="menu" — clicking
            # it opens a DROPDOWN (e.g. current-page vs full-report), it does NOT
            # download directly. So: (1) click the trigger, (2) click the menu item
            # that actually exports, capturing the download.
            trigger_ok = await self._click_first_visible(page, download_selectors, timeout=12000)
            if not trigger_ok:
                await _checkpoint(page, "gm_3_no_button")
                raise _fail("gm_3_no_button", "Phoenix גמל: 'להורדת דוח אקסל' trigger not found")
            await page.wait_for_timeout(1500)

            # Dump any menu items that appeared, for diagnosis / selector tuning.
            try:
                items = await page.evaluate(
                    """() => [...document.querySelectorAll('[role=menuitem], .mat-mdc-menu-item, .cdk-overlay-pane button, .cdk-overlay-pane a')]
                        .map(el => (el.innerText || el.textContent || '').trim().replace(/\\s+/g,' '))
                        .filter(t => t)"""
                )
            except Exception:
                items = []
            try:
                (SCREENSHOT_ROOT / f"{run_id}_gm_3_menu.txt").write_text(
                    "MENU ITEMS AFTER TRIGGER:\n" + "\n".join(f"  - {t}" for t in items),
                    encoding="utf-8",
                )
            except Exception:
                pass
            await _checkpoint(page, "gm_3_menu")

            # Click the export action inside the menu. Prefer a "full report"
            # option; fall back to anything excel-ish, then the first menu item.
            action_selectors = [
                "[role='menuitem']:has-text('כל')",
                "[role='menuitem']:has-text('מלא')",
                "[role='menuitem']:has-text('אקסל')",
                "[role='menuitem']:has-text('Excel')",
                "[role='menuitem']:has-text('ייצוא')",
                "[role='menuitem']:has-text('הורד')",
                ".mat-mdc-menu-item:has-text('אקסל')",
                ".cdk-overlay-pane button:has-text('אקסל')",
                "[role='menuitem']",
                ".mat-mdc-menu-item",
            ]
            action_matched = None
            try:
                async with page.expect_download(timeout=60000) as dl_info:
                    action_matched = await self._click_first_visible(page, action_selectors, timeout=8000)
                    if not action_matched:
                        # No menu appeared — maybe the trigger itself downloads but
                        # was slow; just wait on the native event from the trigger.
                        pass
                download = await dl_info.value
                await download.save_as(str(raw_path))
            except Exception as native_err:
                logger.info(
                    "phoenix_gemel: no native download (menu action=%s); collecting responses (%s)",
                    action_matched, native_err,
                )
                for _ in range(50):  # up to 25s
                    if file_capture["bytes"] or ctx_dl["obj"] is not None:
                        break
                    await asyncio.sleep(0.5)
                try:
                    (SCREENSHOT_ROOT / f"{run_id}_gm_3_responses.txt").write_text(
                        f"trigger: {trigger_ok}  menu_action: {action_matched}\n"
                        f"menu items: {items}\n"
                        f"best file len: {file_capture['best_len']} url: {file_capture['url']}\n\n"
                        "ALL RESPONSES:\n" + "\n".join(responses_log),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                if ctx_dl["obj"] is not None:
                    await ctx_dl["obj"].save_as(str(raw_path))
                elif file_capture["bytes"]:
                    raw_path.write_bytes(file_capture["bytes"])
                else:
                    await _checkpoint(page, "gm_3_download_fail")
                    raise _fail(
                        "gm_3_download_fail",
                        f"Phoenix גמל: export produced no file ({native_err})",
                    )
        finally:
            page.remove_listener("response", _on_response)
            try:
                page.context.remove_listener("download", _on_ctx_download)
            except Exception:
                pass

        await _checkpoint(page, "gm_3_downloaded")
        logger.info(
            "phoenix_gemel: raw report saved %s (%d bytes)",
            raw_path.name, raw_path.stat().st_size,
        )

        if as_commission:
            out = download_dir / "הפניקס נפרעים גמל.xlsx"
            raw_path.rename(out)
            logger.info("phoenix_gemel: נפרעים (commission) file %s", out.name)
            return out
        production_xlsx = _gemel_to_production_xlsx(raw_path, download_dir, run_id, SCREENSHOT_ROOT)
        logger.info("phoenix_gemel: built production file %s", production_xlsx.name)
        return production_xlsx
    finally:
        if opened_new_tab:
            try:
                await report_page.close()
            except Exception:
                pass


# ── גמל → production schema transform (column auto-discovery) ──────────────────

def _pick(columns: list[str], candidates: list[str]) -> str | None:
    cset = {c.strip(): c for c in columns}
    for cand in candidates:
        if cand in cset:
            return cset[cand]
    # loose contains-match fallback
    for cand in candidates:
        for c in columns:
            if cand in c:
                return c
    return None


def _find_header_row(raw_path: Path) -> int:
    probe = pd.read_excel(raw_path, header=None, nrows=20, dtype=str)
    for i in range(len(probe)):
        cells = [str(c).strip() for c in probe.iloc[i].tolist()]
        if _pick(cells, _ID_CANDIDATES) and (
            _pick(cells, _PREMIUM_CANDIDATES) or _pick(cells, _ACCUM_CANDIDATES)
        ):
            return i
    return 0


def _gemel_to_production_xlsx(
    raw_path: Path, download_dir: Path, run_id: str, screenshot_root: Path
) -> Path:
    header_row = _find_header_row(raw_path)
    df = pd.read_excel(raw_path, header=header_row, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    id_col = _pick(cols, _ID_CANDIDATES)
    name_col = _pick(cols, _NAME_CANDIDATES)
    prem_col = _pick(cols, _PREMIUM_CANDIDATES)
    accum_col = _pick(cols, _ACCUM_CANDIDATES)
    prod_col = _pick(cols, _PRODUCT_CANDIDATES)
    policy_col = _pick(cols, _POLICY_CANDIDATES)

    # Log the discovered mapping + all source columns for tightening later.
    try:
        (screenshot_root / f"{run_id}_gm_columns.txt").write_text(
            "HEADER ROW: %d\n\nSOURCE COLUMNS:\n%s\n\nMAPPING:\n"
            "  id=%s  name=%s  premium=%s  accumulation=%s  product=%s  policy=%s\n"
            % (
                header_row, "\n".join(f"  - {c}" for c in cols),
                id_col, name_col, prem_col, accum_col, prod_col, policy_col,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    if not id_col:
        raise RuntimeError(
            f"Phoenix גמל: no id column found among {cols} "
            f"(see {run_id}_gm_columns.txt) — extend _ID_CANDIDATES"
        )

    ids = df[id_col]
    out_rows = []
    for i in range(len(df)):
        id_raw = ids.iloc[i]
        if id_raw is None or (isinstance(id_raw, float) and pd.isna(id_raw)):
            continue
        id_str = str(id_raw).strip()
        if not id_str or id_str.lower() in ("nan", "none"):
            continue
        first, last = _split_name(str(df[name_col].iloc[i]) if name_col else "")
        out_rows.append({
            "יצרן": GEMEL_COMPANY,
            "סוג מוצר": _cell(df[prod_col], i) if prod_col else "גמל",
            "מוצר": _cell(df[prod_col], i) if prod_col else "גמל",
            "מס' חשבון/פוליסה": _cell(df[policy_col], i) if policy_col else None,
            "מספר ת.ז": id_str,
            "שם פרטי לקוח": first,
            "שם משפחה לקוח": last,
            'סה"כ פרמיה': _cell(df[prem_col], i) if prem_col else None,
            "צבירה": _cell(df[accum_col], i) if accum_col else None,
            "סטטוס מוצר": "פעיל",
            "תאריך הצטרפות למוצר": None,
            "מספר סוכן": None,
        })

    if not out_rows:
        raise RuntimeError("Phoenix גמל: no data rows with an id_number to convert")

    out_df = pd.DataFrame(out_rows, columns=[
        "יצרן", "סוג מוצר", "מוצר", "מס' חשבון/פוליסה", "מספר ת.ז",
        "שם פרטי לקוח", "שם משפחה לקוח", 'סה"כ פרמיה', "צבירה",
        "סטטוס מוצר", "תאריך הצטרפות למוצר", "מספר סוכן",
    ])

    period = _period_label(df)
    out_path = download_dir / f"הפניקס גמל - פרודוקציה ({period}).xlsx"
    out_df.to_excel(out_path, index=False)
    logger.info("phoenix_gemel: %d rows → %s", len(out_df), out_path.name)
    return out_path
