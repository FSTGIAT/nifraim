import asyncio, sys
from playwright.async_api import async_playwright

ERRORS, FAILS = [], []
def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'} — {label}" + (f"  [{detail}]" if detail else ""))
    if not ok: FAILS.append(label)

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page()
        pg.on("console", lambda m: m.type == "error" and ERRORS.append(m.text))
        pg.on("pageerror", lambda e: ERRORS.append(f"pageerror: {e}"))

        # log in the way a user does
        await pg.goto("http://localhost:5173/login", wait_until="networkidle")
        await pg.fill('input[type="email"]', "test@test.com")
        await pg.fill('input[type="password"]', "test123")
        await pg.click('button[type="submit"]')
        await pg.wait_for_timeout(2500)
        check("login lands inside the app", "/login" not in pg.url, pg.url)

        await pg.goto("http://localhost:5173/dev/maslaka", wait_until="networkidle")
        await pg.wait_for_timeout(1500)
        check("console page renders", "מסלקה" in await pg.inner_text("body"))

        # ── OUTBOUND: build a real request for the real customer ──
        await pg.click('button:has-text("9100")') if await pg.locator('button:has-text("9100")').count() else None
        await pg.fill('input[placeholder="381788223"]', "56004914")
        await pg.click('button:has-text("בנה בקשה")')
        await pg.wait_for_timeout(2000)
        body = await pg.inner_text("body")
        check("filename ruler shows a legal name", "EVENTS000007" in body,
              next((l for l in body.split("\n") if "EVENTS000007" in l), "")[:60])
        check("XSD verdict is rendered", "סכימה" in body)
        check("verdict says VALID (green path)", "תקין מול הסכימה הרשמית" in body,
              next((l for l in body.split("\n") if "סכימה" in l), "")[:70])
        check("XML is shown", "<KOD-EIRUA>9100</KOD-EIRUA>" in body or "KOD-EIRUA" in body)
        check("env code 1 = TEST in the rendered XML", "<KOD-SVIVAT-AVODA>1<" in body)

        # ── third tab: send log + vault state ──
        await pg.click('button:has-text("מה נשלח בפועל")')
        await pg.wait_for_timeout(2000)
        body = await pg.inner_text("body")
        check("send-log tab renders vault state", "מצב הכספת" in body)
        check("it admits this host is NOT the vault host", "זהו שרת פיתוח" in body,
              next((l for l in body.split("\n") if "שרת פיתוח" in l), "")[:60])

        # ── inbound tab: real vendor file through the parser + schema ──
        await pg.click('button:has-text("קבצים נכנסים")')
        await pg.wait_for_timeout(1500)
        items = pg.locator("nav button")
        if await items.count():
            await items.nth(0).click()
            await pg.wait_for_timeout(2500)
        body = await pg.inner_text("body")
        check("inbound file decodes and shows rows", "צבירה" in body or "רשומות" in body)
        check("inbound validation banner present", "סכימה" in body)

        await pg.screenshot(path="/tmp/maslaka_console.png", full_page=True)
        await b.close()

    print()
    if ERRORS:
        print(f"CONSOLE ERRORS ({len(ERRORS)}):")
        for e in ERRORS[:8]: print("   ", e[:160])
    else:
        print("No JS console errors.")
    print()
    print(f"{len(FAILS)} FAILURE(S): " + "; ".join(FAILS) if FAILS else "ALL PASS")
    sys.exit(1 if FAILS or ERRORS else 0)

asyncio.run(main())
