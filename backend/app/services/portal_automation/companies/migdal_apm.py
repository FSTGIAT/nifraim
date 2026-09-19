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

from app.services.portal_automation.base import (
    BasePortalAutomation,
    reporting_months,
)
from app.services.portal_automation._apm_helpers import apm_login_submit

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://apmaccess.migdal.co.il/my.policy"

# The agent's owner ID (תז בעלים). The "משולמים בעלים" report lists owners; clicking
# this row scopes the export to the agent's full book — the same value appears on
# every exported row (it's the agent, not a client).
# TODO: promote to a per-credential field if a second agent ever uses this portal.
OWNER_ID = "40336281"

# Israeli insurers publish a reporting month on a fixed day of the FOLLOWING
# month; Migdal's cycle runs on the 21st, same as הכשרה's. `reporting_months`
# turns that into "which month should exist right now", newest-plausible first.
CYCLE_CUTOFF_DAY = 21


class MigdalApmPortal(BasePortalAutomation):
    portal_kind = "migdal_apm"
    company_label = "מגדל — אזור סוכנים (עמלות)"
    # Folded into the consolidated `migdal` plugin, which downloads the mfte
    # production then logs into apmaccess (2nd OTP via the runner's otp_provider)
    # for this נפרעים report. Still runnable as a manual single run.
    # FALSE, like every other folded leg (clal_nifraim, menora_nifraim,
    # harel_commissions, phoenix_nifraim_gemel). This used to be True, which
    # contradicted the comment directly above it and made the batch fetch this
    # report TWICE: `migdal` downloads mfte production and then folds apmaccess
    # here (2nd OTP), after which the standalone entry logged in AGAIN and asked
    # for a THIRD code. Live 2026-07-19 (batch 9e708cbc): the folded leg produced
    # `מגדל נפרעים יוני 2026.xlsx` (180 records) at 16:45, then the duplicate run
    # failed `stage=otp, Timeout 20000ms` at 16:46 — a red card for a company
    # that had in fact succeeded, plus a wasted login, ~2 minutes and an OTP that
    # a later portal in the same batch might have needed.
    include_in_batch = False

    async def _restart_if_bounced(self, page: "Page") -> bool:
        """F5 APM bot gate: a hit can bounce to my.logout.php3?errorcode=19.

        The recovery link's href is a (literal, server-templated) session token
        "https://apmaccess.migdal.co.il/[SESSION_RESTART_URL]"; navigating to it
        restarts the session and serves the real logon form. We navigate by href
        rather than click because the page has TWO "לחץ כאן" links — the other is
        a remote-support link to lpsplatformp.migdal.co.il. Loop in case it bounces
        more than once. Returns True if we followed a restart link.
        """
        recovered = False
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
            recovered = True
        return recovered

    async def login(self, page: "Page", username: str, password: str) -> None:
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        await self._restart_if_bounced(page)

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
        try:
            await self._wait_visible(page, self.OTP_FIELD, timeout=20000)
        except Exception:
            # The gate can also bounce us AFTER the credentials — we land back on
            # my.logout.php3?errorcode=19 and there IS no OTP field to wait for.
            # Recovery only ran before the submit, so this died on a bare 20s
            # timeout. It bites hardest in a batch: the sibling `migdal` credential
            # logs into this same F5 seconds earlier (and retries), so by the time
            # apmaccess is hit the gateway is hostile. Restart the session and log
            # in once more rather than failing the company for the whole batch.
            from app.services.portal_automation.runner import _worker_note
            _worker_note(f"migdal_apm: no OTP field (url={page.url}) — F5 restart + retry login")
            if not await self._restart_if_bounced(page):
                await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                await self._restart_if_bounced(page)
            await apm_login_submit(page, username, password)
            await page.wait_for_timeout(2000)
            await self._wait_visible(page, self.OTP_FIELD, timeout=30000)
            _worker_note("migdal_apm: recovered — OTP field is up after the F5 restart")

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

        # Step 5b: pin the export to the CYCLE reporting month.
        #
        # This report had no month step at all: it exported whatever period the
        # portal happened to default to, and `_rename_with_period` then named the
        # file after whatever came out. Live 2026-09-15 that was 08/2026 while
        # every other company in the same batch landed on 07/2026, so the merged
        # נפרעים file carried nine companies at 07 and מגדל alone at 08 — and the
        # dashboard drew a 2026-08 column containing one insurer.
        #
        # 🚫 NEVER "pick the newest option". The picker offers a month whose
        # cycle has not published yet; taking it downloads a thin or empty report
        # that still looks like a successful run. Compute the month from the
        # cycle, then step BACKWARD only — the same rule as הכשרה's חודש עיבוד
        # (`hachshara.py`).
        target_period = await self._select_report_month(page, run_id)

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

        # Did the portal actually give us the month we asked for? A picker that
        # silently ignored the click, or a missing control, both produce a
        # perfectly well-formed file for the WRONG period — and every downstream
        # check passes. Say so in the run summary rather than letting a
        # single-company month appear on the dashboard unexplained.
        got = self._exported_month(target)
        if got and target_period and got > target_period:
            from app.services.portal_automation.runner import _worker_note
            msg = (
                f"מגדל נפרעים: התקבל חודש {got[1]:02d}/{got[0]} במקום "
                f"{target_period[1]:02d}/{target_period[0]} (מחזור ה-{CYCLE_CUTOFF_DAY}) — "
                "בחירת החודש בפורטל לא נתפסה"
            )
            self.partial_errors.append(msg)
            try:
                _worker_note(f"migdal_apm: {msg}")
            except Exception:
                pass

        # Rename with the report's Hebrew month so detect_period_month (filename-first)
        # resolves correctly. The parser maps חודש תחילת ביטוח → sign_date (policy
        # inception year, e.g. 2011), which would otherwise mislead period detection.
        final = self._rename_with_period(target)
        return [final]

    async def _select_report_month(self, page: "Page", run_id: str) -> tuple[int, int] | None:
        """Point the 'משולמים בעלים' report at the cycle's reporting month.

        Returns the (year, month) we asked for, or None when no month control
        was found. **Never raises.** A missing or renamed picker must degrade to
        today's behaviour — the default export — not turn a working download
        into a failed run. The mismatch is reported after the download instead.
        """
        from datetime import date

        from app.services.portal_automation.runner import SCREENSHOT_ROOT, _worker_note

        candidates = reporting_months(date.today(), CYCLE_CUTOFF_DAY)

        # Dump BEFORE touching anything: the first live run is how we learn what
        # this control actually is, and a dump taken after a failed click shows
        # the wrong page.
        month_dump = SCREENSHOT_ROOT / f"{run_id}_month_picker.png"
        try:
            await self._safe_screenshot(page, month_dump)
            await self._dump_page_state(page, month_dump)
        except Exception:
            pass

        # Anchored on the Hebrew label, never on a positional id: those shift as
        # the form grows (הכשרה's live field is #mat-input-14).
        field = None
        for sel in (
            "select[name*='חודש']",
            "select[aria-label*='חודש']",
            "input[placeholder*='לחודש'], input[aria-label*='לחודש']",
            "input[placeholder*='חודש'], input[aria-label*='חודש']",
            "select:near(:text('לחודש'))",
            "select:near(:text('חודש'))",
        ):
            try:
                loc = page.locator(sel).first
                if await loc.count():
                    field = loc
                    break
            except Exception:
                continue

        if field is None:
            try:
                _worker_note(
                    "migdal_apm: no month control found — exporting the portal "
                    f"default (see {month_dump.stem}.txt)"
                )
            except Exception:
                pass
            return None

        async def _option_texts() -> list[str]:
            for sel in ("option", "[role='option']", "mat-option", "li"):
                try:
                    loc = page.locator(sel)
                    n = await loc.count()
                    if n:
                        return [((await loc.nth(i).inner_text()) or "").strip()
                                for i in range(min(n, 60))]
                except Exception:
                    continue
            return []

        # A <select> takes select_option; anything else needs a click to open
        # its overlay before the options exist.
        tag = ""
        try:
            tag = (await field.evaluate("el => el.tagName") or "").lower()
        except Exception:
            pass
        if tag != "select":
            try:
                await field.click(timeout=5000)
                await page.wait_for_timeout(600)
            except Exception:
                pass

        texts = await _option_texts()

        def _matches(text: str, year: int, month: int) -> bool:
            digits = re.sub(r"[^0-9]", "", text)
            return (
                f"{month:02d}/{year}" in text
                or f"{month}/{year}" in text
                or f"{year}-{month:02d}" in text
                or digits in (f"{month:02d}{year}", f"{year}{month:02d}")
            )

        for year, month in candidates:
            idx = next((i for i, t in enumerate(texts) if _matches(t, year, month)), None)
            if idx is None:
                continue
            try:
                if tag == "select":
                    await field.select_option(index=idx)
                else:
                    for sel in ("[role='option']", "mat-option", "li"):
                        loc = page.locator(sel)
                        if await loc.count() > idx:
                            await loc.nth(idx).click(timeout=5000)
                            break
                await page.wait_for_timeout(1200)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                _worker_note(f"migdal_apm: reporting month set to {month:02d}/{year}")
                return (year, month)
            except Exception as e:
                try:
                    _worker_note(f"migdal_apm: month {month:02d}/{year} click failed: {e}")
                except Exception:
                    pass
                break

        try:
            _worker_note(
                "migdal_apm: cycle month "
                f"{candidates[0][1]:02d}/{candidates[0][0]} not offered "
                f"({len(texts)} options) — exporting the portal default"
            )
        except Exception:
            pass
        return None

    @staticmethod
    def _exported_month(path: Path) -> tuple[int, int] | None:
        """(year, month) the exported report actually covers, or None.

        Reads the explicit 'לחודש' column (MM/YYYY), falling back to the latest
        'תאריך תשלום'. Used BOTH to name the file and to verify the portal gave
        us the month we asked for."""
        try:
            import pandas as pd

            df = pd.read_excel(path)
            for col in df.columns:
                if str(col).strip() == "לחודש":
                    vals = df[col].dropna().astype(str)
                    if len(vals):
                        m = re.search(r"(\d{1,2})\s*[/.\-]\s*(\d{4})", vals.iloc[0])
                        if m:
                            return int(m.group(2)), int(m.group(1))
                    break
            for col in df.columns:
                if "תאריך תשלום" in str(col):
                    dts = pd.to_datetime(df[col], dayfirst=True, errors="coerce").dropna()
                    if len(dts):
                        return int(dts.max().year), int(dts.max().month)
                    break
        except Exception:
            pass
        return None

    @classmethod
    def _rename_with_period(cls, path: Path) -> Path:
        """Rename a Migdal נפרעים export to 'מגדל נפרעים <חודש> <שנה>.xlsx' using the
        month `_exported_month` read. Returns the path unchanged if unknown."""
        try:
            from app.services.parser_service import _HE_MONTH_TO_INT

            got = cls._exported_month(path)
            if not got:
                return path
            year, month = got
            int_to_he = {v: k for k, v in _HE_MONTH_TO_INT.items()}
            if month in int_to_he:
                new_path = path.with_name(f"מגדל נפרעים {int_to_he[month]} {year}.xlsx")
                path.rename(new_path)
                return new_path
        except Exception:
            pass
        return path
