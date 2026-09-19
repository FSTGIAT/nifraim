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

## Vault file layout (CP862 fixed-width) — the ת"ז is NOT at הכשרה's offset

The five `ר.ת.-מורחב` reports are parsed by `services/harel_vault_prod.py`, which reuses
`hachshara_prod`'s line parsers for the name / date / product / fund fields but **must not** reuse
its identity offsets: `[6:15]` — הכשרה's national-ID slice — is הראל's **policy number**.

| file | lines (kiko 07-2026) | policy | ת"ז | ת"ז check digit | same slice read as ת"ז |
|---|---:|---|---|---|---|
| `SP…` ר.ת.-מורחב חיים פוליסות | 65 | `[6:15]` | `[25:34]` | 64/65 | `[6:15]` → 2/65 |
| `RP…` ר.ת.-מורחב בריאות פוליסות | 229 | `[6:15]` | `[25:34]` | 228/229 | `[6:15]` → 19/229 |
| `SB…` ר.ת.-מורחב חיים ביטוחים | 107 | `[6:15]` | **none in file** | — | join to SP by policy (107/107) |
| `RB…` ר.ת.-מורחב בריאות ביטוחים | 1354 | `[6:15]` | `[70:79]` | 1353/1354 | `[6:15]` → 146/1354 |
| `RM….07R` ר.ת. פוליסות מגוון | 28 | `[0:9]` | **none in file** | — | join to SP by policy (26/28) |

Shared with הכשרה and verified correct on the real הראל files: last name `[43:58]`, first name
`[58:73]`, SP sign_date `[342:350]`, SB/RB product `[125:150]`, RM funds from 85 stride 30.

- **SB and RM carry no ת"ז at all** — `fill_identity_from_masters` joins theirs from the **SP**
  master by POLICY. RB has its own ת"ז and takes only the name, from **RP**, by ת"ז. The maps are
  per-family: SP and RP share exactly one policy number, so a merged map misattributes that row.
- Only RB has a ת"ז at `[70:79]`. Reading that slice on SB returns junk that still passes the
  check digit 16/106 of the time — a shape test alone does not catch it.
- `harel_vault_prod` logs a WARNING when under 80% of a file's ids pass the Israeli check digit.
  That is the offset tripwire; **never gate rows on it** (הראל books a few non-TZ identifiers).

**The bug this replaced (QA 2026-09-06):** every vault row's `מספר ת.ז` held a policy and
`מס' חשבון/פוליסה` was hardcoded `None` → 1,240 הראל rows in `פרודוקציה מאוחד` with a 0/1,240
policy column, and "גלעד בארי" filed under `103340379` (his policy) instead of `031400617`.
It also collapsed multiple insureds sharing one policy into a single row.

## Notes
- Real Chrome binary for the safe (bundled Chromium hits F5 errorcode-19/22). See `portal_harel*` memories.
