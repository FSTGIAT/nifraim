"""פנסיה-נט (pensyanet.cma.gov.il) XML export → pensyanet_data.

data.gov.il's פנסיה-נט resource (services/fund_market, `fund_market_monthly`) already holds the
per-track monthly numbers — measured 2026-10-10: the same 292 tracks, FUND_ID == the site's
ID_MASLUL_RISHUY, identical assets. What only the site has, through its "הורדת קובץ XML":
  * asset allocation per track and per fund (10 main groups, risk level, exposures, tradable,
    domestic/foreign; full detail at fund level) — one month per download;
  * the fund-level actuarial balance (the site stopped publishing fund yields in 01/2017);
  * extra risk stats per track (betas, R², liquidity ratio) for the last 12 months.

The site needs a real browser: plain HTTP gets a gov.il WAF page. Railway's Chromium (installed
for portal automation) reaches it. The flow is the page's own: select every fund in its kendo
multiselect, tick the report, press "הורד קובץ" (parameters.js downloadXML → ExportToXML).
Never parse the rendered SSRS report or replay its __VIEWSTATE.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund_market import FundMarketMonthly, PensyanetData

logger = logging.getLogger(__name__)

URL = "https://pensyanet.cma.gov.il/Parameters/Index"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

# (report key, level, page radio for the level, page radio for the report)
LEVEL_RADIO = {"fund": "XmlMainReportType1", "track": "XmlMainReportType1001"}
REPORTS = [
    ("general", "track", "XmlGeneralReportType1"),      # per track: flows, fees, yields, betas, R², liquidity
    ("assets_main", "track", "XmlAssetsReportType5"),   # per track: 10 main groups, risk, exposures, tradable, IL/abroad
    ("general", "fund", "XmlGeneralReportType1"),
    ("yields", "fund", "XmlGeneralReportType3"),        # fund assets + actuarial balance, 12 months (yields blank since 2017)
    ("tracks", "fund", "XmlGeneralReportType6"),        # every track of every fund, 12 months of risk stats
    ("assets_main", "fund", "XmlAssetsReportType5"),
    ("assets_full", "fund", "XmlAssetsReportType4"),
    ("assets_trad", "fund", "XmlAssetsReportType2"),
]
_TEXT = {"SHM_KRN", "SHM_MASLUL", "SHM_HEVRA_MENAHELET", "SUG_KRN", "SHM_TAAGID_SHOLET", "SUG_TAAGID_SHOLET",
         "TAARICH_HAFAKAT_HADOCH", "MATZAV_DIVUACH", "TAARICH_SIUM_PEILUT", "KVUTZAT_NECHASIM",
         "SHM_SUG_NECHES", "SHM_NATUN"}


def _num(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    n = _num(v)
    return int(n) if n is not None else None


def parse(xml_bytes: bytes, report: str, level: str) -> list[dict]:
    """One export → pensyanet_data rows. Asset reports are long (a row per asset type);
    the others are wide (the whole row kept in `data`)."""
    root = ET.fromstring(xml_bytes)
    now = datetime.utcnow()
    out: dict[tuple, dict] = {}
    for el in root.findall("ROW"):
        r = {c.tag: (c.text or "").strip() for c in el}
        period = _int(r.get("TKF_DIVUACH") or r.get("AD_TKUFAT_DIVUACH"))
        if report == "tracks":   # rows are tracks even though the export is "by fund"
            lvl, ent = "track", _int(r.get("ID_MASLUL_RISHUY") or r.get("ID_MASLUL"))
            name = r.get("SHM_MASLUL") or r.get("SHM_KRN")
        elif level == "track":
            lvl, ent = level, _int(r.get("ID_MASLUL_RISHUY") or r.get("ID") or r.get("ID_KRN"))
            name = r.get("SHM_KRN")
        else:
            lvl, ent = level, _int(r.get("ID_KRN") or r.get("ID"))
            name = r.get("SHM_KRN")
        if ent is None or period is None:
            continue
        row = {"report": report, "level": lvl, "entity_id": ent, "entity_name": (name or None) and name[:200],
               "period": period, "grp": "", "item_id": 0, "item_name": None, "amount": None, "pct": None,
               "data": None, "fetched_at": now}
        if "SHM_SUG_NECHES" in r:
            row.update(grp=(r.get("KVUTZAT_NECHASIM") or "")[:80], item_id=_int(r.get("ID_SUG_NECHES")) or 0,
                       item_name=(r.get("SHM_SUG_NECHES") or "")[:200],
                       amount=_num(r.get("SCHUM_SUG_NECHES")), pct=_num(r.get("ACHUZ_SUG_NECHES")))
        elif "SHM_NATUN" in r:
            row.update(item_id=_int(r.get("ID_NATUN")) or 0, item_name=(r.get("SHM_NATUN") or "")[:200],
                       amount=_num(r.get("ERECH_NATUN")), pct=_num(r.get("ACHUZ")))
        else:
            row["data"] = {k: (v if k in _TEXT else _num(v)) for k, v in r.items() if v != ""}
        out[(lvl, ent, period, row["grp"], row["item_id"])] = row   # last wins inside one export
    return list(out.values())


ASSET_REPORTS = [r for r in REPORTS if r[0].startswith("assets")]


async def download_all(reports=REPORTS, timeout_ms: int = 180_000, end_period: int | None = None) -> dict[tuple, bytes]:
    """Every (report, level) XML for all funds. Default = the site's window (last 12 months; asset
    reports = its last month). `end_period` (YYYYMM) moves the window to end there — how asset
    history is backfilled, since an asset export holds one month only. One browser, a fresh
    context per export."""
    from playwright.async_api import async_playwright

    got: dict[tuple, bytes] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled",
                                                                "--no-sandbox", "--disable-dev-shm-usage"])
        try:
            for report, level, radio in reports:
                ctx = await browser.new_context(locale="he-IL", accept_downloads=True, user_agent=UA)
                try:
                    page = await ctx.new_page()
                    await page.goto(URL, wait_until="networkidle", timeout=90_000)
                    if end_period:
                        y, m = divmod(end_period, 100)
                        await page.evaluate("""([y, m]) => { const cb = document.querySelector('input.big-checkbox');
                            if (cb && cb.checked) cb.click();
                            const s = $('#date-start').data('kendoDatePicker'), e = $('#date-end').data('kendoDatePicker');
                            s.value(new Date(y - 1, m, 1)); s.trigger('change');
                            e.value(new Date(y, m - 1, 1)); e.trigger('change') }""", [y, m])
                    n = await page.evaluate("""() => { const ms = $('#funds_multi').data('kendoMultiSelect');
                        const v = ms.dataSource.data().map(d => d[ms.options.dataValueField]);
                        ms.value(v); ms.trigger('change'); return v.length }""")
                    await page.evaluate("""ids => { for (const id of ids) { const e = document.getElementById(id);
                        e.checked = true; $(e).trigger('click').trigger('change') } }""", [LEVEL_RADIO[level], radio])
                    async with page.expect_download(timeout=timeout_ms) as dl:
                        await page.evaluate("$('#btn-xml-download').trigger('click')")
                    path = await (await dl.value).path()
                    got[(report, level)] = open(path, "rb").read()
                    logger.info("pensyanet: %s/%s (%s funds) %d bytes", report, level, n, len(got[(report, level)]))
                except Exception as e:  # noqa: BLE001 — one report failing keeps the others
                    logger.warning("pensyanet: %s/%s failed: %s", report, level, e)
                finally:
                    try:
                        await ctx.close()
                    except Exception:  # noqa: BLE001 — a crashed browser can't close its context
                        pass
                if not browser.is_connected():   # crashed: relaunch for the remaining reports
                    browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled",
                                                                            "--no-sandbox", "--disable-dev-shm-usage"])
        finally:
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                pass
    return got


async def _upsert(db: AsyncSession, rows: list[dict]) -> int:
    for i in range(0, len(rows), 500):
        chunk = rows[i: i + 500]
        stmt = insert(PensyanetData).values(chunk)
        cols = {c: getattr(stmt.excluded, c) for c in ("entity_name", "item_name", "amount", "pct", "data", "fetched_at")}
        await db.execute(stmt.on_conflict_do_update(constraint="uq_pensyanet_row", set_=cols))
    await db.commit()
    return len(rows)


async def latest_period(db: AsyncSession) -> int | None:
    return (await db.execute(select(func.max(PensyanetData.period))
                             .where(PensyanetData.report == "assets_main", PensyanetData.level == "track"))).scalar_one_or_none()


async def sync(db: AsyncSession, *, force: bool = False) -> dict:
    """Import when data.gov.il has a pension month we don't have here yet (the site publishes the
    same month), or always with `force`. Cheap DB check first — the browser only runs when needed."""
    have = await latest_period(db)
    market = (await db.execute(select(func.max(FundMarketMonthly.report_period))
                               .where(FundMarketMonthly.source == "pension"))).scalar_one_or_none()
    if not force and have and market and have >= market:
        return {"skipped": True, "period": have}
    files = await download_all()
    stats = {}
    for (report, level), blob in files.items():
        try:
            rows = parse(blob, report, level)
        except ET.ParseError as e:
            logger.warning("pensyanet: %s/%s not XML: %s", report, level, e)
            continue
        stats[f"{report}/{level}"] = await _upsert(db, rows) if rows else 0
    logger.info("pensyanet sync: %s", stats)
    return stats


async def backfill_assets(db: AsyncSession, months: int = 12) -> dict:
    """Asset allocation for the `months` before the newest stored month (an asset export is one
    month). Only months not stored yet. The other reports already carry 12 months each."""
    have = await latest_period(db)
    if not have:
        return {"error": "run sync() first"}
    stored = set((await db.execute(select(PensyanetData.period).where(
        PensyanetData.report == "assets_main", PensyanetData.level == "track").distinct())).scalars())
    stats = {}
    y, m = divmod(have, 100)
    for _ in range(months):
        m -= 1
        if m < 1:
            y, m = y - 1, 12
        per = y * 100 + m
        if per in stored:
            continue
        files = await download_all(ASSET_REPORTS, end_period=per)
        for (report, level), blob in files.items():
            rows = [r for r in parse(blob, report, level) if r["period"] == per]
            stats[f"{per} {report}/{level}"] = await _upsert(db, rows) if rows else 0
    logger.info("pensyanet backfill: %s", stats)
    return stats
