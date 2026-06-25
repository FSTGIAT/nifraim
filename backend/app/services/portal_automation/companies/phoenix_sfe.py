"""Phoenix SFE (הפניקס — כספת) file vault — login, download newest production .DAT.

Unlike the main `phoenix` plugin (agent.fnx.co.il, behind F5 APM + a native
PowerTerm terminal we can't drive), the SFE כספת at `sfe.fnx.co.il` is a plain
ExtJS file vault:

  - Direct form login, **no OTP** (`requires_otp = False`).
  - A greeting modal (password-reset notice) may pop up first → dismiss with OK.
  - It's a CyberArk SFE accordion: expand the **"Safes"** section, then click the
    **"Inbox"** tree node of the safe (e.g. `SFA_AGF44766 (Achzakot- Life)`). The
    file grid loads via AJAX only after Inbox is selected, listing one `.DAT` per
    reporting month (newest first).
  - Each grid row carries its own `services/DownloadFile.ashx?Data=<base64>` URL
    inside a hidden JSON cell. We pick the newest by the YYYYMMDD embedded in the
    filename (locale-proof; the display date column renders per session locale).

The downloaded `.DAT` is standard Israeli Mimshak holdings XML (the same
"מבנה אחיד" format the Migdal Mimshak path already parses), so the runner ingests
it as a production file with no new parsing logic (see `mimshak.parse_mimshak_dat`).

NOTE: ExtJS assigns volatile `ext-genNN` ids per session — never hardcode them.
We key off stable class names (`.x-tool-toggle`, `.x-grid3-row`,
`.x-grid3-td-columnN`) and the `file_download.gif` icon src instead.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

SFE_BASE = "https://sfe.fnx.co.il/SFE/"
SFE_URL = "https://sfe.fnx.co.il/SFE/Logon.aspx?ReturnUrl=%2fSFE%2ffiles.aspx"


class PhoenixSfePortal(BasePortalAutomation):
    portal_kind = "phoenix_sfe"
    company_label = "הפניקס — כספת"
    requires_otp = False
    # Folded into the consolidated `phoenix_nifraim` plugin, which (after its
    # agentportal OTP login) opens this no-OTP SFE vault with the same creds to
    # grab production. Still runnable as a manual single run.
    include_in_batch = False

    async def _dismiss_greeting(self, page: "Page") -> None:
        """Close the optional ExtJS greeting/password-reset modal (OK button)."""
        await self._click_first_visible(
            page,
            [
                "button.x-btn-text:has-text('OK')",
                "button:has-text('OK')",
                "button:has-text('אישור')",
            ],
            timeout=3000,
        )

    async def login(self, page: "Page", username: str, password: str) -> None:
        await page.goto(SFE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1500)
        await self._dismiss_greeting(page)

        # Resilient field selectors — SFE's ExtJS login form field names aren't
        # documented; try common ones, then fall back to the first text/password
        # inputs on the page.
        filled_user = False
        for sel in (
            "input[name='username']",
            "input[name='Username']",
            "input[name='txtUsername']",
            "input#username",
            "input[type='text']:visible",
        ):
            try:
                await page.fill(sel, username, timeout=2500)
                filled_user = True
                break
            except Exception:
                continue
        if not filled_user:
            raise RuntimeError("SFE login: could not locate the username field")

        for sel in ("input[type='password']", "input[name='password']", "input#password"):
            try:
                await page.fill(sel, password, timeout=2500)
                break
            except Exception:
                continue

        # Submit — try a login button, else press Enter in the password field.
        clicked = await self._click_first_visible(
            page,
            [
                "button:has-text('כניסה')",
                "button:has-text('התחבר')",
                "input[type='submit']",
                "button[type='submit']",
                "a:has-text('כניסה')",
            ],
            timeout=4000,
        )
        if not clicked:
            try:
                await page.press("input[type='password']", "Enter")
            except Exception:
                pass

        # Land on the files vault. Dismiss the greeting again (it sometimes
        # renders only after auth) and wait for the grid.
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        await self._dismiss_greeting(page)

    async def submit_otp(self, page: "Page", otp: str) -> None:  # pragma: no cover
        raise NotImplementedError("Phoenix SFE vault has no OTP step")

    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
    ) -> list[Path]:
        self.report_password = None
        download_dir.mkdir(parents=True, exist_ok=True)

        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name

        async def _checkpoint(stem: str) -> None:
            p = SCREENSHOT_ROOT / f"{run_id}_{stem}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        await self._dismiss_greeting(page)
        await _checkpoint("sfe_login")

        # Navigate the CyberArk SFE accordion: expand "Safes", then real-click the
        # "Inbox" tree node (where Phoenix drops production files). Files load via
        # AJAX into the grid only after Inbox is selected. ExtJS tree nodes need a
        # genuine mouse click — a synthetic el.click() won't fire the handler — so
        # use Playwright clicks throughout.
        await self._click_first_visible(
            page,
            [
                "span.x-panel-header-text:has-text('Safes')",
                ".x-accordion-hd:has-text('Safes')",
            ],
            timeout=6000,
        )
        await page.wait_for_timeout(1500)
        clicked_inbox = await self._click_first_visible(
            page,
            ["a.x-tree-node-anchor:has-text('Inbox')"],
            timeout=8000,
        )
        if not clicked_inbox:
            await _checkpoint("sfe_no_inbox")
            raise RuntimeError("SFE vault: Inbox node not found (see *_sfe_no_inbox artifacts)")

        try:
            await page.wait_for_function(
                "() => document.querySelectorAll('.x-grid3-row').length > 0",
                timeout=15000,
            )
        except Exception:
            await _checkpoint("sfe_no_grid")
            raise RuntimeError("SFE vault: file grid never populated (see *_sfe_no_grid artifacts)")
        await page.wait_for_timeout(1200)
        await _checkpoint("sfe_grid")

        # Read every row: name + date column (display only) + the per-row download
        # URL. The JSON cell index isn't stable, so scan each row's spans for the
        # one carrying "DownloadFileURL" rather than keying on a column class.
        rows = await page.evaluate(
            """() => {
                const out = [];
                document.querySelectorAll('.x-grid3-row').forEach((tr, idx) => {
                    let name = null, url = null, dateText = null;
                    for (const sp of tr.querySelectorAll('span')) {
                        const t = sp.textContent || '';
                        if (t.includes('DownloadFileURL')) {
                            try { const m = JSON.parse(t); name = m.Name || null; url = m.DownloadFileURL || null; } catch (e) {}
                        }
                    }
                    const d = tr.querySelector('.x-grid3-td-column5');
                    if (d) dateText = d.textContent.trim();
                    out.push({ idx, name, url, dateText });
                });
                return out;
            }"""
        )

        def _file_date_key(name: str | None) -> str:
            # The reporting date is embedded in the filename as YYYYMMDD right
            # after the HOLDNG marker + 3-digit version (locale-proof, unlike the
            # display column which renders DD/MM/YYYY or M/D/YYYY by session locale):
            #   201000520023185 HOLDNGING 009 20260517 1633570567 .DAT
            m = re.search(r"HOLDNG[A-Z]*\d{3}(\d{8})", name or "")
            return m.group(1) if m else ""

        dat_rows = [
            r for r in rows
            if r.get("name") and str(r["name"]).lower().endswith(".dat") and r.get("url")
        ]
        if not dat_rows:
            await _checkpoint("sfe_no_dat")
            raise RuntimeError(
                f"SFE vault: no .DAT rows found among {len(rows)} grid rows "
                "(see *_sfe_no_dat artifacts)"
            )

        # Newest = max embedded filename date; tie-break to the topmost grid row
        # (the grid is sorted newest-first, so -idx keeps idx 0 on ties / no-date).
        chosen = max(dat_rows, key=lambda r: (_file_date_key(r["name"]), -r["idx"]))
        logger.info(
            "phoenix_sfe: %d .DAT row(s); picking newest '%s' (shown %s)",
            len(dat_rows), chosen["name"], chosen.get("dateText"),
        )

        out = download_dir / chosen["name"]
        abs_url = SFE_BASE + str(chosen["url"]).lstrip("/")

        # Migdal/Harel-style capture: XHR listener first, native expect_download
        # on the row's download icon, then a direct authenticated GET fallback.
        xhr_capture: dict = {"bytes": None}

        async def _on_response(resp):
            try:
                url = resp.url.lower()
                if "downloadfile.ashx" in url and xhr_capture["bytes"] is None:
                    body = await resp.body()
                    if body and len(body) > 256:
                        xhr_capture["bytes"] = body
            except Exception:
                pass

        page.on("response", _on_response)
        try:
            icon = page.locator(".x-grid3-row").nth(chosen["idx"]).locator(
                "img[src*='file_download.gif']"
            )
            try:
                async with page.expect_download(timeout=45000) as dl_info:
                    await icon.click(timeout=8000)
                download = await dl_info.value
                await download.save_as(str(out))
            except Exception as native_err:
                logger.warning("phoenix_sfe: native download failed (%s); trying fallbacks", native_err)
                for _ in range(20):
                    if xhr_capture["bytes"]:
                        break
                    await asyncio.sleep(0.5)
                if xhr_capture["bytes"]:
                    out.write_bytes(xhr_capture["bytes"])
                else:
                    resp = await page.request.get(abs_url)
                    body = await resp.body()
                    if not body or len(body) < 256:
                        await _checkpoint("sfe_dl_fail")
                        raise RuntimeError(
                            f"SFE download failed for {chosen['name']}: native error {native_err}, "
                            f"GET {resp.status}, {len(body or b'')} bytes"
                        )
                    out.write_bytes(body)
        finally:
            page.remove_listener("response", _on_response)

        await _checkpoint("sfe_done")
        logger.info("phoenix_sfe: saved %s (%d bytes)", out.name, out.stat().st_size)
        return [out]
