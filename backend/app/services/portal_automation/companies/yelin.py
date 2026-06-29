"""ילין לפידות (Yelin Lapidot) agent portal — login, OTP, commission download.

Login (https://online.yl-invest.co.il/agents/) is a JS SPA. The operator logs in
with **ת.ז (ID)** + **מספר פלאפון (phone)**; the portal then SMS-OTPs that phone.

Credential convention:  ``username = "<id>"`` (ת"ז 40336281),
                        ``password = "<phone>"`` (פלאפון 504302306 → 0504302306).

Flow (operator):  top menu → עמלות → export to Excel ("ייצוא לאקסל").

The exact form/menu/export selectors aren't knowable from the static HTML (SPA),
so login/submit_otp/download_reports use broad candidate-selector lists and dump
``<run_id>_*.{png,html,txt}`` aggressively. Refine the selectors from the FIRST
live run's `.txt` dumps (visible inputs / links / buttons) — re-running costs an
OTP, so fix selectors before the next run.

The downloaded עמלות Excel format is confirmed against a real sample on the first
run; if `detect_format` misses it, add a `yelin`/`yelin_nifraim` signature to
`hebrew_mappings.py` (company_source=ילין לפידות). No parser change until then.
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

PORTAL_URL = "https://online.yl-invest.co.il/agents/"


class YelinPortal(BasePortalAutomation):
    portal_kind = "yelin"
    company_label = "ילין לפידות"
    # Live-verified end-to-end 2026-06-29 (hands-free phone-forward OTP → עמלות
    # download → ingest → parse, 614 customers). Now in the run-all batch.
    include_in_batch = True

    def _split(self, username: str, password: str) -> tuple[str, str]:
        """username='<id>', password='<phone>'. Pad the Israeli ת"ז to 9 digits
        and the mobile to 10 (the operator stores 40336281 / 504302306, dropping
        the leading zero)."""
        id_no = re.sub(r"\D", "", username or "")
        phone = re.sub(r"\D", "", password or "")
        if len(id_no) == 8:
            id_no = "0" + id_no
        if len(phone) == 9 and not phone.startswith("0"):
            phone = "0" + phone
        return id_no, phone

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        id_no, phone = self._split(username, password)

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        land = SCREENSHOT_ROOT / "yelin_login.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # Real DOM (verified live): the agent form is
        #   input[name="personalId"]   — ת"ז (placeholder "תעודת זהות של מורשה גישה")
        #   input[name="mobileNumber"] — phone (maxlength 10)
        #   radio name="method": method_0 = בהודעת SMS (default), method_1 = קולית
        #   checkbox name="confirm"    — terms approval — MUST be checked or
        #                                the "המשך" submit button stays disabled
        #   button "המשך"              — submit → SMS OTP
        # React/Ant form: drive real KEYSTROKES so validation enables submit.
        async def _type(selectors: list[str], val: str, label: str) -> bool:
            for sel in selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=4000)
                except Exception:
                    continue
                try:
                    await page.click(sel)
                    await page.fill(sel, "")
                    await page.keyboard.type(val, delay=70)
                    cur = await page.input_value(sel)
                    if cur != val:  # retry once if a char dropped
                        await page.fill(sel, "")
                        await page.click(sel)
                        await page.keyboard.type(val, delay=90)
                    logger.info("ילין: filled %s via %s", label, sel)
                    return True
                except Exception:
                    continue
            return False

        id_ok = await _type([
            "input[name='personalId']",
            "input[placeholder*='תעודת זהות']",
            "input[placeholder*='זהות']",
        ], id_no, "ת\"ז")

        phone_ok = await _type([
            "input[name='mobileNumber']",
            "input[placeholder*='טלפון']",
            "input[placeholder*='נייד']",
        ], phone, "טלפון")

        if not (id_ok and phone_ok):
            raise RuntimeError(
                "ילין: לא נמצאו שדות ת\"ז/טלפון בטופס ההתחברות — בדוק yelin_login.txt/html"
            )

        # Prefer SMS delivery (default checked, but force it in case of voice).
        try:
            await page.check("input[name='method'][value='1'], #method_0", timeout=2000)
        except Exception:
            pass

        # Approve terms — the submit stays disabled until this is checked.
        checked = False
        for sel in ("input[name='confirm']", "label[for='confirm']",
                    ".yui-checkbox-label", "span.ant-checkbox"):
            try:
                await page.check(sel, timeout=2000)
                checked = True
                break
            except Exception:
                try:
                    await page.click(sel, timeout=2000)
                    checked = True
                    break
                except Exception:
                    continue
        if not checked:
            logger.warning("ילין: לא סומן צ'קבוקס אישור התנאים — ייתכן וההמשך יישאר מושבת")
        await page.wait_for_timeout(500)

        # Submit "המשך".
        clicked = await self._click_first_visible(page, [
            "button:has-text('המשך')",
            "button:has-text('שלח')",
            "button:has-text('כניסה')",
            "button[type='submit']:not([disabled])",
            "input[type='submit']",
        ], timeout=10000)
        if not clicked:
            raise RuntimeError(
                "ילין: כפתור 'המשך' לא נמצא או נשאר מושבת (בדוק שאישור התנאים סומן) — "
                "בדוק yelin_login.txt"
            )

        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "yelin_after_send.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)

        # Wait for the OTP screen to render (a short numeric field or a segmented
        # group appears) OR an error toast, so we fail fast on bad creds.
        otp_sel = (
            "input[formcontrolname*='otp' i], input[name*='otp' i], "
            "input[autocomplete='one-time-code'], input[placeholder*='קוד'], "
            "input[type='tel'][maxlength='1']"
        )
        for _ in range(60):  # ~30s
            try:
                if await page.locator(otp_sel).count() and \
                        await page.locator(otp_sel).first.is_visible():
                    return
            except Exception:
                pass
            try:
                err = await page.evaluate(
                    """() => [...document.querySelectorAll('.error,.toast,.alert,[class*=error i],[class*=Error]')]
                        .map(e => (e.innerText||'').trim()).filter(Boolean).join(' | ').slice(0,300)"""
                )
            except Exception:
                err = ""
            if err and any(w in err for w in ("שגוי", "שגיא", "לא נמצא", "נסה")):
                raise RuntimeError(f"ילין: הכניסה נדחתה — {err}")
            await page.wait_for_timeout(500)
        # Didn't clearly transition — let the runner await OTP anyway; submit_otp
        # re-detects the field. The dump above is the diagnostic.

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")

        filled = False
        # Case A: segmented single-char boxes (type one digit each).
        try:
            boxes = page.locator("input[type='tel'][maxlength='1']:visible")
            n = await boxes.count()
            if 0 < n <= len(digits) + 2:
                for i in range(min(n, len(digits))):
                    b = boxes.nth(i)
                    await b.click()
                    await b.fill("")
                    await page.keyboard.type(digits[i], delay=60)
                filled = True
        except Exception:
            pass
        # Case B: a single OTP input.
        if not filled:
            for sel in (
                "input[formcontrolname*='otp' i]",
                "input[name*='otp' i]",
                "input[autocomplete='one-time-code']",
                "input[placeholder*='קוד']",
                "input[name='code']",
            ):
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=3000)
                    await page.click(sel)
                    await page.keyboard.type(digits, delay=70)
                    filled = True
                    break
                except Exception:
                    continue

        await page.wait_for_timeout(400)
        await self._click_first_visible(page, [
            "button:has-text('אישור')",
            "button:has-text('כניסה')",
            "button:has-text('התחבר')",
            "button:has-text('המשך')",
            "button[type='submit']:not([disabled])",
            "input[type='submit']",
        ], timeout=6000)

        try:
            await page.wait_for_url(
                lambda u: "login" not in (u or "").lower(), timeout=25000
            )
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        post = SCREENSHOT_ROOT / "yelin_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("ילין: לא נמצא שדה OTP — בדוק yelin_after_send.txt")

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

        # 1) Top menu → עמלות.
        await self._click_first_visible(page, [
            "nav a:has-text('עמלות')",
            "header a:has-text('עמלות')",
            "a:has-text('עמלות')",
            "[role='menuitem']:has-text('עמלות')",
            "button:has-text('עמלות')",
            "span:has-text('עמלות')",
            "li:has-text('עמלות')",
        ], timeout=12000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        await ck("nav_1_amlot")

        # 2) Export to Excel — capture native download OR XHR bytes. (If the
        #    עמלות screen needs a sub-selection — a report row / month / "הצג" —
        #    refine here from nav_1_amlot.txt after the first run.)
        target = download_dir / "ילין לפידות עמלות.xlsx"
        xhr = {"bytes": None, "url": None}

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
                        xhr["url"] = resp.url
            except Exception:
                pass
        page.on("response", on_resp)

        got = None
        try:
            async with page.expect_download(timeout=30000) as dl:
                clicked = await self._click_first_visible(page, [
                    "button:has-text('ייצוא לאקסל')",
                    "a:has-text('ייצוא לאקסל')",
                    "button:has-text('יצוא לאקסל')",
                    "button:has-text('הורד לאקסל')",
                    "button:has-text('ייצוא לאקס')",
                    "button:has-text('אקסל')",
                    "a:has-text('אקסל')",
                    "button:has-text('ייצוא')",
                    "button:has-text('הורדה')",
                    "button:has-text('הורד')",
                    "[title*='אקסל']",
                    "[title*='Excel' i]",
                    "[aria-label*='אקסל']",
                    "img[src*='excel' i]",
                    "[class*='excel' i]",
                ], timeout=12000)
                if not clicked:
                    raise RuntimeError("no-export-trigger")
            d = await dl.value
            await d.save_as(str(target))
            got = target
        except Exception as native_err:
            import asyncio
            for _ in range(20):
                if xhr["bytes"]:
                    break
                await asyncio.sleep(0.5)
            if xhr["bytes"]:
                target.write_bytes(xhr["bytes"])
                got = target
            else:
                await ck("nav_2_no_download")
                raise RuntimeError(
                    f"ילין: לא ירד קובץ מ-{page.url}. בדוק {run_id}_nav_1_amlot.txt / "
                    f"_nav_2_no_download.txt : {native_err}"
                )
        finally:
            page.remove_listener("response", on_resp)

        await ck("nav_2_after_export")
        if not got:
            raise RuntimeError(
                f"ילין: לא ירד קובץ — בדוק {run_id}_nav_1_amlot.txt / _nav_2_after_export.txt"
            )
        return [got]
