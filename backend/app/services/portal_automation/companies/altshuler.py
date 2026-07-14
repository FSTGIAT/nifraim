"""אלטשולר שחם (Altshuler Shaham) agent portal — login, OTP, commission download.

Login (https://agents.as-invest.co.il/Login) is an Angular SPA with a
**segmented single-char input** form (NOT F5 APM, NOT a plain user/pass):

  * a toggle  רישיון | ח.פ  (default = רישיון, the one we use)
  * "מספר רישיון"  — `L-` mark + **8** `<input type=tel maxlength=1>` boxes
  * "מספר תעודת זהות" — **9** `<input type=tel maxlength=1>` boxes
  * "שלחו לי קוד זיהוי" submit → SMS OTP to the agent's registered phone

Credential convention:  ``username = "<license>"`` , ``password = "<id>"``.
Both are zero-padded LEFT to the box count (license→8, id→9), matching the
agent's own padding habit (ת"ז 40336281 → 040336281, license 125514 → 00125514).
There is an invisible reCAPTCHA on the page; real-Chrome fingerprint passes it.

After OTP: top nav → עמלות → "פירוט עמלות סוכנים לפי קופה" → download to Excel.
The file is the existing ``altshuler`` parser format (company_source=אלטשולר,
commission/נפרעים) — no parser changes needed.

Selectors for the post-login menu + export are refined from
``<run_id>_post_otp.txt`` / ``_nav_*.txt`` after the first live run.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from playwright.async_api import Page

PORTAL_URL = "https://agents.as-invest.co.il/Login"


class AltshulerPortal(BasePortalAutomation):
    portal_kind = "altshuler"
    company_label = "אלטשולר"
    # Keep out of the run-all batch until live-verified.
    include_in_batch = True

    # ---- helpers -----------------------------------------------------------

    async def _fill_segmented(self, page: "Page", boxes, value: str) -> None:
        """Type ``value`` into a group of single-char boxes, one digit per box.

        Doesn't rely on the component's auto-advance — clicks each box and types
        its own digit (``onfocusin=this.select()`` clears any stale char first).
        """
        n = await boxes.count()
        for i in range(min(n, len(value))):
            box = boxes.nth(i)
            await box.click()
            await box.fill("")
            await page.keyboard.type(value[i], delay=60)

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        land = SCREENSHOT_ROOT / "altshuler_login.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # Two segmented groups, DOM order: [0]=license (L- mark), [1]=ת"ז.
        containers = page.locator(".login-new-input-container")
        try:
            await containers.first.wait_for(state="visible", timeout=15000)
        except Exception:
            raise RuntimeError(
                "אלטשולר: טופס ההתחברות לא נטען (login-new-input-container חסר) — "
                "בדוק altshuler_login.txt"
            )
        if await containers.count() < 2:
            raise RuntimeError(
                "אלטשולר: צפויים 2 שדות (רישיון + ת\"ז), נמצאו פחות — בדוק altshuler_login.txt"
            )

        license_boxes = containers.nth(0).locator("input[type='tel']")
        id_boxes = containers.nth(1).locator("input[type='tel']")
        n_lic = await license_boxes.count()
        n_id = await id_boxes.count()

        lic = re.sub(r"\D", "", username or "").zfill(n_lic)[-n_lic:]
        idn = re.sub(r"\D", "", password or "").zfill(n_id)[-n_id:]
        logger.info(
            "אלטשולר login: %d license boxes, %d id boxes; typing license=%s id=%s",
            n_lic, n_id, lic, idn,
        )

        await self._fill_segmented(page, license_boxes, lic)
        await self._fill_segmented(page, id_boxes, idn)
        await page.wait_for_timeout(300)

        # Submit "שלחו לי קוד זיהוי".
        clicked = await self._click_first_visible(page, [
            "button:has-text('שלחו לי קוד זיהוי')",
            "button.login-new-button-component",
            "button[type='submit']:not(.CloseTabButton)",
        ], timeout=8000)
        if not clicked:
            raise RuntimeError("אלטשולר: כפתור 'שלחו לי קוד זיהוי' לא נמצא")

        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # The login screen shows 17 segmented boxes (8 license + 9 id). The OTP
        # screen replaces them with a SHORT segmented group (~4-6 boxes). Wait for
        # that transition (or an error toast) so we fail fast on bad creds.
        deadline = 35
        for _ in range(deadline * 2):
            try:
                vis = await page.evaluate(
                    """() => [...document.querySelectorAll("input[type='tel'][maxlength='1']")]
                        .filter(e => { const r = e.getBoundingClientRect(); return r.width>0 && r.height>0; })
                        .length"""
                )
            except Exception:
                vis = 0
            # Error toast (wrong license/id / rate limit)
            try:
                err = await page.evaluate(
                    """() => {
                        const t = [...document.querySelectorAll('.error, .toast, .alert, [class*=error], [class*=Error]')]
                            .map(e => (e.innerText||'').trim()).filter(Boolean);
                        return t.join(' | ').slice(0, 300);
                    }"""
                )
            except Exception:
                err = ""
            if 0 < vis < 17:
                post = SCREENSHOT_ROOT / "altshuler_otp_screen.png"
                await self._safe_screenshot(page, post)
                await self._dump_page_state(page, post)
                return
            if err and ("שגוי" in err or "שגיא" in err or "לא נמצא" in err or "נסה" in err):
                raise RuntimeError(f"אלטשולר: הכניסה נדחתה — {err}")
            await page.wait_for_timeout(500)

        # Didn't clearly transition — dump and let the runner await OTP anyway;
        # submit_otp re-detects the boxes.
        post = SCREENSHOT_ROOT / "altshuler_after_send.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")

        # The OTP segmented boxes (visible single-char tel inputs, fewer than the
        # 17 on the login screen). Type one digit per box.
        boxes = page.locator("input[type='tel'][maxlength='1']:visible")
        filled = False
        try:
            n = await boxes.count()
            if 0 < n <= len(digits) + 2:
                await self._fill_segmented(page, boxes, digits[:n])
                filled = True
        except Exception:
            pass
        if not filled:
            # Fallback: a single OTP field.
            for sel in ("input[name='otp']", "input[autocomplete='one-time-code']",
                        "input[name='code']"):
                try:
                    await page.fill(sel, digits, timeout=2000)
                    filled = True
                    break
                except Exception:
                    continue

        await page.wait_for_timeout(400)
        # Confirm — the form may auto-submit when the last digit lands, but click
        # any explicit confirm button to be safe.
        await self._click_first_visible(page, [
            "button:has-text('אישור')",
            "button:has-text('כניסה')",
            "button:has-text('המשך')",
            "button:has-text('התחבר')",
            "button.login-new-button-component",
            "button[type='submit']:not(.CloseTabButton)",
        ], timeout=6000)

        # Success = the SPA navigates off /Login to the dashboard ("/"). A WRONG
        # or EXPIRED code leaves us on /Login (it resets to the license/ID form).
        left_login = False
        try:
            await page.wait_for_url(
                lambda u: "/login" not in (u or "").lower(), timeout=25000
            )
            left_login = True
        except Exception:
            left_login = "/login" not in (page.url or "").lower()
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "altshuler_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("אלטשולר: לא נמצא שדה OTP — בדוק altshuler_otp_screen.txt")
        if not left_login:
            raise RuntimeError(
                "אלטשולר: קוד ה-OTP נדחה — נשארנו במסך ההתחברות (/Login). "
                "ייתכן שהקוד פג תוקף או שנצרך קוד ישן. נסו שוב עם קוד טרי."
            )

    HOME_URL = "https://agents.as-invest.co.il/"
    # The עמלות top-nav trigger: a role=button div whose title ends with "עמלות".
    AMLOT_TRIGGER = "div.nav-item.has-submenu[title*='עמלות']"
    # Hebrew month names, newest-first within a year — the נפרעים report's month
    # picker has no useful default (lands on an empty month), so we probe from the
    # likely-latest backwards until a month with data renders a download link.
    _HE_MONTHS_DESC = [
        "דצמבר", "נובמבר", "אוקטובר", "ספטמבר", "אוגוסט", "יולי",
        "יוני", "מאי", "אפריל", "מרץ", "פברואר", "ינואר",
    ]

    async def _open_amlot_menu(self, page: "Page") -> None:
        """Open the עמלות mega-menu (ul.nav-item-menu loses its 'hide' class)."""
        trigger = page.locator(self.AMLOT_TRIGGER).first
        await trigger.wait_for(state="visible", timeout=12000)
        # role=button div — a click toggles aria-expanded. Hover as a fallback for
        # hover-driven menus.
        for attempt in range(3):
            try:
                if attempt == 1:
                    await trigger.hover()
                else:
                    await trigger.click()
            except Exception:
                pass
            try:
                await page.wait_for_selector(
                    f"{self.AMLOT_TRIGGER}[aria-expanded='true'], "
                    "ul.nav-item-menu:not(.hide) a[aria-label*='עמלות']",
                    state="visible", timeout=2500,
                )
                return
            except Exception:
                continue

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        otp_provider=None,
    ) -> list[Path]:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        self.report_password = None
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        async def ck(tag: str):
            p = SCREENSHOT_ROOT / f"{run_id}_{tag}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        await ck("nav_0_home")

        saved: list[Path] = []
        errors: list[str] = []

        # Report 1 — עמלות נפרעים-גמל → mat-tab "פירוט עמלות סוכנים לפי קופה"
        # (the operator's primary נפרעים report; matches the `altshuler` parser).
        try:
            f = await self._dl_nifraim_kupa(page, download_dir / "אלטשולר נפרעים גמל.xlsx", ck)
            saved.append(f)
        except Exception as e:
            await ck("rep0_ERR")
            errors.append(f"נפרעים גמל: {e}")
            logger.warning("אלטשולר נפרעים-גמל failed: %s", e)

        # Report 2 — ריכוז עמלות לפי מוצרים (הנמקה).
        try:
            f = await self._dl_products(page, download_dir / "אלטשולר עמלות לפי מוצרים.xlsx", ck)
            saved.append(f)
        except Exception as e:
            await ck("rep1_ERR")
            errors.append(f"לפי מוצרים: {e}")
            logger.warning("אלטשולר לפי-מוצרים failed: %s", e)

        if not saved:
            raise RuntimeError(
                "אלטשולר: לא ירד אף דוח. " + " | ".join(errors)
                + f" — בדוק {run_id}_rep*_*.txt"
            )
        if errors:
            logger.warning("אלטשולר: חלק מהדוחות נכשלו: %s", " | ".join(errors))
            # Surface on the run/batch — the נפרעים-גמל leg is the only altshuler
            # file with a parser, so losing it means zero altshuler rows in the
            # merged נפרעים while the run still shows success.
            self.partial_errors.extend(f"דוח {e}" for e in errors)
        return saved

    async def _nav_amlot_link(self, page: "Page", aria: str) -> None:
        """From home, open the עמלות mega-menu and click a report link by aria."""
        await page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(800)
        await self._open_amlot_menu(page)
        link = page.locator(f"a[aria-label='{aria}']").first
        await link.wait_for(state="visible", timeout=8000)
        await link.click()
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

    async def _dl_nifraim_kupa(self, page: "Page", target: Path, ck) -> Path:
        """עמלות → עמלות נפרעים-גמל → mat-tab 'פירוט עמלות סוכנים לפי קופה' →
        pick the newest month that has data → הצג → download "להורדת הדו"ח".
        """
        await self._nav_amlot_link(page, "קישור לעמוד עמלות נפרעים - גמל")
        await ck("rep0_1_report")

        # Switch to the "פירוט עמלות סוכנים לפי קופה" sub-tab (a mat-tab
        # `div[role=tab]`, id mat-tab-group-3-label-2). EXACT match — there is
        # also "...סוכנים מקושרים לפי קופה" whose name is NOT a superset but is
        # close. LIVE-DIAGNOSED (run a8a0ed28): a plain Playwright .click() on the
        # tab silently no-ops (the mdc-tab ripple overlay swallows the pointer),
        # so we VERIFY the switch via the <h1> heading and retry with a JS click.
        TAB = "פירוט עמלות סוכנים לפי קופה"
        switched = await self._click_tab_verified(page, TAB)
        await ck("rep0_2_tab")
        if not switched:
            raise RuntimeError(
                f"אלטשולר: מעבר ללשונית '{TAB}' נכשל (הכותרת לא השתנתה) — "
                "בדוק rep0_2_tab.txt"
            )

        # The filter has two mat-selects: [0]=חודש (month, Hebrew name),
        # [1]=שנה (year). SCOPE TO :visible — each sub-tab has its OWN
        # app-commissions-filter and the inactive ones stay in the DOM, so an
        # unscoped locator would drive the hidden default tab's filter.
        selects = page.locator("app-commissions-filter mat-select:visible")
        try:
            await selects.first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass

        # Probe newest-first. EARLIER BUG (live-diagnosed 2026-06-29 from run
        # 2551f87d dumps): only the MONTH was set — the YEAR select kept its
        # default, and the loop waited solely for "להורדת הדו". The report page
        # was correct (tab + 86 mat-selects + the הצג present-btn all present in
        # the HTML) but the grid never populated for the default year, so the
        # download link never appeared and rep0 always fell through to no-data.
        # Fix: drive BOTH selects (year newest-first too), and treat the report
        # as ready when the DATA GRID populates OR a download affordance shows —
        # not only the exact "להורדת הדו" text. Dump the post-הצג state so the
        # real export control is captured even if this still misses.
        import datetime
        today = datetime.date.today()
        cur = today.month  # 1..12
        has_year = False
        try:
            has_year = (await selects.count()) >= 2
        except Exception:
            pass

        async def _show_and_check(label: str) -> Path | None:
            """Click הצג, wait for data, dump, and download if ready."""
            show = page.locator(
                "button.present-btn:visible, button[aria-label*='להציג']:visible, "
                "button.btn-green:has-text('הצג'):visible"
            ).first
            try:
                if await show.count() and await show.is_visible():
                    await show.click()
                else:
                    await show.click(force=True)
            except Exception:
                pass
            if await self._wait_report_ready(page):
                logger.warning("אלטשולר נפרעים-גמל: נתונים ל-%s", label)
                await ck(f"rep0_3_show_{label}")
                return await self._click_download_link(page, target, ck, "rep0")
            return None

        # PRIMARY (matches the operator): pick the LAST option in the שנה select,
        # then the LAST option in the חודש select — the dropdowns only list
        # reported periods, so the last entry is the latest one WITH data. This
        # replaces the old hardcoded month-name probe that landed on an empty
        # current month (run b792546f: May-2026 empty → false-ready → no export).
        try:
            ylabel = "?"
            if has_year:
                ylabel = await self._select_mat_last(page, selects.nth(1))
            mlabel = await self._select_mat_last(page, selects.nth(0))
            got = await _show_and_check(f"last_{ylabel}_{mlabel}")
            if got:
                return got
            await ck("rep0_3_last_no_data")
        except Exception as e:
            logger.warning("אלטשולר: בחירת חודש/שנה אחרונים נכשלה: %s", e)

        # FALLBACK: newest-first probe (kept in case the dropdowns aren't ordered
        # latest-last or the latest period has no data for this agent).
        probe_cur = [m for m in self._HE_MONTHS_DESC
                     if (12 - self._HE_MONTHS_DESC.index(m)) <= cur]
        year_plan = [(today.year, probe_cur), (today.year - 1, self._HE_MONTHS_DESC)]

        for year, months in year_plan:
            if has_year:
                try:
                    await self._select_mat_option(page, selects.nth(1), str(year))
                except Exception as e:
                    logger.info("אלטשולר: בחירת שנה %s נכשלה: %s", year, e)
            for month in months:
                try:
                    await self._select_mat_option(page, selects.nth(0), month)
                except Exception as e:
                    logger.info("אלטשולר: בחירת חודש %s נכשלה: %s", month, e)
                    continue
                got = await _show_and_check(f"{year}_{month}")
                if got:
                    return got

        await ck("rep0_3_no_data")
        raise RuntimeError(
            "לא נמצאו נתונים באף חודש/שנה (בדוק שטעינת 'הצג' עבדה ושיש תקופות זמינות) "
            "— בדוק rep0_3_show_*.txt / rep0_3_no_data.txt"
        )

    async def _wait_report_ready(self, page: "Page", timeout_ms: int = 9000) -> bool:
        """After clicking הצג, return True once the report renders a downloadable
        result — the "להורדת הדו"ח" link, ANY excel/export affordance, OR a
        populated data grid (mat-rows). Returns False (keep probing the next
        period) when an explicit empty-state shows or nothing appears in time.

        STRICTNESS (fixed 2026-06-29, run 375e51cc): the old check matched a
        download affordance by `class*=excel`/`src` too — which false-positived on
        an EMPTY month (some hidden template/icon matched), so the probe stopped at
        an empty 2026 month and never reached 2025 where the agent's data actually
        is (the products report is titled "...לשנת 2025"). Now we require a REAL
        populated grid (visible rows carrying cell text) OR a genuine TEXT download
        link ("להורדת הדו"/"ייצוא לאקסל") — not a class/src guess — so empty months
        correctly return False and the probe walks back into 2025."""
        import asyncio
        ready_js = r"""() => {
            const vis = el => { const r = el.getBoundingClientRect();
                return r.width > 8 && r.height > 8; };
            // Real text download link only (no class/src guessing).
            const dl = [...document.querySelectorAll('a,button')]
                .find(e => vis(e) && /להורדת הדו|הורדת הדו|ייצוא לאקסל|ייצוא לאקס/
                    .test((e.innerText||'') + ' ' + (e.getAttribute('aria-label')||'')));
            // A populated grid: visible rows that actually carry cell text.
            const rows = [...document.querySelectorAll(
                'mat-row, cdk-row, tr.mat-mdc-row, .mat-mdc-row, tbody tr[role=row], '
                + 'table tbody tr, .ag-row, .k-grid tr')]
                .filter(r => vis(r) && (r.innerText||'').trim().length > 0);
            // The operator's "excel sign" — an export icon that appears WITH data
            // (img/svg/icon whose src/alt/aria/class names excel/xls/אקסל).
            const xl = [...document.querySelectorAll('img,svg,mat-icon,i,a,button,[class]')]
                .find(e => vis(e) && /excel|xls|אקסל|file_download|download/i.test(
                    (e.getAttribute('src')||'') + ' ' + (e.getAttribute('alt')||'') + ' '
                    + (e.getAttribute('aria-label')||'') + ' ' + (e.getAttribute('title')||'')
                    + ' ' + (e.className && e.className.baseVal!==undefined ? e.className.baseVal : (e.className||''))));
            const empty = [...document.querySelectorAll('*')].some(e => vis(e)
                && /אין נתונים|לא נמצאו נתונים|אין תוצאות|לא קיימים נתונים/.test(e.innerText||''));
            return {dl: !!dl, rows: rows.length, xl: !!xl, empty};
        }"""
        deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
        last = {"dl": False, "rows": 0, "xl": False, "empty": False}
        while asyncio.get_event_loop().time() < deadline:
            try:
                last = await page.evaluate(ready_js)
            except Exception:
                last = {"dl": False, "rows": 0, "xl": False, "empty": False}
            if last.get("dl") or last.get("xl") or last.get("rows", 0) > 0:
                logger.warning("אלטשולר: דוח מוכן (rows=%s dl=%s xl=%s)",
                               last.get("rows"), last.get("dl"), last.get("xl"))
                return True
            if last.get("empty"):
                return False
            await page.wait_for_timeout(600)
        logger.info("אלטשולר: דוח לא נטען בזמן (rows=%s dl=%s empty=%s)",
                    last.get("rows"), last.get("dl"), last.get("empty"))
        return False

    async def _click_tab_verified(self, page: "Page", tab_text: str) -> bool:
        """Click a mat-tab by EXACT visible text and verify the switch took.

        Angular Material's mdc-tab ripple overlay can swallow a normal
        Playwright click, so we confirm the active tab via aria-selected on the
        exact `div[role=tab]` whose trimmed text == tab_text (guards against the
        longer "...מקושרים לפי קופה" sibling) and retry with a JS dispatch."""
        async def heading_is_target() -> bool:
            try:
                return await page.evaluate(
                    """(t) => {
                        const el = [...document.querySelectorAll('div[role=tab]')]
                            .find(e => (e.innerText||'').trim() === t);
                        return !!el && (el.getAttribute('aria-selected') === 'true'
                            || el.classList.contains('mdc-tab--active'));
                    }""", tab_text)
            except Exception:
                return False

        tab = page.get_by_role("tab", name=tab_text, exact=True)
        for attempt in range(4):
            try:
                if attempt < 2:
                    await tab.click(timeout=5000, force=(attempt == 1))
                else:
                    # JS click the exact role=tab whose text matches.
                    await page.evaluate(
                        """(t) => {
                            const el = [...document.querySelectorAll('div[role=tab]')]
                                .find(e => (e.innerText||'').trim() === t);
                            if (el) el.click();
                        }""", tab_text)
            except Exception:
                pass
            for _ in range(8):  # ~4s for the tab body + heading to swap
                if await heading_is_target():
                    return True
                await page.wait_for_timeout(500)
        return await heading_is_target()

    async def _dl_products(self, page: "Page", target: Path, ck) -> Path:
        """עמלות → ריכוז עמלות לפי מוצרים (הנמקה). The download link
        ("להורדת הדו"ח") is present immediately — no filter/הצג."""
        await self._nav_amlot_link(page, "קישור לעמוד פירוט עמלות לפי מוצרים")
        await ck("rep1_1_report")
        link = page.locator("text=להורדת הדו").first
        for _ in range(10):
            try:
                if await link.is_visible():
                    break
            except Exception:
                pass
            await page.wait_for_timeout(800)
        return await self._click_download_link(page, target, ck, "rep1")

    async def _select_mat_last(self, page: "Page", select_locator) -> str:
        """Open a <mat-select> and pick the LAST option (the operator picks 'the
        last month and year' — the dropdowns only list available/reported periods,
        so the last entry is the latest one with data). Returns the chosen text."""
        await select_locator.click()
        await page.wait_for_timeout(400)
        opts = page.locator("mat-option:visible, [role='option']:visible")
        try:
            await opts.last.wait_for(state="visible", timeout=4000)
        except Exception:
            pass
        n = await opts.count()
        if not n:
            raise RuntimeError("no mat-options rendered")
        last = opts.nth(n - 1)
        text = (await last.inner_text()).strip()
        await last.click()
        await page.wait_for_timeout(500)
        return text

    async def _select_mat_option(self, page: "Page", select_locator, option_text: str) -> None:
        """Open an Angular Material <mat-select> and pick an option by exact text."""
        await select_locator.click()
        await page.wait_for_timeout(400)
        opt = page.get_by_role("option", name=option_text, exact=True)
        try:
            await opt.first.wait_for(state="visible", timeout=4000)
            await opt.first.click()
        except Exception:
            # Fallback: mat-option text node.
            await page.locator(
                f"mat-option:has(span.mdc-list-item__primary-text:text-is('{option_text}'))"
            ).first.click(timeout=4000)
        await page.wait_for_timeout(500)

    async def _click_download_link(self, page: "Page", target: Path, ck, tag: str) -> Path:
        """Click the "להורדת הדו"ח" trigger and save the file (native or XHR)."""
        import asyncio
        await ck(f"{tag}_pre_download")
        xhr = {"bytes": None}

        async def on_resp(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                if any(x in (ct + cd + url) for x in (
                    "spreadsheet", "vnd.ms-excel", ".xlsx", ".xls", "excel", "octet-stream",
                )) and xhr["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr["bytes"] = body
            except Exception:
                pass
        page.on("response", on_resp)

        candidates = [
            "text=להורדת הדו",
            "[aria-label*='להורדת']",
            "text=הורדת הדו",
            "button:has-text('ייצוא לאקסל')",
            "a:has-text('אקסל')",
            # נפרעים-גמל may expose the export as an icon / toolbar button rather
            # than the "להורדת הדו"ח" text link the products report uses.
            "[aria-label*='ייצוא']",
            "[aria-label*='אקסל']",
            "[aria-label*='Excel' i]",
            "button:has-text('ייצוא')",
            "img[src*='excel' i]",
            "img[src*='xls' i]",
            "img[alt*='excel' i]",
            "img[alt*='אקסל']",
            "[title*='אקסל']",
            "[title*='Excel' i]",
            "svg[class*='excel' i]",
            "[class*='excel' i]",
            "[class*='xls' i]",
            "a:has(img[src*='excel' i])",
            "button:has(img[src*='excel' i])",
            "mat-icon:has-text('file_download')",
            "a[href$='.xlsx']",
            "a[href$='.xls']",
        ]
        try:
            async with page.expect_download(timeout=30000) as dl:
                clicked = await self._click_first_visible(page, candidates, timeout=10000)
                if not clicked:
                    # Last resort: JS-click the first excel-ish element (the icon
                    # may be an <img>/<svg> Playwright won't treat as "visible").
                    clicked = await page.evaluate(
                        r"""() => {
                            const vis = el => { const r = el.getBoundingClientRect();
                                return r.width > 4 && r.height > 4; };
                            const el = [...document.querySelectorAll('img,svg,a,button,mat-icon,i,[class]')]
                                .find(e => vis(e) && /excel|xls|אקסל|file_download/i.test(
                                    (e.getAttribute('src')||'')+' '+(e.getAttribute('alt')||'')+' '
                                    +(e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '
                                    +(e.className && e.className.baseVal!==undefined ? e.className.baseVal : (e.className||''))));
                            if (el) { (el.closest('a,button') || el).click(); return true; }
                            return false;
                        }"""
                    )
                if not clicked:
                    raise RuntimeError("no-download-trigger")
            d = await dl.value
            await d.save_as(str(target))
            page.remove_listener("response", on_resp)
            return target
        except Exception as native_err:
            for _ in range(20):
                if xhr["bytes"]:
                    break
                await asyncio.sleep(0.5)
            page.remove_listener("response", on_resp)
            if xhr["bytes"]:
                target.write_bytes(xhr["bytes"])
                return target
            await ck(f"{tag}_no_download")
            raise RuntimeError(f"no download at {page.url}: {native_err}")
