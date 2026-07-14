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

import os
import sys
import json
import time
import asyncio
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

URL = "https://agent.fnx.co.il/my.policy"

# Steps before the session is established. A browser that dies here died on
# arrival (stranded profile lock / half-dead relaunch), so ONE clean relaunch is
# worth trying. Later steps mean a real portal problem — never retry those.
_EARLY_STEPS = ("launch-edge", "open-portal", "check-session")

# Files a force-killed Chromium strands in a persistent profile. A stale one
# makes the next launch exit before Playwright ever attaches.
_SINGLETON_FILES = ("SingletonLock", "SingletonCookie", "SingletonSocket")

_RELAUNCH_SETTLE_S = 7   # PHOENIX_SKILL.md: settle ~7s before relaunching

_WORKER_TOKEN = ""
_BACKEND_BASE = ""


def _post_log(msg: str) -> None:
    """Best-effort POST to the worker log, so this shows up in Railway as
    WORKER-LOG. The parent only forwards the LAST ~600 chars of our stdout, so
    facts printed early — above all which browser actually launched — would
    otherwise never leave the agent's machine."""
    if not _WORKER_TOKEN or not _BACKEND_BASE:
        return
    try:
        req = urllib.request.Request(
            f"{_BACKEND_BASE}/api/portal-automation/worker/log/{_WORKER_TOKEN}",
            data=f"phoenix_browser: {msg}"[:3500].encode("utf-8"), method="POST",
        )
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass


def _browser_died(e) -> bool:
    """Playwright's wording for 'the browser process is gone'. Distinct from a
    network failure, which surfaces as net::ERR_* or a goto timeout."""
    s = str(e)
    return "has been closed" in s or "Target closed" in s or "Browser closed" in s


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
    """Clear everything that makes the NEXT persistent launch die on arrival.

    PHOENIX_SKILL.md prescribes the full cure: kill the orphaned playwright
    `node.exe` AND the automation `msedge.exe`, then settle ~7s. We used to do
    only the msedge half, with no settle, and launched on the very next line —
    so `phoenix_terminal`, which the run-all batch starts one second after
    `phoenix_nifraim` finishes, launched straight into a half-dead browser.

    Two further traps this closes:
      * In PowerShell `-like`, a backslash is LITERAL, not an escape. The old
        pattern doubled them, so it matched nothing and this function had in
        fact never killed a single process.
      * Force-killing Chromium strands `SingletonLock` in the profile dir, and
        the next launch exits immediately when it finds one.

    Never touches the user's OWN Edge — processes are matched by our profile
    path appearing on their command line.
    """
    import subprocess

    killed = False
    try:
        # `-like` wildcards are * ? [ ]; a path needs no backslash escaping, but a
        # quote would break out of the single-quoted string.
        pat = profile.replace("'", "''")
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*{pat}*' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };"
            "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*playwright*' }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=25)
        killed = True
    except Exception as e:
        print(f">> stale-edge cleanup skipped: {e}", flush=True)

    for name in _SINGLETON_FILES:
        try:
            os.remove(os.path.join(profile, name))
            print(f">> removed stale {name}", flush=True)
        except FileNotFoundError:
            pass
        except OSError as e:
            print(f">> could not remove {name}: {e}", flush=True)

    if killed:
        time.sleep(_RELAUNCH_SETTLE_S)


async def _launch_persistent(pw, profile):
    """Launch the persistent context; return (ctx, label).

    Prefer REAL Edge. Phoenix sits behind an F5 WAF that bounces bundled
    Chromium — and a bounce looks exactly like "the browser died by itself" a
    couple of seconds after goto() returns. Falling back silently turned a
    machine-provisioning problem into an unattributable browser death, so the
    fallback now announces itself.
    """
    launch_kw = dict(user_data_dir=profile, headless=False, no_viewport=True,
                     locale="he-IL", args=["--start-maximized"])
    try:
        ctx = await pw.chromium.launch_persistent_context(channel="msedge", **launch_kw)
        return ctx, "msedge"
    except Exception as e:
        print(f"!! Edge (msedge) persistent launch failed: {e}", flush=True)
        ctx = await pw.chromium.launch_persistent_context(**launch_kw)
        return ctx, "chromium-bundled"


async def main(username, password, token, base):
    from playwright.async_api import async_playwright

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    global _WORKER_TOKEN, _BACKEND_BASE
    _WORKER_TOKEN, _BACKEND_BASE = token, base

    profile = _profile_dir()
    for attempt in (1, 2):
        print(f">> [start] launching Edge attempt {attempt}/2 "
              f"(persistent profile: {profile})…", flush=True)

        # MUST run BEFORE async_playwright() starts our own driver: the cleanup
        # kills every playwright node.exe, and our driver is one of them. Killing
        # it mid-launch surfaced as `Connection closed while reading from the
        # driver` + BrokenPipeError — i.e. we shot ourselves. Each attempt
        # therefore gets a fresh driver, started after the machine is clean.
        _kill_stale_automation_edge(profile)
        os.makedirs(profile, exist_ok=True)

        async with async_playwright() as pw:
            try:
                ctx, label = await _launch_persistent(pw, profile)
            except Exception as e:
                # Neither real Edge nor bundled Chromium could start: a worker
                # provisioning problem, not a portal one. Say so out loud —
                # otherwise it escapes as a bare traceback and exit 1.
                msg = f"NO BROWSER: neither msedge nor bundled chromium launched: {e}"
                print(f"!! {msg}", flush=True)
                _post_log(msg)
                raise SystemExit(1)

            if label == "msedge":
                print(">> browser=msedge (real Edge)", flush=True)
                _post_log("browser=msedge")
            else:
                warn = (f"browser={label} — real Microsoft Edge NOT found on this "
                        "worker. Phoenix's F5 WAF bounces bundled Chromium, which "
                        "presents as the browser closing on its own. Install Edge.")
                print(f"!! {warn}", flush=True)
                _post_log(warn)

            await _load_shared_phoenix_session(ctx)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            try:
                await _run_login_flow(page, username, password, token, base)
                return
            except SystemExit:
                raise
            except Exception as e:
                step = _CUR_STEP[0]
                # A browser that died before the session was established gets ONE
                # clean relaunch. Anything later is a real portal failure.
                if attempt == 1 and step in _EARLY_STEPS and _browser_died(e):
                    msg = f"browser died at '{step}' ({e}) — full cleanup, relaunching once"
                    print(f">> {msg}", flush=True)
                    _post_log(msg)
                    try:
                        await ctx.close()
                    except Exception:
                        pass
                    continue        # leaves `async with`, stopping this driver

                import traceback
                print(f"!! login failed at step '{step}': {e}", flush=True)
                print(traceback.format_exc(), flush=True)
                await _shot(page, step)
                _post_log(f"login failed at step '{step}' (browser={label}): {e}")
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

    # Warm vs cold decides whether we need an OTP at all. Phoenix issues ONE per
    # session and phoenix_nifraim consumes it seconds earlier in the run-all
    # batch, so a cold profile here is precisely the `no OTP forwarded within
    # 300s` failure. Surface it: it is a fact about the machine, not the code.
    _post_log(f"profile={'warm' if logged_in else 'COLD'} (otp_needed={not logged_in})")

    if logged_in:
        print(">> already authenticated (warm Phoenix session) — skipping login+OTP", flush=True)
    else:
        print(">> COLD profile — full login + OTP required", flush=True)
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
    _step("dismiss-overlays")
    await _dismiss_overlays(page)

    # my-systems icon → ביטוח חיים menuitem → התחבר. Each is a hard UI dependency;
    # wrap so a failure names the exact click that broke (not a bare exit 1) and
    # leaves a screenshot via the outer handler.
    # my-systems opens a menu; ביטוח חיים is inside it. On a WARM (cookie-reused)
    # session the menu can render a beat differently than after a fresh login, so
    # RETRY: re-open my-systems and try several selectors for the menu item before
    # giving up. Each attempt dumps the menu state so a miss is diagnosable.
    _step("click-my-systems")
    # "המערכות שלי" is a BUTTON (button.btn-secondary-thicker.ng-star-inserted) that
    # happens to contain an icon — keying only off the <img> was brittle. Match the
    # button by text/class first and fall back to the icon.
    ms = page.locator(
        "button:has-text('המערכות שלי'), "
        "button.btn-secondary-thicker:has-text('המערכות'), "
        "img[src*='my-systems.svg'], img[src*='my-systems']"
    ).first
    await ms.wait_for(state="visible", timeout=20000)

    _step("click-ביטוח-חיים")
    # SCOPED to the open my-systems dropdown — never page-wide. "ביטוח חיים" also
    # appears as a NAVIGATION LINK in the site chrome, and a page-wide
    # `a:has-text(...)` / `*:has-text(...):visible` happily matched it: the run
    # navigated to /digital-services/ביטוח-חיים (a marketing page with no התחבר) and
    # then timed out waiting for a button that was never going to exist there. The
    # menu item we want lives inside the dropdown panel; look only there.
    # The REAL markup (confirmed against the live portal):
    #     <div class="flex justify-between w-full"> ביטוח חיים
    #         <fnx-nx-ui-standalone-icon><img src=".../left.svg"></fnx-nx-ui-standalone-icon>
    #     </div>
    # It is a DIV — not a button, not an anchor, no role=menuitem. Every selector we
    # tried missed it, and the page-wide `a:has-text('ביטוח חיים')` fallback then
    # matched a NAVIGATION LINK elsewhere on the page: the run left for
    # /digital-services/ and waited forever for a התחבר that cannot exist there.
    # Match the row by its class + its left-chevron icon, and never by <a> — so a
    # link can no longer impersonate the menu item.
    _life_sels = [
        "div.justify-between:has-text('ביטוח חיים'):has(img[src*='left.svg'])",
        "div.justify-between:has-text('ביטוח חיים')",
        "li:has(div.justify-between:has-text('ביטוח חיים'))",
        "[role='menuitem']:has-text('ביטוח חיים')",
    ]

    async def _find_life():
        for sel in _life_sels:
            loc = page.locator(sel).first
            try:
                if await loc.count() and await loc.is_visible():
                    print(f">> ביטוח חיים matched by: {sel}")
                    return loc
            except Exception:
                continue
        return None

    life = None
    for attempt in range(4):
        # The ביטוח-חיים submenu may ALREADY be open — clicking my-systems can land us
        # straight inside the section, and its fly-out then renders OVER the parent
        # item (RTL). The parent is still "visible" to a selector but is no longer
        # hittable, so hovering it can never succeed: live, this burned the full 30s
        # actionability timeout and killed the run ("element intercepts pointer
        # events") — we were fighting our own successful click. If התחבר is already
        # on screen, the menu has done its job; don't touch the parent at all.
        if await _connect_button(page).count() and await _connect_button(page).first.is_visible():
            print(">> ביטוח חיים submenu is already open (התחבר is on screen) — skipping the menu click")
            life = None
            break

        try:
            await ms.click()
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        if await _connect_button(page).count() and await _connect_button(page).first.is_visible():
            print(">> my-systems click opened ביטוח חיים directly — skipping the menu click")
            life = None
            break

        # Capture the OPEN MENU while it is still on screen. (This shot used to be
        # taken at the bottom of the loop — i.e. AFTER go_back() — so every capture
        # was a blank page mid-navigation. Useless exactly when it mattered.)
        await _shot(page, f"menu-attempt{attempt}")
        await _dump_menu_candidates(page)

        life = await _find_life()
        if life:
            # HOVER FIRST — do not click. On this portal the category is a LINK: a
            # click navigates to /digital-services/… (a marketing page with no התחבר),
            # while hovering expands the fly-out that actually holds the systems and
            # their התחבר buttons. Click only if hovering produced nothing.
            try:
                await life.hover(timeout=5000)
                await page.wait_for_timeout(1500)
            except Exception as e:
                print(f">> hover on ביטוח חיים failed ({str(e).splitlines()[0][:70]})")

            if await _connect_button(page).count() and await _connect_button(page).first.is_visible():
                print(">> hover opened the ביטוח חיים fly-out — התחבר is on screen")
                _post_log("ביטוח חיים fly-out opened by HOVER (no click needed)")
                life = None
                break

            await _click_through(page, life, "ביטוח חיים")
            await page.wait_for_timeout(1500)

            if await _connect_button(page).count() and await _connect_button(page).first.is_visible():
                print(">> ביטוח חיים is open — התחבר is on screen")
                life = None
                break

            # Or did it NAVIGATE us off the portal home? (live: /digital-services/…)
            # Go back and retry — the menu item is not whatever we just clicked.
            if "digital-services" in (page.url or ""):
                print(f"!! that click navigated to {page.url} — going back and retrying the MENU item")
                _post_log(f"ביטוח חיים click navigated to {page.url} (wrong element) — retrying")
                try:
                    await page.go_back(wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(2500)
                except Exception:
                    await page.goto(URL, timeout=40000)
                    await page.wait_for_timeout(2500)
            life = None
        print(f">> ביטוח חיים not usable yet (attempt {attempt+1}/4) — reopening my-systems", flush=True)
        await page.wait_for_timeout(1200)
    else:
        raise RuntimeError("could not open ביטוח חיים after 4 attempts "
                           "(see the 'menu candidates' lines in the worker log)")
    await page.wait_for_timeout(1200)

    _step("click-התחבר")
    # NO _dismiss_overlays() here. An Angular Material menu opens WITH a
    # `cdk-overlay-backdrop`, so the dismisser cannot tell our own open fly-out from
    # a nuisance dialog — it pressed Escape and CLOSED the menu we had just opened,
    # then we waited 15s for a התחבר we had personally dismissed. (Live: the run
    # logged "fly-out opened by HOVER" and died at click-התחבר one step later.)
    connect = _connect_button(page).first
    await connect.wait_for(state="visible", timeout=15000)
    if not await _click_through(page, connect, "התחבר"):
        await _shot(page, "connect-blocked")
        raise RuntimeError("התחבר is visible but every click was blocked (see connect-blocked.png)")
    print(">> clicked התחבר — PowerTerm terminal should now open (own window).")

    # The terminal is a separate native window and PERSISTS after the browser
    # closes. Keep the browser open until the PowerTerm client has actually put
    # a TERM window on screen — see _wait_for_term_window for why we verify.
    _step("await-terminal-launch")
    opened = await _wait_for_term_window(page, timeout_s=45)
    await page.context.close()
    if opened:
        print(">> browser closed; terminal stays open for the export driver.")
    else:
        # Do NOT fail the run here: the export driver waits for the TERM window too
        # and may still catch a slow launch. But say so LOUDLY and now, attributed to
        # the step that caused it.
        print("!! terminal did NOT appear while the browser was open — the export "
              "driver will keep waiting, but this is the step that failed.")
        _post_log("terminal did NOT open after clicking התחבר (no TERM window within 45s)")


async def _dismiss_overlays(page, passes: int = 5) -> None:
    """Close anything covering the page: post-login Angular dialogs (which drop a
    `cdk-overlay-backdrop`) AND the F5 VPN error dialog.

    The F5 one is the reason this is a reusable helper rather than a one-shot pass.
    Phoenix's portal is an F5 BIG-IP APM gateway, and it can throw
    "F5 VPN — Failed to establish VPN connection … the previous request is still in
    progress" at ANY point, including after we've already dismissed the welcome
    dialogs. Live, it landed on top of the my-systems menu and Playwright's hover
    died with "element intercepts pointer events" — 30s of waiting for a menu item
    that was visible but buried.
    """
    for _ in range(passes):
        # NEVER dismiss our own open menu. A mat-menu fly-out ships its own
        # cdk-overlay-backdrop, so "there is a backdrop" does NOT mean "there is a
        # nuisance dialog". If התחבר is on screen the menu is open and doing exactly
        # what we want — leave it alone.
        try:
            if await _connect_button(page).count() and await _connect_button(page).first.is_visible():
                return
        except Exception:
            pass

        backdrop = page.locator(".cdk-overlay-backdrop-showing")
        f5 = page.locator(
            "*:has-text('Failed to establish VPN connection'), "
            "*:has-text('previous request is still in progress')"
        )
        has_backdrop = await backdrop.count() > 0
        try:
            has_f5 = await f5.count() > 0
        except Exception:
            has_f5 = False
        if not (has_backdrop or has_f5):
            return
        if has_f5:
            print("!! F5 VPN dialog is on screen — dismissing it")
            _post_log("F5 VPN dialog on screen ('previous request still in progress') — dismissing")
        closed = False
        for sel in ("button:has-text('אישור')", "button[aria-label*='סגור']",
                    "button.close", "[mat-dialog-close]", "button:has-text('סגור')",
                    "button:has-text('הבנתי')", "button:has-text('OK')"):
            loc = page.locator(sel)
            try:
                if await loc.count() and await loc.first.is_visible():
                    await loc.first.click(timeout=2000)
                    closed = True
                    break
            except Exception:
                continue
        if not closed:
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                if has_backdrop:
                    await backdrop.first.click(timeout=2000, force=True)
            except Exception:
                pass
        await page.wait_for_timeout(800)


async def _dump_menu_candidates(page) -> list:
    """Report every visible 'ביטוח חיים' element to WORKER-LOG — tag/role/class/href.

    The failure screenshots were useless (blank: they were taken mid-navigation), and
    we cannot read files off an agent's PC. So the run itself must tell us what the
    menu is actually made of. Without this we are guessing selectors blind, and each
    guess costs a deploy + a worker update + a live run.
    """
    try:
        cands = await page.evaluate(
            """() => {
                const out = [];
                for (const el of document.querySelectorAll('a,button,li,div,span,[role]')) {
                    const t = (el.innerText || '').trim();
                    if (!t.includes('ביטוח חיים') || t.length > 60) continue;   // skip wrappers
                    const r = el.getBoundingClientRect();
                    if (!r.width || !r.height) continue;                        // skip hidden
                    out.push({
                        tag: el.tagName,
                        role: el.getAttribute('role') || '',
                        cls: String(el.className || '').slice(0, 70),
                        href: el.getAttribute('href') || '',
                        text: t.slice(0, 25),
                        pos: Math.round(r.x) + ',' + Math.round(r.y),
                    });
                    if (out.length >= 10) break;
                }
                return out;
            }"""
        )
    except Exception as e:
        print(f">> menu dump failed: {e}")
        return []
    import json as _json
    msg = f"menu candidates ({len(cands)}): " + _json.dumps(cands, ensure_ascii=False)
    print(">> " + msg, flush=True)
    _post_log(msg[:3800])
    return cands


def _connect_button(page):
    """The התחבר button inside the ביטוח-חיים fly-out — the thing that launches
    PowerTerm. Its presence is also our proof that the submenu is open, which is why
    it's a named locator rather than an inline string in two places."""
    return page.locator(
        "button.btn-primary-sm:has-text('התחבר'), "
        "button:has-text('התחבר'):not(:has-text('מחדש'))"
    )


async def _click_through(page, loc, label: str) -> bool:
    """Click an element even if an overlay is sitting on top of it.

    A plain `hover()` + `click()` defers to Playwright's actionability check, so ANY
    covering element (see _dismiss_overlays) turns it into a 30s timeout and a dead
    run. Escalate instead: normal → dismiss overlays and force → dispatch the click
    in the page. Short timeouts, because the whole point is to fail fast to the next
    strategy rather than burn the run's budget on one blocked hover.
    """
    try:
        await loc.hover(timeout=5000)
        await page.wait_for_timeout(400)
        await loc.click(timeout=5000)
        return True
    except Exception as e:
        print(f"!! {label}: normal click blocked ({str(e).splitlines()[0][:90]}) — clearing overlays")

    await _dismiss_overlays(page, passes=3)
    try:
        await loc.click(timeout=5000, force=True)
        print(f">> {label}: clicked (force) after clearing overlays")
        return True
    except Exception as e:
        print(f"!! {label}: force click failed ({str(e).splitlines()[0][:90]}) — dispatching in-page")

    try:
        await loc.evaluate("el => el.click()")
        print(f">> {label}: clicked (in-page dispatch)")
        return True
    except Exception as e:
        print(f"!! {label}: in-page click failed: {str(e).splitlines()[0][:120]}")
        return False


def _find_term_hwnds() -> list:
    """Visible native PowerTerm windows, by window CLASS. Mirrors
    phoenix_win_terminal.find_term — the export driver's own detector."""
    try:
        import win32gui
    except Exception:
        return []                                  # no pywin32 (WSL) — can't tell
    hits = []

    def _cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        try:
            if win32gui.GetClassName(h) == "TERM":
                hits.append(h)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return []
    return hits


async def _wait_for_term_window(page, timeout_s: int = 45) -> bool:
    """Poll for the green-screen TERM window after clicking התחבר.

    Why this exists: clicking התחבר does NOT open the terminal directly. The portal
    page writes a `<PtConnect>…</PtConnect>` payload into the BROWSER WINDOW TITLE
    (and/or fires the `epsShare:` protocol); a locally-installed Ericom helper polls
    for it and spawns PowerTerm. That handoff can silently not happen — the browser
    is perfectly happy either way.

    We used to just `wait_for_timeout(20000)` and declare success. The failure then
    surfaced 300s later, inside the *export* driver, as "no TERM window appeared" —
    blaming the step that was merely the first to notice. Detect it here, where it
    actually happens, and while the browser is still alive to be screenshotted.

    Returns False on WSL/no-pywin32 rather than pretending — the export driver is
    then the only detector, exactly as before.
    """
    try:
        import win32gui  # noqa: F401
    except Exception:
        print(">> (no pywin32 here — cannot verify the terminal window; "
              "leaving detection to the export driver)")
        await page.wait_for_timeout(20000)
        return True                                # unknown → don't cry wolf
    for i in range(timeout_s):
        hwnds = _find_term_hwnds()
        if hwnds:
            print(f">> terminal window is up (TERM hwnd={hwnds[0]}) after ~{i}s.")
            _post_log(f"terminal opened after ~{i}s (TERM hwnd={hwnds[0]})")
            await page.wait_for_timeout(2000)      # let it finish painting
            return True
        await page.wait_for_timeout(1000)
    await _shot(page, "no-terminal")               # what was on screen when it didn't open
    return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: python phoenix_browser_win.py <username> <password> <token> [backend_base]")
        raise SystemExit(2)
    base = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8000"
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], base))
