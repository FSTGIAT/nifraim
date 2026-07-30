# הראל (Harel) — `harel_savings` (production) / `harel_commissions` (נפרעים) / vault

| | |
|---|---|
| Portal | `agents.harel-group.co.il/my.policy` (F5 APM) → `agents-int.harel-group.co.il` |
| Plugins | `companies/harel_savings.py`, `harel_commissions.py`, shared `_harel_report.py`, `harel.py` (vault) |
| Login | APM + SMS OTP. Credential may be `<agents-pw>` OR `<agents-pw>|<vault-pw>` (split on `|`) |

## Two report planes
- **Agents portal** (`agents-int…`): savings **production** (גמל/מגוון) + חיים/בריאות **נפרעים**. Works.
  Drills loop ALL מספר-חשבון accounts dynamically (memory `harel_multi_account`).
- **Safe vault** (`harelsafe.co.il`): the חיים/בריאות **production** "ר.ת.-מורחב" reports live ONLY here.

## The vault fold problem (diagnosed live 2026-07-24) — "downloaded only 1 of 5"
`harel_savings` folds a vault grab (`HarelPortal.download_reports`) after its agents-portal legs. The
vault relies on the APM **auto-SSO** landing straight on `harelsafe/frmReportStat?key=…` right after
OTP — the `key=` is **single-use**. But in the folded run that one-time SSO was already spent landing
on the AGENTS portal, so `goto(harelsafe/Login.aspx)` drops to a **password form** — which the agents
password does NOT open (the vault is a separate credential). Result: silent 0/5 reports.

**Live-confirmed:** kiko's vault login was rejected at `harelsafe.co.il/Login.aspx`; neither royg nor
kiko has a `|`-split vault password (both fall back to the agents pw). royg's standalone vault worked
because it used the SSO, not a password.

**Fix (2026-07-24):** the vault login now **fails loudly** — after the cmdOK postback, if still on
`Login.aspx`, raise a specific error: *"ה-SSO החד-פעמי כבר נוצל; שמור סיסמת-כספת נפרדת
('<agents>|<vault>') או הרץ את הכספת כהתחברות נפרדת."* No more silent 0/5. Wrapped best-effort so it
degrades to a partial (the agents-portal legs still return).

**To actually GET the 5 vault reports:** store the real harelsafe vault password as `<agents>|<vault>`,
OR run Harel-vault as its own login (keeps the post-OTP SSO). Config/architecture, not a code bug.

## Notes
- Real Chrome binary for the safe (bundled Chromium hits F5 errorcode-19/22). See `portal_harel*` memories.
