"""Harel (הראל) — agents-portal commission report "ריכוז תשלומי עמלות".

Distinct from the `harel` plugin (which logs in a SECOND time to the
harelsafe.co.il vault and pulls CP862 fixed-width files). This plugin stays on
the agents portal after APM+OTP and exports the clean **נפרעים** Excel from the
life/health commissions report — the same file shape as the manually-uploaded
`הראל נפרעים חיים ובריאות *.xlsx`, parsed by the existing `harel_nifraim` format.

Login + OTP are inherited from `HarelPortal` (F5 APM at
`agents.harel-group.co.il/my.policy`, errorcode-19 recovery, SMS OTP). Only the
single agents-tier password is used (no `|`-joined safe password needed).

Operator-described flow (2026-06-15):
    1. After login, open "ריכוז תשלומי עמלות"
       (/Information/Reports/life-health-saving/Agent/Pages/commissions/payments-assembly.aspx)
    2. The "מספר - חשבון" param defaults to the first account (113061826).
    3. Click "סנן מידע" to run the report.
    4. In the עמלות section click the total number (a drill link), then again,
       to reach the per-policy detail.
    5. Click the bar-excel button (title="הדפס תצורת אקסל") to download.

Steps 4-5 are structurally uncertain; we dump full page state at each step so
selectors can be refined from `data/portal_screenshots/<run_id>_*` without a
re-login.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from app.services.portal_automation.companies.harel import HarelPortal

if TYPE_CHECKING:
    from playwright.async_api import Page


# Report path is relative — the agent portal lives on `agents-int.harel-group.co.il`
# after the APM/OTP redirect (NOT the `agents.` login host), so we derive the origin
# from the post-login URL rather than hardcoding the subdomain.
REPORT_PATH = (
    "/Information/Reports/life-health-saving/Agent/Pages/commissions/payments-assembly.aspx"
)
# The agent's first account (operator-provided). The "מספר - חשבון" param
# usually defaults to this; we still try to select it explicitly.
# TODO: promote to a per-credential field when a second account is needed.
ACCOUNT_NUMBER = "113061826"


class HarelCommissionsPortal(HarelPortal):
    portal_kind = "harel_commissions"
    company_label = "הראל — ריכוז תשלומי עמלות"
    # Folded into the consolidated `harel_savings` plugin: harel_savings runs after
    # this alphabetically and calls HarelCommissionsPortal().download_reports() on its
    # OWN authenticated page — one Harel login yields BOTH production (מוצרי צבירה) and
    # this נפרעים report with no second OTP. Running standalone in the batch only burns a
    # duplicate Harel OTP and produces a false failure. Manual single-runs are unaffected.
    include_in_batch = False

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
            logger as _logger,
        )

        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        async def _checkpoint(stem: str) -> None:
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        await _checkpoint("post_otp")

        # ── Hangup recovery ──
        # F5 sometimes lands the post-OTP session on the logout/hangup page
        # (vdesk/hangup.php3) which carries a "לחץ כאן" (href="/") restart link.
        # The OTP already set the MRHSession cookie, so clicking through / hitting
        # the site root re-lands us in the authenticated portal (agents-int)
        # WITHOUT a fresh OTP. Loop a few times — F5 can bounce more than once.
        def _bounced(u: str) -> bool:
            return any(s in (u or "") for s in ("hangup", "logout", "my.policy", "my.logout"))

        if _bounced(page.url):
            for _ in range(4):
                parsed = urlparse(page.url)
                origin = f"{parsed.scheme}://{parsed.netloc}"
                clicked = await self._click_first_visible(
                    page, ["a:has-text('לחץ כאן')"], timeout=4000
                )
                if not clicked:
                    try:
                        await page.goto(origin + "/", wait_until="domcontentloaded", timeout=20000)
                    except Exception:
                        pass
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
                if not _bounced(page.url):
                    break
            await _checkpoint("0_post_hangup_recovery")
            if _bounced(page.url):
                raise RuntimeError(
                    f"הסשן של הראל הסתיים מיד לאחר ה-OTP ולא הצלחנו לשחזר ({page.url}). "
                    "ודא שאין חיבור פעיל אחר לאזור הסוכנים ונסה שוב."
                )

        # ── Step 1: open the commission report ──
        # Navigate directly to the report on the post-login origin (the home-page
        # link exists but is styled non-visible, so a click won't match).
        parsed = urlparse(page.url)
        report_url = f"{parsed.scheme}://{parsed.netloc}{REPORT_PATH}"
        try:
            await page.goto(report_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            # Fallback: force-click the (possibly hidden) home-page link.
            try:
                await page.locator('a[href*="payments-assembly.aspx"]').first.click(
                    timeout=8000, force=True
                )
            except Exception as e:
                await _checkpoint("1_report_nav_failed")
                raise RuntimeError(
                    f"לא הצלחנו לפתוח את דוח ריכוז תשלומי עמלות ({page.url}): {e}"
                )
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)  # report params load async
        await _checkpoint("1_report_loaded")

        # ── The report renders inside an "intellisys" BI iframe — all params,
        # the סנן מידע button, the עמלות drill numbers and the bar-excel button
        # live INSIDE it. Acquire the frame and operate within it. ──
        async def _get_frame(poll_seconds: int = 40):
            # Hardened like _harel_report._get_frame (harel_savings): poll ~40s with
            # 3 strategies so a slow BI render / re-attach doesn't fail the run.
            _SELS = (
                "iframe.intellisys",
                "iframe[id*='intellisys']",
                "iframe[src*='intellisys']",
                "iframe[name*='intellisys']",
                "iframe[src*='_sp_dashboard']",
            )
            _KW = ("intellisys", "_sp_dashboard")
            for _ in range(max(1, poll_seconds * 2)):
                # 1) DOM iframe element → content_frame
                for sel in _SELS:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            fr = await el.content_frame()
                            if fr:
                                return fr
                    except Exception:
                        pass
                # 2) Playwright frame URL/name scan (before the <iframe> attaches)
                try:
                    for fr in page.frames:
                        u = (fr.url or "").lower(); n = (fr.name or "").lower()
                        if u in ("", "about:blank"):
                            continue
                        if any(kw in u or kw in n for kw in _KW):
                            return fr
                except Exception:
                    pass
                # 3) any frame with Intellisys drillable cells (last resort)
                try:
                    for fr in page.frames:
                        try:
                            if await fr.locator("td.click-enter").count() > 0:
                                return fr
                        except Exception:
                            continue
                except Exception:
                    pass
                await asyncio.sleep(0.5)
            return None

        async def _dump_frame(stem: str, fr) -> None:
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            try:
                html = await fr.content()
                p.with_suffix(".html").write_text(html, encoding="utf-8")
            except Exception:
                pass
            # Also list the VISIBLE drillable cells (data_colid + text) — the .html
            # includes hidden insets, so this clarifies what's actually clickable.
            try:
                cells = await fr.eval_on_selector_all(
                    "td.click-enter",
                    "els => els.filter(e => e.offsetParent !== null)"
                    ".map(e => (e.getAttribute('data_colid')||'?') + '=' + (e.innerText||'').trim())"
                    ".slice(0, 80)",
                )
                p.with_suffix(".cells.txt").write_text("\n".join(cells), encoding="utf-8")
            except Exception:
                pass

        frame = await _get_frame()
        if frame is None:
            await _checkpoint("1_no_intellisys_frame")
            raise RuntimeError(
                f"לא נמצא iframe של הדוח (intellisys) ב-{page.url}. "
                f"בדוק {run_id}_1_report_loaded.html"
            )
        # Wait for the dashboard's params/filter to render inside the frame.
        for sel in ("#_ctrlParam__2", ".param-container", "button.bar-excel"):
            try:
                await frame.wait_for_selector(sel, timeout=20000)
                break
            except Exception:
                continue
        await page.wait_for_timeout(2000)
        await _dump_frame("1b_frame_loaded", frame)

        # ── Step 2: ensure the "מספר - חשבון" param is the target account ──
        # It usually defaults to ACCOUNT_NUMBER; selecting is best-effort.
        try:
            cur = await frame.locator("#ctrlParam__2").inner_text(timeout=4000)
        except Exception:
            cur = ""
        if ACCOUNT_NUMBER not in (cur or ""):
            try:
                await frame.click("#_ctrlParam__2", timeout=4000)
                await page.wait_for_timeout(800)
                for sel in (
                    f'div.ctrlText:has-text("{ACCOUNT_NUMBER}")',
                    f'[title*="{ACCOUNT_NUMBER}"]',
                    f'li:has-text("{ACCOUNT_NUMBER}")',
                ):
                    try:
                        await frame.click(sel, timeout=3000)
                        break
                    except Exception:
                        continue
                await page.wait_for_timeout(500)
            except Exception:
                _logger.warning("Harel-commissions: account select best-effort failed")
        await _dump_frame("2_account_selected", frame)

        # ── Step 3: click "סנן מידע" to run the report (inside the frame) ──
        filtered = False
        for sel in (
            'button:has-text("סנן מידע")',
            'a:has-text("סנן מידע")',
            'input[value*="סנן"]',
            '[title*="סנן"]',
            'text="סנן מידע"',
        ):
            try:
                await frame.click(sel, timeout=4000)
                filtered = True
                break
            except Exception:
                continue
        if not filtered:
            await _dump_frame("3_filter_button_not_found", frame)
            raise RuntimeError(
                f"לא נמצא כפתור 'סנן מידע' בתוך הדוח. בדוק {run_id}_3_filter_button_not_found.html"
            )
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)
        frame = await _get_frame() or frame  # re-acquire in case of re-render
        await _dump_frame("3_after_filter", frame)

        # ── XHR fallback listener for the Excel export ──
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

        page.on("response", _on_response)

        async def _click_first_visible(loc, *, require_text=True) -> bool:
            """Click the first VISIBLE (and, by default, non-empty) match.
            The mid-level view has the same cells in hidden insets, and there
            are 3 bar-excel buttons — plain .first/strict-click would hit a
            hidden element or violate strict mode."""
            try:
                n = await loc.count()
            except Exception:
                n = 0
            for j in range(min(n, 40)):
                el = loc.nth(j)
                try:
                    if not await el.is_visible():
                        continue
                    if require_text:
                        txt = (await el.inner_text()).strip()
                        if not txt or txt in ("0", "-"):
                            continue
                    await el.click(timeout=5000)
                    return True
                except Exception:
                    continue
            return False

        async def _click_last_visible(loc) -> bool:
            """Click the LAST visible match — for bar-excel, the deepest grid's
            export button is appended last in the DOM as drills open."""
            try:
                n = await loc.count()
            except Exception:
                n = 0
            for j in range(n - 1, -1, -1):
                try:
                    el = loc.nth(j)
                    if await el.is_visible():
                        await el.click(timeout=5000)
                        return True
                except Exception:
                    continue
            return False

        try:
            # ── Step 4: two-step drill summary → agent breakdown → per-policy ──
            async def _has_detail(fr) -> bool:
                """True once per-policy columns (מבוטח/פוליסה/ענף/חודש עיבוד) appear."""
                for s in ('th:has-text("מבוטח")', 'td[data-title*="מבוטח"]',
                          'th:has-text("מספר פוליסה")', 'th:has-text("סוג פוליסה")',
                          'th:has-text("ענף")', 'th:has-text("חודש עיבוד")',
                          'th:has-text("שם מבוטח")'):
                    try:
                        if await fr.locator(s).count() > 0:
                            return True
                    except Exception:
                        continue
                return False

            # Drill 0 — summary נפרעים cell → agent-breakdown modal.
            for sel in ('td[data_colid="Schum_Nifraim"].cell_action',
                        'td[data-title="נפרעים"].cell_action'):
                if await _click_first_visible(frame.locator(sel)):
                    break
            await page.wait_for_timeout(3000)
            frame = await _get_frame() or frame
            await _dump_frame("4_drill_0", frame)

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
                            cell = frame.locator('td[data_colid="_M2_Schum"].cell_action').first
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
                        frame = await _get_frame() or frame
                        if await _has_detail(frame):
                            break
                if popup is not None:
                    _logger.info("Harel-commissions: drill 1 opened a popup window")
                    try:
                        await popup.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    await popup.wait_for_timeout(2500)
                    page = popup  # export now operates on the popup tab
                    frame = await _get_frame() or popup.main_frame
                    await _dump_frame("4_detail_popup", frame)
                else:
                    await _dump_frame("4_drill1_nopopup", frame)
                    _logger.warning("Harel-commissions: drill 1 — no popup, no in-frame detail")

            # ── Step 5: export via the bar-excel button (inside the frame) ──
            target = download_dir / "הראל נפרעים חיים ובריאות.xlsx"
            try:
                async with page.expect_download(timeout=30000) as dl_info:
                    ok = False
                    for sel in (
                        'button.bar-excel',
                        '[title="הדפס תצורת אקסל"]',
                    ):
                        if await _click_last_visible(frame.locator(sel)):
                            ok = True
                            break
                    if not ok:
                        raise RuntimeError("no-excel-button")
                download = await dl_info.value
                # The portal suggests a generic "New Excel.xls" — keep our
                # meaningful base name, just preserve the real extension.
                suggested = (download.suggested_filename or "").strip().lower()
                if suggested.endswith(".xls"):
                    target = target.with_suffix(".xls")
                await download.save_as(str(target))
            except Exception as native_err:
                for _ in range(20):  # 10s grace for XHR
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    sug = (xhr_capture["filename"] or "").strip().lower()
                    if sug.endswith(".xls"):
                        target = target.with_suffix(".xls")
                    target.write_bytes(xhr_capture["bytes"])
                else:
                    await _dump_frame("5_export_failed", frame)
                    raise RuntimeError(
                        f"לא הצלחנו להוריד אקסל מדוח עמלות הראל. "
                        f"בדוק {run_id}_5_export_failed.html ו-{run_id}_3_after_filter.html: {native_err}"
                    )
        finally:
            try:
                page.remove_listener("response", _on_response)
            except Exception:
                pass

        _logger.info(
            "Harel-commissions: downloaded %s (%d bytes)",
            target.name, target.stat().st_size,
        )
        return [target]
