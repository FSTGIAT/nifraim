"""Probe the Phoenix PowerTerm WebConnect terminal tab for AccessNow (HTML5).

PowerTerm WebConnect can serve a terminal two ways:
  - native client (AccessPad): localStorage/title handshake -> a local .exe
  - AccessNow (HTML5): renders to a <canvas> in-browser, streaming the host
    screen over a WebSocket to the WebConnect server.

The native handshake fires when a client is installed; on a clean machine the
loader often falls back to AccessNow. This probe drives login -> OTP -> nav ->
התחבר, then watches the terminal tab for ~25s: WebSocket opens, canvas
appearance, "install client" prompts, and grabs HostViewLoader.js. The output
tells us whether Phoenix's WebConnect can run AccessNow (browser-automatable)
or is native-only.

Usage (from backend/, venv active):
    python scripts/phoenix_accessnow_probe.py 040336281 'Hruakho!2026'
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portal_automation.companies.phoenix import PhoenixPortal  # noqa: E402
from app.services.portal_automation.runner import SCREENSHOT_ROOT  # noqa: E402

OUT = SCREENSHOT_ROOT / "phoenix_accessnow"


async def main(username: str, password: str) -> None:
    from playwright.async_api import async_playwright

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plugin = PhoenixPortal()
    ws_urls: list[str] = []
    js_sources: dict[str, str] = {}

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(
                channel="chrome", headless=False,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
        context = await browser.new_context(
            accept_downloads=True, locale="he-IL",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-platform": '"Windows"', "sec-ch-ua-mobile": "?0",
            },
        )
        await context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = await context.new_page()
        try:
            print(">> login…")
            await plugin.login(page, username, password)
            print(">> TYPE THE OTP IN THE WINDOW now…")
            await page.wait_for_selector(
                "img[src*='my-systems'], [style*='my-systems']",
                state="visible", timeout=240000,
            )
            print(">> logged in. Navigating my-systems → ביטוח חיים → התחבר…")

            await page.wait_for_timeout(1500)
            await page.locator("img[src*='my-systems.svg']").first.click()
            await page.wait_for_timeout(1500)
            life = page.locator("button[role='menuitem']:has-text('ביטוח חיים')").first
            await life.hover()
            await page.wait_for_timeout(600)
            await life.click()
            await page.wait_for_timeout(1200)

            async with context.expect_page(timeout=20000) as np:
                await page.locator(
                    "button.btn-primary-sm:has-text('התחבר'), "
                    "button:has-text('התחבר'):not(:has-text('מחדש'))"
                ).first.click()
            term = await np.value
            print(f">> terminal tab: {term.url}")

            # Attach listeners on the terminal tab.
            def _on_ws(ws):
                ws_urls.append(ws.url)
                print(f"   [WebSocket] {ws.url}")

            term.on("websocket", _on_ws)

            async def _on_resp(resp):
                u = resp.url
                if u.endswith(".js") and ("HostView" in u or "AccessNow" in u or "WebConnect" in u):
                    try:
                        js_sources[u] = await resp.text()
                    except Exception:
                        pass

            term.on("response", _on_resp)

            # Poll the terminal tab for ~25s, looking for AccessNow signatures.
            print(">> watching terminal tab for AccessNow (canvas/WebSocket)…")
            report = []
            for t in range(6):
                await term.wait_for_timeout(4000)
                try:
                    info = await term.evaluate(
                        """() => ({
                            canvases: [...document.querySelectorAll('canvas')].map(c => {
                                const r = c.getBoundingClientRect();
                                return Math.round(r.width)+'x'+Math.round(r.height);
                            }),
                            bodyText: (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,400),
                            objects: document.querySelectorAll('object,embed,applet').length,
                            iframes: document.querySelectorAll('iframe').length,
                            globals: {
                                AccessNow: typeof window.AccessNow !== 'undefined',
                                ptStartConnection: typeof window.ptStartConnection !== 'undefined',
                                Ericom: typeof window.Ericom !== 'undefined',
                                ssl: typeof window.SSLAgent !== 'undefined' || typeof window.sslAgent !== 'undefined',
                            },
                        })"""
                    )
                except Exception as e:
                    info = {"error": str(e)}
                line = f"[{(t+1)*4}s] canvas={info.get('canvases')} obj={info.get('objects')} iframe={info.get('iframes')} globals={info.get('globals')}"
                print("   " + line)
                report.append(line)
                report.append(f"      bodyText: {info.get('bodyText','')[:200]}")
                await plugin._dump_all_frames(term, OUT.parent / f"phoenix_accessnow_t{t}.png")

            # Write findings.
            ws_lines = [f"  {u}" for u in ws_urls] or ["  (none — no AccessNow stream)"]
            findings = [
                f"TERMINAL URL: {term.url}",
                "",
                f"WEBSOCKETS ({len(ws_urls)}):",
                *ws_lines,
                "",
                "TIMELINE:",
                *report,
                "",
                f"JS FILES CAPTURED: {list(js_sources.keys())}",
            ]
            (OUT.parent / "phoenix_accessnow_findings.txt").write_text(
                "\n".join(findings), encoding="utf-8"
            )
            for u, src in js_sources.items():
                name = u.rsplit("/", 1)[-1].split("?")[0]
                (OUT.parent / f"phoenix_accessnow_{name}").write_text(src, encoding="utf-8")
            print("\n==== FINDINGS WRITTEN ====")
            print(f"  {OUT.parent}/phoenix_accessnow_findings.txt")
            print(f"  WebSockets seen: {len(ws_urls)} | JS captured: {len(js_sources)}")
            print(">> holding 10s…")
            await term.wait_for_timeout(10000)
        finally:
            try:
                await context.close(); await browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python scripts/phoenix_accessnow_probe.py <username> <password>")
        raise SystemExit(2)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
