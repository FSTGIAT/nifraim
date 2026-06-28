"""Harel (הראל) agent portal — APM login + safe-vault download.

Two-stage flow (operator-verified 2026-06-01):

    1. APM login at `https://agents.harel-group.co.il/my.policy`
       (F5 BIG-IP — same `_apm_helpers.apm_login_submit` shape used by
       Phoenix / Hachshara / Clal / Migdal-APM). SMS OTP follows.
    2. After OTP, the agent has to authenticate AGAIN at
       `https://www.harelsafe.co.il/Login.aspx` (ASP.NET WebForms) with the
       SAME username but a DIFFERENT (vault-only) password. Inside the
       agent portal there's a hamburger menu (`svg#navPanel`) → tile
       "הפצת קבצי מידע (כספת)" that opens the safe in a new tab — we use
       direct navigation as the primary path and fall back to that nav-tile
       click if the cross-domain handoff loses our session.

Credentials shape — the `PortalCredential.encrypted_password` field stores
BOTH passwords joined by `|`:

    <agents_password>|<safe_password>

(e.g. `Hruakho!2026|HAREL54384`). If no `|` is present we assume the same
password works for both logins.

Once logged into the safe, the report grid renders rows like:

    <span id="ctl00_MainContent_grdList_ctl03_ReportTypeName" dir="rtl">
        ר.ת.-מורחב חיים פוליסות
    </span>

We click the row containing that label, press the "הצגה" button
(`__doPostBack('ctl00$MainButtons$cmdReports','')`), and download the
top-most (most recent month) file from the resulting list.

When a run fails (or even succeeds), debug artifacts land in
`data/portal_screenshots/<run_id>_nav_*.{png,html,txt}` — the `.txt` lists
visible links/buttons so selectors can be refined without re-running.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation._apm_helpers import apm_login_submit

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://agents.harel-group.co.il/my.policy"
SAFE_LOGIN_URL = "https://www.harelsafe.co.il/Login.aspx"

# All 5 Harel safe report types to download per run (operator-confirmed
# 2026-06-01). Each row of these triggers a separate frmReportList page
# from which we dblclick the latest-month file.
REPORT_LABELS: list[str] = [
    "ר.ת.-מורחב חיים פוליסות",
    "ר.ת.-מורחב בריאות פוליסות",
    "ר.ת.-מורחב חיים ביטוחים",
    "ר.ת.-מורחב בריאות ביטוחים",
    "ר.ת. - פוליסות מגוון",
]
# Back-compat single-label constant — kept so any external import doesn't
# break, but no longer used by download_reports.
REPORT_LABEL = REPORT_LABELS[0]


def _slug(s: str) -> str:
    """Short ASCII-ish slug for checkpoint filenames."""
    return re.sub(r"[^\w֐-׿]+", "_", s).strip("_")[:30] or "report"


class HarelPortal(BasePortalAutomation):
    portal_kind = "harel"
    company_label = "הראל"
    # Harel's WAF blocks the shared ISP zone's hosting ASN (WS Telecom) at the
    # network layer (ERR_TUNNEL_CONNECTION_FAILED on ~6/6 IPs) but accepts a
    # Bright Data residential-zone IP (302). Route all Harel variants through the
    # residential zone via IL_HAREL_PROXY; falls back to IL_RESIDENTIAL_PROXY if
    # unset. Inherited by _HarelReportPortal / harel_savings / harel_commissions.
    proxy_zone_env = "IL_HAREL_PROXY"
    # The legacy SAFE-vault flow (harelsafe.co.il, `|`-split password) is a
    # SEPARATE production source from the agents-portal. The batch's single Harel
    # credential is the consolidated `harel_savings` (production + נפרעים in one
    # agents-portal login), so keep this safe-vault path out of the batch to
    # avoid a duplicate Harel run. Still runnable as a manual single run.
    include_in_batch = False

    def _split_passwords(self, raw: str) -> tuple[str, str]:
        """`encrypted_password` carries two passwords joined by `|`:
        `<agents_password>|<safe_password>`. Falls back to one password
        for both stages when no delimiter is present.
        """
        if "|" in raw:
            first, second = raw.split("|", 1)
            return first.strip(), second.strip()
        return raw, raw

    async def login(self, page: "Page", username: str, password: str) -> None:
        # Stage 1: F5 APM auth at agents.harel-group.co.il/my.policy with
        # the agents-tier password. F5 then SMS-OTPs to the agent's phone.
        # Stage 2 (safe form fill) happens in download_reports after OTP.
        self._agents_password, self._safe_password = self._split_passwords(password)

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)

        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        safe_user = re.sub(r"[^A-Za-z0-9_]", "_", username)[:32] or "anon"
        landing = SCREENSHOT_ROOT / f"harel_apm_landing_{safe_user}.png"
        await self._safe_screenshot(page, landing)
        await self._dump_page_state(page, landing)

        # F5 APM can interrupt login two ways BEFORE the credentials form, both
        # resolved by clicking a reset link that returns the real login form:
        #   1. errorcode / my.logout bounce → Hebrew "לחץ כאן" link.
        #   2. "Access policy evaluation is already in progress for your current
        #      session" — a STALE/concurrent F5 session (a prior run that didn't
        #      log out). Reset link is English "here" whose href is
        #      `javascript:document.location=redirectURI`; clicking it kills the
        #      old session and drops back on the credentials form (operator
        #      confirmed). F5 allows ONE session per user, so without this every
        #      run after the first lands here instead of the OTP screen and times
        #      out at the otpass wait. Clicking it at login start = self-healing.
        # Loop a few times: click whichever reset link is present until the
        # username field appears.
        reset_selectors = (
            "a:has-text('לחץ כאן')",
            "a[href*='redirectURI']",
            "a[href^='javascript:document.location']",
        )
        for attempt in range(4):
            if await page.locator("input[name='username']").count():
                break
            clicked = False
            for sel in reset_selectors:
                try:
                    link = page.locator(sel).first
                    if await link.count():
                        await link.click(timeout=4000)
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        clicked = True
                        break
                except Exception:
                    continue
            recovery = SCREENSHOT_ROOT / f"harel_apm_recovery_{safe_user}_{attempt}.png"
            await self._safe_screenshot(page, recovery)
            await self._dump_page_state(page, recovery)
            if not clicked:
                break

        # Inline APM form fill — explicit waits, since the shared helper's
        # selector iteration races with Harel's form re-render after the
        # recovery click.
        await self._wait_visible(page, "input[name='username']", timeout=15000)
        await page.fill("input[name='username']", username)
        await self._wait_visible(page, "input[name='password']", timeout=5000)
        await page.fill("input[name='password']", self._agents_password)
        await self._wait_visible(page, "input.credentials_input_submit, input[type='submit']", timeout=5000)
        await page.click("input.credentials_input_submit, input[type='submit']")

        post = SCREENSHOT_ROOT / f"harel_apm_post_submit_{safe_user}.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

        # F5 APM SMS OTP — same selectors the other APM portals use.
        await self._wait_visible(
            page,
            "input[name='otpass'], input[name='otp'], "
            "input[autocomplete='one-time-code'], "
            "input[name='code'], input[name='answer']",
            timeout=20000,
        )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(
            "input[name='otpass'], input[name='otp'], "
            "input[autocomplete='one-time-code'], "
            "input[name='code'], input[name='answer']",
            otp,
        )
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

        # Wait for F5 to redirect us OFF the my.policy login URL — APM
        # redirects to harelsafe.co.il only after the OTP is accepted.
        # Without this, download_reports starts mid-redirect and lands on
        # the wrong URL.
        try:
            await page.wait_for_url(
                lambda u: "my.policy" not in (u or "")
                          and "my.logout" not in (u or ""),
                timeout=20000,
            )
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        # Safe-vault downloads are NOT password-protected at the file level
        # (the second login already gates them).
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

        async def _checkpoint(stem: str) -> Path:
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)
            return p

        # ── Step 0: hangup recovery ──
        # After OTP, Harel sometimes parks the session on vdesk/hangup.php3 (a
        # logout bounce) or my.logout instead of SSO-ing into the safe — the
        # exact batch failure seen 2026-06-20 (post_otp URL = .../vdesk/hangup.php3).
        # The OTP cookie is already set, so clicking its "לחץ כאן" recovery link
        # (or re-hitting the origin) re-lands us authenticated and lets APM
        # forward to the safe. Loop a few times — the first recovery can bounce.
        from urllib.parse import urlparse
        for _ in range(3):
            url = page.url or ""
            if "hangup" not in url and "my.logout" not in url:
                break
            try:
                link = page.locator("a:has-text('לחץ כאן')").first
                if await link.count():
                    await link.click(timeout=5000)
                else:
                    parsed = urlparse(url)
                    await page.goto(
                        f"{parsed.scheme}://{parsed.netloc}/",
                        wait_until="domcontentloaded", timeout=20000,
                    )
            except Exception:
                pass
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)
        await _checkpoint("0_post_hangup_recovery")

        # ── Step 1: reach the safe vault ──
        # APM SSO drops us on `harelsafe.co.il/frmReportStat.aspx?key=...`
        # automatically after OTP — DON'T navigate away. The signed `key=`
        # is single-use; a goto would invalidate the session. Only navigate
        # if we somehow landed off the safe domain.
        if "harelsafe.co.il" not in page.url:
            try:
                await page.goto(SAFE_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass
        await _checkpoint("1_safe_landing")

        # ── Step 2: log in to the safe vault — OR skip if already in ──
        # After APM auth + OTP, Harel routes us through the safe with a
        # signed `key=` URL (frmReportStat.aspx?key=...) so no second login
        # form is presented. If we land on a frmReport*.aspx page, treat
        # that as "already in" and jump to row selection.
        if "frmReport" in page.url or "frmDirectAccess" in page.url:
            await _checkpoint("2_safe_auto_logged_in")
        else:
            try:
                await self._wait_visible(page, "input#txtUser, input[name='txtUser']", timeout=15000)
            except Exception:
                await _checkpoint("2_safe_login_not_found")
                raise RuntimeError(
                    f"לא נמצא טופס כניסה בכספת הראל ({page.url}). "
                    f"בדוק {run_id}_nav_2_safe_login_not_found.txt"
                )

            await page.fill("input#txtUser, input[name='txtUser']", username or "")
            pwd_filled = False
            for sel in (
                "input#txtPass",
                "input[name='txtPass']",
                "input[name='txtPassword']",
                "input[type='password']",
            ):
                try:
                    await page.fill(sel, self._safe_password, timeout=1500)
                    pwd_filled = True
                    break
                except Exception:
                    continue
            if not pwd_filled:
                await _checkpoint("2_safe_pwd_not_found")
                raise RuntimeError(
                    f"לא נמצא שדה סיסמה בכספת הראל ({page.url}). "
                    f"בדוק {run_id}_nav_2_safe_pwd_not_found.txt"
                )

            # InfoBay safe form uses `<input type="button" id="cmdOK"
            # onclick="__doPostBack('cmdOK','')" value="כניסה">`. Firing the
            # postback directly via JS sidesteps Playwright's click-handler
            # racing the navigation.
            try:
                await page.evaluate("__doPostBack('cmdOK', '')")
            except Exception:
                # Fallback: real click
                try:
                    await page.click("input#cmdOK", timeout=4000, no_wait_after=True)
                except Exception:
                    await _checkpoint("2_safe_submit_not_found")
                    raise RuntimeError(
                        f"לא נמצא כפתור כניסה בכספת הראל ({page.url}). "
                        f"בדוק {run_id}_nav_2_safe_submit_not_found.txt"
                    )

            # Wait for the postback to land us on frmReport*
            try:
                await page.wait_for_url(
                    lambda u: "frmReport" in (u or "") or "frmDirectAccess" in (u or ""),
                    timeout=15000,
                )
            except Exception:
                pass
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            await _checkpoint("2_safe_logged_in")

        # ── XHR fallback listener — captures Excel/ZIP/octet downloads in
        # case Playwright's expect_download misses a WebMethod stream. Reset
        # per-report below so we don't reuse a previous capture.
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

        # ── Loop over each REPORT_LABEL: select row → הצגה → dblclick row → back ──
        downloaded: list[Path] = []

        async def _ensure_at_report_selector():
            """If we're not on frmReportStat, click חזרה (cmdReturn) to get
            back. Best-effort — the row select fallback handles edge cases."""
            for _ in range(2):
                if "frmReportStat" in page.url:
                    return
                try:
                    await page.evaluate("__doPostBack('ctl00$MainButtons$cmdReturn', '')")
                    await page.wait_for_url(
                        lambda u: "frmReportStat" in (u or ""), timeout=10000
                    )
                    await page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:
                    pass

        for idx, label in enumerate(REPORT_LABELS):
            await _ensure_at_report_selector()
            await _checkpoint(f"3_{idx}_{_slug(label)}_selector")

            # Step 3: click the row label
            row_sel = await self._click_first_visible(
                page,
                [
                    f'span[id$="_ReportTypeName"]:has-text("{label}")',
                    f'tr:has(span[id$="_ReportTypeName"]:has-text("{label}")) input[type="radio"]',
                    f'tr:has(span[id$="_ReportTypeName"]:has-text("{label}")) td:first-child',
                    f'tr:has-text("{label}")',
                ],
                timeout=10000,
            )
            if not row_sel:
                _logger.warning("Harel: report row '%s' not found — skipping", label)
                await _checkpoint(f"3_{idx}_{_slug(label)}_not_found")
                continue

            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except Exception:
                pass

            # Step 4: click הצגה (cmdReports) via JS postback
            try:
                await page.evaluate(
                    "__doPostBack('ctl00$MainButtons$cmdReports', '')"
                )
            except Exception:
                # Fallback to real click
                try:
                    await page.click(
                        "input#ctl00_MainButtons_cmdReports", timeout=4000
                    )
                except Exception as e:
                    _logger.warning("Harel: cmdReports click failed for '%s': %s", label, e)
                    continue

            try:
                await page.wait_for_url(
                    lambda u: "frmReportList" in (u or ""), timeout=12000
                )
            except Exception:
                pass
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            await _checkpoint(f"4_{idx}_{_slug(label)}_display_clicked")

            # Step 5: dblclick first data row → download
            xhr_capture.update({"bytes": None, "url": None, "filename": None})
            row_locator = page.locator("tr.cssItemStyle").first
            fallback_out = download_dir / f"הראל - {label}.xlsx"

            final_path: Path | None = None
            try:
                await row_locator.wait_for(state="visible", timeout=10000)
                async with page.expect_download(timeout=45000) as dl_info:
                    await row_locator.dblclick()
                download = await dl_info.value
                suggested = (download.suggested_filename or "").strip()
                final_path = download_dir / (suggested or fallback_out.name)
                # Some safe rows return the same filename across reports;
                # ensure uniqueness by prepending the label slug if needed.
                if final_path.exists() or final_path == download_dir / "report.xlsx":
                    final_path = download_dir / f"הראל - {label} - {final_path.name}"
                await download.save_as(str(final_path))
            except Exception as native_err:
                for _ in range(20):
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    suggested = (xhr_capture["filename"] or "").strip()
                    final_path = download_dir / (suggested or fallback_out.name)
                    final_path.write_bytes(xhr_capture["bytes"])
                else:
                    _logger.warning(
                        "Harel: download failed for '%s' (%s): %s",
                        label, page.url, native_err,
                    )
                    await _checkpoint(f"5_{idx}_{_slug(label)}_download_failed")
                    continue

            if final_path:
                downloaded.append(final_path)
                _logger.info(
                    "Harel: downloaded '%s' → %s (%d bytes)",
                    label, final_path.name, final_path.stat().st_size,
                )
                await _checkpoint(f"5_{idx}_{_slug(label)}_downloaded")
        try:
            page.remove_listener("response", _on_response)
        except Exception:
            pass

        if not downloaded:
            raise RuntimeError(
                f"Harel: לא הצלחנו להוריד אף דוח מתוך {len(REPORT_LABELS)} סוגים"
            )

        _logger.info(
            "Harel: downloaded %d/%d reports", len(downloaded), len(REPORT_LABELS),
        )
        return downloaded
