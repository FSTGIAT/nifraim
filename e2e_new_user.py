"""
End-to-end test of the new-user activation journey against the LIVE backend
(no API mocking). Registers a brand-new account, documents the subscription
gate, walks the compact Ark-UI activation card step-by-step, then verifies
show-once + bell-reminder reopen. Cleans up its own test user at the end.

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

        # 2. Grant access and enter the workspace
        check("Grant subscription access via DB", grant_access(EMAIL))
        await page.evaluate("() => localStorage.setItem('onboarding_completed','true')")
        await page.goto(f"{BASE}/workspace", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        check("Compact activation card visible", await page.query_selector(".actc") is not None)
        check("Counter starts at 1/4", await text(page, ".actc-counter") == "1/4",
              await text(page, ".actc-counter"))
        inds = await page.query_selector_all(".actc-ind")
        check("Ark UI stepper renders 4 indicators", len(inds) == 4, f"{len(inds)} found")
        check("Shows current step = connect phone",
              "טלפון" in (await text(page, ".actc-current-label") or ""),
              await text(page, ".actc-current-label"))
        await page.screenshot(path="/home/roygi/test/e2e_v2_step1.png")

        # 3. Step phone: generate token via modal → ticks to 2/4
        await page.click(".actc-cta")
        await page.wait_for_timeout(1200)
        check("PhoneForwardModal opens from card", await page.query_selector(".pf-overlay") is not None)
        gen = await page.query_selector("text=צור כתובת מאובטחת")
        if gen:
            await gen.click(); await page.wait_for_timeout(2000)
        close_btn = await page.query_selector(".pf-overlay .pf-close, .pf-overlay [aria-label='סגור']")
        if close_btn: await close_btn.click()
        else: await page.keyboard.press("Escape")
        await page.wait_for_timeout(1500)
        check("Step ticks to 2/4 after phone connected", await text(page, ".actc-counter") == "2/4",
              await text(page, ".actc-counter"))
        check("Current step advances to add-portal",
              "פורטל" in (await text(page, ".actc-current-label") or ""),
              await text(page, ".actc-current-label"))
        await page.screenshot(path="/home/roygi/test/e2e_v2_step2.png")

        # 4. Step portal: add a credential → ticks to 3/4
        await page.click(".actc-cta")
        await page.wait_for_timeout(2000)
        check("Add-credential modal auto-opens on automation tab",
              await page.query_selector("select") is not None)
        opts = await page.eval_on_selector_all("select option:not([disabled])", "els => els.map(e=>e.value)")
        await page.select_option("select", opts[0])
        await page.fill('input[placeholder="שם המשתמש בפורטל"]', "e2e_user")
        await page.fill('input[type="password"]', "e2e_pass")
        await page.click("button.btn-primary")
        await page.wait_for_timeout(2000)
        await page.goto(f"{BASE}/workspace", wait_until="networkidle")
        await page.wait_for_timeout(2500)
        # NB: this is the 2nd workspace entry — but the card was NOT closed, only
        # navigated; show-once means it stays hidden now. Verify via the bell reminder.
        seen_hidden = await page.query_selector(".actc") is None
        check("Show-once: card hidden on 2nd entry (not finished)", seen_hidden)

        # 5. Bell reminder exists and reopens the card
        bell = await page.query_selector(".ws-bell-anchor button, [class*='bell'] button, button[aria-label*='התראות']")
        if bell:
            await bell.click(); await page.wait_for_timeout(800)
        reminder = await page.query_selector("text=השלם את הפעלת האוטומציה")
        check("Bell reminder present while setup incomplete", reminder is not None)
        cont = await page.query_selector("text=המשך הגדרה")
        if cont:
            await cont.click(); await page.wait_for_timeout(1500)
        check("Bell 'המשך הגדרה' reopens the card", await page.query_selector(".actc") is not None)
        check("Reopened card shows 3/4", await text(page, ".actc-counter") == "3/4",
              await text(page, ".actc-counter"))
        check("Current step is run-automation",
              "הרץ" in (await text(page, ".actc-current-label") or ""),
              await text(page, ".actc-current-label"))
        await page.screenshot(path="/home/roygi/test/e2e_v2_step3.png")

        # 6. Run step routes to the 1-click run-all bar
        await page.click(".actc-cta")
        await page.wait_for_timeout(2000)
        check("Run step routes to the run-all bar",
              await page.query_selector("text=הורדה אוטומטית מכל החברות") is not None)

        check("No console/page errors during journey", len(ERRORS) == 0, "; ".join(ERRORS[:3]))
        await browser.close()

    cleanup(EMAIL)
    print(f"\n=== {sum(1 for _,ok,_ in RESULTS if ok)}/{len(RESULTS)} checks passed · test user removed ===")
    sys.exit(0 if all(ok for _,ok,_ in RESULTS) else 1)


asyncio.run(main())
