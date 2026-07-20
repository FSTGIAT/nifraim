"""מור (Mor) agent portal — נפרעים / commission download.

Login (https://join.more.co.il/agentsportal/agents/login) asks for THREE fields:
מס' רשיון (license) + תעודת זהות (ID) + טלפון (phone). It then SMS-OTPs the phone.
Credential convention: ``username = "<license>|<id>"`` and ``password = "<phone>"``.

Flow (operator): right-menu → חישוב עמלות → pick the month → download to Excel.
The downloaded Excel is the existing ``nifraim`` format (company_source=מור,
commission), so no parser changes are needed.
"""
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.portal_automation.base import BasePortalAutomation

if TYPE_CHECKING:
    from playwright.async_api import Page

PORTAL_URL = "https://join.more.co.il/agentsportal/agents/login"


class MorPortal(BasePortalAutomation):
    portal_kind = "mor"
    company_label = "מור"
    # In the run-all batch. Mor's reCAPTCHA Enterprise gate only passes on the
    # Windows LOCAL WORKER (real desktop Chrome + IL IP) — never headless/Linux
    # Railway — so the batch must defer this credential to the worker.
    include_in_batch = True
    # Mor's login is gated by reCAPTCHA *Enterprise* (score-based). The server
    # returns HTTP 400 ("אירעה שגיאה") whenever Google scores the browser as a
    # bot. Proven live: headless + the runner's UA override → 400; headed +
    # native fingerprint + a persistent profile → 201 Success → OTP modal. So
    # Mor must run on the LOCAL WORKER (headed desktop session, real IL IP) —
    # never the headless Railway container. See memory `portal_mor`.
    headed = True
    native_fingerprint = True
    use_persistent_profile = True
    # Run on the worker's OWN residential IL IP — a Bright Data datacenter proxy
    # IP would sink the reCAPTCHA Enterprise score. (Also a no-op unless a proxy
    # env is set, but we never want one routed here.)
    needs_residential_proxy = False

    def _split(self, username: str, password: str) -> tuple[str, str, str]:
        """username='<license>|<id>', password='<phone>'. Falls back to
        license==id when no pipe (operator often has them equal).

        Every value is reduced to DIGITS. The user types the phone into a form
        field, so it can arrive as 050-4302306 or with spaces; Angular would then
        reject it (or Mor's server would) for a reason no log would explain. Yelin
        and Meitav already strip this way — Mor only did `.strip()`."""
        parts = (username or "").split("|")
        license_no = re.sub(r"\D", "", parts[0])
        id_no = re.sub(r"\D", "", parts[1]) if len(parts) > 1 else license_no
        phone = re.sub(r"\D", "", password or "")
        return license_no, id_no, phone

    # Set by runner.py when this portal's persistent profile dir did not exist —
    # i.e. the first-ever Mor run on this machine.
    profile_was_cold = False

    @staticmethod
    def _classify(status: int | None, body: str) -> str:
        """What did Mor's server ACTUALLY say? 'credentials' | 'recaptcha' | 'unknown'.

        The on-screen toast is the same generic "אירעה שגיאה" for a low bot score and
        for wrong פרטים, so the toast alone cannot tell them apart — yet the old error
        message asserted "ציון reCAPTCHA נמוך" every time. That guess sends a user with
        a typo'd phone into a pointless 30-minute cooldown. Judge the response body."""
        b = (body or "").lower()
        if any(k in b for k in ("recaptcha", "captcha", "score", "robot", "suspicious")):
            return "recaptcha"
        if any(k in body for k in ("פרטים שגויים", "פרטים לא", "שגוי", "לא נמצא", "לא קיים")) or \
           any(k in b for k in ("invalid", "unauthorized", "not found", "incorrect")):
            return "credentials"
        if status in (401, 403):
            return "credentials"
        return "unknown"

    async def _warm_cold_profile(self, page: "Page") -> None:
        """Give a brand-new profile something to be scored ON, before the one submit.

        reCAPTCHA Enterprise scores the profile making the request: its Google
        cookies, its site history, and the human-ness of the interaction. A
        first-ever profile has none of that and gets rejected instantly — which is
        why Mor works on a dev box that's run it for months and fails on a new
        agent's PC. Warming is strictly NON-SUBMITTING (a rejected submit lowers the
        score further, so this must happen before the first attempt, never as a
        retry): let Google set its cookies, then dwell on Mor's page with real
        pointer movement while the Enterprise script collects signals."""
        from app.services.portal_automation.runner import logger as _llog
        _llog.info("Mor: COLD profile — warming up before first submit")
        try:
            await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)
            for x, y in ((320, 240), (520, 380), (700, 300)):
                await page.mouse.move(x, y)
                await page.wait_for_timeout(350)
        except Exception as e:
            _llog.warning("Mor: warm-up google step failed (continuing): %s", e)
        try:
            await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=40000)
            try:
                await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            # Dwell on the login page with human-ish pointer movement + a scroll.
            for i in range(12):
                await page.mouse.move(260 + i * 28, 200 + (i % 4) * 45)
                await page.wait_for_timeout(1200)
            await page.mouse.wheel(0, 220)
            await page.wait_for_timeout(2500)
            await page.mouse.wheel(0, -220)
        except Exception as e:
            _llog.warning("Mor: warm-up dwell failed (continuing): %s", e)
        _llog.info("Mor: warm-up done")

    async def login(self, page: "Page", username: str, password: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        license_no, id_no, phone = self._split(username, password)

        # Record what Mor's SERVER says when it rejects, so the failure message is a
        # measurement instead of a guess. Registered before any navigation.
        #
        # A bare `400 {"resultCode":"Bad Request"}` — no "score"/"captcha" wording,
        # no HTTP 401/403 — reads like a PAYLOAD-SHAPE rejection (a malformed/empty
        # field failing schema validation), not the usual score-based gate (which
        # returns 200 + a friendly rejection body). Capture the REQUEST body too
        # (field NAMES + lengths only — never the raw token/value) so a future
        # failure can show whether e.g. the reCAPTCHA token field was empty/short,
        # instead of only ever seeing the response. Also keep every POST to
        # more.co.il seen during the window (`all_posts`), not just the one that
        # first looked like a rejection — a background telemetry/health call
        # returning its own 400 could otherwise get misattributed as the login
        # response.
        srv: dict = {"status": None, "body": "", "url": "", "req": ""}
        all_posts: list[str] = []

        def _describe_req_body(raw: str) -> str:
            """Field names + lengths only — a reCAPTCHA Enterprise token is a
            long opaque string, so an EMPTY or unusually short value here is the
            decisive signal, without logging the token/credentials themselves."""
            if not raw:
                return "EMPTY"
            try:
                import json as _json
                obj = _json.loads(raw)
                if isinstance(obj, dict):
                    parts = []
                    for k, v in obj.items():
                        if isinstance(v, str):
                            parts.append(f"{k}=len{len(v)}")
                        else:
                            parts.append(f"{k}={v!r}")
                    return "{" + ", ".join(parts) + "}"
            except Exception:
                pass
            # NON-JSON bodies: field NAMES only, never values. This used to
            # return `raw[:120]`, which for a form-encoded login body
            # (`licenseId=…&identity=…&phoneNumber=…`) put the licence, the
            # national ID and the phone verbatim into the Railway worker log AND
            # into run.error_message shown in the UI — while the docstring above
            # promised "never the raw token/value". Background POSTs are exactly
            # the ones most likely to be non-JSON, so this path is not rare.
            try:
                from urllib.parse import parse_qsl
                pairs = parse_qsl(raw, keep_blank_values=True)
                if pairs:
                    return "{" + ", ".join(f"{k}=len{len(v)}" for k, v in pairs) + "}"
            except Exception:
                pass
            return f"len{len(raw)} (non-json, values withheld)"

        async def _on_resp(resp):
            try:
                if resp.request.method != "POST" or "more.co.il" not in resp.url:
                    return
                body = ""
                try:
                    body = (await resp.text())[:600]
                except Exception:
                    pass
                req_body = ""
                try:
                    req_body = resp.request.post_data or ""
                except Exception:
                    pass
                all_posts.append(f"{resp.status} {resp.url} req={_describe_req_body(req_body)}")
                if resp.status >= 400 or "שגיא" in body:
                    srv["status"], srv["body"], srv["url"] = resp.status, body, resp.url
                    srv["req"] = req_body
            except Exception:
                pass

        page.on("response", _on_resp)

        if self.profile_was_cold:
            await self._warm_cold_profile(page)

        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=40000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)

        safe = re.sub(r"[^A-Za-z0-9_]", "_", license_no)[:32] or "anon"
        land = SCREENSHOT_ROOT / f"mor_login_{safe}.png"
        await self._safe_screenshot(page, land)
        await self._dump_page_state(page, land)

        # Angular reactive form + Kendo inputs: page.fill() leaves the controls
        # ng-pristine/ng-invalid so the submit button stays disabled. Real
        # KEYSTROKES are required to drive Angular's validation. The ת"ז field
        # needs 9 digits and the phone 10 — pad a leading zero when the stored
        # value drops it (operator stores 40336281 / 504302306).
        # The ת"ז and the phone are padded to 9 / 10. The LICENSE is NOT — it is
        # its own number (מספר רשיון (ת.ז/ח.פ)) and is 8 digits with no leading
        # zero. A working manual login was captured 2026-07-20:
        #     מספר רשיון (ת.ז/ח.פ)      40336281     <- 8, NO leading zero
        #     מספר זהות של המשתמש/ת     040336281    <- 9
        #     טלפון נייד                0504302306   <- 10
        # This block used to pad the license too, on a 2026-06-28 guess that the
        # server "wants the 9-digit form for BOTH". That guess turned 40336281
        # into 040336281 and is what produced `400 {"resultCode":"Bad Request"}`
        # on every run: the instrumentation showed licenseId=len9 while the real
        # form submits len8. Editing the stored credential could never fix it —
        # the padding re-applied on the way out, which is why the DB held the
        # correct 8-digit value and the wire still carried 9.
        # Do not re-add license padding without a fresh screenshot of the form.
        if len(id_no) == 8 and not id_no.startswith("0"):
            id_no = "0" + id_no
        if len(phone) == 9 and not phone.startswith("0"):
            phone = "0" + phone

        # ---- Form-ready retry ---------------------------------------------------
        # On a COLD persistent-profile (first run after a worker restart) the
        # Angular reactive form may take longer than 15 s to paint, or a
        # transient reCAPTCHA challenge causes the page to blank-reload after
        # cookies settle.  Retry up to 4 times (re-goto between attempts, 22 s
        # each) so the first batch run of the day self-heals without human
        # intervention.  Dump screenshot + state on every miss so the next
        # failure is diagnosable even without a live re-run.
        _FORM_FIELD = "input[formcontrolname='licenseId']"
        _MAX_ATT = 4
        _form_ready = False
        for _att in range(1, _MAX_ATT + 1):
            try:
                await page.wait_for_selector(_FORM_FIELD, state="visible", timeout=22000)
                _form_ready = True
                break
            except Exception:
                # Dump what the browser shows right now
                _retry_path = SCREENSHOT_ROOT / f"mor_login_{safe}_retry{_att}.png"
                await self._safe_screenshot(page, _retry_path)
                await self._dump_page_state(page, _retry_path)
                # Detect an obvious block / error page for the diagnostic txt
                try:
                    _body_text = await page.evaluate(
                        "() => (document.body && document.body.innerText || '').slice(0, 800)"
                    )
                except Exception:
                    _body_text = ""
                # Log the detection in the .txt (already written by _dump_page_state);
                # do NOT raise yet — a reload may still recover the session.
                _ = any(
                    kw in _body_text
                    for kw in ("אירעה שגיאה", "שגיאה", "reCAPTCHA", "Access Denied", "blocked")
                )
                if _att < _MAX_ATT:
                    # Re-navigate so the persistent-profile cookies & reputation
                    # get another chance to satisfy reCAPTCHA Enterprise.
                    try:
                        await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=40000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=12000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(3000)
                    except Exception:
                        pass

        if not _form_ready:
            _fail_path = SCREENSHOT_ROOT / f"mor_login_{safe}_failed.png"
            await self._safe_screenshot(page, _fail_path)
            await self._dump_page_state(page, _fail_path)
            raise RuntimeError(
                f"Mor: שדה הכניסה (licenseId) לא הופיע לאחר {_MAX_ATT} ניסיונות טעינה — "
                f"בדוק mor_login_{safe}_retry*.txt לאיבחון."
            )
        # -------------------------------------------------------------------------

        async def _type(sel: str, val: str):
            await self._wait_visible(page, sel, timeout=15000)
            await page.click(sel)
            await page.keyboard.type(val, delay=70)
            cur = await page.input_value(sel)
            if cur != val:  # retry once if a char dropped
                await page.fill(sel, "")
                await page.click(sel)
                await page.keyboard.type(val, delay=90)

        # Fill + submit, with ONE retry on a transient reCAPTCHA-Enterprise
        # rejection. Mor's server returns "אירעה שגיאה" post-submit when Google
        # scores the session low (cold profile / low recent activity) — NOT a bad
        # credential. The reCAPTCHA token has a short TTL, so waiting ~90s and
        # re-navigating earns a fresh scoring window. Retry once before failing so
        # a single bad score doesn't kill the whole batch run (it passed yesterday
        # on the same creds). See math/diagnosis: the run died in 11s on attempt 1.
        otp_sel = "#otpInput, input[formcontrolname='otpCode']"
        # Single submit — the recovery below patiently waits instead of re-navigating
        # (re-nav + re-submit just burns the reCAPTCHA score further).
        _MAX_SUBMIT_ATT = 1
        for _att in range(1, _MAX_SUBMIT_ATT + 1):
            if _att > 1:
                await page.wait_for_timeout(90_000)  # let the old reCAPTCHA token expire
                try:
                    await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=40000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    await page.wait_for_selector(_FORM_FIELD, state="visible", timeout=22000)
                except Exception:
                    pass

            await _type("input[formcontrolname='licenseId']", license_no)
            await _type("input[formcontrolname='identity']", id_no)
            await _type("input[placeholder*='טלפון']", phone)
            await page.keyboard.press("Tab")

            # Kendo/Angular validate asynchronously — WAIT for the submit button to
            # actually enable before clicking (a premature click hits the disabled
            # button and no-ops, leaving us stuck on the login form).
            try:
                await page.wait_for_selector(
                    "button[type='submit']:not([disabled])", state="attached", timeout=12000
                )
            except Exception:
                err = await page.evaluate(
                    "() => [...document.querySelectorAll('.k-tooltip, [id^=kendo-error]')]"
                    ".map(e => e.innerText.trim()).filter(Boolean).join(' | ')"
                )
                raise RuntimeError(f"Mor: כפתור הכניסה נשאר מושבת (טופס לא תקין). שגיאות: {err or 'אין'}")

            # ── The FOURTH field: the reCAPTCHA token ────────────────────────
            # Mor's login page loads INVISIBLE reCAPTCHA:
            #   recaptcha/api.js?onload=reCaptchaOnloadCallback&render=6Letqt…
            # and the rendered form carries `id="g-recaptcha-response-100000"`.
            # The page's own JS mints a token into that element; the login POST
            # is supposed to carry it alongside licenseId/identity/phoneNumber.
            #
            # We were clicking submit as soon as Angular enabled the button —
            # BEFORE the token existed — so the request went out with only three
            # fields and Mor answered `400 {"resultCode":"Bad Request"}`. That is
            # a malformed-payload rejection, not a score rejection (a low score
            # returns 200 + a rejection body), which is why six timing/ordering/
            # credential hypotheses all failed: none of them could conjure a
            # token that was never being produced. Confirmed from the saved page
            # dumps (data/portal_screenshots/mor_login_*.html) plus the request
            # instrumentation, which showed exactly 3 fields and no token.
            token_ok = False
            try:
                await page.wait_for_function(
                    """() => {
                        const el = document.querySelector("[id^='g-recaptcha-response']");
                        return !!(el && (el.value || '').length > 20);
                    }""",
                    timeout=25000,
                )
                token_ok = True
            except Exception:
                pass

            if not token_ok:
                # SUBMIT ANYWAY. Do NOT turn this into a hard refusal.
                #
                # An earlier revision raised here. That was unsafe: with INVISIBLE
                # reCAPTCHA the token is very often minted by `grecaptcha.execute()`
                # wired to the submit handler — i.e. only AFTER the click. If that
                # is the mechanism here, refusing to click means the token can
                # never appear and Mor is permanently bricked by its own fix.
                # The one recorded success (2026-07-14 12:48 standalone) ran under
                # code that clicked immediately, which is evidence the click is
                # part of the mint path rather than something to withhold.
                # Waiting first is still right — if the page mints eagerly we now
                # carry the token instead of racing it. But when the wait expires
                # the honest move is to try, and say what we saw.
                #
                # CORRECTION (do not restore the earlier wording): this comment
                # used to claim the tokenless submits also degraded meitav via a
                # "shared reCAPTCHA score". That is REFUTED, and by this very
                # fix. If no token was transmitted, Mor's backend never called
                # createAssessment, so Google never scored those attempts —
                # there was no assessment to fail and no reputation to degrade.
                # The two claims cannot both be true. Independently: profiles are
                # per-portal (`BROWSER_PROFILE_ROOT / portal_kind`, runner.py) so
                # the cookie jars are separate, the site keys differ (mor
                # 6Letqt… via api.js, meitav 6LehTw… via enterprise.js), and
                # meitav's `לא נמצאו שדות` failure is raised at meitav.py:137
                # BEFORE any POST — a score cannot delete form fields. meitav
                # runs at ~19% flake across every position (see batch_runner.py);
                # its failures are its own.
                tok_len = await page.evaluate(
                    """() => {
                        const el = document.querySelector("[id^='g-recaptcha-response']");
                        return el ? (el.value || '').length : -1;
                    }"""
                )
                state = "השדה לא קיים בדף" if tok_len == -1 else f"נשאר ריק (len={tok_len})"
                try:
                    from app.services.portal_automation.runner import _worker_note
                    _worker_note(
                        f"mor: recaptcha token not present pre-click ({state}) — "
                        "submitting anyway (invisible reCAPTCHA may mint on click)"
                    )
                except Exception:
                    pass
                self.partial_errors.append(
                    f"Mor: אסימון reCAPTCHA לא נוצר לפני השליחה ({state}) — נשלח בכל זאת"
                )

            await page.click("button[type='submit']:not([disabled])")

            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            post = SCREENSHOT_ROOT / f"mor_login_{safe}_post_submit{_att}.png"
            await self._safe_screenshot(page, post)
            await self._dump_page_state(page, post)

            # After submit Mor either opens the OTP MODAL (#otpInput,
            # formcontrolname="otpCode", maxlength 6) or shows "אירעה שגיאה".
            deadline = 30
            _rejected = False
            for _ in range(deadline * 2):
                if await page.locator(otp_sel).count() and await page.locator(otp_sel).first.is_visible():
                    return  # OTP modal open — success
                try:
                    err = page.locator("text=אירעה שגיאה")
                    if await err.count() and await err.first.is_visible():
                        _rejected = True
                        break
                except Exception:
                    pass
                await page.wait_for_timeout(500)

            if _rejected:
                # "אירעה שגיאה" post-submit means EITHER a low reCAPTCHA-Enterprise
                # score OR wrong פרטים — the toast is identical, so ask the SERVER
                # which it was (srv[] was captured off the POST response).
                #
                # Ship this via `_worker_note` (reaches Railway logs), NOT
                # `logger.info` — a prior fix here used `_logger.info` and was
                # undiagnosable because that only writes the WORKER's local log
                # file, which we never see. See memory `mor_batch_recaptcha_score`.
                from app.services.portal_automation.runner import _worker_note, logger as _llog
                cause = self._classify(srv.get("status"), srv.get("body", ""))
                _worker_note(
                    f"mor login rejected: cause={cause} http={srv.get('status')} "
                    f"url={srv.get('url')} resp_body={srv.get('body', '')[:300]!r} "
                    f"req_body={_describe_req_body(srv.get('req', ''))} "
                    f"all_posts({len(all_posts)})={' || '.join(all_posts[:8])}"[:1800]
                )

                # Wrong credentials will NEVER heal by waiting or re-clicking, and each
                # extra submit costs reCAPTCHA score. Fail straight away and tell the
                # user which field to check.
                if cause == "credentials":
                    raise RuntimeError(
                        "Mor: הפרטים נדחו על ידי מור (לא ציון reCAPTCHA — השרת החזיר שגיאת פרטים). "
                        "בדוק מספר רשיון / תעודת זהות / טלפון. "
                        f"תשובת השרת: {srv.get('status')} {srv.get('body', '')[:160]}"
                    )

                # Otherwise: DO NOT spam re-clicks or re-navigate — each extra submit
                # lowers the score further (a rapid test loop once drove it low enough
                # that even manual clicks bounced). ONE gentle re-click, then PATIENTLY
                # wait for the OTP modal (~2 min) so a transient recovery — or an
                # operator clicking התחבר on the headed worker — carries it through.
                try:
                    btn = page.locator(
                        "button[type='submit']:not([disabled]), "
                        "button:has-text('התחבר'):not([disabled]), "
                        "button:has-text('כניסה'):not([disabled])"
                    ).first
                    await btn.wait_for(state="visible", timeout=6000)
                    await btn.click()
                except Exception:
                    pass
                _llog.info(
                    "Mor login: waiting up to 120s for OTP modal "
                    "(operator may click התחבר on the headed worker)"
                )
                for _i in range(60):  # 60 × 2s = 120s
                    if await page.locator(otp_sel).count() and await page.locator(otp_sel).first.is_visible():
                        _llog.info("Mor login: OTP modal opened (recovered) after ~%ds", _i * 2)
                        return
                    await page.wait_for_timeout(2000)

                # Report the evidence, not a theory. `cold` matters: a first-ever
                # profile on a new agent's PC is the classic low-score case.
                _cold = " (פרופיל חדש במחשב הזה — ניקוד reCAPTCHA נמוך אופייני)" if self.profile_was_cold else ""
                _srv_txt = (
                    f" תשובת השרת: {srv.get('status')} {srv.get('body', '')[:160]}"
                    if srv.get("status") or srv.get("body") else " (השרת לא החזיר גוף שגיאה)"
                )

                # `cause == "unknown"` means the body itself is silent (Mor's own
                # generic 400 — see _classify). But this credential's OWN run
                # history is a MEASURED fact the plugin does have: if the exact
                # same license/id/phone succeeded recently, that already RULES
                # OUT a typo'd/rotated credential (those don't intermittently
                # start working again) without asserting reCAPTCHA as a guess.
                # Proven live 2026-07-14: this exact username succeeded at 12:48
                # (490 records) and was rejected with this exact body at 15:50,
                # inside a batch that had just run 9 other portal logins from the
                # same worker/IP in the preceding ~14 minutes.
                _recent_note = ""
                if cause == "unknown" and self.cred_last_run_status == "success" and self.cred_last_run_at:
                    from datetime import datetime as _dt
                    _last = self.cred_last_run_at
                    _now = _dt.now(_last.tzinfo) if _last.tzinfo else _dt.utcnow()
                    _hrs = (_now - _last).total_seconds() / 3600
                    # 0 <= _hrs, not just < 24: `last_run_at` is written from the
                    # WORKER's clock while this compares against local now, and a
                    # worker PC running fast/slow is a shipped failure mode here
                    # (see memory otp_worker_clock_skew). A negative delta would
                    # render "לפני כ--2.0 שעות" and read as a bug to the agent.
                    if 0 <= _hrs < 24:
                        _recent_note = (
                            f" הפרטים תקינים (אותם פרטים הצליחו לפני כ-{_hrs:.1f} שעות) — "
                            "כנראה ניקוד reCAPTCHA שירד עקב ריצות אוטומטיות רבות ברצף (למשל בתוך "
                            "אותו באטצ'), לא בעיית פרטים."
                        )

                # Compact request-payload summary (field names + lengths only) so
                # the DECISIVE evidence — was the reCAPTCHA token field empty/short? —
                # lands in run.error_message itself, not only in the Railway
                # worker-log (which needs a separate `railway logs` grep to see).
                _req_txt = f" req={_describe_req_body(srv.get('req', ''))[:200]}"

                raise RuntimeError(
                    f"Mor: הכניסה נדחתה (אירעה שגיאה){_cold}. סיבה משוערת: "
                    f"{'ציון reCAPTCHA נמוך' if cause == 'recaptcha' else 'לא ודאית'}."
                    f"{_recent_note}{_srv_txt}{_req_txt} המתן ~20-30 דקות ונסה שוב."
                )
            raise RuntimeError("Mor: מודאל ה-OTP לא נפתח תוך 30 שניות")

    async def submit_otp(self, page: "Page", otp: str) -> None:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        digits = re.sub(r"\D", "", otp or "")[:6]
        otp_sel = "#otpInput, input[formcontrolname='otpCode']"
        filled = False
        try:
            await self._wait_visible(page, otp_sel, timeout=8000)
            await page.click(otp_sel)
            await page.keyboard.type(digits, delay=70)  # Angular needs keystrokes
            filled = True
        except Exception:
            try:
                await page.fill(otp_sel, digits, timeout=3000)
                filled = True
            except Exception:
                pass
        await page.wait_for_timeout(400)
        # CRITICAL: the OTP submit button lives inside the <app-otp> dialog, but
        # the LOGIN form BEHIND the modal ALSO has a `type=submit` "כניסה" button
        # that appears FIRST in the DOM. A bare `button:has-text('כניסה')` clicks
        # that background button → the OTP is never submitted and the modal just
        # sits there (no error). Scope the click to the dialog; fall back to
        # pressing Enter inside the OTP field.
        clicked = await self._click_first_visible(page, [
            "app-otp button[type='submit']",
            ".k-dialog-content button[type='submit']",
            "app-otp button:has-text('כניסה')",
        ], timeout=6000)
        if not clicked:
            try:
                await page.focus(otp_sel)
                await page.keyboard.press("Enter")
            except Exception:
                pass
        # Accepted ⇒ the OTP dialog detaches (the SPA keeps the URL on
        # /agents/login, so don't gate on the URL).
        try:
            await page.wait_for_selector("app-otp", state="detached", timeout=20000)
        except Exception:
            pass
        post = SCREENSHOT_ROOT / "mor_post_otp.png"
        await self._safe_screenshot(page, post)
        await self._dump_page_state(page, post)
        if not filled:
            raise RuntimeError("Mor: לא נמצא שדה OTP — בדוק mor_login_*_post_submit.txt")
        # If the OTP dialog is still open, the code was rejected (or the click
        # missed) — fail with the on-screen error instead of silently navigating
        # download_reports against the login page.
        if await page.locator("#otpInput").count() and await page.locator("#otpInput").first.is_visible():
            err = await page.evaluate(
                "() => {const e=document.querySelector('.erroronbatt');return e?e.innerText.trim():'';}"
            )
            raise RuntimeError(
                f"Mor: קוד ה-OTP לא התקבל (מודאל ה-OTP עדיין פתוח). {('שגיאה: '+err) if err else ''}"
            )

    async def download_reports(self, page: "Page", download_dir: Path, **kwargs) -> list[Path]:
        from app.services.portal_automation.runner import SCREENSHOT_ROOT
        run_id = download_dir.name
        download_dir.mkdir(parents=True, exist_ok=True)
        self.report_password = None

        async def ck(tag):
            p = SCREENSHOT_ROOT / f"{run_id}_{tag}.png"
            await self._safe_screenshot(page, p)
            await self._dump_page_state(page, p)

        await ck("nav_0_home")

        # 0) Dismiss the post-login announcement modal. Mor shows a custom Angular
        #    modal on login (<lib-modal id="mainModal" class="response-modal">, e.g.
        #    the "סוכנות וסוכנים יקרים" updated-bank-account notice — a הבא/קודם
        #    slideshow). Its .lib-modal-background backdrop (z-index 99998,
        #    rgba(0,0,0,.75)) intercepts pointer events, so the תגמול drawer click
        #    below is swallowed and no report downloads.
        #
        #    VERIFIED against the live failed-run dump (9677d0fd_nav_0_home): the
        #    ✕ is `button.btn-close-modal` but it's ICON-ONLY (no text) and can sit
        #    off the visible-elements list, so a plain click may miss — and on a
        #    multi-slide modal the ✕ may only appear on the last slide. So: try the
        #    ✕ + Escape a few times, then GUARANTEE dismissal by nuking the modal in
        #    the DOM (hide #mainModal, remove the backdrop, drop body.g-modal-open).
        #    All steps are full no-ops when no modal is present.
        for _ in range(3):
            try:
                close_btn = page.locator("button.btn-close-modal")
                if not await close_btn.count():
                    break
                clicked = False
                for j in range(min(await close_btn.count(), 5)):
                    b = close_btn.nth(j)
                    try:
                        if await b.is_visible():
                            await b.click(timeout=3000)
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    try:
                        await close_btn.first.click(timeout=2000, force=True)
                    except Exception:
                        pass
                await page.wait_for_timeout(700)
            except Exception:
                break
        # Escape as a second-chance dismiss (Angular listens for it on some modals).
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)
        except Exception:
            pass
        # Bulletproof fallback: if ANY response-modal / backdrop is still in the DOM,
        # remove it outright so the drawer click can't be intercepted. It's only an
        # announcement — tearing it down client-side is safe.
        try:
            await page.evaluate(
                """() => {
                    document.querySelectorAll(
                        'lib-modal, .lib-modal, .lib-modal-background, .response-modal'
                    ).forEach(el => el.remove());
                    document.body.classList.remove('g-modal-open');
                    document.body.style.overflow = '';
                }"""
            )
            await page.wait_for_timeout(300)
        except Exception:
            pass
        await ck("nav_0b_after_modal")
        from app.services.portal_automation.runner import logger as _mlog
        try:
            _backdrop = await page.locator(
                ".lib-modal-background, lib-modal#mainModal, .response-modal"
            ).count()
            _mlog.info(
                "Mor nav: after modal-dismiss — url=%s backdrop_remaining=%d",
                page.url, _backdrop,
            )
        except Exception:
            pass

        # 1) Right side-menu (Kendo drawer) → "חישוב תגמול" — the DETAILED
        #    commission-calculation report (the agent calls it "חישוב עמלות").
        #    IMPORTANT: the sibling "תגמול" (index 8) is only a monthly SUMMARY
        #    (חודש/סטטוס/נפרעים/דמי סליקה/…) with NO policy-level detail and no
        #    id_number — the parser rejects it (unknown_format_known_company). The
        #    real per-policy נפרעים lives under "חישוב תגמול" (index 9): pick the
        #    latest month there, THEN export.
        await self._click_first_visible(page, [
            "li[aria-label='חישוב תגמול']",
            "li[data-kendo-drawer-index='9']",
            "li[aria-label='חישוב תגמול'] span.k-item-text",
        ], timeout=12000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        await ck("nav_1_calc")
        try:
            _mlog.info("Mor nav: after חישוב תגמול click — url=%s", page.url)
        except Exception:
            pass

        # 2) חישוב תגמול shows NO data until a MONTH is chosen: the startDate Kendo
        #    date-picker is empty on load (grid = "NO DATA FOUND"), so exporting
        #    immediately yields an empty 19-column file. Set the latest month that
        #    HAS data (Mor נפרעים lags → walk back from this month), click חפש to
        #    load the grid, THEN export. Reference of a correct file:
        #    Desktop/KIKO/12_2025_נפרעים מור.xlsx = 455 rows × 19 cols.
        from datetime import date as _date
        import re as _re

        # The picker is a MONTH field displayed as MM/YYYY (verified live — it read
        # "01/2025", NOT a dd/mm/yyyy date). Type exactly 6 digits: MM then YYYY.
        date_input = page.locator(
            "kendo-datepicker[formcontrolname='startDate'] input.k-input, "
            "kendo-datepicker[formcontrolname='startDate'] input"
        ).first
        search_btn = page.locator("button:has-text('חפש')").first

        async def _result_count() -> int:
            # The pager reads "1 - 10 מתוך 367 תוצאות" — the total after מתוך is the
            # authoritative row count (the grid rows themselves have no k-master-row
            # class, so counting <tr> undercounts). Fall back to visible data rows.
            try:
                txt = await page.locator(
                    "text=/מתוך\\s+[\\d,]+\\s+תוצאות/"
                ).first.inner_text(timeout=3000)
                mm = _re.search(r"מתוך\s+([\d,]+)\s+תוצאות", txt)
                if mm:
                    return int(mm.group(1).replace(",", ""))
            except Exception:
                pass
            if await page.locator("kendo-grid .k-grid-norecords").count():
                return 0
            try:
                return await page.locator("kendo-grid tbody tr").count()
            except Exception:
                return 0

        today = _date.today()
        loaded = 0
        found_m, found_y = today.month, today.year
        for back in range(0, 10):
            m, y = today.month - back, today.year
            while m <= 0:
                m += 12
                y -= 1
            digits = f"{m:02d}{y}"  # MM YYYY — Kendo month-input auto-advances segments
            try:
                await date_input.click(timeout=6000)
                await page.keyboard.press("Control+A")
                await date_input.type(digits, delay=90)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(400)
                await search_btn.click(timeout=6000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:
                    pass
                await page.wait_for_timeout(1800)
                cnt = await _result_count()
                _mlog.info("Mor: month %02d/%d → %d results", m, y, cnt)
                if cnt > 0:
                    loaded, found_m, found_y = cnt, m, y
                    break
            except Exception as e:
                _mlog.warning("Mor: month %02d/%d select/search failed: %s", m, y, e)
        _mlog.info("Mor: month selection done — %d results for %02d/%d", loaded, found_m, found_y)
        await ck("nav_1b_month_selected")
        if loaded == 0:
            # Don't export an empty grid (it would ingest as a false-success 0-row
            # file). Surface a clear error + the dump so the month-pick can be fixed.
            raise RuntimeError(
                f"Mor: לא נטענו נתונים ב'חישוב תגמול' לאף חודש (10 חודשים אחורה). "
                f"בחירת החודש/חיפוש נכשלו — בדוק {run_id}_nav_1b_month_selected.{{png,html,txt}}"
            )

        # Embed the loaded month (MM-YYYY) in the filename so detect_period_month
        # reads it directly (step 2) instead of falling back to data-date inference.
        target = download_dir / f"מור נפרעים {found_m:02d}-{found_y}.xlsx"
        xhr = {"bytes": None}

        async def on_resp(resp):
            try:
                cd = resp.headers.get("content-disposition") or ""
                ct = resp.headers.get("content-type") or ""
                if any(x in (cd + ct).lower() for x in ("spreadsheet", ".xlsx", ".xls", "excel", "octet-stream")):
                    b = await resp.body()
                    if b and len(b) > 1024 and xhr["bytes"] is None:
                        xhr["bytes"] = b
            except Exception:
                pass
        page.on("response", on_resp)

        got = None
        try:
            async with page.expect_download(timeout=20000) as dl:
                await self._click_first_visible(page, [
                    "button:has-text('ייצוא לאקסל')",
                    "a:has-text('ייצוא לאקסל')",
                    "button:has-text('אקסל')",
                    "*:has-text('ייצוא')",
                    "button:has-text('הורד')",
                    "[title*='Excel' i]",
                    "img[src*='excel' i]",
                ], timeout=12000)
            d = await dl.value
            await d.save_as(str(target))
            got = target
        except Exception:
            if xhr["bytes"]:
                target.write_bytes(xhr["bytes"])
                got = target

        await ck("nav_2_after_export")
        if not got:
            raise RuntimeError(f"Mor: לא ירד קובץ — בדוק {run_id}_nav_1_commissions.txt / _nav_2_after_export.txt")
        return [got]
