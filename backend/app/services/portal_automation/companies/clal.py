"""Clal (כלל) agent portal — login, OTP, download PRODUCTION files from PayLink.

Flow (per the operator):
  1. Go to `https://www.clalnet.co.il/my.policy` (F5 BIG-IP APM).
  2. Click the pre-login entry link ("לכניסה לאתר / לחץ/י כאן").
  3. Submit username + password (shared APM form — see `_apm_helpers.py`).
  4. Password-change branch: clalnet sometimes redirects to
     `…/ClalnetForgotPsw/ClalnetForgotPassword.html` (הפקת סיסמה חדשה). We can't
     reset the password — stop with a clear, user-facing message.
  5. SMS OTP step → reuse the runner's otp_inbox.
  6. The site is an Angular SPA; click the sidebar toggle (`button.open-icon`).
  7. Enter the PayLink (פיילינק) system — an ASP.NET WebForms app whose grid
     `ctl00_MainContent_grdList` lists report types (e.g. בריאות). Download ALL
     production-payment rows.

Files are saved with production-preserving Hebrew names ("כלל - פרודוקציה …") so
`detect_format()` routes them as production, NOT commission (the filename must
never contain עמלות / נפרעים). See the auto-ingest pipeline + Menora plugin.

Selectors for steps 6-7 (Angular SPA + ASP.NET grid) can only be confirmed
against the live site, so `download_reports` ships best-effort with heavy
checkpoint dumps + an XHR fallback. Refine from `<run_id>_*.txt` artifacts under
`data/portal_screenshots/` after the first live run.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation._apm_helpers import apm_login_submit

# Module-level, deliberately. `_logger` used to be imported INSIDE
# `_grab_report`; a caller added elsewhere in the file then raised
# `name '_logger' is not defined` and took the whole Clal run down at
# stage=download (live 2026-07-19 batch a1f30dd6). A logger must not be
# scoped to one function in a module that logs from several.
_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://www.clalnet.co.il/my.policy"

# Substrings that mark a row/filename as something OTHER than production. The
# PayLink grid is production-payment files, but guard against commission rows
# slipping in (they'd be misrouted by the ingest dispatcher).
_NON_PRODUCTION = ("עמלות", "נפרעים", "commission")

# The drawer that actually holds production. Confirmed by QA against the live
# portal (2026-07-19): InfoBay → drawer `קבצי פרודוקציה` → "הצגה"
# (`cmdReports`) → its report list holds the `תיבה_<box>_כלל_חיים_מתאריך_…` /
# `תיבה_<box>_בריאות_חיים_מתאריך_…` files, newest first.
#
# Selecting drawers by _NON_PRODUCTION alone is a BLACKLIST: every drawer that
# isn't obviously commission got treated as production, so the run walked into a
# payments drawer whose reports really are PDFs — which `upload_ingest` then
# rejected ("Unsupported file extension 'pdf'"), and Clal contributed nothing to
# the merged file for weeks. The PDFs were never a format problem; they were the
# wrong drawer. Prefer this name when present, and only fall back to the
# blacklist when it isn't (a renamed drawer must not silently download nothing).
_PRODUCTION_DRAWERS = ("קבצי פרודוקציה", "קבצי פרודקציה")


def _sniff_ext(body: bytes, content_type: str = "", fallback: str = ".htm") -> str:
    """Identify a downloaded blob by its MAGIC BYTES, not by content-type.

    InfoBay serves the `קבצי פרודוקציה` box files with a generic/absent
    content-type, so the old header-only ladder fell through to `.htm` — which
    `upload_ingest` rejects ("Unsupported file extension 'htm'"). That extension
    meant "we could not tell", never "this is HTML", so the real format was
    invisible: live 2026-07-20, `כלל - פרודוקציה קבצי פרודוקציה 0.htm` was the
    right file from the right drawer, discarded for want of a name.

    Magic first, header second, fallback last.
    """
    head = bytes(body or b"")[:8]
    if head[:2] == b"PK":
        # A .xlsx IS a zip, so PK alone is NOT enough — look inside. Getting this
        # wrong is not cosmetic: `upload_ingest` dispatches on the extension, and
        # `ext == "zip"` goes to `_parse_zip_bundle`, which only recognises the
        # Mimshak / Menora-legacy / Menora-amalot bundles. An xlsx labelled .zip
        # would be rejected there instead of parsed as a spreadsheet — turning a
        # perfectly good download into a silent loss.
        try:
            import io as _io
            import zipfile as _zf
            with _zf.ZipFile(_io.BytesIO(bytes(body))) as z:
                names = set(z.namelist())
            # `xl/` FIRST. Every OOXML archive carries [Content_Types].xml —
            # docx and pptx included — so testing that first made the
            # word/ppt branch unreachable and labelled a .docx as .xlsx, which
            # then dies deep inside the spreadsheet parser instead of taking
            # the clean not-ingestible path.
            if any(n.startswith("xl/") for n in names):
                return ".xlsx"
            if any(n.startswith("word/") or n.startswith("ppt/") for n in names):
                return ".zip"          # OOXML but not a workbook — not ingestible
        except Exception:
            pass                        # truncated/corrupt archive → fall through
        return ".zip"
    if head[:4] == b"%PDF":
        return ".pdf"
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":   # OLE2 → legacy .xls
        return ".xls"
    lowered = bytes(body or b"")[:512].lstrip().lower()
    if lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html"):
        return ".htm"
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return ".pdf"
    if "zip" in ct:
        return ".zip"
    if "excel" in ct or "spreadsheet" in ct or ".xls" in ct:
        return ".xlsx"
    return fallback


def _describe_blob(body: bytes) -> str:
    """Short, loggable fingerprint of an unidentified download — first bytes as
    hex + printable prefix. Enough to name the format on the NEXT run without
    anyone having to fetch the file off the worker's disk."""
    b = bytes(body or b"")
    if not b:
        return "EMPTY"
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in b[:24])
    return f"{len(b)}B magic={b[:8].hex()} ascii={printable!r}"


def _sanitize_label(text: str) -> str:
    """Collapse whitespace + strip filesystem-hostile chars for a filename."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = re.sub(r"[\\/:*?\"<>|]", "", cleaned)
    return cleaned[:60] or "report"


class ClalPortal(BasePortalAutomation):
    portal_kind = "clal"
    company_label = "כלל — פיילינק (פרודוקציה)"
    # Downloaded on this same login (see download_reports) — mirror our
    # outcome onto its credential so its card is not stuck at "ממתין".
    folds = ('clal_nifraim',)

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT

        async def _attempt() -> str:
            """One full logon attempt. Returns 'otp' | 'creds' | 'pwchange' | 'timeout'."""
            await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            # Landing entry link before the APM form
            # ("<span class='LoginText'> לכניסה לאתר <a>לחץ/י כאן</a></span>").
            await self._click_first_visible(
                page,
                ["span.LoginText a", "a:has-text('לחץ')", "a:has-text('לכניסה')"],
                timeout=6000,
            )
            # Standard F5 APM user+password form (input#input_1 / input#input_2).
            await apm_login_submit(page, username, password)
            # A real URL redirect marks the reset page (the login page's own
            # "שכחתי סיסמה" link would false-positive a body substring).
            for _ in range(24):  # ~12s
                if self._is_password_change_url(page.url):
                    return "pwchange"
                if await self._has_credentials_error(page):
                    return "creds"
                try:
                    el = await page.query_selector(self.OTP_FIELD)
                    if el and await el.is_visible():
                        return "otp"
                except Exception:
                    pass
                await page.wait_for_timeout(500)
            if self._is_password_change_url(page.url):
                return "pwchange"
            try:
                await self._wait_visible(page, self.OTP_FIELD, timeout=10000)
                return "otp"
            except Exception:
                return "timeout"

        async def _dump_rejection() -> None:
            base = SCREENSHOT_ROOT / "clal_login_rejected.png"
            await self._safe_screenshot(page, base)
            await self._dump_page_state(page, base)

        _PWCHANGE_MSG = (
            "כלל מבקשת לעדכן סיסמה. החליפ/י סיסמה באתר כלל (clalnet.co.il) ואז "
            "עדכנ/י את הסיסמה השמורה כאן כדי שהאוטומציה תוכל להתחבר."
        )

        # F5 BIG-IP APM allows only a limited number of concurrent sessions per
        # user. A leftover session from an earlier run re-renders the logon page
        # WITH the inline "שם המשתמש או הסיסמא שגויים" error even though the
        # password is correct — measured 2026-07-24: the SAME creds succeeded at
        # 14:57 and a fresh login 65 min later was bounced with that text in 5 s.
        # Clearing cookies kills the stale F5 session, so retry ONCE on a clean
        # session before trusting a credentials rejection (the same self-heal
        # Hachshara — same F5 platform — already has). A GENUINE bad password
        # still fails: it is rejected again on the clean second attempt.
        for attempt in range(2):
            result = await _attempt()
            if result == "otp":
                return
            if result == "pwchange":
                raise RuntimeError(_PWCHANGE_MSG)
            if attempt == 0:
                # 'creds' or 'timeout' on the first try → likely a stale F5
                # session. Shed cookies and retry clean.
                _logger.warning(
                    "Clal: login gave %r on attempt 1 — clearing cookies "
                    "(likely stale F5 session) and retrying clean", result)
                try:
                    await page.context.clear_cookies()
                except Exception:
                    pass
                await page.wait_for_timeout(1000)
                continue
            # Second attempt on a clean session still failed → real.
            await _dump_rejection()
            if result == "creds":
                raise RuntimeError(
                    "כלל דחתה את שם המשתמש/הסיסמה (\"שם המשתמש או הסיסמא שגויים\") "
                    "גם אחרי ניקוי סשן F5 — ייתכן שהסיסמה פגה/הוחלפה. התחבר/י ידנית "
                    "לאתר כלל, עדכנ/י סיסמה, ואז עדכנ/י את הפרטים השמורים כאן. "
                    "בדוק clal_login_rejected.txt"
                )
            raise RuntimeError(
                "כלל: מסך ה-OTP לא הופיע אחרי התחברות (גם אחרי ניקוי סשן) — "
                "בדוק clal_login_rejected.txt"
            )

    @staticmethod
    def _is_password_change_url(url: str | None) -> bool:
        u = (url or "").lower()
        return "forgotpsw" in u or "forgotpassword" in u

    async def _has_credentials_error(self, page: "Page") -> bool:
        """The F5 APM logon page re-renders with an inline Hebrew error when the
        username/password is rejected: "שם המשתמש או הסיסמא שגויים, נסה שנית."
        (no redirect, no OTP). Detect it so the run fails with an actionable
        message instead of an opaque "OTP field never appeared" timeout."""
        try:
            body = await page.inner_text("body")
        except Exception:
            return False
        return "שם המשתמש או הסיסמא שגויים" in body or "הסיסמא שגויים" in body

    # APM portals reuse the password input (#input_2) for the OTP step and
    # relabel it (cf. Phoenix's "קוד זיהוי" placeholder). Cover both the
    # dedicated-OTP-field and reused-input_2 variants.
    OTP_FIELD = (
        "input[name='otp'], input[autocomplete='one-time-code'], "
        "input[name='code'], input[name='answer'], "
        "input[placeholder*='קוד'], input#input_2"
    )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(self.OTP_FIELD, otp)
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
        # Clal's post-login UI is an Angular SPA (…/ClalAgentClient/#/) that polls
        # continuously, so it often NEVER reaches "networkidle" — an unguarded wait
        # here raises `Timeout 20000ms exceeded` and kills a run whose OTP was
        # actually accepted (live: kikohib 2026-07-30 batch failed @otp on exactly
        # this line). The wait is only a settle; download_reports navigates the SPA
        # home and has its own checkpoints, so a timeout must NOT fail the run.
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        self.report_password = None

        from app.services.portal_automation.runner import (
            SCREENSHOT_ROOT, logger, _worker_note,
        )

        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)
        # The post-OTP SPA home — we return here before the נפרעים grab (the
        # "לפירוט עמלות" link that opens the commissions tab lives on this view).
        clal_home_url = page.url

        async def _checkpoint(stem: str) -> None:
            base = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, base)
            await self._dump_page_state(page, base)

        # XHR fallback: ASP.NET grids frequently serve files via __doPostBack
        # POSTs whose response is the file stream — `expect_download` may never
        # fire. Capture every Excel-ish response so we still get the bytes.
        xhr_captures: list[dict] = []

        def _attach_response_listener(target: "Page") -> None:
            async def _on_response(resp):
                try:
                    ct = (resp.headers.get("content-type") or "").lower()
                    cd = (resp.headers.get("content-disposition") or "").lower()
                    url = resp.url.lower()
                    # Capture any downloadable response — the universal signal is
                    # Content-Disposition: attachment, plus known report types
                    # (PDF / Excel / ZIP / .htm report files). Migdal-style.
                    exts = (".xlsx", ".xls", ".zip", ".pdf", ".csv", ".htm", ".html", ".dat")
                    is_file = (
                        "attachment" in cd
                        or "spreadsheetml" in ct
                        or "vnd.ms-excel" in ct
                        or "application/pdf" in ct
                        or "application/octet-stream" in ct
                        or "application/zip" in ct
                        or any(ext in cd for ext in exts)
                        or any(("/" + url.rsplit("/", 1)[-1]).find(ext) > -1 for ext in exts)
                    )
                    # EXCLUDE static assets. The URL test below matches any
                    # segment containing ".htm", and InfoBay serves stylesheets
                    # from .htm endpoints — live 2026-07-20 the capture that
                    # reached ingest was 1789 bytes of jQuery UI CSS
                    # (magic 2f2a2054 = "/* Theme", "ThemeRoller override").
                    # A report is never text/css, javascript, an image or a font.
                    is_asset = (
                        "text/css" in ct
                        or "javascript" in ct
                        or ct.startswith("image/")
                        or ct.startswith("font/")
                        or "font-woff" in ct
                        or url.rsplit("?", 1)[0].endswith((".css", ".js", ".png",
                                                           ".jpg", ".gif", ".svg",
                                                           ".woff", ".woff2", ".ico"))
                    )
                    if is_file and not is_asset:
                        body = await resp.body()
                        if body and len(body) > 1024:
                            xhr_captures.append({
                                "bytes": body, "url": resp.url, "cd": cd, "ct": ct,
                            })
                except Exception:
                    pass

            target.on("response", _on_response)

        _attach_response_listener(page)

        # ShowReport() for .htm reports fires a native confirm() ("continue in
        # this window?"); Playwright auto-DISMISSES native dialogs by default
        # (= Cancel), so window.open never runs and the report never opens.
        # Auto-ACCEPT every native dialog, on the main page AND every popup, so
        # .htm reports open like .pdf ones do.
        def _accept_dialog(dialog) -> None:
            import asyncio as _a
            _a.ensure_future(dialog.accept())

        page.on("dialog", _accept_dialog)
        page.context.on("page", lambda p: p.on("dialog", _accept_dialog))

        await _checkpoint("post_otp")

        # Step 6: open the Angular sidebar/menu via the toggle button.
        await self._click_first_visible(
            page,
            [
                "button.open-icon",
                "button:has(span.arrow-left)",
                "button.ng-star-inserted.open-icon",
                "button:has(span.arrow-right)",
            ],
            timeout=8000,
        )
        await page.wait_for_timeout(1200)
        await _checkpoint("after_toggle")

        # Step 7: open "infobay" — Clal's reports system (data.clal.co.il) that
        # hosts the "מגירות מידע" drawer grid (frmReportStat.aspx, grdList) with
        # rows like "קבצי פרודוקציה" and "בריאות".
        #
        # DIAGNOSED LIVE 2026-07-24 (kiko batch 3c0b055f): the old
        # `*:has-text('infobay')` text-click was too loose — it matched a promo
        # tile and navigated to a MARKETING PDF (ניוד-פנסיה-מגיל-60.pdf), so the
        # grid never rendered → 0 drawers → the run hard-raised and even the
        # נפרעים leg was lost. The real entry is a specific anchor whose href
        # points at `data.clal.co.il` with a signed, session-scoped `k=` key.
        # Navigate to that href in a NEW page (the sidebar overlay makes the
        # anchor itself flaky to click, but its href SSO-lands straight on the
        # drawer grid — verified live). Fall back to the old text-click.
        infobay_url = None
        try:
            a = page.locator("a[href*='data.clal.co.il']").first
            if await a.count():
                infobay_url = await a.get_attribute("href")
        except Exception:
            pass
        opened = False
        if infobay_url:
            try:
                popup = await page.context.new_page()
                await popup.goto(infobay_url, wait_until="domcontentloaded", timeout=30000)
                page = popup
                _attach_response_listener(page)
                opened = True
                logger.info("Clal: infobay opened via anchor href %s", page.url)
            except Exception as e:
                logger.warning("Clal: infobay href navigation failed (%s) — trying click", e)
        if not opened:
            infobay_candidates = [
                "a[href*='data.clal.co.il']",
                "a:has-text('infobay')",
                "div.text:has-text('infobay')",
            ]
            try:
                async with page.context.expect_page(timeout=8000) as popup_info:
                    await self._click_first_visible(page, infobay_candidates, timeout=8000)
                popup = await popup_info.value
                await popup.wait_for_load_state("domcontentloaded", timeout=20000)
                page = popup
                _attach_response_listener(page)
                logger.info("Clal: infobay opened in popup %s", page.url)
            except Exception:
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

        # InfoBay one-session guard: "מהלך עבודה פעיל בלשונית אחרת" — when a prior
        # (failed) run left an active InfoBay session, this modal blocks the grid
        # with יציאה / המשך. Clicking המשך continues into THIS window's grid.
        # Without it the grid never renders → 0 drawers (recurs for an agent whose
        # runs fail mid-session, e.g. kiko). It's InfoBay's OWN HTML modal, not a
        # native browser dialog, so click the button element.
        try:
            cont = page.locator(
                "input[value='המשך'], button:has-text('המשך'), a:has-text('המשך')"
            ).first
            if await cont.count() and await cont.is_visible():
                await cont.click(timeout=4000)
                logger.info("Clal: dismissed InfoBay 'active session' modal via המשך")
                await page.wait_for_timeout(1500)
        except Exception:
            pass

        # Wait for the ASP.NET grid to render before enumerating.
        try:
            await page.wait_for_selector("table[id*='grdList']", timeout=15000)
        except Exception:
            pass

        await _checkpoint("paylink")

        # The InfoBay screen (frmReportStat.aspx, "מגירות מידע") lists report-type
        # DRAWERS, each a <tr> with a ReportTypeName span. The real download flow
        # (per operator) is button-driven, NOT double-click:
        #   1. select a drawer row → click "הצגה" (cmdReports) → its report list
        #   2. select a report row → click "הורדה" (cmdReportProp) → download
        #   3. "חזרה למסך הקודם" back to the drawer list for the next type
        # A "מהלך עבודה פעיל בלשונית אחרת" (#DialogUserActive) warning pops up
        # intermittently and must be dismissed to keep working in this window.
        SHOW_BTN = "#ctl00_MainButtons_cmdReports"
        VIEW_BTN = "#ctl00_MainButtons_cmdReportProp"  # "הצגה" on the report list
        BACK_SELECTORS = [
            "a:has-text('חזרה למסך הקודם')",
            "#ctl00_MainButtons_cmdReturn",
            "input[value='חזרה']",
            "input[value*='חזרה למסך']",
            "a:has-text('חזרה')",
            "[title*='חזרה']",
        ]
        ROW_SELECTOR = (
            "table[id*='grdList'] tr.cssItemStyle, "
            "table[id*='grdList'] tr.cssAlternatingItemStyle, "
            "table[id*='grdList'] tr[ondblclick]"
        )

        async def _dismiss_dialog(p) -> None:
            try:
                if not await p.query_selector("#DialogUserActive"):
                    return
                for sel in (
                    ".ui-dialog:has(#DialogUserActive) .ui-dialog-buttonpane button",
                    ".ui-dialog:has(#DialogUserActive) .ui-dialog-titlebar-close",
                    ".ui-dialog-titlebar-close",
                ):
                    try:
                        await p.click(sel, timeout=1500)
                        return
                    except Exception:
                        continue
                await p.keyboard.press("Escape")
            except Exception:
                pass

        def _box_month(text: str):
            """(year, month) from a box name's `…מתאריך_DD-MM-YYYY…` stamp, else None.
            The box's own name carries its creation date — more reliable than
            guessing which date CELL is 'תאריך יצירה'."""
            m = re.search(r"מתאריך[_\s-]*(\d{2})-(\d{2})-(\d{4})", text or "")
            return (int(m.group(3)), int(m.group(2))) if m else None

        async def _close_bundle_modal(p) -> None:
            """Close the in-page frmBundle box modal so the NEXT row is clickable.
            The modal stays open after a download and its backdrop intercepts
            clicks — leaving it open is why the old loop only ever got box 0."""
            frames = [f for f in p.frames if "frmbundle" in (f.url or "").lower()]
            for t in frames + [p]:
                for sel in ("input[value='סגירה']", "button:has-text('סגירה')",
                            "a:has-text('סגירה')", "input[value*='סגירה']", "#cmdClose"):
                    try:
                        loc = t.locator(sel).first
                        if await loc.count() and await loc.is_visible():
                            await loc.click(timeout=2500)
                            await p.wait_for_timeout(500)
                            return
                    except Exception:
                        continue
            # Fallback: tear the modal/backdrop out so it stops eating clicks.
            try:
                await p.evaluate(
                    """() => {
                        ['divModalDialog','frBundle'].forEach(id => {
                            const e = document.getElementById(id);
                            if (e) { const d = e.closest('.ui-dialog') || e; d.remove(); }
                        });
                        document.querySelectorAll('.ui-widget-overlay').forEach(e => e.remove());
                    }"""
                )
            except Exception:
                pass

        async def _goto_next_page(p, cur: int) -> bool:
            """Advance the InfoBay pager to page cur+1 (best-effort). Returns
            True if it moved — used only when a month's boxes overflow one page."""
            nxt = str(cur + 1)
            for sel in (f"a:text-is('{nxt}')", f"a:has-text('{nxt}')"):
                try:
                    loc = p.locator(sel).last
                    if await loc.count():
                        await loc.click(timeout=4000)
                        await p.wait_for_load_state("domcontentloaded", timeout=8000)
                        await p.wait_for_selector(ROW_SELECTOR, timeout=6000)
                        await p.wait_for_timeout(400)
                        return True
                except Exception:
                    continue
            return False

        async def _save_dl(dl, base_name: str) -> "Path | None":
            ext = Path(dl.suggested_filename or "").suffix or ".bin"
            t = download_dir / f"{base_name}{ext}"
            try:
                await dl.save_as(str(t))
                return t
            except Exception:
                return None

        async def _harvest_viewer(vp, base_name: str, dump_stem: str | None) -> "Path | None":
            """On a report viewer (popup or same-tab), look for a 'הורדה' button
            for the real file; else save the rendered HTML."""
            if dump_stem:
                await self._safe_screenshot(vp, SCREENSHOT_ROOT / f"{dump_stem}.png")
                await self._dump_page_state(vp, SCREENSHOT_ROOT / f"{dump_stem}.png")
            holder: dict = {}
            vp.once("download", lambda d: holder.setdefault("dl", d))
            clicked = await self._click_first_visible(
                vp,
                [
                    "input[value='הורדה']",
                    "a:has-text('הורדה')",
                    "input[value*='הורד']",
                    "[title*='הורד']",
                    "input[value*='ייצוא']",
                    "a:has-text('Excel')",
                ],
                timeout=4000,
            )
            if clicked:
                for _ in range(20):
                    if holder.get("dl"):
                        break
                    await asyncio.sleep(0.4)
                if holder.get("dl"):
                    got = await _save_dl(holder["dl"], base_name)
                    if got:
                        return got
            # No download button — fetch the underlying file the viewer is
            # showing (PDF/HTML report served at vp.url) reusing the session
            # cookies, so we save the real bytes rather than a viewer shell.
            try:
                vurl = vp.url or ""
                if vurl and not vurl.startswith("about:"):
                    resp = await vp.context.request.get(vurl)
                    body = await resp.body()
                    ct = (resp.headers.get("content-type") or "").lower()
                    if body and len(body) > 512:
                        ext = ".pdf" if vurl.lower().endswith(".pdf") else _sniff_ext(body, ct)
                        if ext == ".htm":
                            _logger.info("clal: unidentified viewer blob %s", _describe_blob(body))
                            self.partial_errors.append(
                                f"{base_name}: פורמט לא מזוהה — {_describe_blob(body)}"
                            )
                        t = download_dir / f"{base_name}{ext}"
                        t.write_bytes(body)
                        return t
            except Exception:
                pass
            # Last resort: save the rendered HTML/DOM of the report viewer.
            try:
                t = download_dir / f"{base_name}.htm"
                t.write_text(await vp.content(), encoding="utf-8")
                return t
            except Exception:
                return None

        async def _harvest_bundle_modal(p, base_name: str, dump_stem: str | None) -> "Path | None":
            """Capture a production "תיבה" box from the IN-PAGE MODAL iframe.

            For bundle='2' reports (קבצי פרודוקציה), ShowReport() does NOT open a
            popup or navigate — it loads `#frBundle` (iframe) with
            src="frmBundle.aspx?RepID=…" inside `#divModalDialog`, and that frame
            shows the box message with the attached `.exe` self-extracting file
            and a "הורד" link (confirmed live 2026-07-24 from the saved
            frmReportList HTML + the operator screenshot). The old code watched
            only for download/popup/nav/xhr, none of which fire for a modal
            iframe — hence "לא ירדו קבצים" for every production report.

            Find the frmBundle frame, click הורד/הורדה, capture the download.
            """
            # Locate the bundle iframe by URL (survives re-render better than #id).
            fr = None
            for _ in range(30):  # ~12s for the iframe to attach + load
                for f in p.frames:
                    if "frmbundle.aspx" in (f.url or "").lower():
                        fr = f
                        break
                if fr:
                    break
                await asyncio.sleep(0.4)
            if fr is None:
                return None
            try:
                await fr.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            if dump_stem:
                await self._safe_screenshot(p, SCREENSHOT_ROOT / f"{dump_stem}.png")
                await self._dump_page_state(p, SCREENSHOT_ROOT / f"{dump_stem}.png")

            # The download attaches to the PAGE, not the frame. Arm the listener,
            # then click the per-file "הורד" link (or the "הורדה" button) inside
            # the frame. `a:has-text('הורד')` matches both הורד and הורדה.
            holder: dict = {}
            p.once("download", lambda d: holder.setdefault("dl", d))
            clicked = False
            # The per-file download control is confirmed live (2026-07-30) to be
            #   <a href="javascript:download();" class="lnkDownload" title="הורד">הורד</a>
            # so match its CLASS first (unambiguous), then title/text, then the
            # "הורדה" button, before the broader fallbacks.
            for sel in ("a.lnkDownload", "a[title='הורד']", "a:has-text('הורד')",
                        "input[value='הורדה']", "input[value*='הורד']",
                        "[onclick*='Download']", "a[href*='Download']"):
                try:
                    loc = fr.locator(sel).first
                    if await loc.count():
                        await loc.click(timeout=4000)
                        clicked = True
                        break
                except Exception:
                    continue
            # The link's action is a bare `javascript:download()` call. If no
            # selector clicked, or the click didn't register a download event,
            # invoke the frame's (or page's) own download() directly — this is
            # what the anchor would have run anyway.
            if not clicked or not holder.get("dl"):
                for _tgt in (fr, p):
                    try:
                        await _tgt.evaluate("typeof download==='function' && download()")
                    except Exception:
                        continue
            for _ in range(30):  # boxes can be a few MB
                if holder.get("dl"):
                    break
                await asyncio.sleep(0.4)
            if not holder.get("dl"):
                # Some InfoBay builds stream the box via the response listener.
                return None
            dl = holder["dl"]
            raw_name = dl.suggested_filename or f"{base_name}.exe"
            box_path = download_dir / raw_name
            try:
                await dl.save_as(str(box_path))
            except Exception:
                return None
            data = box_path.read_bytes()
            _logger.info("clal: box captured %s (%d bytes) magic=%s",
                         raw_name, len(data), data[:4].hex())
            try:
                _worker_note(
                    f"clal box {raw_name}: {len(data)}B magic={data[:8].hex()} "
                    f"ascii={data[:16].decode('latin-1', 'replace')!r}"
                )
            except Exception:
                pass
            # Extract the payload. InfoBay .exe boxes are self-extracting ZIPs;
            # Python's zipfile scans for the End-Of-Central-Directory record, so a
            # ZIP-SFX opens directly from the .exe bytes — pure-Python, portable
            # to the Windows worker (no 7z/unzip dependency). If it isn't a ZIP,
            # keep the .exe and surface it (do NOT invent a parser for an unseen
            # format).
            try:
                import io as _io
                import zipfile as _zip
                if _zip.is_zipfile(_io.BytesIO(data)):
                    with _zip.ZipFile(_io.BytesIO(data)) as zf:
                        inner = [n for n in zf.namelist() if not n.endswith("/")]
                        _worker_note(f"clal box {raw_name}: ZIP-SFX inner={inner[:10]}")
                        # Prefer a spreadsheet/data member; else the largest file.
                        pick = next(
                            (n for n in inner if n.lower().endswith((".xlsx", ".xls", ".csv", ".txt", ".dat"))),
                            max(inner, key=lambda n: zf.getinfo(n).file_size) if inner else None,
                        )
                        if pick:
                            payload = zf.read(pick)
                            ext = Path(pick).suffix or _sniff_ext(payload)
                            out = download_dir / f"{base_name}{ext}"
                            out.write_bytes(payload)
                            _logger.info("clal: box payload %s → %s (%d bytes)", raw_name, pick, len(payload))
                            return out
            except Exception as e:
                _logger.warning("clal: box extract failed for %s: %s", raw_name, e)
            # Not a ZIP (or empty): surface the box for follow-up, keep the file.
            self.partial_errors.append(
                f"{base_name}: תיבת .exe התקבלה אך לא חולצה — {_describe_blob(data)}"
            )
            return box_path

        async def _grab_report(p, row, base_name: str, dump_stem: str | None) -> "Path | None":
            """Double-click a report row (ShowReport → window.open) and capture
            the file across all behaviours: native download, popup viewer, or
            same-tab navigation. ShowReport is the universal trigger — it fires
            for every report type, unlike the cmdReportProp toolbar button
            (a no-op for .htm).

            NOTE: an earlier attempt forced `ShowReport('1')` (InfoBay's Excel
            path) here, on the theory that the PDFs we kept getting were a
            format choice. That was the wrong diagnosis — the PDFs came from
            opening the WRONG DRAWER (see _PRODUCTION_DRAWERS above). The real
            production drawer holds `תיבה_*` vault files, which are data, not
            spreadsheets, so forcing an Excel render would corrupt them. The
            manual flow QA documented uses a plain select + "הצגה"
            (cmdReportProp), which is exactly the fallback below.
            """
            holder: dict = {}
            url_before = p.url
            xhr_before = len(xhr_captures)
            p.once("download", lambda d: holder.setdefault("dl", d))
            p.context.once("page", lambda pg: holder.setdefault("pg", pg))

            try:
                await row.dblclick(timeout=6000)
            except Exception:
                # Fallback: select row + click the toolbar action button
                # ("הצגה" / cmdReportProp) — this is exactly the manual flow.
                try:
                    await row.click(timeout=4000)
                    await p.click(VIEW_BTN, timeout=4000)
                except Exception:
                    return None
            for _ in range(25):
                if (holder.get("dl") or holder.get("pg") or p.url != url_before
                        or len(xhr_captures) > xhr_before):
                    break
                # The "active session in another tab" warning can pop up here and
                # block the report from opening — dismiss it and keep waiting.
                await _dismiss_dialog(p)
                await asyncio.sleep(0.4)

            got: Path | None = None
            if holder.get("dl"):
                got = await _save_dl(holder["dl"], base_name)
            elif holder.get("pg"):
                pop = holder["pg"]
                try:
                    await pop.wait_for_load_state("domcontentloaded", timeout=12000)
                except Exception:
                    pass
                await asyncio.sleep(1.0)
                if holder.get("dl"):
                    got = await _save_dl(holder["dl"], base_name)
                else:
                    got = await _harvest_viewer(pop, base_name, dump_stem)
                try:
                    await pop.close()
                except Exception:
                    pass
            elif p.url != url_before:
                try:
                    await p.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                got = await _harvest_viewer(p, base_name, dump_stem)
                # Return from the same-tab viewer to the report list.
                await self._click_first_visible(p, BACK_SELECTORS, timeout=5000)
                try:
                    await p.wait_for_load_state("domcontentloaded", timeout=8000)
                    await p.wait_for_selector(ROW_SELECTOR, timeout=6000)
                except Exception:
                    pass
                await _dismiss_dialog(p)

            # Production "תיבה" box: ShowReport('0') loaded an IN-PAGE MODAL
            # iframe (frmBundle.aspx), not a popup/nav — so none of the branches
            # above fired. Harvest the .exe box from that iframe. This is THE path
            # for קבצי פרודוקציה (bundle=2); the checks above serve the בריאות
            # PDFs and other report types.
            if got is None:
                got = await _harvest_bundle_modal(p, base_name, dump_stem)
                if got is not None:
                    # Close the modal so the next report row is clickable.
                    for sel in ("#divModalDialog a:has-text('סגירה')",
                                "input[value='סגירה']", ".jqmClose",
                                "a:has-text('סגירה')"):
                        try:
                            loc = p.locator(sel).first
                            if await loc.count() and await loc.is_visible():
                                await loc.click(timeout=2000)
                                break
                        except Exception:
                            continue
                    await _dismiss_dialog(p)

            # Migdal-style fallback: if no download/popup yielded a file, take any
            # bytes the response listener captured during this report.
            if got is None and len(xhr_captures) > xhr_before:
                # Pick the BEST capture, not the most recent one. `[-1]` returns
                # whatever the page happened to load last, which on 2026-07-20
                # was a stylesheet rather than the report. Prefer an explicit
                # Content-Disposition: attachment; otherwise the largest body —
                # a real report dwarfs any stray asset that slips the filter.
                cands = xhr_captures[xhr_before:]
                cap = next(
                    (c for c in reversed(cands) if "attachment" in (c.get("cd") or "")),
                    max(cands, key=lambda c: len(c.get("bytes") or b"")),
                )
                blob = (cap.get("cd") or "") + " " + (cap.get("ct") or "") + " " + (cap.get("url") or "").lower()
                ext = _sniff_ext(cap.get("bytes") or b"", blob)
                if ext == ".htm":
                    _logger.info("clal: unidentified xhr blob %s", _describe_blob(cap.get("bytes")))
                    self.partial_errors.append(
                        f"{base_name}: פורמט לא מזוהה — {_describe_blob(cap.get('bytes'))}"
                    )
                try:
                    t = download_dir / f"{base_name}{ext}"
                    t.write_bytes(cap["bytes"])
                    got = t
                except Exception:
                    pass
            return got

        await _dismiss_dialog(page)

        # Enumerate the production drawers (skip any commission type).
        rows = await page.evaluate(
            """() => {
                const out = [];
                const grid = document.querySelector("table[id*='grdList']");
                if (!grid) return out;
                grid.querySelectorAll('tr').forEach((tr, i) => {
                    const rt = tr.querySelector("span[id*='ReportTypeName']");
                    if (!rt) return;
                    out.push({
                        index: i,
                        label: (rt.innerText || rt.textContent || '').trim(),
                        spanId: rt.id,
                    });
                });
                return out;
            }"""
        ) or []
        # WHITELIST first: the drawer QA confirmed by name. Only if it is absent
        # (renamed / different tenant) fall back to the old blacklist, so a name
        # change degrades to the previous behaviour instead of downloading zero.
        named = [
            r for r in rows
            if r.get("label") and any(w in r["label"] for w in _PRODUCTION_DRAWERS)
        ]
        if named:
            targets = named
            _logger.info(
                "clal: production drawer matched by name → %s",
                [r["label"] for r in named],
            )
        else:
            targets = [
                r for r in rows
                if r.get("label") and not any(b in r["label"] for b in _NON_PRODUCTION)
            ]
            self.partial_errors.append(
                "מגירת 'קבצי פרודוקציה' לא נמצאה — נעשה שימוש בסינון הישן. "
                f"מגירות שנמצאו: {[r.get('label') for r in rows][:8]}"
            )

        (SCREENSHOT_ROOT / f"{run_id}_grid_rows.txt").write_text(
            "URL: " + page.url + "\n\nALL ROWS:\n"
            + "\n".join(str(r) for r in rows)
            + "\n\nTARGET (production) DRAWERS:\n"
            + "\n".join(str(r) for r in targets),
            encoding="utf-8",
        )

        if not targets:
            # DEGRADE, don't hard-raise: this raise used to abort the whole run
            # BEFORE the נפרעים leg (live batch 3c0b055f — an empty production
            # grid took נפרעים down with it, flipping a partial into a total
            # failure). Record it and fall through to the נפרעים grab, which
            # shares this one Clal login. The final "no results at all" guard
            # still raises if BOTH legs come back empty.
            logger.warning("Clal: no production drawers at %s — continuing to נפרעים", page.url)
            self.partial_errors.append(
                f"פרודוקציה: לא נמצאו מגירות ({page.url[:80]}) — "
                f"בדוק {run_id}_paylink.txt / {run_id}_grid_rows.txt"
            )
            targets = []

        saved: list[Path] = []
        for r in targets:
            label = _sanitize_label(r["label"])

            # 1. Open the drawer's report list. Double-clicking the drawer row
            # (rowDblClick) navigates straight to THAT drawer's list with a fresh
            # key — more reliable than select+הצגה, which reused the previous
            # drawer's selection (same-key bug). Fall back to select+הצגה.
            opened = False
            try:
                await page.dblclick(f"#{r['spanId']}", timeout=6000)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                opened = True
            except Exception:
                pass
            if not opened:
                try:
                    await page.click(f"#{r['spanId']}", timeout=6000)
                    await page.wait_for_timeout(600)
                    await page.click(SHOW_BTN, timeout=6000)
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
            await _dismiss_dialog(page)
            try:
                await page.wait_for_selector(ROW_SELECTOR, timeout=12000)
            except Exception:
                pass
            await self._safe_screenshot(page, SCREENSHOT_ROOT / f"{run_id}_reports_{label}.png")
            await self._dump_page_state(page, SCREENSHOT_ROOT / f"{run_id}_reports_{label}.png")

            # 2. Download THIS MONTH's boxes — not just the newest.
            #
            # The list is newest-first and each box name carries its creation
            # date (…מתאריך_DD-MM-YYYY…). Each date is a separate box holding a
            # few clients, so a single month's production spans several boxes
            # (live 2026-07-30: 12 boxes total; July = the 3 newest = the real
            # month's production, ~20 clients — the old code grabbed only box 0,
            # one client). Walk top-down, download every box whose month == the
            # NEWEST box's month, and STOP at the first box from an earlier month
            # ("everything created this month"). Each box opens an IN-PAGE modal
            # that must be CLOSED before the next row, or its backdrop blocks the
            # next click. Pages overflow at 5 rows — follow the pager only while
            # still inside the target month.
            target_month = None
            ri, page_no, box_i = 0, 1, 0
            while True:
                rows_loc = page.locator(ROW_SELECTOR)
                n_rows = await rows_loc.count()
                if ri >= n_rows:
                    # End of this page — is the next page still the same month?
                    if target_month is not None and await _goto_next_page(page, page_no):
                        page_no += 1
                        ri = 0
                        continue
                    break
                row = rows_loc.nth(ri)
                try:
                    # The VISIBLE cell text is truncated ("…מתאריך_15-07-202 …"),
                    # so inner_text loses the 4-digit year and _box_month can't
                    # read the date. The FULL box name lives in a `title`
                    # attribute — read that instead (live 2026-07-30: this was
                    # why the month filter skipped every row and downloaded 0).
                    name = await row.evaluate(
                        """el => {
                            const t = [...el.querySelectorAll('[title]')]
                                .map(e => e.getAttribute('title') || '')
                                .find(x => x.includes('מתאריך'));
                            return t || el.innerText || '';
                        }"""
                    )
                    name = (name or "").strip()
                except Exception:
                    ri += 1
                    continue
                mo = _box_month(name)
                if mo is None:
                    ri += 1
                    continue
                if target_month is None:
                    target_month = mo
                    logger.info("clal: target production month = %02d/%d", mo[1], mo[0])
                if mo != target_month:
                    logger.info("clal: box '%s' is %02d/%d (earlier) — stopping",
                                name[:40], mo[1], mo[0])
                    break
                got = await _grab_report(
                    page, row, f"כלל - פרודוקציה {label} {box_i}",
                    dump_stem=f"{run_id}_view_{label}" if box_i == 0 else None,
                )
                await _close_bundle_modal(page)
                await _dismiss_dialog(page)
                if got:
                    saved.append(got)
                ri += 1
                box_i += 1
            logger.info("clal: downloaded %d production box(es) for %s", box_i, label)

            # 3. Back to the drawer list for the next type (app's own back —
            # browser back / re-visiting the key URL drops the InfoBay session).
            await self._click_first_visible(page, BACK_SELECTORS, timeout=6000)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                await page.wait_for_selector(
                    "table[id*='grdList'] span[id*='ReportTypeName']", timeout=8000
                )
            except Exception:
                pass
            await _dismiss_dialog(page)
            if "frmlogin" in page.url.lower():
                logger.warning("Clal: bounced to login after '%s'", label)
                break

        # Merge the month's production boxes into ONE clal production file.
        # Each box is a Mimshak .DAT holding a few clients; the runner ingests
        # every returned file with make_active=True, which DEACTIVATES
        # same-company actives — so returning the raw per-box .DATs would keep
        # only the LAST box (one client). Parse each and rebuild one
        # unified-format workbook (the same 6-tab shape as the manual
        # "פרודוקציה כלל" export), so ALL of the month's clients land in a single
        # active production upload. Best-effort: on failure, fall back to the raw
        # boxes rather than lose everything.
        # The month's clients live in the boxes' `.MEV` files (Clal fixed-width),
        # NOT the Mimshak `.DAT` (which holds one client) — parsing the `.DAT`
        # was why every run showed "1 customer" (live 2026-07-31). Extract the
        # `.MEV` from each downloaded box `.exe`, parse (clal_mev handles the
        # cp862-visual / cp1255 encodings + Hebrew reversal), dedup, and build
        # one unified-format production workbook.
        exe_boxes = sorted(download_dir.glob("תיבה_*.exe"))
        if exe_boxes:
            try:
                import zipfile
                from app.services.clal_mev import parse_clal_mev, product_for_box
                from app.services.portal_automation.aggregate import (
                    build_unified_workbook_bytes,
                )
                mev_rows: list = []
                for exe in exe_boxes:
                    prod, ptype = product_for_box(exe.name)
                    try:
                        with zipfile.ZipFile(exe) as z:
                            for zi in z.infolist():
                                if zi.filename.upper().endswith(".MEV") and zi.file_size > 100:
                                    mev_rows.extend(parse_clal_mev(z.read(zi.filename), prod, ptype))
                    except Exception as e:
                        logger.warning("clal: MEV parse failed for %s: %s", exe.name, e)
                seen: set = set()
                uniq: list = []
                for row in mev_rows:
                    k = (row["id_number"], row["product"])
                    if k not in seen:
                        seen.add(k)
                        uniq.append(row)
                if uniq:
                    out = download_dir / "כלל - פרודוקציה.xlsx"
                    out.write_bytes(build_unified_workbook_bytes(uniq))
                    # Replace the raw per-box .DAT files with the merged MEV file.
                    saved = [f for f in saved if f.suffix.lower() != ".dat"] + [out]
                    logger.info("clal: %d clients from %d boxes (.MEV)", len(uniq), len(exe_boxes))
                    _worker_note(f"clal production: {len(uniq)} clients from {len(exe_boxes)} boxes (.MEV)")
            except Exception as e:
                logger.warning("clal: MEV merge failed (keeping raw boxes): %s", e)

        results: list[Path] = list(saved)
        if not saved:
            logger.warning("Clal: no production files downloaded; continuing to נפרעים")
            self.partial_errors.append("פרודוקציה: לא ירדו קבצים")

        # ── Also grab נפרעים from the SAME APM session (one Clal login) ──
        # clal_nifraim opens the commissions tab via the "לפירוט עמלות" link on
        # the SPA home, so return there first. Best-effort — production still
        # returned if this fails.
        try:
            from app.services.portal_automation.companies.clal_nifraim import (
                ClalNifraimPortal,
            )
            try:
                await page.goto(clal_home_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
            except Exception:
                pass
            nif_files = await ClalNifraimPortal().download_reports(
                page, download_dir, username=username
            )
            results.extend(nif_files or [])
            logger.info("Clal: also downloaded נפרעים → %s", [p.name for p in (nif_files or [])])
        except Exception as e:
            logger.warning("Clal: נפרעים grab failed (production still returned): %s", e)
            # Folded leg — without this the batch merges a נפרעים file with no
            # כלל rows while the clal run shows success.
            self.partial_errors.append(f"נפרעים: {str(e)[:120]}")

        if not results:
            hint = (SCREENSHOT_ROOT / f"{run_id}_paylink.txt").name
            # Surface the per-leg causes — the generic text alone hid WHY each
            # leg came back empty (batch 3c0b055f: undiagnosable from the run row).
            legs = " | ".join(self.partial_errors[-4:]) if self.partial_errors else ""
            raise RuntimeError(
                f"Clal: לא ירדו קבצים (פרודוקציה+נפרעים)"
                + (f" — {legs}" if legs else "")
                + f". בדוק/י {hint}, {run_id}_grid_rows.txt ו-{run_id}_A_commissions_*.txt."
            )
        return results
