# מנורה (Menora) — `menora` (production) / `menora_nifraim` (נפרעים)

| | |
|---|---|
| Plugins | `companies/menora.py`, `companies/menora_nifraim.py` |
| Portal | `/agents-site` → כספות (vaults) |
| Production | filter DocTable rows by **פרודוקציה** (skip עמלות rows); ZIP → CSV. `07-24: מנורה - חיים פרודוקציה.zip` ✓ |
| נפרעים | creds are **REVERSED** (user=CODE, pass=phone); CSV-in-ZIP → `menora_amalot.py` |

## Status: WORKING (07-26 batch success — both legs)
## Gotchas (memory `portal_menora`, `portal_menora_nifraim`, `menora_legacy_parser`)
- Menora ID truncation + מבוטלות/snapshot dedup were fixed 2026-07-23 (`batch_qa_20260723`).
- Legacy `.ARJ` = misnamed ZIP of CP862 fixed-width `P.TXT`/`G.TXT`.

### ⚠️ The P.TXT offsets have now bitten TWICE — read before touching them

Both bugs were the same shape: a plausible-looking fixed-width slice, self-consistent
everywhere inside the parser, silently wrong against the real world.

| Field | Wrong slice | Correct | Found by |
|---|---|---|---|
| ת"ז | `[38:47]` | **`[38:48]`** | QA 07-23 "missing the last digit" |
| policy | `[4:11]` | **`[2:11]`, then `lstrip("0")`** | QA 07-26 "מספר הפוליסה מופיעה בלי שני המספרים הראשונים" |

`[0:2]` is a constant `06` marker; the `34/35/36/37` that follows it is the **policy's own
leading pair**, not a "record-type prefix" (which is what the docstring used to claim, and
is why the slice started at 4). The field is 9 wide and zero-padded, so the policy inside
can be shorter — measured on a live bundle: **72×9-digit, 7×8-digit, 1×7-digit**. Never
assert a fixed length.

**The parser cannot detect either error on its own** — the G.TXT premium join used the same
slice on both sides, so a wrong offset truncated both and still joined. Verify against an
**external** oracle: the נפרעים report's `מספר פוליסה` column for the same ת"ז. On a real
bundle that score went **1/80 → 80/80**.

Also fixed 07-26: `first_name`/`last_name` were **inverted**. The whole-field CP862 reverse
already undoes Menora's surname-first visual ordering, so `parts[0]` is the GIVEN name —
the old code mapped it to `last_name`.

**Tools**: `backend/tests/test_menora_legacy_parser.py` (no fixture needed) and
`backend/scripts/verify_menora_policy_width.py <zip>` (old-vs-new on the same bytes +
the נפרעים oracle; set `DATABASE_URL` for the oracle).

**Stored data is NOT retroactively fixed** — the parser change is forward-only.
