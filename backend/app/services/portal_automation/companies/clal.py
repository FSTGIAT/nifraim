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
    if head[:2] == b"PK":                      # zip container (also .xlsx/.docx)
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
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)

        # Step 2: the landing page shows an entry link before the APM form
        # ("<span class='LoginText'> לכניסה לאתר <a>לחץ/י כאן</a></span>").
        # Best-effort — harmless if the credentials form is already rendered.
        await self._click_first_visible(
            page,
            [
                "span.LoginText a",
                "a:has-text('לחץ')",
                "a:has-text('לכניסה')",
            ],
            timeout=6000,
        )

        # Step 3: standard F5 APM username + password form (sits directly on the
        # clalnet landing page: input#input_1 / input#input_2, button "כניסה").
        await apm_login_submit(page, username, password)

        # Steps 4+5: after submit the POST resolves to one of two screens —
        #   (a) the password-change branch: a redirect to
        #       …/ClalnetForgotPsw/ClalnetForgotPassword.html (we can't reset it), or
        #   (b) the OTP-entry screen.
        # Poll for whichever appears first. NOTE: only a real URL redirect marks
        # the reset page — the login page itself carries a "שכחתי סיסמה" link to
        # ForgotPassword.html, so a body-substring check would false-positive.
        for _ in range(24):  # ~12s
            if self._is_password_change_url(page.url):
                raise RuntimeError(
                    "כלל מבקשת לעדכן סיסמה. החליפ/י סיסמה באתר כלל "
                    "(clalnet.co.il) ואז עדכנ/י את הסיסמה השמורה כאן כדי שהאוטומציה "
                    "תוכל להתחבר."
                )
            if await self._has_credentials_error(page):
                raise RuntimeError(
                    "כלל דחתה את שם המשתמש/הסיסמה (\"שם המשתמש או הסיסמא שגויים\"). "
                    "ייתכן שהסיסמה פגה/הוחלפה — התחבר/י ידנית לאתר כלל, אפס/עדכן/י "
                    "סיסמה, ואז עדכנ/י את פרטי ההתחברות השמורים כאן."
                )
            try:
                el = await page.query_selector(self.OTP_FIELD)
                if el and await el.is_visible():
                    return
            except Exception:
                pass
            await page.wait_for_timeout(500)

        # Neither appeared — wait once more so the failure carries a clear
        # "OTP field never showed" diagnostic (runner dumps page state).
        if self._is_password_change_url(page.url):
            raise RuntimeError(
                "כלל מבקשת לעדכן סיסמה. החליפ/י סיסמה באתר כלל ואז עדכנ/י את "
                "הסיסמה השמורה כאן כדי שהאוטומציה תוכל להתחבר."
            )
        await self._wait_visible(page, self.OTP_FIELD, timeout=10000)

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
        await page.wait_for_load_state("networkidle", timeout=20000)

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        self.report_password = None

        from app.services.portal_automation.runner import SCREENSHOT_ROOT, logger

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
                    if is_file:
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

        # Step 7: open "infobay" — Clal's reports system that hosts the PayLink
        # grid (ctl00_MainContent_grdList, with report-type rows like "תשלומים
        # במערכת פיילינק" and "בריאות"). It's an ASP.NET WebForms app reached from
        # the open-icon side menu, and opens in a new tab.
        infobay_candidates = [
            "a:has-text('infobay')",
            "div.text:has-text('infobay')",
            "*:has-text('infobay')",
        ]
        try:
            async with page.context.expect_page(timeout=8000) as popup_info:
                await self._click_first_visible(page, infobay_candidates, timeout=8000)
            popup = await popup_info.value
            await popup.wait_for_load_state("domcontentloaded", timeout=20000)
            page = popup  # swap active handle to the infobay/PayLink tab
            _attach_response_listener(page)
            logger.info("Clal: infobay opened in popup %s", page.url)
        except Exception:
            # No popup — infobay may have loaded in the same tab (or the click
            # missed; the dumps below will show which).
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
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

            # Migdal-style fallback: if no download/popup yielded a file, take any
            # bytes the response listener captured during this report.
            if got is None and len(xhr_captures) > xhr_before:
                cap = xhr_captures[-1]
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
            hint = (SCREENSHOT_ROOT / f"{run_id}_paylink.txt").name
            raise RuntimeError(
                f"לא נמצאו מגירות פרודוקציה ב-{page.url}. "
                f"בדוק/י את {hint} ואת {run_id}_grid_rows.txt לרשימת השורות."
            )

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

            # 2. Download each report by double-clicking its row (ShowReport).
            n_reports = await page.evaluate(
                """(sel) => {
                    const g = document.querySelector("table[id*='grdList']");
                    return g ? g.querySelectorAll(sel.replace(/table\\[id\\*='grdList'\\] /g,'')).length : 0;
                }""",
                ROW_SELECTOR,
            )
            for ri in range(n_reports or 0):
                row = page.locator(ROW_SELECTOR).nth(ri)
                # Select first (highlights + sets the hidden fields), then grab.
                try:
                    await row.click(timeout=5000)
                    await page.wait_for_timeout(300)
                except Exception:
                    pass
                got = await _grab_report(
                    page,
                    row,
                    f"כלל - פרודוקציה {label} {ri}",
                    dump_stem=f"{run_id}_view_{label}" if ri == 0 else None,
                )
                await _dismiss_dialog(page)
                if got:
                    saved.append(got)

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
            raise RuntimeError(
                f"Clal: לא ירדו קבצים (פרודוקציה+נפרעים). בדוק/י {hint}, "
                f"{run_id}_grid_rows.txt ו-{run_id}_A_commissions_*.txt."
            )
        return results
