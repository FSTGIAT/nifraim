"""Abstract base for per-portal automation plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from playwright.async_api import Page

# An async callable the runner passes into download_reports so a plugin can
# request a SECOND SMS OTP mid-download (for companies whose production and
# נפרעים reports sit behind two different logins, e.g. Migdal mfte + apmaccess).
# Awaiting it flips the run back to `awaiting_otp`, waits for a fresh
# company-routed code, and returns it.
OtpProvider = Callable[[], Awaitable[str]]


class BasePortalAutomation(ABC):
    """One subclass per insurance portal.

    Subclasses implement the three abstract methods. The runner orchestrates:
        login → (await OTP from otp_inbox) → submit_otp → download_reports.

    Plugins that download password-protected Excel files (e.g. Phoenix) should
    set `report_password` after `download_reports`; the runner forwards it to
    `parse_excel(..., password=report_password)` so msoffcrypto can decrypt.
    """

    portal_kind: str = ""
    company_label: str = ""  # Hebrew display name
    report_password: str | None = None
    # Set to False by plugins whose portal doesn't have a 2FA step (e.g. the
    # Harel safe vault — accessed via direct ASP.NET form login). The runner
    # checks this flag and skips the otp_inbox poll + submit_otp call.
    requires_otp: bool = True
    # Set to False to exclude a portal from the "run all" batch (still runnable
    # as a single manual run). Used for dead-end portals that can't auto-download
    # (e.g. the Phoenix Ericom terminal) and for sub-reports that another portal
    # already downloads in one login (e.g. phoenix_nifraim_gemel, folded into
    # phoenix_nifraim). Keeps the batch from burning an OTP on a guaranteed fail.
    include_in_batch: bool = True
    # Israeli insurer WAFs geo/datacenter-block non-IL IPs: from Railway's
    # foreign datacenter IP, harel/menora/phoenix hang at the first page.goto
    # (30s timeout) while the same domains answer in <250ms from a local IL IP.
    # When True AND settings.IL_RESIDENTIAL_PROXY is configured, the runner
    # routes this portal's browser context through the IL residential proxy.
    # Default True (most IL insurers block); Migdal opts out (works direct).
    # No proxy env set → runner falls back to a direct connection, so this flag
    # is a no-op until a proxy is provisioned. See memory
    # `railway_ip_geoblocked_insurers`.
    needs_residential_proxy: bool = True

    @abstractmethod
    async def login(self, page: "Page", username: str, password: str) -> None:
        """Navigate to the portal and submit username + password.

        Should leave the page on the OTP-entry screen.
        """

    @abstractmethod
    async def submit_otp(self, page: "Page", otp: str) -> None:
        """Type the SMS OTP into the form and submit.

        Should leave the page on a logged-in state from which `download_reports`
        can navigate.
        """

    @abstractmethod
    async def download_reports(
        self,
        page: "Page",
        download_dir: Path,
        *,
        username: str | None = None,
        otp_provider: "OtpProvider | None" = None,
    ) -> list[Path]:
        """Navigate to the reports section and download every relevant file.

        ``username`` is forwarded so plugins can build precise selectors when a
        portal labels files by agent (e.g. Migdal Safes System uses
        ``{USERNAME}_FROMMIGDAL_*`` filenames). Plugins are free to ignore it.

        ``otp_provider`` (optional) lets a plugin obtain a SECOND OTP after a
        second login inside download_reports — `otp = await otp_provider()`.
        Only multi-login consolidated plugins (e.g. Migdal mfte+apmaccess) use
        it; everyone else ignores it. The runner passes None when there's no
        OTP context (e.g. the no-OTP SFE vault).

        Returns the list of saved file paths (under `download_dir`).
        """

    # ------ Optional: contact-phone migration (one-time per agent at signup) ------

    async def change_contact_phone(self, page: "Page", new_phone: str) -> None:
        """After a successful login, navigate to account settings and submit
        a contact phone change to `new_phone`. Should leave the page on a state
        where the OLD phone OTP is awaited (the runner pulls from otp_inbox)."""
        raise NotImplementedError(
            f"change_contact_phone not implemented for '{self.portal_kind}'"
        )

    async def confirm_contact_phone_change(self, page: "Page", otp: str) -> None:
        """Submit the OTP that came to the OLD phone, completing the change."""
        raise NotImplementedError(
            f"confirm_contact_phone_change not implemented for '{self.portal_kind}'"
        )

    # ------ Shared helpers (subclasses may override or compose) ------

    async def _wait_visible(self, page: "Page", selector: str, timeout: int = 15000) -> None:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)

    async def _click_first_visible(
        self, page: "Page", selectors: list[str], timeout: int = 20000
    ) -> str | None:
        """Try each selector in order; click the first that becomes visible.

        Returns the matched selector, or None if none became visible within
        ``timeout`` total. Avoids the default 30s timeout per selector that
        Playwright would otherwise apply when given an `or` list of misses.
        """
        import asyncio
        deadline = asyncio.get_event_loop().time() + (timeout / 1000)
        for sel in selectors:
            remaining_ms = max(500, int((deadline - asyncio.get_event_loop().time()) * 1000))
            try:
                await page.wait_for_selector(sel, state="visible", timeout=min(2500, remaining_ms))
            except Exception:
                continue
            try:
                await page.click(sel, timeout=5000)
                return sel
            except Exception:
                continue
        return None

    async def _safe_screenshot(self, page: "Page", path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(path), full_page=True)
        except Exception:
            # Never let screenshot failure mask the original error
            pass

    async def _dump_page_state(self, page: "Page", base_path: Path) -> None:
        """Save the page HTML + a human-readable list of visible links/buttons
        alongside the screenshot. Used to diagnose selector mismatches when
        post-login navigation fails without re-running.

        Writes two files at the same stem as ``base_path``:
            <stem>.html — full DOM
            <stem>.txt  — current URL, title, and visible interactive elements
        """
        try:
            base_path.parent.mkdir(parents=True, exist_ok=True)
            stem = base_path.with_suffix("")
            html = await page.content()
            stem.with_suffix(".html").write_text(html, encoding="utf-8")

            url = page.url
            try:
                title = await page.title()
            except Exception:
                title = ""

            interactive = await page.evaluate(
                """() => {
                    const out = [];
                    for (const el of document.querySelectorAll('a, button, [role="link"], [role="button"]')) {
                        const r = el.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) continue;
                        const txt = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                        if (!txt) continue;
                        out.push(`${el.tagName.toLowerCase()}: ${txt.slice(0, 120)}`);
                    }
                    return out;
                }"""
            )

            lines = [f"URL: {url}", f"TITLE: {title}", "", "VISIBLE INTERACTIVE ELEMENTS:"]
            lines.extend(interactive[:200])
            stem.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            # Diagnostics must never raise — the original error is what matters
            pass

    async def _dump_all_frames(self, page: "Page", base_path: Path) -> None:
        """Like `_dump_page_state`, but dumps EVERY frame (top + nested
        iframes), not just the top document.

        Legacy terminal emulators (Phoenix's "מסוף", Ericom/Flynet/OpenText)
        live inside an iframe — sometimes nested several levels deep — or paint
        to a `<canvas>`. `page.content()` only returns the top document, so the
        terminal screen is invisible to `_dump_page_state`. This helper walks
        `page.frames` and, per frame, writes:

            <stem>__frameNN.html — that frame's full DOM
            <stem>__frameNN.txt  — url/name, the <iframe> element's id/src, and
                                    a dump of canvas/pre/table/input/text nodes

        plus a `<stem>__elements.txt` on the top doc enumerating every
        iframe/canvas/object/embed (the canvas tell-tale for "this is a pixel
        terminal we can't scrape"). Never raises.
        """
        try:
            base_path.parent.mkdir(parents=True, exist_ok=True)
            stem = base_path.with_suffix("")
            await self._safe_screenshot(page, base_path)

            # Top-document embedded-object inventory — answers "what is the terminal".
            try:
                inventory = await page.evaluate(
                    """() => {
                        const vw = window.innerWidth, vh = window.innerHeight;
                        const out = [];
                        for (const el of document.querySelectorAll('iframe, canvas, object, embed, applet')) {
                            const r = el.getBoundingClientRect();
                            const big = r.width >= vw * 0.5 && r.height >= vh * 0.4;
                            out.push(
                                `${el.tagName.toLowerCase()}`
                                + ` id=${el.id || '-'}`
                                + ` name=${el.getAttribute('name') || '-'}`
                                + ` src=${el.getAttribute('src') || el.getAttribute('data') || '-'}`
                                + ` size=${Math.round(r.width)}x${Math.round(r.height)}`
                                + (big ? ' [VIEWPORT-SIZED]' : '')
                            );
                        }
                        return {viewport: `${vw}x${vh}`, items: out};
                    }"""
                )
            except Exception:
                inventory = {"viewport": "?", "items": []}

            inv_lines = [
                f"URL: {page.url}",
                f"VIEWPORT: {inventory.get('viewport')}",
                f"FRAME COUNT: {len(page.frames)}",
                "",
                "EMBEDDED OBJECTS (iframe/canvas/object/embed/applet):",
            ]
            inv_lines.extend(inventory.get("items") or ["(none)"])
            stem.with_name(stem.name + "__elements").with_suffix(".txt").write_text(
                "\n".join(inv_lines), encoding="utf-8"
            )

            # Per-frame DOM + content dump.
            for idx, frame in enumerate(page.frames):
                fstem = stem.with_name(f"{stem.name}__frame{idx:02d}")
                try:
                    html = await frame.content()
                    fstem.with_suffix(".html").write_text(html, encoding="utf-8")
                except Exception:
                    html = ""

                try:
                    el = await frame.frame_element()
                    el_tag = await el.evaluate(
                        "e => `${e.tagName.toLowerCase()} id=${e.id||'-'} name=${e.getAttribute('name')||'-'} src=${e.getAttribute('src')||'-'}`"
                    )
                except Exception:
                    el_tag = "(top frame or detached)"

                try:
                    nodes = await frame.evaluate(
                        """() => {
                            const out = [];
                            for (const el of document.querySelectorAll('canvas, pre, table, input, textarea, [class*="term"], [class*="screen"], [id*="term"], [id*="screen"]')) {
                                const r = el.getBoundingClientRect();
                                const txt = (el.innerText || el.value || el.textContent || '').trim().replace(/\\s+/g, ' ');
                                out.push(`${el.tagName.toLowerCase()} id=${el.id||'-'} class=${(el.className||'').toString().slice(0,60)} size=${Math.round(r.width)}x${Math.round(r.height)} text="${txt.slice(0,300)}"`);
                            }
                            return out;
                        }"""
                    )
                except Exception:
                    nodes = []

                flines = [
                    f"FRAME {idx}",
                    f"URL: {frame.url}",
                    f"NAME: {frame.name}",
                    f"ELEMENT: {el_tag}",
                    f"HTML_LEN: {len(html)}",
                    "",
                    "TERMINAL-CANDIDATE NODES (canvas/pre/table/input/term/screen):",
                ]
                flines.extend(nodes[:120] or ["(none)"])
                fstem.with_suffix(".txt").write_text("\n".join(flines), encoding="utf-8")
        except Exception:
            # Diagnostics must never raise — the original error is what matters
            pass

    async def _expect_download(self, page: "Page", trigger_coro, save_to: Path) -> Path:
        """Helper: run `trigger_coro` (which clicks the download button) inside
        `expect_download`, then save the resulting file to `save_to`."""
        async with page.expect_download() as dl_info:
            await trigger_coro
        download = await dl_info.value
        save_to.parent.mkdir(parents=True, exist_ok=True)
        await download.save_as(str(save_to))
        return save_to
