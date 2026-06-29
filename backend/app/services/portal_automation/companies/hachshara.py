"""Hachshara (הכשרה) agent portal — login, OTP, download נפרעים (commission) report.

F5 BIG-IP APM at `agents-login.hcsra.co.il/my.policy`. Shares the APM login
form with Phoenix, Clal, Migdal-APM (see `_apm_helpers.py`).

Operator nav (live): right menu → **דוחות** → scroll to **עמלות** → open the
**בסט אינווסט** (Best Invest) window/חלונית → **דוחות נפרעים** → export Excel.
The Best-Invest step may open a NEW TAB (handled via context.expect_page, same
pattern as Clal's infobay). Downloaded file = `hachshara_nifraim` format
(company_source=הכשרה, commission) — no parser changes.

Selectors are best-effort against the operator's described path; refine from the
`<run_id>_<step>.txt` dumps after the first live run.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://agents-login.hcsra.co.il/my.policy"


class HachsharaPortal(BasePortalAutomation):
    portal_kind = "hachshara"
    company_label = "הכשרה"
    # Run headed: the נפרעים report is an Angular-Material page whose autocomplete
    # ("הכל") + "הורד ל excel" force-click were verified headed on the local
    # worker (like Mor). Flip to False only after a headless live-verify.
    headed = True

    async def login(self, page: "Page", username: str, password: str) -> None:
        # Hachshara wants the 9-digit username (leading-zero padded): 40336281 →
        # 040336281. Without the 0 the F5 form accepts the POST but login fails
        # (no OTP is sent → the OTP screen never appears).
        username = (username or "").strip()
        if len(username) == 8 and not username.startswith("0"):
            username = "0" + username

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1500)

        # F5 BIG-IP errorcode-19 bounce: first hit lands on
        # `my.logout.php3?errorcode=19` ("הגישה נדחתה … session information")
        # whose recovery link is **חיבור חדש** (Hachshara's wording — Phoenix uses
        # התחבר מחדש / לחץ כאן). Click it until the real logon form appears.
        for _ in range(4):
            has_user = await page.locator("input[name='username']").count()
            if has_user and "errorcode" not in page.url and "logout" not in page.url:
                break
            clicked = await self._click_first_visible(page, [
                "a:has-text('חיבור חדש')", "a:has-text('התחבר מחדש')",
                "a:has-text('לחץ כאן')", "input[value*='חיבור']",
            ], timeout=5000)
            if not clicked:
                break
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)

        # Fill + submit ourselves (the shared apm_login_submit's normal click on
        # the submit input TIMES OUT here — the `input[type=submit]` value=התחברות
        # is present+visible but not click-actionable, it's covered). Submit via
        # Enter in the password field (canonical F5 POST form), force-click fallback.
        await self._wait_visible(page, "input[name='username']", timeout=15000)
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        try:
            await page.press("input[name='password']", "Enter")
        except Exception:
            pass
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        # Fallback: still on the logon form → force-click the submit input.
        if await page.locator("input[name='username']").count():
            try:
                await page.click("input[type='submit']", force=True, timeout=4000)
            except Exception:
                pass

        await self._wait_visible(page, self._OTP_SEL, timeout=20000)

    # Hachshara's OTP input is name="text"/id="text" ("קוד חד פעמי"), NOT the usual
    # otp/code/answer names. Keep the others as fallbacks.
    _OTP_SEL = (
        "input#text, input[name='text'], input[name='otp'], "
        "input[autocomplete='one-time-code'], input[name='code'], input[name='answer']"
    )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        await page.fill(self._OTP_SEL, otp)
        # Same F5 form: the submit input isn't click-actionable → press Enter in the
        # OTP field, force-click fallback.
        try:
            await page.press(self._OTP_SEL, "Enter")
        except Exception:
            pass
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        if await page.locator(self._OTP_SEL).count():
            try:
                await page.click("input[type='submit']", force=True, timeout=4000)
            except Exception:
                pass
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        # Detect a rejected OTP fast (don't proceed to the nav on a not-logged-in
        # page). The F5 re-renders the OTP screen with "שם המשתמש או הסיסמא שגויים"
        # — usually a STALE/expired code: the phone's SMS forwarder batched an old
        # OTP (Doze) and it was consumed instead of the current one. Reinstall the
        # immediate-forward APK + disable battery optimization (see sms_forward_immediate).
        try:
            body = (await page.inner_text("body"))[:1500]
        except Exception:
            body = ""
        if "שגוי" in body or "נסה שנית" in body or "נסה שוב" in body:
            raise RuntimeError(
                "Hachshara: קוד ה-OTP נדחה (\"שם המשתמש או הסיסמא שגויים\") — ככל "
                "הנראה קוד ישן/פג תוקף שהועבר ב-batch. ודא שאפליקציית Nifraim SMS "
                "מעבירה כל SMS מיידית (התקן מחדש את ה-APK + בטל אופטימיזציית סוללה)."
            )

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        self.report_password = None

        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / "הכשרה נפרעים.xlsx"

        async def ck(tag: str):
            p = SCREENSHOT_ROOT / f"{run_id}_{tag}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        # Excel XHR sniffer — fallback if the "הורד ל excel" button streams the
        # bytes via XHR instead of a native browser download.
        xhr_capture: dict = {"bytes": None, "url": None}

        async def _on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                url = resp.url.lower()
                is_excel = (
                    "spreadsheetml" in ct or "vnd.ms-excel" in ct
                    or "octet-stream" in ct
                    or ".xlsx" in url or ".xlsx" in cd or ".xls" in cd
                )
                if is_excel and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 1024:
                        xhr_capture["bytes"] = body
                        xhr_capture["url"] = resp.url
            except Exception:
                pass

        page.on("response", _on_response)
        await ck("post_otp")

        # 1) right menu → דוחות  (live element: <span> דוחות</span>)
        await self._click_first_visible(page, [
            "span:has-text('דוחות')", "a:has-text('דוחות')",
            "button:has-text('דוחות')", "*:has-text('דוחות'):visible",
        ], timeout=10000)
        await page.wait_for_timeout(1200)
        await ck("nav1_dohot")

        # 2) עמלות  (live element: <h5 class="hover-affected-child-color">עמלות</h5>)
        for sel in ("h5:has-text('עמלות')", "*:has-text('עמלות'):visible"):
            loc = page.locator(sel).first
            try:
                if await loc.count():
                    await loc.scroll_into_view_if_needed(timeout=2500)
                    break
            except Exception:
                continue
        await self._click_first_visible(page, [
            "h5:has-text('עמלות')", "a:has-text('עמלות')", "*:has-text('עמלות'):visible",
        ], timeout=8000)
        await page.wait_for_timeout(1200)
        await ck("nav2_amlot")

        # 3) "בסט אינווסט-עמלות נפרעים" — ONE item (live element: <p>), SAME TAB
        #    (no popup). Goes to .../reports/66 (the פיקדונות נפרעים grid).
        await self._click_first_visible(page, [
            "p:has-text('בסט אינווסט'):has-text('נפרעים')",
            "p:has-text('בסט אינווסט')",
            "*:has-text('בסט אינווסט'):visible",
            "a:has-text('נפרעים')",
        ], timeout=8000)
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        await ck("nav3_nifraim")

        # 4) agent financial-number autocomplete (#mat-input-0, placeholder
        #    "בחר מספר פיננסי סוכן") → pick the **הכל** (ALL) option. WITHOUT this
        #    the grid stays empty and only the column headers export.
        agent = page.locator(
            "#mat-input-0, input[placeholder*='פיננסי סוכן'], input[placeholder*='בחר מספר']"
        ).first
        try:
            await agent.click()
            await page.wait_for_timeout(1000)
            picked = await self._click_first_visible(page, [
                "mat-option:has-text('הכל')", "[role='option']:has-text('הכל')",
                ".mat-option:has-text('הכל')",
            ], timeout=5000)
            if not picked:
                await agent.press("ArrowDown")
                await page.wait_for_timeout(600)
                await self._click_first_visible(page, [
                    "mat-option:has-text('הכל')", "mat-option", "[role='option']",
                ], timeout=4000)
            # Close the mat-autocomplete panel — its cdk-overlay backdrop otherwise
            # intercepts the subsequent "הורד ל excel" click (the observed "selects
            # הכל but never presses download" bug). Then let the grid load.
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        await ck("nav4_agent_all")

        # 5) download — button "הורד ל excel" (<i class="mdi mdi-microsoft-excel">).
        #    This Angular page covers elements, so FORCE-click the exact button;
        #    native download + XHR fallback.
        async def _click_excel() -> bool:
            for sel in (
                "button:has-text('הורד ל excel')",
                "button.btn-outline-ele:has(i.mdi-microsoft-excel)",
                "button:has(i.mdi-microsoft-excel)",
                "i.mdi-microsoft-excel",
                "button:has-text('ייצוא לאקסל')", "button:has-text('יצוא לאקסל')",
            ):
                loc = page.locator(sel).first
                try:
                    if await loc.count():
                        await loc.scroll_into_view_if_needed(timeout=2000)
                        await loc.click(force=True, timeout=4000)
                        return True
                except Exception:
                    continue
            return False

        try:
            async with page.expect_download(timeout=30000) as dl_info:
                if not await _click_excel():
                    raise RuntimeError("no-download-trigger-visible")
            download = await dl_info.value
            await download.save_as(str(target))
        except Exception as native_err:
            for _ in range(24):
                if xhr_capture["bytes"]:
                    break
                await asyncio.sleep(0.5)
            if xhr_capture["bytes"]:
                target.write_bytes(xhr_capture["bytes"])
            else:
                await ck("nav5_no_download")
                raise RuntimeError(
                    f"Hachshara: לא נמצא טריגר הורדה ב-{page.url}. בדוק "
                    f"{run_id}_nav4_agent_all.txt / _nav5_no_download.txt: {native_err}"
                )
        finally:
            try:
                page.remove_listener("response", _on_response)
            except Exception:
                pass

        await ck("nav5_after_export")
        return [target]
