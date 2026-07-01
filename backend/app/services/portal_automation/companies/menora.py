"""Menora (מנורה) agent portal — login, SMS OTP, download production files.

Flow (verified with operator 2026-05-31):
    1. https://menoranet.menora.co.il/        — username + password
    2. SMS OTP page (Twilio / phone-forward fills otp_inbox)
    3. Lands on https://menoranet.menora.co.il/agents-site/
    4. Click `<span>כספות - AgentFilesMaster</span>` tile
    5. Vault renders rows with `<button class="button_DocTable">הורד קבצים</button>`.
       Some rows are production (e.g. `חיים פרודוקציה`) and some are
       commission (`דוח עמלות`). We download ONLY the production rows.

Filename strategy: preserve the Hebrew row label (which contains "פרודוקציה")
so the ingest dispatcher classifies the file as production via column-signature
detection (see upload_ingest.category_for_format + parser_service.detect_format).

When a run fails (or even succeeds), the runner saves
`data/portal_screenshots/<run_id>{,_post_otp,_nav_*}.{png,html,txt}`
so we can iterate selectors from real evidence.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page


PORTAL_URL = "https://menoranet.menora.co.il/"
AGENTS_SITE_URL = "https://menoranet.menora.co.il/agents-site/"


class MenoraPortal(BasePortalAutomation):
    portal_kind = "menora"
    company_label = "מנורה"

    async def login(self, page: "Page", username: str, password: str) -> None:
        # NOTE: Menora's login is NOT username + password. The form asks for
        # `#username` + `#phoneNumber`. The portal sends an SMS OTP to that
        # phone number. We treat the credential's `password` field as the
        # phone number (operator stores e.g. `0504302306`).
        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)

        # CRITICAL hydration wait: the login form is an Angular SPA whose "אישור"
        # button is a bare <button type="submit"> inside <form method="POST"
        # action=null>. Click it before Angular binds the submit handler and a
        # NATIVE form submit fires → POST / → a "Cannot POST /" error page (the
        # exact batch failure observed 2026-06-20). Waiting for the app to settle
        # lets the JS handler attach so the click triggers the SMS flow instead.
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        safe_user = re.sub(r"[^A-Za-z0-9_]", "_", username)[:32] or "anon"
        landing = SCREENSHOT_ROOT / f"menora_login_{safe_user}.png"
        await self._safe_screenshot(page, landing)
        await self._dump_page_state(page, landing)

        await self._wait_visible(page, "input#username", timeout=15000)
        await page.fill("input#username", username)
        # Normalize the phone (password holds the phone for Menora's reversed creds).
        # A stored number that lost its leading 0 (e.g. 9-digit "5XXXXXXXX" instead
        # of "05XXXXXXXX") is rejected by Menora's login → the field ends up empty,
        # no SMS is sent, and the OTP box never appears (25s timeout). Restore it.
        phone = re.sub(r"\D", "", password or "")
        if len(phone) == 9 and not phone.startswith("0"):
            phone = "0" + phone
        await page.fill("input#phoneNumber", phone)
        # MUI controlled inputs occasionally drop a programmatic fill — if the field
        # didn't take the value, type it key-by-key so the SMS request actually fires.
        try:
            if (await page.input_value("input#phoneNumber")) != phone:
                await page.click("input#phoneNumber")
                await page.fill("input#phoneNumber", "")
                await page.keyboard.type(phone, delay=40)
        except Exception:
            pass
        await page.wait_for_timeout(500)

        # Single submit button labeled "אישור" (Angular handler bound after the
        # hydration wait above).
        await page.click("button:has-text('אישור')")

        # Snapshot the post-submit state regardless of success — first-run
        # evidence for the OTP page selectors.
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        post_submit = SCREENSHOT_ROOT / f"menora_login_{safe_user}_post_submit.png"
        await self._safe_screenshot(page, post_submit)
        await self._dump_page_state(page, post_submit)

        # Wait for the OTP screen. Menora's OTP field is six single-digit
        # <input id="otp-input-1..6" type="tel"> boxes (verified live
        # 2026-06-20) — match those FIRST; the broad fallbacks cover any future
        # redesign (MUI / one-time-code / common name= patterns).
        await self._wait_visible(
            page,
            (
                "input#otp-input-1, input[id^='otp-input'], "
                "input[autocomplete='one-time-code'], "
                "input[name='otp'], input[name='OTP'], "
                "input[name='VerificationCode'], input[name='code'], "
                "input[name='SmsCode'], input[name='sms'], "
                "input[name='verificationCode'], input[name='smsCode'], "
                "input[inputmode='numeric']:not(#phoneNumber), "
                "input.MuiInput-input:not(#username):not(#phoneNumber)"
            ),
            timeout=25000,
        )

    async def submit_otp(self, page: "Page", otp: str) -> None:
        # Menora's OTP form uses 6 separate single-digit Material-UI inputs:
        #   #otp-input-1 .. #otp-input-6
        # Submit button #submit-login-btn starts disabled until all 6 digits
        # are filled. Strip non-digits and fill char-by-char.
        digits = re.sub(r"\D", "", otp or "")
        if len(digits) < 6:
            raise RuntimeError(
                f"OTP חסר ספרות: צריך 6 ספרות, התקבלו {len(digits)}"
            )

        # Focus the first box, then type — Menora's component auto-advances
        # on each keystroke. Falling back to per-input fill if typing doesn't
        # progress (some MUI OTP inputs need explicit per-cell fill).
        try:
            await page.click("#otp-input-1", timeout=4000)
            await page.keyboard.type(digits[:6], delay=40)
        except Exception:
            pass

        # Verify each input got its digit; if not, fill explicitly.
        for i, ch in enumerate(digits[:6], start=1):
            try:
                val = await page.input_value(f"#otp-input-{i}", timeout=1000)
            except Exception:
                val = ""
            if val != ch:
                try:
                    await page.fill(f"#otp-input-{i}", ch, timeout=1500)
                except Exception:
                    pass

        # Wait for the submit button to become enabled. The OTP screen shows an
        # "אישור" button (type=button, disabled until all 6 digits present);
        # older builds id'd it #submit-login-btn. Match either.
        try:
            await page.wait_for_function(
                """() => {
                    const b = document.querySelector('#submit-login-btn')
                        || [...document.querySelectorAll('button')]
                             .find(x => (x.innerText || '').trim() === 'אישור');
                    return b && !b.disabled;
                }""",
                timeout=8000,
            )
        except Exception:
            pass

        # Click whichever submit control exists (id first, then the OTP-screen
        # "אישור" button — distinct from the "חזרה" back button).
        try:
            await page.click("#submit-login-btn", timeout=2000)
        except Exception:
            await page.click("button:has-text('אישור')", timeout=5000)

        # Wait for the real post-OTP navigation. Menora redirects to
        # /agents-site/ via APM. Critical: do NOT force a goto here — that
        # bypasses the APM session and lands on a BIG-IP error page.
        try:
            await page.wait_for_url(
                lambda u: "/agents-site" in (u or ""),
                timeout=25000,
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
        # Menora vault files are not password-protected.
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

        async def _click_step(
            label: str, selectors: list[str], timeout: int = 8000
        ) -> str | None:
            sel = await self._click_first_visible(page, selectors, timeout=timeout)
            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except Exception:
                pass
            await _checkpoint(f"nav_{label}")
            return sel

        # ── XHR fallback (some Menora endpoints stream via axios blob) ──
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
                        # Extract original filename from content-disposition
                        m = re.search(
                            r"filename\*?=(?:UTF-8'')?\"?([^\";\r\n]+)",
                            resp.headers.get("content-disposition") or "",
                            re.IGNORECASE,
                        )
                        if m:
                            xhr_capture["filename"] = m.group(1).strip()
            except Exception:
                pass

        # XHR listener attached to whichever page handle ends up running the
        # downloads. Tracked so we can detach in finally.
        listener_page = page
        page.on("response", _on_response)

        try:
            # ── Step 1: ensure we're on agents-site after OTP ──
            # Do NOT force-navigate (goto bypasses the F5 APM session). After OTP
            # the SPA redirects to /agents-site organically. BUT a stale/concurrent
            # F5 session (e.g. a prior run that didn't log out, or a retry) lands
            # on a "BIG-IP - Error Page" ("Access policy evaluation is already in
            # progress") whose only control is a "here" reset link. Click it to
            # drop the old session and let the authenticated session continue —
            # the same recovery the Harel plugin uses. Retry a few times.
            for _attempt in range(3):
                if "/agents-site" in page.url:
                    break
                reset = None
                for sel in (
                    "a:has-text('here')",
                    "a:has-text('לחץ כאן')",
                    "a:has-text('כאן')",
                    "a[href*='redirectURI']",
                ):
                    try:
                        loc = page.locator(sel).first
                        if await loc.count():
                            reset = loc
                            break
                    except Exception:
                        continue
                if reset is None:
                    break
                await _checkpoint(f"0_bigip_recovery_{_attempt}")
                try:
                    await reset.click(timeout=5000)
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    try:
                        await page.wait_for_url(
                            lambda u: "/agents-site" in (u or ""), timeout=15000
                        )
                    except Exception:
                        pass
                except Exception:
                    break

            if "/agents-site" not in page.url:
                await _checkpoint("0_not_on_agents_site")
                raise RuntimeError(
                    f"OTP submit לא ניווט ל-/agents-site/ — נשארנו על {page.url}. "
                    f"בדוק {run_id}_nav_0_not_on_agents_site.txt"
                )
            await _checkpoint("0_agents_site")

            # ── Step 2: open the כספות vault tile ──
            # The tile is a <div class="system-data"> wrapping a <span> with
            # the label. Click handlers are attached by React to the div,
            # not the span. Clicking the tile opens the vault in a new tab.
            kasafot_selectors = [
                'div.system-data:has(span:has-text("כספות - AgentFilesMaster"))',
                'div.system-data:has(span:has-text("AgentFilesMaster"))',
                '[data-mnr-bo^="systemName-"]:has(span:has-text("כספות"))',
                'div.system-data:has-text("כספות - AgentFilesMaster")',
                'span:has-text("כספות - AgentFilesMaster")',
                'span:has-text("AgentFilesMaster")',
            ]

            vault_page: "Page" = page  # may switch to popup
            try:
                async with page.context.expect_page(timeout=8000) as popup_info:
                    clicked_kasafot = await self._click_first_visible(
                        page, kasafot_selectors, timeout=12000
                    )
                vault_page = await popup_info.value
                await vault_page.wait_for_load_state(
                    "domcontentloaded", timeout=15000
                )
                _logger.info(
                    "Menora: vault opened in popup → %s", vault_page.url
                )
            except Exception:
                # No popup fired — either the vault renders inline or the
                # click missed. Either way, keep using the main page.
                clicked_kasafot = await self._click_first_visible(
                    page, kasafot_selectors, timeout=4000
                )

            if not clicked_kasafot:
                await _checkpoint("1_kasafot_no_match")
                raise RuntimeError(
                    f"לא נמצאה אריח 'כספות - AgentFilesMaster' ב-{page.url}. "
                    f"בדוק {run_id}_nav_1_kasafot_no_match.txt"
                )

            # Switch page reference for the rest of the flow and re-attach
            # the XHR listener so the popup's downloads are captured.
            if vault_page is not listener_page:
                try:
                    listener_page.remove_listener("response", _on_response)
                except Exception:
                    pass
                listener_page = vault_page
                vault_page.on("response", _on_response)
            page = vault_page
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            await _checkpoint("1_kasafot")

            # ── Step 3: discover vault rows via checkboxes ──
            # The vault uses #rowcheck0..N selectable rows with TWO global
            # download buttons: "הורד קבצים" (individual) and
            # "הורד קבצים מכווץ" (bundled ZIP). We tick the production rows
            # and click the bundled-ZIP button to fetch them in one go.
            for _ in range(12):
                cnt = await page.evaluate(
                    "() => document.querySelectorAll('input[type=\"checkbox\"][id^=\"rowcheck\"]').length"
                )
                if cnt:
                    break
                await asyncio.sleep(0.5)

            all_rows: list[dict] = await page.evaluate(
                """
                () => {
                    const out = [];
                    document.querySelectorAll('input[type="checkbox"][id^="rowcheck"]').forEach((cb) => {
                        const m = (cb.id || '').match(/rowcheck(\\d+)/);
                        if (!m) return;
                        const idx = parseInt(m[1], 10);
                        const row = cb.closest('tr') || cb.parentElement;
                        const label = (row?.innerText || row?.textContent || '')
                                        .trim()
                                        .replace(/\\s+/g, ' ');
                        out.push({ idx, id: cb.id, label });
                    });
                    return out;
                }
                """
            )

            # Skip rows whose filename column carries a commission marker:
            # rows 3+4 in the live vault are categorized "פרודוקציה מסווגת"
            # but the file is actually `דוח_עמלות_סוכן_...xlsx` (commission).
            def _is_production(label: str) -> bool:
                if "פרודוקציה" not in label:
                    return False
                hay = label.replace("_", " ")
                blocked = ("דוח עמלות", "עמלות סוכן", "דוח חודשי", "נפרעים")
                return not any(b in hay for b in blocked)

            wanted = [r for r in all_rows if _is_production(r["label"])]

            _logger.info(
                "Menora: %d total vault rows, %d match production filter",
                len(all_rows), len(wanted),
            )

            if not wanted:
                await _checkpoint("2_no_production_match")
                raise RuntimeError(
                    f"לא נמצאו שורות פרודוקציה בכספת מנורה ב-{page.url} "
                    f"({len(all_rows)} שורות סך הכל). "
                    f"בדוק {run_id}_nav_2_no_production_match.txt"
                )

            # ── Step 4: tick each wanted row's checkbox ──
            for r in wanted:
                try:
                    await page.check(f"#{r['id']}", timeout=4000)
                except Exception:
                    # Some checkboxes need a regular click (not .check) if
                    # they're controlled by React state
                    try:
                        await page.click(f"#{r['id']}", timeout=2500)
                    except Exception as e:
                        _logger.warning(
                            "Menora: failed to tick %s: %s", r["id"], e
                        )
            await _checkpoint("3_rows_checked")

            # ── Step 5: trigger the bundled-ZIP download ──
            # The "הורד קבצים מכווץ" button packages all selected rows into
            # one ZIP. Fallback to "הורד קבצים" (un-suffixed) if not present.
            xhr_capture.update({"bytes": None, "url": None, "filename": None})
            zip_button_selectors = [
                'button.button_DocTable:has-text("הורד קבצים מכווץ")',
                'button:has-text("הורד קבצים מכווץ")',
                'button.button_DocTable:has-text("הורד קבצים")',
                'button:has-text("הורד קבצים")',
            ]

            row_labels = " | ".join(r["label"][:40] for r in wanted[:4])
            slug = re.sub(r"[^\w]+", "_", row_labels)[:60].strip("_") or "files"
            fallback_out = download_dir / f"מנורה - חיים פרודוקציה ({slug}).zip"

            final_path: Path | None = None
            try:
                async with page.expect_download(timeout=90000) as dl_info:
                    sel = await self._click_first_visible(
                        page, zip_button_selectors, timeout=8000
                    )
                    if not sel:
                        raise RuntimeError("no-zip-button-visible")
                download = await dl_info.value
                suggested = (download.suggested_filename or "").strip()
                if suggested:
                    final_path = download_dir / suggested
                else:
                    final_path = fallback_out
                await download.save_as(str(final_path))
            except Exception as native_err:
                # XHR fallback — some Menora endpoints stream the zip via
                # axios blob rather than a navigation download.
                for _ in range(30):
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    suggested = (xhr_capture["filename"] or "").strip()
                    final_path = download_dir / (suggested or fallback_out.name)
                    final_path.write_bytes(xhr_capture["bytes"])
                else:
                    await _checkpoint("4_download_failed")
                    raise RuntimeError(
                        f"הורדה לא הופעלה בכספת מנורה ({page.url}). "
                        f"בדוק {run_id}_nav_4_download_failed.txt: {native_err}"
                    )

            await _checkpoint("4_downloaded")
            _logger.info(
                "Menora: bundled download → %s (%d bytes, %d rows selected)",
                final_path.name, final_path.stat().st_size, len(wanted),
            )

            # Rename to a Hebrew-labeled name if the server filename doesn't
            # carry a production marker — needed so detect_format routes the
            # file to production rather than the default Menora-commission.
            if "פרודוקציה" not in final_path.name and "ייצור" not in final_path.name:
                renamed = download_dir / f"מנורה - חיים פרודוקציה.zip"
                if renamed != final_path and not renamed.exists():
                    final_path.rename(renamed)
                    final_path = renamed

            # ── Step 6: ALSO grab the נפרעים report from the SAME open vault ──
            # One Menora login → both production AND נפרעים (the נפרעים row lives
            # in this very vault popup). If it fails, production is still
            # returned — partial success beats a dead run.
            results = [final_path]
            try:
                from app.services.portal_automation.companies.menora_nifraim import (
                    MenoraNifraimPortal,
                )
                nif_path = await MenoraNifraimPortal()._download_nifraim_row(
                    page, download_dir, run_id
                )
                results.append(nif_path)
                _logger.info("Menora: also downloaded נפרעים → %s", nif_path.name)
            except Exception as e:
                _logger.warning(
                    "Menora: נפרעים grab failed (production still returned): %s", e
                )
            return results
        finally:
            try:
                listener_page.remove_listener("response", _on_response)
            except Exception:
                pass


async def open_menora_vault(plugin, page: "Page", run_id: str) -> "Page":
    """Click the 'כספות - AgentFilesMaster' tile from /agents-site/ and return
    the vault page (a popup if one opened, else the same page). Shared by the
    standalone menora_nifraim run; the consolidated menora production run opens
    the vault inline and then reuses that same page for the נפרעים grab."""
    from app.services.portal_automation.runner import SCREENSHOT_ROOT, logger as _logger

    kasafot_selectors = [
        'div.system-data:has(span:has-text("כספות - AgentFilesMaster"))',
        'div.system-data:has(span:has-text("AgentFilesMaster"))',
        '[data-mnr-bo^="systemName-"]:has(span:has-text("כספות"))',
        'div.system-data:has-text("כספות - AgentFilesMaster")',
        'span:has-text("כספות - AgentFilesMaster")',
        'span:has-text("AgentFilesMaster")',
    ]
    vault_page: "Page" = page
    clicked = False
    try:
        async with page.context.expect_page(timeout=8000) as popup_info:
            clicked = await plugin._click_first_visible(page, kasafot_selectors, timeout=12000)
        vault_page = await popup_info.value
        await vault_page.wait_for_load_state("domcontentloaded", timeout=15000)
        _logger.info("Menora: vault opened in popup → %s", vault_page.url)
    except Exception:
        clicked = await plugin._click_first_visible(page, kasafot_selectors, timeout=4000)
    if not clicked:
        p = SCREENSHOT_ROOT / f"{run_id}_1_kasafot_no_match.png"
        await plugin._safe_screenshot(page, p)
        await plugin._dump_page_state(page, p)
        raise RuntimeError(
            f"לא נמצאה אריח 'כספות - AgentFilesMaster' ב-{page.url}. "
            f"בדוק {run_id}_1_kasafot_no_match.txt"
        )
    try:
        await vault_page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    p = SCREENSHOT_ROOT / f"{run_id}_1_kasafot.png"
    await plugin._safe_screenshot(vault_page, p)
    await plugin._dump_page_state(vault_page, p)
    return vault_page
