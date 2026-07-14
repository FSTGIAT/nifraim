"""Phoenix נפרעים חיים ובריאות → unified production file (UI download).

The main `phoenix` plugin drives the legacy Ericom green-screen terminal (a dead
end for automation) and is intentionally left untouched. This plugin instead
grabs the **עמלות נפרעים חא"ט ובריאות** report from Phoenix's modern Angular SPA
(`fnx-nx-ui`) at `agentportal.fnx.co.il/digital-services/`, which is fully
scrapeable:

    עמלות  →  עמלות נפרעים חא"ט ובריאות  →  excel download icon

Login + OTP are identical to the main portal (F5 BIG-IP APM, errorcode-19
recovery, "קוד זיהוי" OTP), so we **subclass `PhoenixPortal`** and inherit
`login` / `submit_otp` / `OTP_FIELD` verbatim — only `download_reports` differs.

Routing to PRODUCTION (per the operator): the נפרעים report's columns
(`{תז המבוטח, סה"כ לתשלום}`) are detected as *commission* by the parser. So —
exactly like the Migdal plugin emits a production-schema XLSX — this plugin
**reshapes** the downloaded file into a sheet carrying the production signature
(`{'סה"כ פרמיה', "סטטוס מוצר", "יצרן"}`) and names it with "פרודוקציה", so the
ingest pipeline detects it as `production` and aggregates it alongside
Migdal/Menora in the unified production file (no parser/API/frontend changes).
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from app.services.portal_automation.companies.phoenix import PhoenixPortal

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

HEBREW_MONTHS = [
    "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]


class PhoenixNifraimPortal(PhoenixPortal):
    portal_kind = "phoenix_nifraim"
    company_label = "הפניקס"
    # login / submit_otp / OTP_FIELD inherited from PhoenixPortal unchanged.
    # PhoenixPortal sets include_in_batch=False (dead-end terminal); re-enable it
    # here — this is THE batch entry point for Phoenix נפרעים (downloads both the
    # חא"ט and גמל reports in one login).
    include_in_batch = True

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        password: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        """One Phoenix login → BOTH נפרעים reports + the SFE-vault production.

        The agentportal SMS login (one OTP) downloads the חא"ט ובריאות and גמל
        נפרעים reports, emitted as their natural COMMISSION files (הפניקס). Then,
        WITHOUT a second OTP, the no-OTP SFE כספת vault (sfe.fnx.co.il, same
        creds) is opened in a fresh page to grab the holdings .DAT PRODUCTION
        file. Result: Phoenix contributes BOTH production (SFE) and נפרעים
        (agentportal) from a single credential. Each step is best-effort —
        whatever succeeds is returned.
        """
        self.report_password = None
        download_dir.mkdir(parents=True, exist_ok=True)

        from app.services.portal_automation.runner import SCREENSHOT_ROOT, PROJECT_ROOT
        run_id = download_dir.name

        # ── Hand the authenticated Phoenix session to phoenix_terminal ──
        # F5 allows ONE session/OTP per user, so phoenix_terminal's separate
        # native-Edge login can NEVER get its own OTP while this session is live
        # (QA 2026-07-07). Save this already-authenticated session's cookies so
        # the terminal flow REUSES it → in run-all, no second OTP ever. Path is
        # per-worker (PHOENIX_SESSION_FILE override), never a hardcoded user dir.
        try:
            import os as _os
            from pathlib import Path as _P
            sf = _os.environ.get("PHOENIX_SESSION_FILE") or str(
                PROJECT_ROOT / "data" / "phoenix_session.json"
            )
            _P(sf).parent.mkdir(parents=True, exist_ok=True)
            await page.context.storage_state(path=sf)
            print(f">> saved Phoenix session for terminal reuse: {sf}", flush=True)
        except Exception as _e:
            print(f">> phoenix session save skipped: {_e}", flush=True)

        # Step 0: settle + dismiss any post-login modal — once, for both reports.
        await page.wait_for_timeout(2000)
        await self._click_first_visible(
            page,
            [
                "button:has-text('קראתי והבנתי')",  # privacy/consent banner (2026-06)
                "button:has-text('סגור')",
                "button:has-text('אישור')",
                "button:has-text('הבנתי')",
                ".modal-close",
                "[aria-label='Close']",
                "[aria-label='סגור']",
            ],
            timeout=4000,
        )
        p = SCREENSHOT_ROOT / f"{run_id}_nx_0_post_otp.png"
        await self._safe_screenshot(page, p)
        await self._dump_page_state(page, p)
        root_url = page.url

        results: list[Path] = []

        # נפרעים 1: חא"ט ובריאות → commission (הפניקס).
        try:
            results.append(
                await download_health_report(
                    self, page, download_dir, run_id, root_url, as_commission=True
                )
            )
        except Exception as e:
            logger.warning("phoenix_nifraim: חא\"ט/בריאות report failed: %s", e)
            # Best-effort legs must surface on the run/batch, not just the
            # worker log — a missed leg means a whole Phoenix slice is absent
            # from the merged נפרעים while the run shows success.
            self.partial_errors.append(f"נפרעים חא\"ט/בריאות: {str(e)[:120]}")

        # נפרעים 2: גמל → commission (הפניקס). Lazy import avoids a circular dep.
        try:
            from app.services.portal_automation.companies.phoenix_nifraim_gemel import (
                download_gemel_report,
            )
            results.append(
                await download_gemel_report(
                    self, page, download_dir, run_id, root_url, as_commission=True
                )
            )
        except Exception as e:
            logger.warning("phoenix_nifraim: גמל report failed: %s", e)
            self.partial_errors.append(f"נפרעים גמל: {str(e)[:120]}")

        # PRODUCTION: the no-OTP SFE כספת vault (same creds, separate site). Open
        # it in a fresh page so the agentportal session is untouched. Needs the
        # password (passed by the runner's inspect-dispatch). Best-effort.
        if password:
            sfe_page = None
            try:
                from app.services.portal_automation.companies.phoenix_sfe import (
                    PhoenixSfePortal,
                )
                sfe = PhoenixSfePortal()
                sfe_page = await page.context.new_page()
                await sfe.login(sfe_page, username or "", password)
                sfe_files = await sfe.download_reports(
                    sfe_page, download_dir, username=username
                )
                results.extend(sfe_files or [])
                logger.info(
                    "phoenix_nifraim: SFE production → %s",
                    [f.name for f in (sfe_files or [])],
                )
            except Exception as e:
                logger.warning("phoenix_nifraim: SFE production grab failed: %s", e)
                self.partial_errors.append(f"פרודוקציה (SFE): {str(e)[:120]}")
            finally:
                if sfe_page is not None:
                    try:
                        await sfe_page.close()
                    except Exception:
                        pass

        if not results:
            raise RuntimeError(
                f"Phoenix: all reports failed — see {run_id}_nx_* / {run_id}_gm_* artifacts"
            )
        return results


# ── Report download helpers (shared by the consolidated + single-run flows) ────

async def ensure_dashboard(plugin, root_page: "Page", root_url: str) -> None:
    """Force a FRESH dashboard load so the עמלות accordion is in a clean state.

    Between reports the SPA can be left with a stale/half-collapsed accordion even
    when the URL is still the dashboard — that broke the 2nd report (gemel) which
    bounced back to the dashboard instead of opening. So ALWAYS re-bootstrap the
    Angular app (the session cookie persists in the context) rather than only when
    the URL drifted, and wait for it to settle."""
    try:
        await root_page.goto(root_url, wait_until="networkidle", timeout=30000)
    except Exception:
        try:
            await root_page.goto(root_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass
    await root_page.wait_for_timeout(3000)


async def download_health_report(
    plugin, root_page: "Page", download_dir: Path, run_id: str, root_url: str,
    as_commission: bool = False,
) -> Path:
    """Download the נפרעים חא"ט ובריאות report.

    `as_commission=False` (default, manual single-run): reshape to the production
    schema. `as_commission=True` (consolidated batch run): keep the RAW report —
    it natively detects as `phoenix_insurance_nifraim` (commission, company
    הפניקס), so it lands on the נפרעים side while the SFE vault supplies Phoenix
    production. Operates from the SPA dashboard `root_page`; a report tab is
    closed afterwards. Raises (with artifacts) if the report can't be reached."""
    from app.services.portal_automation.runner import SCREENSHOT_ROOT

    async def _checkpoint(pg: "Page", stem: str) -> None:
        p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
        await plugin._safe_screenshot(pg, p)
        await plugin._dump_page_state(pg, p)

    def _fail(stem: str, msg: str) -> "RuntimeError":
        return RuntimeError(f"{msg} (see {run_id}_{stem}.{{png,html,txt}})")

    await ensure_dashboard(plugin, root_page, root_url)

    # Step 1: expand the "עמלות" accordion. Collapsed by default — its sub-links
    # only enter the DOM once the header is clicked. The חא"ט link is uniquely
    # identified by carrying BOTH נפרעים + בריאות (the גמל report lacks בריאות;
    # the "הפרשי"/"היקף" reports lack נפרעים). Toggle until visible.
    #
    # The sidebar nav item is a <span>עמלות</span>; the home dashboard also grew an
    # "עמלות" summary WIDGET rendered as <h2>עמלות</h2> (with שנה נוכחית/שנה קודמת
    # links). `get_by_text("עמלות", exact=True).first` matched the widget header,
    # so the click was a no-op and the nav flyout (the נפרעים links) never opened
    # (live 2026-06-29: נפרעים count = 0 in the DOM). Scope to the nav <span> via
    # :text-is so the <h2> widget can't be picked.
    nifraim_link = root_page.locator("a:has-text('נפרעים'):has-text('בריאות')").first
    amlot_header = root_page.locator("span:text-is('עמלות')").first
    expanded = False
    for _ in range(3):
        try:
            if await nifraim_link.is_visible():
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
            expanded = await nifraim_link.is_visible()
        except Exception:
            expanded = False
    await _checkpoint(root_page, "nx_1_amlot")
    if not expanded:
        await _checkpoint(root_page, "nx_1_amlot_no_match")
        raise _fail(
            "nx_1_amlot_no_match",
            "Phoenix נפרעים: could not expand 'עמלות' to reveal the נפרעים link",
        )

    # Step 2: click the נפרעים link. The report may render in the same SPA route
    # or open a new tab — handle both, and remember if we opened a tab to close.
    pages_before = set(root_page.context.pages)
    try:
        await nifraim_link.click(timeout=8000)
    except Exception:
        await _checkpoint(root_page, "nx_2_nifraim_no_match")
        raise _fail("nx_2_nifraim_no_match", "Phoenix נפרעים: נפרעים link click failed")
    await root_page.wait_for_timeout(2500)
    new_pages = [pg for pg in root_page.context.pages if pg not in pages_before]
    report_page = new_pages[-1] if new_pages else root_page
    opened_new_tab = report_page is not root_page
    if opened_new_tab:
        try:
            await report_page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass

    try:
        # Let the report grid + its toolbar (with the excel icon) render.
        try:
            await report_page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await report_page.wait_for_timeout(3000)
        await _checkpoint(report_page, "nx_2_nifraim")

        # Step 3: click the excel download icon
        # (<fnx-nx-ui-standalone-icon> wrapping <img src="...excel.svg">).
        # Capture with the Migdal/SFE 3-layer pattern: native expect_download
        # first, an XHR response listener as fallback.
        xhr_capture: dict = {"bytes": None, "name": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_xlsx = (
                    "spreadsheetml" in ct
                    or "vnd.ms-excel" in ct
                    or "octet-stream" in ct
                    or ".xlsx" in url
                    or ".xls" in url
                    or ".xlsx" in cd
                    or ".xls" in cd
                )
                if is_xlsx and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
            except Exception:
                pass

        raw_path = download_dir / "phoenix_nifraim_raw.xlsx"
        icon_selectors = [
            "fnx-nx-ui-standalone-icon img[src*='excel.svg']",
            "img[src*='ui-standalone-components/excel.svg']",
            "img[src*='excel.svg']",
            "fnx-nx-ui-standalone-icon:has(img[src*='excel'])",
            "[class*='icon']:has(img[src*='excel'])",
        ]

        report_page.on("response", _on_response)
        try:
            try:
                async with report_page.expect_download(timeout=45000) as dl_info:
                    if not await plugin._click_first_visible(report_page, icon_selectors, timeout=10000):
                        raise RuntimeError("excel-icon-not-found")
                download = await dl_info.value
                await download.save_as(str(raw_path))
            except Exception as native_err:
                logger.warning(
                    "phoenix_nifraim: native download failed (%s); waiting on XHR capture",
                    native_err,
                )
                for _ in range(24):  # up to 12s
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    raw_path.write_bytes(xhr_capture["bytes"])
                else:
                    await _checkpoint(report_page, "nx_3_download_fail")
                    raise _fail(
                        "nx_3_download_fail",
                        f"Phoenix נפרעים: download did not start ({native_err})",
                    )
        finally:
            report_page.remove_listener("response", _on_response)

        await _checkpoint(report_page, "nx_3_downloaded")
        logger.info(
            "phoenix_nifraim: raw report saved %s (%d bytes)",
            raw_path.name, raw_path.stat().st_size,
        )

        # Step 4: emit the file.
        if as_commission:
            # Keep the raw report → natively detects as commission (הפניקס).
            # NOTE: the filename must NOT contain a double-quote (חא"ט) — `"` is an
            # illegal character in Windows filenames and raw_path.rename() would die
            # with WinError 123 on the worker, silently dropping Phoenix נפרעים from
            # the batch. Use the quote-free spelling חאט.
            out = download_dir / 'הפניקס נפרעים חאט ובריאות.xlsx'
            if out.exists():
                out.unlink()
            raw_path.rename(out)
            logger.info("phoenix_nifraim: נפרעים (commission) file %s", out.name)
            return out
        # Manual single-run: reshape into a production-schema XLSX.
        production_xlsx = _nifraim_to_production_xlsx(raw_path, download_dir)
        logger.info("phoenix_nifraim: built production file %s", production_xlsx.name)
        return production_xlsx
    finally:
        if opened_new_tab:
            try:
                await report_page.close()
            except Exception:
                pass


# ── נפרעים → production schema transform ───────────────────────────────────────

# Source (נפרעים) Hebrew header → output (production) Hebrew header.
# Mirrors PHOENIX_INSURANCE_NIFRAIM_COLUMNS → PRODUCTION_FILE_COLUMNS.
_NIFRAIM_HEADER = "תז המבוטח"          # row anchor for header detection
_NIFRAIM_SIG = 'סה"כ לתשלום'           # second signature column


def _find_header_row(raw_path: Path) -> int:
    """Locate the row index whose cells contain the נפרעים signature columns.

    Phoenix exports sometimes carry a title/blank band above the real header,
    so we scan the first rows for the one holding both signature columns.
    """
    probe = pd.read_excel(raw_path, header=None, nrows=15, dtype=str)
    for i in range(len(probe)):
        cells = {str(c).strip() for c in probe.iloc[i].tolist()}
        if _NIFRAIM_HEADER in cells and _NIFRAIM_SIG in cells:
            return i
    return 0


def _split_name(full: str) -> tuple[str, str]:
    """Split 'שם פרטי שם משפחה' → (first, rest). id_number is the real join key,
    so this heuristic only affects display."""
    full = (full or "").strip()
    if not full:
        return "", ""
    parts = full.split(None, 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _period_label(df: pd.DataFrame) -> str:
    """Hebrew 'חודש שנה' label from the report's חודש עיבוד column, else now."""
    yyyy = mm = None
    if "חודש עיבוד" in df.columns:
        for val in df["חודש עיבוד"].dropna().astype(str):
            m = re.search(r"(\d{1,2})[/\-.](\d{2,4})", val) or re.search(r"(\d{4})[/\-.](\d{1,2})", val)
            if not m:
                continue
            a, b = m.group(1), m.group(2)
            if len(a) == 4:  # YYYY-MM
                yyyy, mm = int(a), int(b)
            else:            # MM/YYYY or MM/YY
                mm = int(a)
                yyyy = int(b) if len(b) == 4 else 2000 + int(b)
            break
    if not (yyyy and 1 <= (mm or 0) <= 12):
        now = datetime.utcnow()
        yyyy, mm = now.year, now.month
    return f"{HEBREW_MONTHS[mm]} {yyyy}"


def _nifraim_to_production_xlsx(raw_path: Path, download_dir: Path) -> Path:
    header_row = _find_header_row(raw_path)
    df = pd.read_excel(raw_path, header=header_row, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]

    def col(name: str):
        return df[name] if name in df.columns else None

    ids = col(_NIFRAIM_HEADER)
    if ids is None:
        raise RuntimeError(
            f"Phoenix נפרעים: source file missing '{_NIFRAIM_HEADER}' header "
            f"(detected header row {header_row})"
        )

    out_rows = []
    names = col("שם המבוטח")
    policies = col("מס' פוליסה")
    branches = col("ענף")
    products = col("סוג פוליסה")
    premiums = col("פרמיה")
    balances = col("צבירה")
    sign_dates = col("תאריך התחלה")
    agents = col("סוכן מקבל עמלה")

    for i in range(len(df)):
        id_raw = ids.iloc[i]
        if id_raw is None or (isinstance(id_raw, float) and pd.isna(id_raw)):
            continue
        id_str = str(id_raw).strip()
        if not id_str or id_str.lower() in ("nan", "none"):
            continue
        first, last = _split_name(str(names.iloc[i]) if names is not None else "")
        out_rows.append({
            "יצרן": "הפניקס",
            "סוג מוצר": _cell(branches, i),
            "מוצר": _cell(products, i),
            "מס' חשבון/פוליסה": _cell(policies, i),
            "מספר ת.ז": id_str,
            "שם פרטי לקוח": first,
            "שם משפחה לקוח": last,
            'סה"כ פרמיה': _cell(premiums, i),
            "צבירה": _cell(balances, i),
            "סטטוס מוצר": "פעיל",
            "תאריך הצטרפות למוצר": _cell(sign_dates, i),
            "מספר סוכן": _cell(agents, i),
        })

    if not out_rows:
        raise RuntimeError("Phoenix נפרעים: no data rows with an id_number to convert")

    out_df = pd.DataFrame(out_rows, columns=[
        "יצרן", "סוג מוצר", "מוצר", "מס' חשבון/פוליסה", "מספר ת.ז",
        "שם פרטי לקוח", "שם משפחה לקוח", 'סה"כ פרמיה', "צבירה",
        "סטטוס מוצר", "תאריך הצטרפות למוצר", "מספר סוכן",
    ])

    period = _period_label(df)
    out_path = download_dir / f"הפניקס - חיים ובריאות פרודוקציה ({period}).xlsx"
    out_df.to_excel(out_path, index=False)
    logger.info("phoenix_nifraim: %d rows → %s", len(out_df), out_path.name)
    return out_path


def _cell(series, i):
    """Series value at i as a clean scalar (None for NaN)."""
    if series is None:
        return None
    val = series.iloc[i]
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return val
