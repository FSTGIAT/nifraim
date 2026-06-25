"""Phoenix (הפניקס) agent portal — login, OTP, download production report.

Phoenix sits behind F5 BIG-IP APM at `agent.fnx.co.il/my.policy`. Shares the
APM login form with Hachshara, Clal, and Migdal-APM (see `_apm_helpers.py`).

Login + OTP are verified. The production report, however, is NOT a clickable
HTML page: after OTP the operator clicks a systems icon → "ביטוח חיים" → the
systems icon again, which opens a LEGACY GREEN-SCREEN TERMINAL EMULATOR
("מסוף"). The menu arrives as visual-order DOS Hebrew (CP862 family) and is
navigated by typing a menu-option NUMBER + Enter, not by clicking links.

We can't see the live terminal's tech (iframe vs HTML5 canvas vs div-grid)
without a run, and that decides how keystrokes are sent and whether the menu
is machine-readable. So `download_reports` currently ships as **Stage A —
recon**: it drives icon → ביטוח חיים → icon into the terminal, captures every
frame via `_dump_all_frames`, writes a `recon_summary.txt`, then raises so the
run is flagged with all artifacts intact under `data/portal_screenshots/`.
Once we inspect those, Stage B replaces this body with keystroke navigation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation
from app.services.portal_automation._apm_helpers import apm_login_submit

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://agent.fnx.co.il/my.policy"


class PhoenixPortal(BasePortalAutomation):
    portal_kind = "phoenix"
    company_label = "הפניקס"
    # The production report lives behind a legacy Ericom green-screen terminal
    # that Playwright can't drive (see module docstring + portal_phoenix_terminal
    # memory). Excluded from the batch so it doesn't burn an OTP on a known
    # dead end. The נפרעים reports are downloaded by phoenix_nifraim instead.
    include_in_batch = False

    async def login(self, page: "Page", username: str, password: str) -> None:
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # F5 APM bot gate: the first hit frequently bounces to
        # `my.logout.php3?errorcode=19`, which renders a "התחבר מחדש" recovery
        # link. Click it to land back on the real logon form (same pattern as
        # the Harel plugin). Loop a few times since it can bounce twice.
        for _ in range(4):
            if "errorcode" not in page.url and "logout" not in page.url:
                break
            clicked = await self._click_first_visible(
                page,
                [
                    "a:has-text('התחבר מחדש')",
                    "a:has-text('חזרה למסך הכניסה')",
                    "a:has-text('לחץ כאן')",
                    "a:has-text('כניסה')",
                ],
                timeout=5000,
            )
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=8000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            if not clicked:
                break

        await apm_login_submit(page, username, password)
        # The OTP step reuses the F5 input (id=input_2) but relabels it with
        # placeholder "קוד זיהוי" and swaps the submit to "כניסה". Wait on the
        # placeholder — that's what distinguishes the OTP screen from the
        # credentials screen (which has the username input_1 alongside).
        await self._wait_visible(
            page,
            "input[placeholder='קוד זיהוי'], input#input_2",
            timeout=20000,
        )

    # Selector for the Phoenix OTP field — placeholder is the reliable anchor.
    OTP_FIELD = "input[placeholder='קוד זיהוי'], input#input_2, input[name='password']"

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(self.OTP_FIELD, otp)
        for sel in (
            "input[type='submit'][value='כניסה']",
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('כניסה')",
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
        # ── STAGE A — RECON ────────────────────────────────────────────────
        # Navigate icon → ביטוח חיים → icon into the terminal, dump every
        # frame at each step, then raise so the run is flagged with artifacts
        # intact. Stage B replaces this with keystroke navigation once we know
        # what the terminal is.
        self.report_password = None

        from app.services.portal_automation.runner import SCREENSHOT_ROOT, logger
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)

        async def _checkpoint(stem: str, target=None) -> None:
            """Screenshot + full per-frame dump under <run_id>_<stem>__*."""
            await self._dump_all_frames(target or page, SCREENSHOT_ROOT / f"{run_id}_{stem}.png")

        # Step 0: settle, dismiss any post-login modal, dump the landing page.
        await page.wait_for_timeout(2000)
        await self._click_first_visible(
            page,
            [
                "button:has-text('סגור')",
                "button:has-text('אישור')",
                "button:has-text('הבנתי')",
                ".modal-close",
                "[aria-label='Close']",
                "[aria-label='סגור']",
            ],
            timeout=4000,
        )
        await _checkpoint("recon_0_post_otp")

        # Step 1: open the "המערכות שלי" (My Systems) menu. Clicking the
        # my-systems.svg <img> reliably opens the mat-menu (clicking the button
        # by text did NOT — observed empirically).
        if not await self._click_first_visible(
            page,
            [
                "img[src*='my-systems.svg']",
                "img[src*='my-systems']",
                "button:has(img[src*='my-systems'])",
                "button:has-text('המערכות שלי')",
            ],
            timeout=8000,
        ):
            await _checkpoint("recon_1_systems_no_match")
            raise RuntimeError(
                f"Phoenix recon: 'המערכות שלי' button not found at {page.url}. "
                f"Inspect {run_id}_recon_1_systems_no_match__*."
            )
        await page.wait_for_timeout(1200)  # let the mat-menu flyout render
        await _checkpoint("recon_1_systems")

        # Helper: enumerate every Material menu item across all overlay panes
        # (parent menu + any open submenu) with its text and whether it carries
        # a my-systems.svg launcher icon. Written to a dedicated artifact so we
        # can read the submenu contents and pin the terminal launcher.
        async def _dump_menuitems(stem: str) -> list[dict]:
            try:
                items = await page.evaluate(
                    """() => {
                        const out = [];
                        const panes = document.querySelectorAll('.cdk-overlay-pane, .mat-mdc-menu-panel');
                        document.querySelectorAll('[role="menuitem"]').forEach((el, i) => {
                            const r = el.getBoundingClientRect();
                            const imgs = [...el.querySelectorAll('img')].map(im => im.getAttribute('src') || '');
                            out.push({
                                i,
                                text: (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
                                hasSubmenu: el.getAttribute('aria-haspopup') === 'menu',
                                expanded: el.getAttribute('aria-expanded'),
                                visible: r.width > 0 && r.height > 0,
                                imgs,
                                mySystems: imgs.some(s => s.includes('my-systems')),
                            });
                        });
                        return out;
                    }"""
                )
            except Exception as e:
                items = [{"error": str(e)}]
            lines = [f"{stem} — {len(items)} menu items", ""]
            for it in items:
                lines.append(str(it))
            (SCREENSHOT_ROOT / f"{run_id}_{stem}.txt").write_text(
                "\n".join(lines), encoding="utf-8"
            )
            return items

        # Step 2: click the "ביטוח חיים" menu item. Per the operator flow this
        # reveals a connect panel with a "התחבר" button (NOT a second systems
        # icon). It's a button[role=menuitem] under the "מערכות הפניקס" header —
        # role=menuitem disambiguates it from the dashboard "ביטוח חיים (0)"
        # counter buttons.
        life_item = page.locator(
            "button[role='menuitem']:has-text('ביטוח חיים')"
        ).first
        try:
            await life_item.hover(timeout=6000)
            await page.wait_for_timeout(600)
            await life_item.click(timeout=4000)
        except Exception:
            await _checkpoint("recon_2_life_no_match")
            await _dump_menuitems("recon_menuitems_no_match")
            raise RuntimeError(
                f"Phoenix recon: 'ביטוח חיים' menu-item not found at {page.url}. "
                f"Inspect {run_id}_recon_2_life_no_match__* and "
                f"{run_id}_recon_menuitems_no_match.txt."
            )
        await page.wait_for_timeout(1500)  # let the connect panel render
        await _checkpoint("recon_2_life")
        await _dump_menuitems("recon_menuitems")

        # Step 3: click the "התחבר" connect button — this launches the terminal,
        # which opens in a NEW TAB (F5 VDI). Capture that popup so we can dump
        # the actual terminal page. "התחבר" (connect) must not match "התחבר
        # מחדש" (reconnect) — anchor on the btn-primary class + exact-ish text.
        term_page = page  # fallback if it somehow opens in the same tab
        connect_selectors = [
            "button.btn-primary-sm:has-text('התחבר')",
            "button.btn-primary:has-text('התחבר')",
            "button:has-text('התחבר'):not(:has-text('מחדש'))",
        ]
        try:
            async with page.context.expect_page(timeout=20000) as new_tab_info:
                if not await self._click_first_visible(page, connect_selectors, timeout=8000):
                    raise RuntimeError("no-connect-button")
            term_page = await new_tab_info.value
            await term_page.wait_for_load_state("domcontentloaded", timeout=20000)
            logger.info("Phoenix recon: terminal opened in new tab %s", term_page.url)
        except Exception as e:
            logger.info("Phoenix recon: no new tab from 'התחבר' (%s) — using same page", e)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
        await _checkpoint("recon_3_connect", term_page)

        # Step 4: let the terminal emulator boot, then dump everything from the
        # terminal page. This is the payload artifact — it shows whether the
        # terminal is an iframe, an HTML5 canvas, or a div-grid, and (if
        # scrapeable) its menu text.
        await term_page.wait_for_timeout(4000)
        await _checkpoint("recon_4_terminal", term_page)

        # Step 5: probe the TERMINAL page for its technology + summary.
        page = term_page  # subsequent probe/summary operate on the terminal tab
        try:
            probe = await page.evaluate(
                """() => {
                    const w = window;
                    const has = (k) => {
                        try { return typeof w[k] !== 'undefined'; } catch (e) { return false; }
                    };
                    const canvases = [...document.querySelectorAll('canvas')].map(c => {
                        const r = c.getBoundingClientRect();
                        return `${Math.round(r.width)}x${Math.round(r.height)} id=${c.id||'-'}`;
                    });
                    return {
                        frameCount: w.frames ? w.frames.length : 0,
                        canvases,
                        applets: document.querySelectorAll('applet').length,
                        objects: document.querySelectorAll('object,embed').length,
                        powerterm: has('PowerTerm') || has('ptweb') || has('PtWeb'),
                        ericom: has('Ericom') || has('ericom'),
                        flynet: has('Flynet') || has('flynet'),
                        websocketCtor: typeof WebSocket !== 'undefined',
                    };
                }"""
            )
        except Exception as e:
            probe = {"error": str(e)}

        summary_lines = [
            f"RUN: {run_id}",
            f"TOP URL: {page.url}",
            f"FRAME COUNT (page.frames): {len(page.frames)}",
            "",
            "PROBE:",
            *[f"  {k}: {v}" for k, v in (probe or {}).items()],
            "",
            "Frame URLs:",
            *[f"  [{i}] {f.url}" for i, f in enumerate(page.frames)],
            "",
            "Inspect the recon_4_terminal__frame*.{html,txt} dumps to identify",
            "the terminal element and (if scrapeable) read the menu, then fill",
            "in Stage B's MENU_PATH.",
        ]
        (SCREENSHOT_ROOT / f"{run_id}_recon_summary.txt").write_text(
            "\n".join(summary_lines), encoding="utf-8"
        )
        logger.info("Phoenix recon complete for run %s — %d frames", run_id, len(page.frames))

        raise RuntimeError(
            f"Phoenix recon complete — terminal reached. Inspect "
            f"{run_id}_recon_4_terminal__frame*.{{html,txt}} and "
            f"{run_id}_recon_summary.txt under data/portal_screenshots/ to wire "
            f"up Stage B keystroke navigation."
        )
