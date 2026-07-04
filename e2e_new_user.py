"""
End-to-end test of the new-user setup wizard ("אשף ההפעלה") against the LIVE
backend (no API mocking). Registers a brand-new account, documents the
subscription gate, verifies the SetupPipelineModal auto-open + live step
ticks, the slim SetupProgressCard, the ✕-close → bell-reminder → reopen path,
the portal deep-link, and the comparison-tab empty-state guide. Cleans up its
own test user at the end.

Run: source backend/venv/bin/activate && python e2e_new_user.py
"""
import asyncio, time, subprocess, sys
from playwright.async_api import async_playwright

BASE = "http://localhost:5173"
EMAIL = f"e2e_{int(time.time())}@test.com"
PW = "test1234"
RESULTS = []
ERRORS = []


def check(name, ok, extra=""):
    RESULTS.append((name, ok, extra))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {extra}" if extra else ""))


def psql(sql):
    return subprocess.run(
        ["docker", "exec", "test-db-1", "psql", "-U", "insurance", "-d",
         "insurance_dashboard", "-tA", "-c", sql],
        capture_output=True, text=True)


def grant_access(email):
    return "UPDATE 1" in psql(f"UPDATE users SET is_active=true WHERE email='{email}';").stdout


def cleanup(email):
    psql(f"DELETE FROM portal_credentials WHERE user_id IN (SELECT id FROM users WHERE email='{email}');")
    psql(f"DELETE FROM portal_run_batches WHERE user_id IN (SELECT id FROM users WHERE email='{email}');")
    psql(f"DELETE FROM users WHERE email='{email}';")


async def text(page, sel):
    el = await page.query_selector(sel)
    return ((await el.text_content()) or "").strip() if el else None


async def goto_workspace(page):
    # Skip the WelcomeOverlay wipe so the wizard opens immediately.
    await page.evaluate("() => sessionStorage.removeItem('justLoggedIn')")
    await page.goto(f"{BASE}/workspace", wait_until="networkidle")
    await page.wait_for_timeout(2500)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("console", lambda m: ERRORS.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: ERRORS.append(f"pageerror: {e}"))

        # 1. Register a brand-new user via the UI
        await page.goto(f"{BASE}/register", wait_until="networkidle")
        await page.fill('input[type="text"]', "בודק חדש")
        await page.fill('input[type="email"]', EMAIL)
        await page.fill('input[type="password"]', PW)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(2500)
        check("New (unpaid) user redirected to subscription gate",
              "subscription-expired" in page.url, page.url)

        # 2. Grant access and enter the workspace → wizard auto-opens
        check("Grant subscription access via DB", grant_access(EMAIL))
        await goto_workspace(page)

        check("Setup wizard auto-opens for a fresh user",
              await page.query_selector(".spm-overlay") is not None)
        steps = await page.query_selector_all(".spm-step")
        check("Wizard renders 4 steps", len(steps) == 4, f"{len(steps)} found")
        check("Counter starts at 0/4", await text(page, ".spm-progress-label") == "0/4",
              await text(page, ".spm-progress-label"))
        check("First incomplete step = install PC (worker)",
              "התקינו את המחשב" in (await text(page, ".spm-step--active .spm-step-title") or ""),
              await text(page, ".spm-step--active .spm-step-title"))
        await page.screenshot(path="/home/roygi/test/e2e_v3_step1.png")

        # 3. Phone step: open PhoneForwardModal from the wizard → tick to 1/4
        await page.click(".spm-step:nth-child(2) .spm-step-head")
        await page.wait_for_timeout(600)
        await page.click(".spm-step:nth-child(2) .spm-cta")
        await page.wait_for_timeout(1200)
        check("PhoneForwardModal stacks above the wizard",
              await page.query_selector(".pf-overlay") is not None)
        gen = await page.query_selector("text=צור כתובת מאובטחת")
        if gen:
            await gen.click(); await page.wait_for_timeout(2000)
        close_btn = await page.query_selector(".pf-overlay .pf-close, .pf-overlay [aria-label='סגור']")
        if close_btn: await close_btn.click()
        else: await page.keyboard.press("Escape")
        await page.wait_for_timeout(1800)
        check("Step ticks live to 1/4 after phone connected",
              await text(page, ".spm-progress-label") == "1/4",
              await text(page, ".spm-progress-label"))
        done = await page.query_selector_all(".spm-step--done")
        check("Phone step marked done", len(done) == 1, f"{len(done)} done")
        await page.screenshot(path="/home/roygi/test/e2e_v3_step2.png")

        # 4. Close wizard → slim progress card remains on home
        await page.click(".spm-close")
        await page.wait_for_timeout(800)
        check("Slim progress card visible after closing wizard",
              await page.query_selector(".spc") is not None)
        check("Card shows 1/4", await text(page, ".spc-ring-label") == "1/4",
              await text(page, ".spc-ring-label"))
        check("Card names the next step",
              "התקינו את המחשב" in (await text(page, ".spc-next") or ""),
              await text(page, ".spc-next"))
        await page.screenshot(path="/home/roygi/test/e2e_v3_card.png")

        # 5. Reload → wizard auto-opens again (incomplete + card not closed)
        await goto_workspace(page)
        check("Wizard re-opens on next entry while setup incomplete",
              await page.query_selector(".spm-overlay") is not None)
        await page.click(".spm-close")
        await page.wait_for_timeout(600)

        # 6. ✕ the card → bell reminder is the way back, opens the wizard
        await page.click(".spc-close")
        await page.wait_for_timeout(800)
        check("Card hidden after ✕", await page.query_selector(".spc") is None)
        bell = await page.query_selector(".ws-bell-anchor button, [class*='bell'] button, button[aria-label*='התראות']")
        if bell:
            await bell.click(); await page.wait_for_timeout(800)
        reminder = await page.query_selector("text=השלם את הפעלת האוטומציה")
        check("Bell reminder present while setup incomplete", reminder is not None)
        cont = await page.query_selector("text=המשך הגדרה")
        if cont:
            await cont.click(); await page.wait_for_timeout(1200)
        check("Bell reopens the wizard", await page.query_selector(".spm-overlay") is not None)

        # 7. Portal step deep-link: CTA closes wizard → automation tab + add modal
        await page.click(".spm-step:nth-child(3) .spm-step-head")
        await page.wait_for_timeout(600)
        await page.click(".spm-step:nth-child(3) .spm-cta")
        await page.wait_for_timeout(2000)
        check("Add-credential modal auto-opens on automation tab",
              await page.query_selector("select") is not None)
        opts = await page.eval_on_selector_all("select option:not([disabled])", "els => els.map(e=>e.value)")
        await page.select_option("select", opts[0])
        await page.fill('input[placeholder="שם המשתמש בפורטל"]', "e2e_user")
        await page.fill('input[type="password"]', "e2e_pass")
        await page.click("button.btn-primary")
        await page.wait_for_timeout(2000)

        # 8. Card was ✕-closed earlier → wizard must NOT auto-open anymore;
        #    the bell reminder is the way back in.
        await goto_workspace(page)
        check("Wizard does not auto-open after card was closed",
              await page.query_selector(".spm-overlay") is None)
        bell = await page.query_selector(".ws-bell-anchor button, [class*='bell'] button, button[aria-label*='התראות']")
        if bell:
            await bell.click(); await page.wait_for_timeout(800)
        cont = await page.query_selector("text=המשך הגדרה")
        if cont:
            await cont.click(); await page.wait_for_timeout(1200)
        await page.wait_for_selector(".spm-overlay", timeout=8000)
        check("Wizard shows 2/4 after portal added",
              await text(page, ".spm-progress-label") == "2/4",
              await text(page, ".spm-progress-label"))
        await page.screenshot(path="/home/roygi/test/e2e_v3_step3.png")

        # 9. Run step CTA routes to the 1-click run-all bar
        await page.click(".spm-step:nth-child(4) .spm-step-head")
        await page.wait_for_timeout(600)
        await page.click(".spm-step:nth-child(4) .spm-cta")
        await page.wait_for_timeout(2000)
        check("Run step routes to the run-all bar",
              await page.query_selector("text=הורדה אוטומטית מכל החברות") is not None)

        # 10. Comparison tab empty state: guide copy + deep-link back into wizard
        await page.goto(f"{BASE}/workspace", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        if await page.query_selector(".spm-overlay"):
            await page.click(".spm-close")
            await page.wait_for_timeout(500)
        tab = await page.query_selector("text=השוואת נפרעים")
        if tab:
            await tab.click(); await page.wait_for_timeout(1500)
        guide = await page.query_selector(".esg--full")
        check("Comparison empty state shows the guide",
              guide is not None and "ההורדה האוטומטית ממלאת" in ((await guide.text_content()) or ""))
        cta = await page.query_selector(".esg--full .esg-cta")
        if cta:
            await cta.click(); await page.wait_for_timeout(1000)
        check("Empty-state CTA opens the wizard at the run step",
              await page.query_selector(".spm-overlay") is not None and
              "הריצו" in (await text(page, ".spm-step--active .spm-step-title") or ""),
              await text(page, ".spm-step--active .spm-step-title"))
        await page.screenshot(path="/home/roygi/test/e2e_v3_empty_state.png")

        check("No console/page errors during journey", len(ERRORS) == 0, "; ".join(ERRORS[:3]))
        await browser.close()

    cleanup(EMAIL)
    print(f"\n=== {sum(1 for _,ok,_ in RESULTS if ok)}/{len(RESULTS)} checks passed · test user removed ===")
    sys.exit(0 if all(ok for _,ok,_ in RESULTS) else 1)


asyncio.run(main())
