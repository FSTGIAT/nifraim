r"""Phoenix browser automation — WINDOWS side, opens PowerTerm end-to-end, HANDS-FREE OTP.

Runs on Windows Python with Playwright driving real Microsoft Edge (channel
"msedge"), because the native PowerTerm client only launches from a Windows
browser (the WSL/Linux browser just offers a download). Flow:

  URL -> F5 errorcode recovery -> fill ID + password
      -> [OTP pulled hands-free from the backend's phone-forward chain]
      -> my-systems -> ביטוח חיים -> התחבר  -> PowerTerm terminal opens.

The OTP is NOT typed by hand: after the creds are submitted (which triggers the
SMS), this polls the backend `next-otp` endpoint (token-authed) which returns the
forwarded code from `otp_inbox`. The terminal opens in its own window and stays
open; the elevated `phoenix_win_terminal.py export14` then drives option 14.

Run (Windows Python):
    /mnt/c/Python313/python.exe scripts/windows/phoenix_browser_win.py \
        <username> <password> <phone_forward_token> [backend_base]
backend_base defaults to http://127.0.0.1:8000
"""

import sys
import json
import time
import asyncio
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

URL = "https://agent.fnx.co.il/my.policy"


def fetch_otp(base, token, company, after_iso, timeout_s=300):
    """Poll the backend for a hands-free, company-routed OTP (consumed on return)."""
    deadline = time.time() + timeout_s
    qs = urllib.parse.urlencode({"company": company, "after": after_iso})
    url = f"{base}/api/portal-automation/phone-forward/{token}/next-otp?{qs}"
    print(f">> waiting for forwarded OTP (poll {url}) …")
    while time.time() < deadline:
        try:
            data = json.loads(urllib.request.urlopen(url, timeout=8).read())
            if data.get("otp"):
                print(f">> got OTP {data['otp']} (company={data.get('company')})")
                return data["otp"]
        except Exception:
            pass
        time.sleep(2)
    return None


def _dbg_dir():
    """Where failure screenshots land — default the USER'S Downloads so a
    non-technical agent can find/share them, not a folder buried in the bundle."""
    import os
    from pathlib import Path
    d = os.environ.get("PHOENIX_DEBUG_DIR")
    if d:
        return d
    up = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    dl = str(Path(up) / "Downloads") if up else ""
    return dl if dl and os.path.isdir(dl) else os.getcwd()


async def _shot(page, name):
    """Save a failure screenshot + a short HTML dump next to it. Best-effort."""
    import os
    try:
        base = os.path.join(_dbg_dir(), f"phoenix_login_{name}")
        await page.screenshot(path=base + ".png", full_page=False)
        try:
            html = await page.content()
            open(base + ".html", "w", encoding="utf-8").write(html[:200000])
        except Exception:
            pass
        print(f">> saved failure capture: {base}.png  (url={page.url})", flush=True)
    except Exception as e:
        print(f">> screenshot failed: {e}", flush=True)


def _session_file():
    """Per-worker path of the session phoenix_nifraim saved (PHOENIX_SESSION_FILE
    override; default <install-root>/data/phoenix_session.json). Same base both
    sides resolve to — no hardcoded user dir."""
    import os
    from pathlib import Path
    return os.environ.get("PHOENIX_SESSION_FILE") or str(
        Path(__file__).resolve().parents[3] / "data" / "phoenix_session.json"
    )


async def _load_shared_phoenix_session(ctx):
    """Inject the Phoenix F5 cookies phoenix_nifraim saved this batch so we land
    already-authenticated (F5 one-session-per-user: we can't get our own OTP
    while nifraim's session is live). Only fnx.co.il cookies, only if fresh
    (<6h). Best-effort — a miss just falls through to the normal login."""
    import os, json, time
    sf = _session_file()
    try:
        if not os.path.exists(sf):
            print(">> no saved Phoenix session yet (nifraim runs first in run-all)", flush=True)
            return
        age_h = (time.time() - os.path.getmtime(sf)) / 3600
        if age_h > 6:
            print(f">> saved Phoenix session is {age_h:.1f}h old (>6h) — ignoring", flush=True)
            return
        state = json.load(open(sf, encoding="utf-8"))
        cookies = [c for c in state.get("cookies", []) if "fnx.co.il" in (c.get("domain") or "")]
        if cookies:
            await ctx.add_cookies(cookies)
            print(f">> loaded {len(cookies)} Phoenix cookies from nifraim's session "
                  f"({age_h:.1f}h old) — expecting NO OTP", flush=True)
    except Exception as e:
        print(f">> shared-session load skipped: {e}", flush=True)


def _profile_dir():
    """Per-worker Edge profile dir (no hardcoded user path). A PERSISTENT profile
    keeps Phoenix's F5 session cookie across runs, so in the run-all batch — where
    phoenix_nifraim already consumed the ONE Phoenix OTP seconds earlier — this
    run reuses the warm session and needs NO second OTP (the QA-confirmed way
    royg's runs stay logged in). Override with PHOENIX_EDGE_PROFILE."""
    import os
    from pathlib import Path
    env = os.environ.get("PHOENIX_EDGE_PROFILE", "").strip()
    if env:
        return env
    # …/backend/scripts/windows/this.py → install root is parents[3].
    root = Path(__file__).resolve().parents[3]
    return str(root / "data" / "phoenix_edge_profile")


def _kill_stale_automation_edge(profile: str) -> None:
    """Kill ONLY a prior automation-Edge that still holds OUR profile dir (matched
    by command line), never the user's own Edge. A leftover Edge locking the
    persistent profile makes the next launch hang (the documented relaunch race)."""
    try:
        import subprocess
        # PowerShell: match msedge processes whose CommandLine contains our profile.
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
            "Where-Object { $_.CommandLine -like '*" + profile.replace("\\", "\\\\") + "*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=20)
    except Exception as e:
        print(f">> stale-edge cleanup skipped: {e}", flush=True)


async def main(username, password, token, base):
    from playwright.async_api import async_playwright
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    page = None
    profile = _profile_dir()
    print(f">> [start] launching Edge (persistent profile: {profile})…", flush=True)
    _kill_stale_automation_edge(profile)
    import os as _os
    _os.makedirs(profile, exist_ok=True)
    async with async_playwright() as pw:
        launch_kw = dict(user_data_dir=profile, headless=False, no_viewport=True,
                         locale="he-IL", args=["--start-maximized"])
        try:
            ctx = await pw.chromium.launch_persistent_context(channel="msedge", **launch_kw)
        except Exception as e:
            # msedge channel needs Microsoft Edge installed; fall back to bundled
            # Chromium (also persistent, same profile) rather than dying opaquely.
            print(f"!! Edge (msedge) persistent launch failed: {e}; falling back to Chromium", flush=True)
            ctx = await pw.chromium.launch_persistent_context(**launch_kw)
        print(">> [edge launched persistent]…", flush=True)
        await _load_shared_phoenix_session(ctx)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            await _run_login_flow(page, username, password, token, base)
        except SystemExit:
            raise
        except Exception as e:
            import traceback
            print(f"!! login failed at step '{_CUR_STEP[0]}': {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            await _shot(page, _CUR_STEP[0])
            try:
                await ctx.close()
            except Exception:
                pass
            raise SystemExit(1)


# Module-level current-step marker so the outer handler can name the failure.
_CUR_STEP = ["launch-edge"]


async def _run_login_flow(page, username, password, token, base):
    def _step(s):
        _CUR_STEP[0] = s
        print(f">> [step] {s}", flush=True)

    _step("open-portal")
    print(">> opening portal…", flush=True)
    await page.goto(URL, wait_until="domcontentloaded", timeout=40000)
    await page.wait_for_timeout(2000)

    # ── Warm-session short-circuit ──────────────────────────────────────────
    # With the persistent profile, the F5 cookie usually survives. If we're
    # already authenticated (my-systems visible, no login form), SKIP the whole
    # login+OTP — this is what lets the run-all batch work: phoenix_nifraim
    # already consumed Phoenix's single OTP, and F5 won't issue a second one.
    _step("check-session")
    await page.wait_for_timeout(1500)
    logged_in = False
    try:
        ms = page.locator("img[src*='my-systems.svg'], img[src*='my-systems']")
        await ms.first.wait_for(state="visible", timeout=8000)
        logged_in = True
    except Exception:
        logged_in = False

    if logged_in:
        print(">> already authenticated (warm Phoenix session) — skipping login+OTP", flush=True)
    else:
        _step("errorcode-recovery")
        for _ in range(4):
            if "errorcode" not in page.url and "logout" not in page.url:
                break
            for sel in ("a:has-text('התחבר מחדש')", "a:has-text('חזרה למסך הכניסה')",
                        "a:has-text('לחץ כאן')"):
                try:
                    await page.click(sel, timeout=4000); break
                except Exception:
                    continue
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)

        _step("fill-credentials")
        print(">> filling ID + password…")
        try:
            await page.wait_for_selector("input[name='username']", state="visible", timeout=25000)
        except Exception:
            # One more errorcode-recovery pass, then retry — F5 sometimes lands the
            # login form a beat late or re-bounces on a busy session.
            for sel in ("a:has-text('התחבר מחדש')", "a:has-text('לחץ כאן')"):
                try:
                    await page.click(sel, timeout=3000); break
                except Exception:
                    continue
            await page.wait_for_timeout(2500)
            await page.wait_for_selector("input[name='username']", state="visible", timeout=20000)
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        # Capture the timestamp BEFORE submit — submit triggers the SMS, so the
        # OTP row will have received_at >= this. BACKDATE by 15s to absorb clock
        # skew between this machine and the (Railway) server.
        after_iso = (datetime.utcnow() - timedelta(seconds=15)).isoformat()
        _step("submit-credentials")
        for sel in ("input[type='submit']", "button:has-text('כניסה')", "button:has-text('המשך')"):
            try:
                await page.click(sel, timeout=2500); break
            except Exception:
                continue

        # After submit Phoenix EITHER shows the OTP field (fresh login) OR — if
        # the F5 session was still warm server-side — drops us straight onto
        # my-systems. Race the two so a no-OTP warm login doesn't wait 300s.
        _step("await-otp-or-home")
        otp_field = "input[placeholder='קוד זיהוי'], input#input_2"
        reached = None
        for _ in range(20):  # ~20s
            try:
                if await page.locator(otp_field).first.is_visible():
                    reached = "otp"; break
            except Exception:
                pass
            try:
                if await page.locator("img[src*='my-systems']").first.is_visible():
                    reached = "home"; break
            except Exception:
                pass
            await page.wait_for_timeout(1000)

        if reached == "home":
            print(">> logged in without OTP (warm F5 session) — skipping OTP", flush=True)
        else:
            if reached != "otp":
                await page.wait_for_selector(otp_field, timeout=15000)
            # ── hands-free OTP ──
            _step("wait-otp")
            otp = await asyncio.get_event_loop().run_in_executor(
                None, fetch_otp, base, token, "phoenix", after_iso, 300
            )
            if not otp:
                print("!! no OTP forwarded within 300s — Phoenix asked for a code but "
                      "none was forwarded (in a batch this usually means phoenix_nifraim "
                      "already used the one Phoenix session; the persistent profile should "
                      "skip OTP once the cookie is warm).", flush=True)
                raise SystemExit(3)
            _step("submit-otp")
            await page.fill(otp_field, str(otp))
            for sel in ("input[type='submit']", "button:has-text('כניסה')", "button:has-text('המשך')"):
                try:
                    await page.click(sel, timeout=2500); break
                except Exception:
                    continue

    _step("await-home")
    try:
        await page.wait_for_selector("img[src*='my-systems'], [style*='my-systems']",
                                     state="visible", timeout=120000)
        print(">> logged in.")
    except Exception:
        print("!! systems icon not seen after login (wrong password / blocked "
              "session?) — continuing to navigation anyway.", flush=True)

    print(">> navigating my-systems → ביטוח חיים → התחבר…")
    await page.wait_for_timeout(1500)
    # Post-login Angular overlays (welcome/notification dialogs) drop a
    # `cdk-overlay-backdrop` that intercepts clicks on the my-systems icon.
    # Dismiss any open overlay (close button → Escape → click backdrop).
    _step("dismiss-overlays")
    for _ in range(5):
        backdrop = page.locator(".cdk-overlay-backdrop-showing")
        if await backdrop.count() == 0:
            break
        print(">> dismissing post-login overlay…")
        closed = False
        for sel in ("button[aria-label*='סגור']", "button.close",
                    "[mat-dialog-close]", "button:has-text('סגור')",
                    "button:has-text('אישור')", "button:has-text('הבנתי')"):
            loc = page.locator(sel)
            try:
                if await loc.count() and await loc.first.is_visible():
                    await loc.first.click(timeout=2000); closed = True; break
            except Exception:
                continue
        if not closed:
            try:
                await page.keyboard.press("Escape"); await page.wait_for_timeout(300)
                await backdrop.first.click(timeout=2000, force=True)
            except Exception:
                pass
        await page.wait_for_timeout(800)

    # my-systems icon → ביטוח חיים menuitem → התחבר. Each is a hard UI dependency;
    # wrap so a failure names the exact click that broke (not a bare exit 1) and
    # leaves a screenshot via the outer handler.
    # my-systems opens a menu; ביטוח חיים is inside it. On a WARM (cookie-reused)
    # session the menu can render a beat differently than after a fresh login, so
    # RETRY: re-open my-systems and try several selectors for the menu item before
    # giving up. Each attempt dumps the menu state so a miss is diagnosable.
    _step("click-my-systems")
    ms = page.locator("img[src*='my-systems.svg'], img[src*='my-systems']").first
    await ms.wait_for(state="visible", timeout=20000)

    _step("click-ביטוח-חיים")
    _life_sels = [
        "button[role='menuitem']:has-text('ביטוח חיים')",
        "[role='menuitem']:has-text('ביטוח חיים')",
        "a:has-text('ביטוח חיים')",
        "li:has-text('ביטוח חיים')",
        "*:has-text('ביטוח חיים'):visible",
        "button:has-text('חיים')",
    ]
    life = None
    for attempt in range(4):
        try:
            await ms.click()
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        for sel in _life_sels:
            try:
                loc = page.locator(sel).first
                if await loc.count() and await loc.is_visible():
                    life = loc; break
            except Exception:
                continue
        if life:
            break
        # Not found yet — dump the open-menu state and retry (re-open my-systems).
        await _shot(page, f"menu-attempt{attempt}")
        print(f">> ביטוח חיים not visible yet (attempt {attempt+1}/4) — reopening my-systems", flush=True)
        await page.wait_for_timeout(1200)
    if not life:
        raise RuntimeError("ביטוח חיים menu item not found after 4 attempts (see menu-attempt*.png)")
    await life.hover(); await page.wait_for_timeout(600); await life.click()
    await page.wait_for_timeout(1200)

    _step("click-התחבר")
    connect = page.locator(
        "button.btn-primary-sm:has-text('התחבר'), "
        "button:has-text('התחבר'):not(:has-text('מחדש'))"
    ).first
    await connect.wait_for(state="visible", timeout=15000)
    await connect.click()
    print(">> clicked התחבר — PowerTerm terminal should now open (own window).")

    # The terminal is a separate native window and PERSISTS after the browser
    # closes. Keep the browser briefly so the client finishes launching.
    _step("await-terminal-launch")
    await page.wait_for_timeout(20000)
    await page.context.close()
    print(">> browser closed; terminal stays open for the export driver.")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: python phoenix_browser_win.py <username> <password> <token> [backend_base]")
        raise SystemExit(2)
    base = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8000"
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], base))
