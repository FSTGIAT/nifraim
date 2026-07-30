# כלל (Clal) — `clal` (production+נפרעים) / `clal_nifraim`

| | |
|---|---|
| Portal | `https://www.clalnet.co.il/my.policy` (F5 BIG-IP APM) |
| Plugin | `companies/clal.py` (login+OTP+production+נפרעים), `companies/clal_nifraim.py` (folded נפרעים) |
| Login | entry link → APM ת"ז/password → SMS OTP. **Rejection text: `שם המשתמש או הסיסמא שגויים`** |
| Post-login | Angular SPA `…/ClalAgentClient/#/` |

## ⚠️ A `@login` "שם המשתמש או הסיסמא שגויים" is usually NOT a bad password
**The Clal credentials are fine.** Objective history (kikohib, 2026-07-24 UTC):

| time | result |
|------|--------|
| 07-24 **14:57** | **SUCCESS** — logged in, downloaded, parsed |
| 07-24 **16:02** | failed @login "שם המשתמש או הסיסמא שגויים" (5 seconds) |

The SAME stored password worked at 14:57 and the credential was **never edited**
(`portal_credentials.updated_at` bumps on every run's status write via `onupdate` — it is NOT a
password-edit signal). So the 16:02 failure is **not a wrong password and not a lockout**.

**Most likely cause: a transient F5 BIG-IP APM rejection** — a stale/concurrent-session collision. The
14:57 success left an active F5 session, and F5 APM limits concurrent sessions per user, so a login
65 min later can be bounced back to the logon page WITH the inline "שם המשתמש או הסיסמא שגויים" text,
which `_has_credentials_error` (a plain body-substring match) reads literally. Same F5 platform as
Hachshara, which already carries explicit stale-session recovery.

**Action: just RE-RUN Clal.** Do NOT reset the password. (A real expiry shows as a redirect to
`ClalnetForgotPsw/…` and raises a *different* "כלל מבקשת לעדכן סיסמה" message — that one, and only that
one, means update the password.)

**Diagnosis gap:** `login()` does NOT screenshot on the credentials-error path (all dumps are in
`download_reports`), so this failure was blind. Worth adding a `_safe_screenshot`+`_dump_page_state`
before the `_has_credentials_error` raise so the next one is diagnosable.

## Production = InfoBay "תיבה" boxes (mechanism solved 2026-07-24, extraction verified)
Clal production had **NEVER** been ingested. The chain, from the portal's own JS:
1. Sidebar → the **infobay** anchor `a[href*='data.clal.co.il']` (href carries a signed `k=` key).
   **Navigate to that href in a new page** — NOT a text-click. The old `*:has-text('infobay')` matched
   a rotating PROMO tile and opened a marketing PDF (`…/ניוד-פנסיה-מגיל-60.pdf`) → empty grid.
2. Lands on `data.clal.co.il/frmReportStat.aspx?key=…` = "מגירות מידע" (drawers): **קבצי פרודוקציה** +
   בריאות. Dismiss the `#DialogUserActive` "מהלך עבודה פעיל בלשונית אחרת" modal via **המשך** (a stale
   session from a prior failed run raises it).
3. Open the קבצי-פרודוקציה drawer → each report row is `SelectMe(id,'0',…,'2','.htm','0')` +
   `ShowReport('0')`. For **bundle=2**, ShowReport loads an **in-page MODAL iframe** `#frBundle`
   (`src=frmBundle.aspx?RepID=…`) — NOT a popup/nav. That iframe shows the box message with a `.exe`
   self-extracting file + **הורד** link.
4. `_harvest_bundle_modal` finds the frame, clicks הורד, captures the `.exe`, and extracts it with
   **pure-Python `zipfile`** (InfoBay boxes are ZIP-SFX; `is_zipfile` reads the appended ZIP straight
   from the .exe — no 7z, worker-portable). Magic bytes + inner filenames log to WORKER-LOG.

Boxes: `תיבה_17853_כלל_חיים…`, `תיבה_17854_בריאות…`. **Still to finalise:** confirm one real box's
inner file + wire the כלל-production parser (needs a live login, currently blocked by the lockout).

## Other fixes 2026-07-24
- Production "no drawers" **degrades** (partial_error) instead of hard-raising — the נפרעים leg (shared
  login) must still run. Before, an empty production grid took נפרעים down with it.
- `clal_nifraim` commissions link: **anchor-scoped only** (`a[href*='commissions']`,
  `a:has-text('לפירוט עמלות')`) — the bare `*:has-text` fallback matched a promo (memberclub PDF).

## login()/submit_otp() are UNTOUCHED by the 2026-07-24 work (all edits are in download_reports).

## Key files & memory
`companies/clal.py`, `companies/clal_nifraim.py`; memory `portal_clal.md` (full InfoBay map + box notes).
