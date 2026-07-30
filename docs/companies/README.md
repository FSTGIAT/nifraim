# Insurer Portal Companies — status & playbook

One file per company. Each covers: portal URL, login/OTP, the gate (reCAPTCHA/APM), the
download flow, known issues, and the 2026-07-24 fixes. Read the company's md **before** touching its
plugin. Deep history lives in the `memory/` files each doc links.

## Status snapshot (kikohib, 2026-07-24 — after the run-all batch)

| Company | Delivers | Status | Blocker / note |
|---------|----------|--------|----------------|
| [analyst](analyst.md) | נפרעים | ✅ WORKING end-to-end (07-25 06:45, downloaded file) | login=recycle to fresh profile; OTP=retry newest code on errorCode:2 |
| [clal](clal.md) | production (box) + נפרעים | box mechanism solved+deployed | creds are FINE (worked 14:57); 16:02 was a transient F5 session reject — just re-run. Then finalise box parser |
| [hachshara](hachshara.md) | נפרעים | ✅ FIXED + verified (356 rows) | production comes by EMAIL, not this portal |
| [altshuler](altshuler.md) | נפרעים | ✅ spinner reload-retry + NaN repair | login SPA was hanging on the spinner |
| [harel](harel.md) | production + נפרעים + vault | agents-portal ✅; vault fails LOUD now | vault needs `<agents>\|<vault>` pw or its own login |
| [meitav](meitav.md) | נפרעים | works but ~19% flaky | post-OTP session bounce seen; Edge required |
| [mor](mor.md) | נפרעים | ✅ working | reCAPTCHA-gated (score) |
| [menora](menora.md) | production + נפרעים | ✅ working | reversed creds for נפרעים |
| [migdal](migdal.md) | production + נפרעים | ✅ working | |
| [phoenix](phoenix.md) | production (terminal) + נפרעים | ✅ working | terminal is Windows-native, worker-only |
| [yelin](yelin.md) | נפרעים | ✅ working | |

## The three failure classes (so results stop looking random)
1. **Login-stage, transient/session** — e.g. an F5 APM stale-session reject that renders the logon page
   with a "wrong credentials" text even though the password is fine (Clal 16:02, after a 14:57 success).
   The run dies BEFORE any download fix runs. Usually clears on a re-run — verify with the run HISTORY
   (did the same creds succeed recently?) before ever telling someone to change a password.
2. **Login-stage, page/gate** — reCAPTCHA score (analyst/meitav/mor), slow SPA (altshuler spinner),
   F5 APM stale session. Fixed with the right browser/profile, reload-retries, and score shedding.
3. **Download-stage** — the actual plugin logic (clal box iframe, hachshara nav). This is where the
   2026-07-24 download fixes live; a run only reaches them if login succeeds.

## How to debug a failure (evidence-first)
See `.claude/skills/portal-automation/SKILL.md` → "Following a LIVE batch run & fixing on the fly".
Short version: failed/partial runs **auto-upload** their dumps → `GET /api/portal-automation/_debug/screenshots`.
Read the portal's OWN JS/HTML dump; never invent a selector. Don't hammer login (portals lock).
