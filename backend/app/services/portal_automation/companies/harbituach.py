"""הר הביטוח (harb.cma.gov.il, משרד האוצר) — a customer's insurance portfolio, ON DEMAND.

Not an insurer and not part of the monthly cycle: Nifra Agent proposes a fetch, the agent's click
queues a HarbRequest (services/policies/harb_jobs), and this plugin — on the agent's local worker
(Israeli IP) — logs in ONCE and drains every pending request of the user:

  harb.cma.gov.il → "כניסת מורשים" (a[href*=MoreInsurance])
    → login.gov.il  (usernamePasswordSMSOtp): #userId (9 digits) + #userPass → #loginSubmit
    → SMS OTP (hands-free via phone-forward, runner._wait_for_otp)
  per customer:
    "תיק ביטוחים על שם מבוטח בגיר" → #txtId + Kendo day/month/year (birth, ID issue)
    → #cbAproveTerm → "צפיה בתיק הביטוחי" → "כל הביטוחים" → .butExcelGeneral (Excel)
    → each policy row's detail view (text) → "כניסה לתיק נוסף" for the next customer.

The runner passes `harb_next()` / `harb_done(...)` (runner.py, kind harbituach): each customer is
ingested the moment it is fetched, and one customer's failure (wrong dates → not_found) never
fails the others. Recon dumps (<run>_harb_*.png/html/txt) are written at every step.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

HOME = "https://harb.cma.gov.il/"
HE_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]

# Visible text that means "the customer details didn't match" on the search form.
NOT_FOUND_HINTS = ("לא נמצא", "לא נמצאו", "אינם תואמים", "לא תואמים", "שגוי", "אינו תקין", "לא תקין", "לא קיים")


class HarbNotFound(RuntimeError):
    pass


class HarBituachPortal(BasePortalAutomation):
    portal_kind = "harbituach"
    company_label = "הר הביטוח"
    requires_otp = True
    include_in_batch = False          # on demand only — never the 21st cycle
    needs_residential_proxy = False   # runs on the agent's worker (Israeli IP)
    headed = True                     # gov WAF: plain clients get 403
    native_fingerprint = True
    use_persistent_profile = True
    browser_channel = "msedge"
    recycle_profile_on_login_failure = False
    run_timeout_s = 40 * 60           # one login may serve a queue of customers

    def __init__(self) -> None:
        super().__init__()
        self._run_tag = "harb"

    # ── helpers ──────────────────────────────────────────────────────────
    async def _dump(self, page: "Page", step: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        p = SCREENSHOT_ROOT / f"{self._run_tag}_harb_{step}.png"
        await self._safe_screenshot(page, p)
        await self._dump_page_state(page, p)

    async def _visible_text(self, page: "Page", selector: str) -> str:
        try:
            return await page.evaluate("""(sel) => [...document.querySelectorAll(sel)]
                .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
                .map(e => (e.innerText || '').trim()).filter(Boolean).join(' | ').slice(0, 600)""", selector)
        except Exception:
            return ""

    async def _text_visible(self, page: "Page", text: str) -> bool:
        """Visible, not merely present — portals keep hidden screens in the DOM."""
        loc = page.get_by_text(text, exact=False)
        try:
            for i in range(min(await loc.count(), 10)):
                if await loc.nth(i).is_visible():
                    return True
        except Exception:
            pass
        return False

    # login.gov.il: Playwright LOCATOR actions can hang there. After some loads the isolated world
    # that locators run in is gone, while the page's own JS still runs: click() stalls at "scrolling
    # into view", focus()/count() never return (kiko 2026-10-07; reproduced locally in real Edge).
    # So on the gov login + SMS screens we read the DOM with page.evaluate (main world) and act with
    # TRUSTED mouse/keyboard input — no locator, and still a real person's click to the bot sensor.
    _BOX_JS = """(sels) => { for (const s of sels) { for (const e of document.querySelectorAll(s)) {
        const r = e.getBoundingClientRect(), st = getComputedStyle(e);
        if (r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none')
            return {sel: s, x: r.x + r.width / 2, y: r.y + r.height / 2,
                    enabled: !e.disabled, value: ('value' in e) ? e.value : null}; } } return null; }"""

    async def _js_box(self, page: "Page", *sels: str) -> dict | None:
        """First VISIBLE element matching any of `sels` (CSS, main world): its centre, enabled, value."""
        try:
            return await asyncio.wait_for(page.evaluate(self._BOX_JS, list(sels)), 8)
        except Exception:
            return None

    async def _wait_responsive(self, page: "Page", max_s: int) -> None:
        """Until 3 probes in a row answer in <300ms — the page's own scripts have settled."""
        import time as _t
        t0, fast = _t.monotonic(), 0
        while _t.monotonic() - t0 < max_s and fast < 3:
            t = _t.monotonic()
            try:
                await asyncio.wait_for(page.evaluate("1"), 5)
                fast = fast + 1 if _t.monotonic() - t < 0.3 else 0
            except Exception:
                fast = 0
            await page.wait_for_timeout(500)
        logger.info("harb: page responsive after %.0fs", _t.monotonic() - t0)

    async def _human_dwell(self, page: "Page", seconds: int) -> None:
        import random
        t0 = asyncio.get_event_loop().time()
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        while asyncio.get_event_loop().time() - t0 < seconds:
            try:
                await page.mouse.move(random.randint(250, 900), random.randint(180, 600), steps=random.randint(8, 20))
                if random.random() < 0.25:
                    await page.mouse.wheel(0, random.choice((120, -120)))
            except Exception:
                pass
            await page.wait_for_timeout(random.randint(900, 2200))

    async def _reach_portal(self, page: "Page", timeout_s: int) -> bool:
        """True once the page is ON the portal host; clicks Cognito's GovID-prd button on the way."""
        from urllib.parse import urlparse
        portal_host = urlparse(HOME).hostname
        clicked_at = -99.0
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < timeout_s:
            host = urlparse(page.url).hostname or ""
            if host == portal_host:
                return True
            now = asyncio.get_event_loop().time()
            if "amazoncognito.com" in host and now - clicked_at > 20:
                if await self._js_click(page, "input[value='GovID-prd']", ".idpButton-customizable"):
                    logger.info("harb: Cognito sign-in page — clicked GovID-prd")
                    clicked_at = now
            await page.wait_for_timeout(1000)
        return False

    async def _js_wait(self, page: "Page", sel: str, timeout_ms: int) -> bool:
        for _ in range(max(1, timeout_ms // 500)):
            if await self._js_box(page, sel):
                return True
            await page.wait_for_timeout(500)
        return False

    async def _js_click(self, page: "Page", *sels: str) -> bool:
        box = await self._js_box(page, *sels)
        if not box:
            return False
        try:
            await page.bring_to_front()
        except Exception:
            pass
        await page.evaluate("(s) => document.querySelector(s)?.scrollIntoView({block: 'center'})", box["sel"])
        box = await self._js_box(page, box["sel"]) or box          # re-measure after the scroll
        await page.mouse.click(box["x"], box["y"])
        return True

    async def _js_type(self, page: "Page", sel: str, val: str, delay: int = 90) -> None:
        if not await self._js_click(page, sel):
            raise RuntimeError(f"הר הביטוח: השדה {sel} לא מוצג בדף הכניסה")
        await page.wait_for_timeout(200)
        await page.evaluate("(s) => { const e = document.querySelector(s); if (e) { e.focus(); e.select && e.select(); } }", sel)
        await page.keyboard.press("Backspace")
        await page.keyboard.type(val, delay=delay)
        got = await page.evaluate("(s) => document.querySelector(s)?.value ?? null", sel)
        if got != val:      # keystrokes lost → set it the way a framework-bound input still notices
            await page.evaluate("""([s, v]) => { const e = document.querySelector(s);
                const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                set.call(e, v); e.dispatchEvent(new Event('input', {bubbles: true}));
                e.dispatchEvent(new Event('change', {bubbles: true})); e.dispatchEvent(new Event('blur')); }""", [sel, val])

    async def _click_text(self, page: "Page", texts: list[str], timeout: int = 15000) -> bool:
        for t in texts:
            loc = page.get_by_text(t, exact=False).locator("visible=true").first
            try:
                await loc.wait_for(state="visible", timeout=timeout)
                await loc.click()
                return True
            except Exception:
                continue
        return False

    # ── login ────────────────────────────────────────────────────────────
    async def login(self, page: "Page", username: str, password: str) -> None:
        idn = "".join(c for c in username if c.isdigit()).zfill(9)
        await page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)
        link = page.locator("a[href*='MoreInsurance']").first
        try:
            await link.wait_for(state="attached", timeout=20000)
            await link.click()
        except Exception:
            await page.goto(HOME.rstrip("/") + "/sso/Auth/MoreInsurance", wait_until="domcontentloaded", timeout=60000)
        self.otp_not_needed = False
        await self._open_login_form(page)
        if self.otp_not_needed:
            return
        # login.gov.il's bot wall (Radware) sets its clearance cookie from JS on the first load, and
        # the login POST only carries it after a RELOAD — without one the submit is answered with
        # "Radware Page" and no SMS (live 2026-10-08, 4/4 incl. a fresh profile on the dev box), with
        # it the SMS came (2026-10-07). The reload once froze the page for minutes, but that was our
        # own un-timed waits; now: look around, reload, wait until the page answers fast, look again.
        await self._human_dwell(page, seconds=12)
        try:
            await page.reload(wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass
        if not await self._js_wait(page, "#userId", 60000):
            raise RuntimeError("הר הביטוח: דף הכניסה של login.gov.il לא נטען אחרי רענון")
        await self._wait_responsive(page, max_s=60)
        await self._human_dwell(page, seconds=10)
        await self._dump(page, "1_login")
        for sel, val in (("#userId", idn), ("#userPass", password)):
            await self._js_type(page, sel, val)
            await page.wait_for_timeout(350)
        for _ in range(24):                       # the button enables after client-side validation
            b = await self._js_box(page, "#loginSubmit")
            if b and b["enabled"]:
                break
            await page.wait_for_timeout(250)
        await page.wait_for_timeout(600)
        # Record the login request's REAL reply (the SMS send is an XHR POST to the same nidp URL):
        # a silent "nothing happened" then says whether the server refused it, and with which code.
        replies: list[str] = []

        async def _on_response(resp):
            try:
                if resp.request.method == "POST" and "nidp" in resp.url:
                    body = await resp.text()
                    replies.append(f"{resp.status} {resp.url.split('?')[0]} {body}")
            except Exception:
                pass
        page.on("response", lambda r: asyncio.ensure_future(_on_response(r)))
        if not await self._js_click(page, "#loginSubmit"):
            await self._js_click(page, "#userPass")   # no visible button → a trusted Enter submits the form
            await page.keyboard.press("Enter")
        # → the SMS-code screen (or a visible error, which runner._wait_for_otp also watches). A COLD
        # profile is scored as a bot: login.gov.il then sends NO code and shows NO error — the page just
        # sits on the login form (measured 2026-10-07, same as Mor/Meitav). Tell the agent that plainly.
        t0 = asyncio.get_event_loop().time()
        nudged = False
        while asyncio.get_event_loop().time() - t0 < 60:   # the SMS send is an XHR that can lag
            await page.wait_for_timeout(750)
            if await self._otp_input(page):
                await self._dump(page, "2_otp")
                return
            err = await self._visible_text(page, "[role=alert], .error, .alert, [class*=error], [class*=Error], .small")
            if err and any(w in err for w in ("שגוי", "לא תקין", "נחסם", "אינם תואמים", "לא נמצא", "חסום")):
                await self._dump(page, "2_login_error")
                raise RuntimeError(f"הר הביטוח: הכניסה נדחתה — {err[:200]}")
            if not nudged and asyncio.get_event_loop().time() - t0 > 30:   # halfway: nudge the sensor
                nudged = True
                await page.mouse.move(400, 300)
                await page.mouse.move(600, 420)
        await self._dump(page, "2_no_otp_screen")
        try:
            from app.services.portal_automation.runner import SCREENSHOT_ROOT
            (SCREENSHOT_ROOT / f"{self._run_tag}_harb_2_login_replies.txt").write_text(
                "\n".join(replies) or "NO POST to nidp after the click (the page never sent the login)", "utf-8")
        except Exception:
            pass
        # The worker's dumps never leave the agent's PC, so the ERROR itself must say what the page
        # showed: the reply's <title> + any error/alert text in it, and the page's visible messages.
        def _reply_summary(r: str) -> str:
            title = re.search(r"<title[^>]*>(.*?)</title>", r, re.S | re.I)
            errs = re.findall(r'class="[^"]*(?:error|alert|invalid|warning)[^"]*"[^>]*>\s*([^<]{3,160})', r, re.I)
            return " · ".join(x for x in [r[:3], (title.group(1).strip() if title else ""), *[e.strip() for e in errs[:3]]] if x)
        server = (f"{len(replies)} POST; " + _reply_summary(replies[-1])) if replies else "לא נשלחה בקשת כניסה מהדף"
        shown = await self._visible_text(page, "[role=alert], .error, .alert, [class*=error], [class*=Error], .small, h1, h2")
        # still on the login form, no code, no error → the browser check didn't pass
        if await self._js_box(page, "#userPass"):
            raise RuntimeError("הר הביטוח: הזיהוי הלאומי (login.gov.il) לא שלח קוד — "
                               f"תשובת השרת: {server[:300]} | בדף: {shown[:300]}")
        raise RuntimeError("הר הביטוח: מסך קוד ה-SMS לא הופיע אחרי הכניסה")

    async def _open_login_form(self, page: "Page") -> None:
        """Wait (by the clock) for login.gov.il's form. No warm-up dwell, no reloads: the reload made
        the page unresponsive for minutes (live 2026-10-07: 5+ min before typing, the Cognito state
        then expired → 400), and a person just waits for the form to appear. Cognito's own
        "GovID-prd" chooser, if it shows up first, gets clicked like a person would."""
        from urllib.parse import urlparse
        t0 = asyncio.get_event_loop().time()
        reloads = 0
        # A FRESH profile sits on Radware's lock loader for minutes before the form renders
        # (live 2026-10-08: 90s was too short on kiko's recycled profile; the dev box got through
        # after a few minutes). So: up to 4 minutes, reloading at 60s and 120s like a person would.
        while asyncio.get_event_loop().time() - t0 < 240:
            el = asyncio.get_event_loop().time() - t0
            if reloads < 2 and el > 60 * (reloads + 1):
                reloads += 1
                logger.info("harb: still on the loader after %.0fs — reloading", el)
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass
            # the persistent profile can still hold a live portal session → no form, no SMS
            if (urlparse(page.url).hostname or "") == urlparse(HOME).hostname and await self._text_visible(page, "התנתקות"):
                logger.info("harb: portal session still alive — no login / OTP needed")
                self.otp_not_needed = True
                return
            if await self._js_box(page, "#userId"):
                await page.wait_for_timeout(1500)     # let the form's scripts finish binding
                return
            if "amazoncognito.com" in (urlparse(page.url).hostname or ""):
                await self._js_click(page, "input[value='GovID-prd']", ".idpButton-customizable")
                await page.wait_for_timeout(3000)
            await page.wait_for_timeout(1000)
        await self._dump(page, "0_no_login_form")
        raise RuntimeError("הר הביטוח: דף הכניסה של login.gov.il לא נטען")

    _OTP_SELS = ("input[autocomplete='one-time-code']", "#otpCode", "#otp", "input[name*='otp' i]",
                 "input[id*='otp' i]", "input[id*='Code']", "input[type='tel']:not(#userId)",
                 "input[type='text']:not(#userId)", "input[type='number']")

    async def _otp_input(self, page: "Page") -> str | None:
        """CSS selector of the visible SMS-code box, or None (main world — see _js_box)."""
        box = await self._js_box(page, *self._OTP_SELS)
        return box["sel"] if box else None

    async def submit_otp(self, page: "Page", otp: str) -> None:
        sel = await self._otp_input(page)
        if sel is None:
            raise RuntimeError("הר הביטוח: שדה הקוד לא נמצא")
        await self._js_type(page, sel, otp, delay=60)
        clicked = await self._js_click(page, "#loginSubmit", "#otpSubmit", "button[type='submit']")
        if not clicked:
            clicked = await page.evaluate("""() => { const b = [...document.querySelectorAll('button, input[type=submit]')]
                .find(e => e.offsetParent && /כניסה|אישור|המשך/.test(e.innerText || e.value || ''));
                if (!b) return null; const r = b.getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2}; }""")
            if clicked:
                await page.mouse.click(clicked["x"], clicked["y"])
        if not clicked:
            await page.keyboard.press("Enter")
        # login.gov.il → harb's AWS Cognito → harb. Cognito sometimes stops on its own page with a
        # single "GovID-prd" button (live 2026-10-07); a person clicks it and login.gov.il, already
        # authenticated, bounces straight back. Match the HOSTNAME — the Cognito URL carries
        # harb.cma.gov.il inside redirect_uri, so a substring match calls it "logged in" too early.
        if not await self._reach_portal(page, timeout_s=90):
            await self._dump(page, "3_after_otp")
            err = await self._visible_text(page, "[role=alert], .error, [class*=error]")
            raise RuntimeError(f"הר הביטוח: הקוד לא התקבל{' — ' + err[:150] if err else ''}")
        await page.wait_for_timeout(2500)
        await self._dump(page, "3_after_otp")

    # ── per customer ─────────────────────────────────────────────────────
    async def _open_search(self, page: "Page") -> None:
        """Get to the 'חיפוש ביטוחים על שם מבוטח' form from wherever we are."""
        if await page.locator("#txtId").count() and await page.locator("#txtId").first.is_visible():
            return
        if not await self._click_text(page, ["תיק ביטוחים על שם מבוטח בגיר"], timeout=6000):
            # after a customer: "כניסה לתיק נוסף" reopens the entry modal
            await self._click_text(page, ["כניסה לתיק נוסף"], timeout=6000)
            if not await self._click_text(page, ["תיק ביטוחים על שם מבוטח בגיר"], timeout=8000):
                await page.goto(HOME.rstrip("/") + "/sso/Auth/MoreInsurance", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                await self._click_text(page, ["תיק ביטוחים על שם מבוטח בגיר"], timeout=15000)
        await page.wait_for_selector("#txtId", state="visible", timeout=20000)

    async def _set_date(self, page: "Page", group: int, d: date) -> None:
        """Kendo day/month/year dropdowns, in DOM order: birth = 0..2, issue = 3..5.
        Widget API first (exact), clicking the list as the fallback."""
        wanted = [[str(d.day), f"{d.day:02d}"],
                  [str(d.month), f"{d.month:02d}", HE_MONTHS[d.month - 1]],
                  [str(d.year)]]
        ok = await page.evaluate("""([group, wanted]) => {
            const $ = window.jQuery; if (!$) return false;
            // the widget's own wrapper — `.k-widget` is gone from newer Kendo renderings
            const ddls = [...document.querySelectorAll("[data-role='dropdownlist']")]
              .filter(e => { const w = $(e).data('kendoDropDownList'); return w && w.wrapper.is(':visible'); });
            let done = 0;
            for (let i = 0; i < 3; i++) {
              const el = ddls[group * 3 + i]; if (!el) return false;
              const w = $(el).data('kendoDropDownList'); if (!w) return false;
              const items = w.dataSource.view(); let idx = -1;
              for (let j = 0; j < items.length; j++) {
                const it = items[j];
                const txt = String(typeof it === 'object' ? (it[w.options.dataTextField] ?? it.text ?? it.Text ?? '') : it).trim();
                const val = String(typeof it === 'object' ? (it[w.options.dataValueField] ?? it.value ?? it.Value ?? '') : it).trim();
                if (wanted[i].includes(txt) || wanted[i].includes(val)) { idx = j; break; }
              }
              if (idx < 0) return false;
              w.select(idx + (w.options.optionLabel ? 1 : 0)); w.trigger('change'); done++;
            }
            return done === 3;
        }""", [group, wanted])
        if ok:
            return
        wrappers = page.locator("span.k-dropdown:visible, span.k-dropdownlist:visible, .k-widget.k-dropdown:visible")
        for i in range(3):
            await wrappers.nth(group * 3 + i).click()
            lst = page.locator(".k-animation-container:visible li, .k-list-container:visible li")
            await lst.first.wait_for(state="visible", timeout=5000)
            picked = False
            for cand in wanted[i]:
                item = lst.filter(has_text=re.compile(rf"^\s*{re.escape(cand)}\s*$"))
                if await item.count():
                    await item.first.scroll_into_view_if_needed()
                    await item.first.click()
                    picked = True
                    break
            if not picked:
                raise RuntimeError(f"הר הביטוח: לא ניתן לבחור תאריך {d:%d/%m/%Y}")

    async def _search(self, page: "Page", req) -> None:
        await self._open_search(page)
        await page.fill("#txtId", "")
        await page.locator("#txtId").type(req.customer_id_number.zfill(9), delay=50)
        await self._set_date(page, 0, req.birth_date)
        await self._set_date(page, 1, req.id_issue_date)
        cb = page.locator("#cbAproveTerm")
        if not await cb.is_checked():
            await cb.click()          # knockout `checked:` binding listens to the click
        await self._dump(page, f"4_form_{req.customer_id_number}")
        if not await self._click_text(page, ["צפיה בתיק הביטוחי"], timeout=8000):
            raise RuntimeError("הר הביטוח: כפתור 'צפיה בתיק הביטוחי' לא נמצא")
        for _ in range(60):
            await page.wait_for_timeout(750)
            if await self._text_visible(page, "כל הביטוחים"):
                return
            msg = await self._visible_text(page, "[role=alert], .modal, .k-window, .error, [class*=error], "
                                                 "[class*=Error], .validationMessage, .field-validation-error")
            if msg and any(h in msg for h in NOT_FOUND_HINTS):
                await self._dump(page, f"5_notfound_{req.customer_id_number}")
                raise HarbNotFound(msg[:300])
        await self._dump(page, f"5_no_result_{req.customer_id_number}")
        raise HarbNotFound("הר הביטוח לא הציג תיק ביטוחי — בדוק ת.ז, תאריך לידה ותאריך הנפקה")

    async def _details(self, page: "Page", req, folder: Path) -> Path | None:
        """Best-effort: open each policy row's detail view and keep its visible text."""
        out: list[dict] = []
        try:
            rows = page.locator(".k-grid tbody tr:visible, table tbody tr:visible")
            n = min(await rows.count(), 80)
            for i in range(n):
                row = rows.nth(i)
                cells = [c.strip() for c in (await row.inner_text()).split("\t") if c.strip()]
                if len(cells) < 3:
                    continue
                before = await self._visible_text(page, ".modal-content, .k-window-content, [role=dialog]")
                try:
                    await row.click(timeout=3000)
                except Exception:
                    continue
                await page.wait_for_timeout(1200)
                text = await self._visible_text(page, ".modal-content, .k-window-content, [role=dialog], .details, [class*=detail]")
                if text and text != before:
                    pol = next((c for c in cells if re.fullmatch(r"\d{5,}", c)), None)
                    co = next((c for c in cells if "בע\"מ" in c or "ביטוח" in c), None)
                    out.append({"title": " — ".join(cells[:3]), "text": text, "company": co, "policy_number": pol})
                    for close in (".modal .close", ".k-window-action", "[aria-label='Close']", "button:has-text('סגור')"):
                        loc = page.locator(close).first
                        if await loc.count() and await loc.is_visible():
                            await loc.click()
                            break
                    else:
                        await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
        except Exception as e:  # noqa: BLE001 — the Excel is the record; details are extra
            self.partial_errors.append(f"הר הביטוח: פרטי פוליסות ל-{req.customer_id_number} לא נקראו ({e})")
        if not out:
            return None
        p = folder / f"harb_{req.customer_id_number}_details.json"
        p.write_text(json.dumps(out, ensure_ascii=False), "utf-8")
        return p

    async def _fetch_one(self, page: "Page", req, folder: Path) -> tuple[Path, Path | None]:
        await self._search(page, req)
        await self._dump(page, f"6_portfolio_{req.customer_id_number}")
        await self._click_text(page, ["כל הביטוחים"], timeout=10000)
        await page.wait_for_selector(".butExcelGeneral", state="visible", timeout=30000)
        await self._dump(page, f"7_all_{req.customer_id_number}")
        xlsx = await self._expect_download(page, page.locator(".butExcelGeneral").first.click(),
                                           folder / f"harb_{req.customer_id_number}.xlsx")
        details = await self._details(page, req, folder)
        return xlsx, details

    async def download_reports(self, page: "Page", download_dir: Path, *, harb_next=None, harb_done=None,
                               **_kw) -> list[Path]:
        if harb_next is None or harb_done is None:
            raise RuntimeError("הר הביטוח מופעל רק מתוך Nifra (שליפה ללקוח), לא כהורדה רגילה")
        self._run_tag = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)
        files: list[Path] = []
        while True:
            req = await harb_next()
            if req is None:
                break
            try:
                xlsx, details = await self._fetch_one(page, req, download_dir)
                await harb_done(req, xlsx=xlsx, details=details)
                files.append(xlsx)
            except HarbNotFound as e:
                await harb_done(req, error=f"הר הביטוח לא מצא את הלקוח: {e}", not_found=True)
            except Exception as e:  # noqa: BLE001 — next customer still gets served
                logger.exception("harb: customer %s failed", req.customer_id_number)
                await self._dump(page, f"9_error_{req.customer_id_number}")
                await harb_done(req, error=f"השליפה נכשלה: {str(e)[:300]}")
            # back to the portfolio home so "כניסה לתיק נוסף" is reachable for the next one
            for _ in range(3):
                if await self._text_visible(page, "כניסה לתיק נוסף"):
                    break
                try:
                    await page.go_back(wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(1500)
                except Exception:
                    break
        await self._click_text(page, ["יציאה מהמערכת"], timeout=3000)
        return files
