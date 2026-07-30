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

## 2026-07-30 — what was wrong, and the fixes (all live-verified on kiko's worker)

Clal ran GREEN in the batch but silently lost BOTH legs. One OTP drives both:
`ClalPortal.download_reports` does **production FIRST, then נפרעים** on the SAME APM
session (folds `ClalNifraimPortal` on the authenticated page). `clal_nifraim` is
`include_in_batch=False` — the folded leg, NOT a second OTP. Kiko clicks the
**"כלל — פרודוקציה"** card (not "כלל — עמלות (נפרעים)").

**Bug 1 — OTP: `submit_otp` killed a run whose OTP was ACCEPTED.** It ended with an
UNGUARDED `wait_for_load_state("networkidle", 20000)`. Clal's Angular SPA polls
forever and never idles → `Timeout 20000ms exceeded` at `stage=otp`. **Fix:** wrap
it in try/except (`clal.py`). The OTP was already accepted; download_reports has its
own checkpoints. *(This is why submit_otp is no longer "untouched" — the 2026-07-24
note that said so was wrong.)*

**Bug 2 — production `הורד` box relied on an incidental capture.** The InfoBay box is
`<a href="javascript:download();" class="lnkDownload" title="הורד">`. **Fix:** pin the
selector to `a.lnkDownload` + a direct `download()` frame-eval fallback
(`_harvest_bundle_modal`). The box is a **707KB ZIP-SFX .exe** → extracts a **Mimshak
(מסלקה) XML `.DAT`** → `upload_ingest` sniffs the `<Mimshak>` root → `parse_mimshak_dat`
→ `format='production'`. **Clal production (NEVER ingested before) now works via the
existing `services/mimshak/` path — no new parser.**

**Bug 3 — נפרעים `לפירוט עמלות` link "not found".** The anchor
(`href="../commissions" target="_blank"`) IS present but Angular keeps it in a
non-active panel, so the visibility-gated `_click_first_visible` skipped it → the run
degraded with no נפרעים. **Fix:** in-page dispatch fallback (`_open_commissions` in
`clal_nifraim.py`) — a direct `.click()` on the anchor; its `target=_blank` still
opens the tab `expect_page` catches. Live: one OTP → production + **3 נפרעים files**
(חיים 19 recs, בריאות 21 recs = 40 matchable).

**גמל נפרעים is an EMPLOYER-summary, not per-insured.** Its export columns are
`שם מעסיק / צבירה / סך עמלה` with **no ת"ז** → 0 matchable rows (correctly skipped).
Per-insured גמל DOES exist: the גמל drill has breakdown tabs `מעסיקים`/**`עמיתים`**/
`סוכני משנה`; it defaults to `מעסיקים`. Clicking **`עמיתים`** before export gives
per-ת"ז rows. NOT yet implemented (needs the tab click + a 1-OTP verify).

**Bug 4 — the standalone FOLD threw, causing TWO symptoms.** A single-company run
(`defer_post_ingest=False`) folds its data into the merged "מאוחד" production/נפרעים
file (`batch_runner.fold_standalone_run_into_merged`). It threw a **ForeignKeyViolation**
because `_delete_uploads` deleted the ESTABLISHED old merged file, which has a
`production_summary` (the batch only ever deletes fresh per-company uploads, so it
never hit this). The caught exception left the **session poisoned**, so:
  - the fold never consolidated → SPLIT production (old merged + a lone clal upload) →
    the download's latest-period logic showed **only clal, 1 row**;
  - `cred.last_run_status="success"` couldn't commit → **both cards showed a stale
    'failed' (Timeout 20000ms)** even though the run succeeded.
**Fixes:** (a) `_delete_uploads` clears `production_summaries`/`portal_snapshots`/
`debts` like the DELETE-production endpoint (861281b); (b) the fold `except` calls
`db.rollback()` so a fold failure can't poison the session (890da0e). See
[[standalone_fold_into_merged]].

**Not data loss — deduped.** After the fix the merged went 2458→1921 (הראל 1837→1299).
That's the INTENDED `_is_duplicate_catalogue_row` dedup (commit 4680b2f): money-less
product-presence rows (harel_vault: NULL policy) dedup by (company,id,product,
product_type). Idempotent — re-aggregating stays 1921.

**Clal production is 1 policy** (box `17853_כלל_חיים` → 1 Mimshak record: שי שלמה גורן).
The merged export is ONE "מאוחד" sheet; clal shows as 1 row with `חברה מקבלת=כלל`.

Commits: `935a13f` (clal fixes + fold), `861281b` (FK), `890da0e` (rollback).

## login() UNTOUCHED by the 2026-07-24 work; submit_otp fixed 2026-07-30 (see Bug 1).

## Key files & memory
`companies/clal.py`, `companies/clal_nifraim.py`; memory `portal_clal.md` (InfoBay map),
`clal_full_flow.md` (one-OTP two legs + the 3 fixes), `standalone_fold_into_merged.md`.
