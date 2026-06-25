"""Shared helpers for F5 BIG-IP APM (`/my.policy`) login pages.

Several Israeli insurer agent portals (Phoenix, Hachshara, Clal, Migdal-APM)
sit behind F5 BIG-IP Access Policy Manager. They share the same logon form:

    <form action="/my.policy" method="post">
      <input name="username" ...>
      <input name="password" ...>
      <input type="submit" name="vhost" ...>
    </form>

This helper fills + submits that form so each per-portal plugin's `login()`
isn't a copy of the same four lines. Plugins still own `page.goto()` for the
specific portal URL and the post-login wait for the OTP-entry selector
(which is portal-specific).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


async def apm_login_submit(page: "Page", username: str, password: str) -> None:
    """Fill the F5 APM logon form and submit.

    Caller is responsible for `page.goto(PORTAL_URL)` first and for waiting
    on the next-step selector (OTP input) afterwards.
    """
    # The standard F5 form names — verified against the four target portals.
    await page.wait_for_selector("input[name='username']", state="visible", timeout=15000)
    await page.fill("input[name='username']", username)
    await page.fill("input[name='password']", password)
    # F5 typically renders a localised "Logon" / "כניסה" submit button. Try
    # the input/submit forms in order — the broad type=submit matches most.
    submit_selectors = [
        "input[type='submit']",
        "button[type='submit']",
        "input[value*='Logon']",
        "input[value*='כניסה']",
        "button:has-text('כניסה')",
        "button:has-text('Logon')",
        "button:has-text('Sign in')",
    ]
    for sel in submit_selectors:
        try:
            await page.click(sel, timeout=2500)
            return
        except Exception:
            continue
    # If we got here, none of the standard submit selectors matched. The
    # caller's wait_for_selector on the next step will time out with a
    # clearer diagnostic; raise here so the runner dumps page state.
    raise RuntimeError("APM logon: no submit button matched")
