"""Shared base for Harel agents-portal "ריכוז תשלומי עמלות" report plugins.

Both `harel_commissions` (נפרעים → commission) and `harel_savings` (מוצרי צבירה →
production) drive the SAME report — same APM login/OTP (inherited from HarelPortal),
same hangup recovery, same intellisys-iframe navigation and "סנן מידע" filter — and
differ only in which column they drill and how they export.

This base carries the stable, shared machinery (verified live against the נפרעים
flow): frame acquisition, page/frame dumping, visible-aware clicking, hangup
recovery, report navigation, the מספר-חשבון account dropdown (list + select), and
the filter button. Subclasses implement `download_reports`.

Note: visible-aware clickers are named `_vis_click_*` so they do NOT shadow the base
`_click_first_visible(page, selectors, timeout)` that HarelPortal.login relies on.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from app.services.portal_automation.companies.harel import HarelPortal

if TYPE_CHECKING:
    from playwright.async_api import Page, Frame


# Same report for both נפרעים and צבירה. Path is relative — the agent portal lives
# on agents-int.harel-group.co.il after the APM/OTP redirect, so we derive the
# origin from the live URL rather than hardcoding the subdomain.
REPORT_PATH = (
    "/Information/Reports/life-health-saving/Agent/Pages/commissions/payments-assembly.aspx"
)


class _HarelReportPortal(HarelPortal):
    """Login + OTP inherited from HarelPortal. Shared report navigation here."""

    # ── frame / dump / click helpers ──────────────────────────────────────────

    async def _get_frame(self, page: "Page", *, poll_seconds: int = 40):
        """Return the intellisys dashboard iframe (re-query each call — it can
        re-render on filter/drill).

        Polls for up to *poll_seconds* (default 40 s, up from the original 15 s,
        to handle slow BI renders after deep drills or on flaky connections).
        Each 0.5 s tick tries three strategies in order:

        1. CSS selector against the DOM iframe element (five variants: class,
           id-substring, src-substring, name-substring, _sp_dashboard src).
        2. Direct ``page.frames`` scan by URL/name keyword — catches iframes
           whose outer-DOM ``<iframe>`` element hasn't attached yet but whose
           Playwright Frame object is already navigated.
        3. Any frame that has rendered Intellisys drillable cells
           (``td.click-enter``) — last resort so we never false-positive on
           empty or utility frames.
        """
        _SELS = (
            "iframe.intellisys",
            "iframe[id*='intellisys']",
            "iframe[src*='intellisys']",
            "iframe[name*='intellisys']",
            "iframe[src*='_sp_dashboard']",
        )
        _KW = ("intellisys", "_sp_dashboard")
        iters = max(1, poll_seconds * 2)  # 0.5 s per tick
        for _ in range(iters):
            # Strategy 1: DOM element → content_frame
            for sel in _SELS:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        fr = await el.content_frame()
                        if fr:
                            return fr
                except Exception:
                    pass
            # Strategy 2: Playwright frame URL / name scan (no DOM element needed)
            try:
                for fr in page.frames:
                    try:
                        url = fr.url or ""
                        name = fr.name or ""
                        if url in ("", "about:blank"):
                            continue
                        if any(kw in url.lower() or kw in name.lower() for kw in _KW):
                            return fr
                    except Exception:
                        continue
            except Exception:
                pass
            # Strategy 3: any frame with Intellisys drillable cells
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

    async def _dump_frame(self, page: "Page", run_id: str, stem: str, fr) -> None:
        """Screenshot + frame HTML + a list of VISIBLE click-enter cells
        (data_colid=text) — the .html includes hidden background insets, so the
        .cells.txt is what clarifies what's actually clickable."""
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
        await self._safe_screenshot(page, p)
        try:
            html = await fr.content()
            p.with_suffix(".html").write_text(html, encoding="utf-8")
        except Exception:
            pass
        try:
            cells = await fr.eval_on_selector_all(
                "td.click-enter",
                "els => els.filter(e => e.offsetParent !== null)"
                ".map(e => (e.getAttribute('data_colid')||'?') + '=' + (e.innerText||'').trim())"
                ".slice(0, 120)",
            )
            p.with_suffix(".cells.txt").write_text("\n".join(cells), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    async def _vis_click_first(loc, *, require_text: bool = True) -> bool:
        """Click the first VISIBLE (and, by default, non-empty/non-zero) match.
        Drill views repeat cells in hidden insets that still report visible via
        offsetParent, so plain .first/strict-click hits the wrong element."""
        try:
            n = await loc.count()
        except Exception:
            n = 0
        for j in range(min(n, 60)):
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

    @staticmethod
    async def _vis_click_last(loc) -> bool:
        """Click the LAST visible match — the deepest grid's bar-excel button is
        appended last in the DOM as drills/tabs open."""
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

    # ── navigation ─────────────────────────────────────────────────────────────

    @staticmethod
    def _bounced(u: str) -> bool:
        return any(s in (u or "") for s in ("hangup", "logout", "my.policy", "my.logout"))

    async def _recover_hangup(self, page: "Page") -> None:
        """F5 can land the post-OTP session on vdesk/hangup.php3; click "לחץ כאן"
        / hit the site root to re-land authenticated (OTP cookie already set)."""
        if not self._bounced(page.url):
            return
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
            if not self._bounced(page.url):
                break
        if self._bounced(page.url):
            raise RuntimeError(
                f"הסשן של הראל הסתיים מיד לאחר ה-OTP ולא הצלחנו לשחזר ({page.url}). "
                "ודא שאין חיבור פעיל אחר לאזור הסוכנים ונסה שוב."
            )

    async def _open_report(self, page: "Page", run_id: str):
        """Recover hangup, navigate to the report, return the loaded intellisys
        frame (params/filter rendered). Raises if the frame never appears."""
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        await self._recover_hangup(page)
        parsed = urlparse(page.url)
        report_url = f"{parsed.scheme}://{parsed.netloc}{REPORT_PATH}"
        try:
            await page.goto(report_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            try:
                await page.locator('a[href*="payments-assembly.aspx"]').first.click(
                    timeout=8000, force=True
                )
            except Exception as e:
                raise RuntimeError(f"לא הצלחנו לפתוח את הדוח ({page.url}): {e}")
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        frame = await self._get_frame(page)
        if frame is None:
            # The BI iframe might still be loading, or the session bounced to
            # hangup.php3 mid-goto. Try hangup recovery and re-poll for a
            # shorter window before giving up completely.
            try:
                await self._recover_hangup(page)
                await page.wait_for_timeout(2000)
            except Exception:
                pass
            frame = await self._get_frame(page, poll_seconds=10)

        if frame is None:
            _no_frame = SCREENSHOT_ROOT / f"{run_id}_1_no_frame.png"
            await self._safe_screenshot(page, _no_frame)
            await self._dump_page_state(page, _no_frame)
            try:
                # Full iframe inventory for post-mortem (src/name/id of every
                # frame Playwright knows about — see _no_frame.iframes.txt).
                await self._dump_all_frames(page, _no_frame)
            except Exception:
                pass
            raise RuntimeError(f"לא נמצא iframe של הדוח (intellisys) ב-{page.url}.")
        for sel in ("#_ctrlParam__2", ".param-container", "button.bar-excel"):
            try:
                await frame.wait_for_selector(sel, timeout=20000)
                break
            except Exception:
                continue
        await page.wait_for_timeout(2000)
        return frame

    # ── account dropdown (מספר - חשבון, #_ctrlParam__2) ─────────────────────────

    async def _list_accounts(self, page: "Page", frame: "Frame") -> list[str]:
        """Open the מספר-חשבון dropdown and return the account-id strings (leading
        number of each option). Falls back to the currently-selected account if
        enumeration fails (single-account behaviour)."""
        accounts: list[str] = []
        try:
            await frame.click("#_ctrlParam__2", timeout=4000)
            await page.wait_for_timeout(800)
            opts = await frame.eval_on_selector_all(
                ".cbo_list .ctrlText, .cbo-list .ctrlText, ul li .ctrlText, "
                "div.ctrlText, li[role='option'], .param-value-container .ctrlText",
                "els => els.filter(e => e.offsetParent !== null)"
                ".map(e => (e.getAttribute('title') || e.innerText || '').trim())",
            )
            for t in opts:
                m = re.match(r"\s*(\d{4,})", t or "")
                if m and m.group(1) not in accounts:
                    accounts.append(m.group(1))
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except Exception:
            pass
        if not accounts:
            try:
                cur = await frame.locator("#ctrlParam__2").inner_text(timeout=3000)
                m = re.search(r"(\d{4,})", cur or "")
                if m:
                    accounts = [m.group(1)]
            except Exception:
                pass
        return accounts

    async def _select_account(self, page: "Page", frame: "Frame", account: str) -> None:
        """Select a specific account in the dropdown (no-op if already current)."""
        try:
            cur = await frame.locator("#ctrlParam__2").inner_text(timeout=3000)
        except Exception:
            cur = ""
        if account in (cur or ""):
            return
        try:
            await frame.click("#_ctrlParam__2", timeout=4000)
            await page.wait_for_timeout(800)
            for sel in (
                f'div.ctrlText:has-text("{account}")',
                f'[title*="{account}"]',
                f'li:has-text("{account}")',
            ):
                try:
                    await frame.click(sel, timeout=3000)
                    break
                except Exception:
                    continue
            await page.wait_for_timeout(500)
        except Exception:
            pass

    async def _run_filter(self, page: "Page", frame: "Frame"):
        """Click "סנן מידע" and return the (re-acquired) frame after the report runs."""
        for sel in (
            'button:has-text("סנן מידע")',
            'a:has-text("סנן מידע")',
            'input[value*="סנן"]',
            '[title*="סנן"]',
            'text="סנן מידע"',
        ):
            try:
                await frame.click(sel, timeout=4000)
                break
            except Exception:
                continue
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)
        frame = await self._get_frame(page) or frame
        # The Intellisys report grid keeps building via document.write AFTER
        # networkidle — proceeding immediately can find ZERO drillable cells
        # (the consolidated batch hit exactly this: sv_2_filtered had 0 cells →
        # drill "not found"). Poll until the Schum_* data cells actually render
        # (re-acquiring the frame, which can be replaced on the async build).
        for _ in range(25):  # up to ~25s
            try:
                n = await frame.locator('td.cell_action[data_colid^="Schum"]').count()
                if n > 0:
                    break
            except Exception:
                pass
            await page.wait_for_timeout(1000)
            frame = await self._get_frame(page) or frame
        return frame
