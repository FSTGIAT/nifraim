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

    async def _frame_with(self, page: "Page", selector: str, *, visible: bool = False):
        """Return the first frame — main OR nested iframe — whose `selector`
        matches. Harel renders the F5 'התחברות נכשלה … לחץ כאן' error page (and
        sometimes the login form itself) INSIDE an iframe, so main-frame-only
        selectors find nothing (proven live: kiko's page dump listed ZERO
        interactive elements on a page that has the לחץ כאן link). page.frames[0]
        is the main frame, so this stays main-frame-first — no behaviour change
        when the element is top-level (royg's path)."""
        for fr in page.frames:
            try:
                loc = fr.locator(selector)
                if await loc.count():
                    if visible and not await loc.first.is_visible():
                        continue
                    return fr
            except Exception:
                continue
        return None

    async def _wait_field_frame(self, page: "Page", selector: str, timeout: int):
        """Poll every frame for a VISIBLE `selector` until found; return its
        frame. Raises on timeout (mirrors _wait_visible, but frame-aware)."""
        import asyncio as _a
        deadline = _a.get_event_loop().time() + timeout / 1000
        while _a.get_event_loop().time() < deadline:
            fr = await self._frame_with(page, selector, visible=True)
            if fr:
                return fr
            await page.wait_for_timeout(300)
        raise RuntimeError(f"harel: no frame with visible '{selector}' within {timeout}ms")

    async def login(self, page: "Page", username: str, password: str) -> None:
        # Stage 1: F5 APM auth at agents.harel-group.co.il/my.policy with
        # the agents-tier password. F5 then SMS-OTPs to the agent's phone.
        # Stage 2 (safe form fill) happens in download_reports after OTP.
        self._agents_password, self._safe_password = self._split_passwords(password)

        # F5 APM allows ONE session per user. A prior run that authenticated but
        # died before finishing OTP — or a lingering manual login — leaves a stale
        # session. The 'התחברות נכשלה … לחץ כאן' bounce links to href="/", which
        # only RECONNECTS into that broken session (it does NOT log out), so the
        # re-login never gets a fresh OTP. It works for an agent with no stale
        # session (royg) and dead-ends at the otpass wait for one that has it
        # (kiko, whose failed runs each left a session). So hit the F5 logout
        # FIRST — harmless when there's nothing to clear — so every login starts
        # from a clean session. Best-effort: tolerate any logout-URL failure.
        async def _f5_logout() -> None:
            """Best-effort F5 APM logout to clear a stale one-per-user session (the
            'התחברות נכשלה … לחץ כאן' href='/' link only RECONNECTS, never logs
            out). Tolerates any logout-URL failure."""
            for _logout_url in (
                "https://agents.harel-group.co.il/vdesk/hangup.php3?hangup_error=1",
                "https://agents.harel-group.co.il/my.logout.php3",
            ):
                try:
                    await page.goto(_logout_url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(700)
                except Exception:
                    continue

        await _f5_logout()
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
        async def _click_reset_until_form(tag: str) -> bool:
            """Click whichever F5 reset link ('לחץ כאן' / redirectURI) is present —
            IN WHATEVER FRAME it lives — until the username field appears. The
            error page and its link render inside an iframe, so this searches all
            frames (main-frame-first), not just the top document."""
            for attempt in range(4):
                if await self._frame_with(page, "input[name='username']"):
                    return True
                clicked = False
                for sel in reset_selectors:
                    fr = await self._frame_with(page, sel)
                    if fr:
                        try:
                            await fr.locator(sel).first.click(timeout=4000)
                            await page.wait_for_timeout(900)
                            clicked = True
                            break
                        except Exception:
                            continue
                recovery = SCREENSHOT_ROOT / f"harel_apm_recovery_{safe_user}_{tag}_{attempt}.png"
                await self._safe_screenshot(page, recovery)
                await self._dump_page_state(page, recovery)
                if not clicked:
                    break
            return bool(await self._frame_with(page, "input[name='username']"))

        async def _reset_link_present() -> bool:
            for sel in reset_selectors:
                if await self._frame_with(page, sel):
                    return True
            return False

        otp_selector = (
            "input[name='otpass'], input[name='otp'], "
            "input[autocomplete='one-time-code'], "
            "input[name='code'], input[name='answer']"
        )

        # F5 can bounce to the 'התחברות נכשלה … לחץ כאן' error page at login start
        # OR right AFTER the credentials submit — a stale one-per-user F5 session
        # (e.g. a lingering manual login, or a prior run that didn't reach OTP).
        # The reset link kills the old session and returns the real login form, so
        # run the whole fill→submit→OTP sequence in a retry loop, re-clicking the
        # reset link whenever the OTP screen fails to appear. Previously the reset
        # click ran ONLY pre-fill, so a post-submit bounce dead-ended at the otpass
        # timeout (kiko: reproducible when a manual Harel session was still open).
        last_exc: Exception | None = None
        for login_attempt in range(3):
            if login_attempt > 0:
                # A bounced submit may have created its OWN broken session; the
                # href='/' reconnect can't clear it, so do a real logout before
                # retrying instead of just re-clicking לחץ כאן.
                await _f5_logout()
                await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            await _click_reset_until_form(f"pre{login_attempt}")

            # Inline APM form fill — IN WHATEVER FRAME the form rendered (the F5
            # login can live inside an iframe, same as the error page).
            uf = await self._wait_field_frame(page, "input[name='username']", 15000)
            await uf.locator("input[name='username']").fill(username)
            await uf.locator("input[name='password']").fill(self._agents_password)
            await uf.locator(
                "input.credentials_input_submit, input[type='submit']"
            ).first.click(timeout=5000)

            post = SCREENSHOT_ROOT / f"harel_apm_post_submit_{safe_user}.png"
            await self._safe_screenshot(page, post)
            await self._dump_page_state(page, post)

            # Self-report the post-submit page to Railway logs (WORKER-LOG …) so we
            # can see WHAT F5 rendered — its URL, every input's name/id/type, and a
            # snippet of visible text — without needing a screenshot off the worker.
            # This is the ground truth for why the OTP box isn't appearing.
            try:
                from app.services.portal_automation.runner import _worker_note
                await page.wait_for_timeout(1500)  # let the page settle
                # Frame-aware: report inputs across ALL frames (the OTP/error
                # content may be inside an iframe, invisible to the top document).
                names, clicks = [], []
                for fr in page.frames:
                    try:
                        fnames = await fr.eval_on_selector_all(
                            "input", "els => els.map(e => (e.name||e.id||'?')+':'+e.type)"
                        )
                        if fnames:
                            names.append((fr.url[-40:], fnames[:12]))
                    except Exception:
                        pass
                    try:
                        # clickables + their href/onclick — so a 'terminate session /
                        # continue' link or button on the F5 choice page is visible
                        # to us (its href/onclick tells us how to proceed).
                        cl = await fr.eval_on_selector_all(
                            "a, button, input[type=submit], input[type=button]",
                            "els => els.map(e => ((e.innerText||e.value||'').trim().slice(0,20))"
                            "+'|'+((e.getAttribute&&(e.getAttribute('href')||e.getAttribute('onclick')))||'').slice(0,40))"
                        )
                        if cl:
                            clicks.append(cl[:10])
                    except Exception:
                        pass
                try:
                    body_txt = " ".join((await page.inner_text("body", timeout=2500)).split())[:150]
                except Exception:
                    body_txt = ""
                _worker_note(
                    f"harel post-submit a{login_attempt}: url={page.url} "
                    f"frames={len(page.frames)} inputs={names} clicks={clicks} text={body_txt}"
                )
            except Exception:
                pass

            # F5 APM SMS OTP — in whatever frame it rendered.
            try:
                await self._wait_field_frame(page, otp_selector, 20000)
                return  # OTP screen reached — login done.
            except Exception as exc:
                last_exc = exc
                # Bounced to the error page? If a reset link is present, loop to
                # click it and retry the whole login. Otherwise it's a genuine
                # failure (wrong password, changed selector) — re-raise.
                if login_attempt < 2 and await _reset_link_present():
                    continue
                raise
        if last_exc:
            raise last_exc

    async def submit_otp(self, page: "Page", otp: str) -> None:
        otp_selector = (
            "input[name='otpass'], input[name='otp'], "
            "input[autocomplete='one-time-code'], "
            "input[name='code'], input[name='answer']"
        )
        # The OTP field can be inside an iframe (same as the login form/error
        # page), so fill it in whatever frame holds it — not just the top document.
        otp_frame = await self._frame_with(page, otp_selector, visible=True) or page
        await otp_frame.locator(otp_selector).first.fill(otp)
        for sel in (
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('כניסה')",
            "button:has-text('המשך')",
            "button:has-text('אישור')",
            "button:has-text('Logon')",
        ):
            try:
                await otp_frame.locator(sel).first.click(timeout=2500)
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
