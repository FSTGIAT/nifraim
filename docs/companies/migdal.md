# מגדל (Migdal) — `migdal` / `migdal_apm` → `migdal_nifraim`

| | |
|---|---|
| Plugins | `companies/migdal.py`, `migdal_apm` (נפרעים) |
| Download | 3 layers: nav pre-step → `expect_download` → XHR capture fallback |
| נפרעים | APM; `errorcode-19` = goto `apmaccess` href; nav כלים→משולמים→owner→ייצוא |
| Production | `07-24: מגדל - ייצור (יולי 2026).xlsx` ✓ |

## Status: WORKING (07-24 batch success)
## Gotchas
- DAT-vs-register dedup fixed 2026-07-23 (`batch_qa_20260723`, `portal_migdal_apm`, `portal_migdal_xhr_fallback`).
- OTP SMS wording uses `apmaccess` (not the brand name) — see `sms_otp_templates`.

### Open (latent, NOT fixed) — two COVRLIFE defects, found during the 07-26 Menora QA

Neither appears in the current live `מאוחד יולי` file: the 07-23 `seen_dat_policies` dedup
suppresses COVRLIFE rows that have a DAT twin. A COVRLIFE policy with **no** DAT twin would
still emit the bad form, so these are traps, not current corruption.

1. **The `01` prefix is stripped for the dedup key but not for the emitted cell.**
   `to_production_xlsx.py:306-311` does `policy_ref[2:]` then `lstrip("0")` → `20534274`;
   `xlsx_writer.py:479` does `_strip_zeros(_safe(1))` only → **`1020534274`**. Same source
   value, two spellings — and the correct `20534274` is already in the same file from the
   LIFEHLTH pass. Seen stored: `1014007738`, `1020534274`, `1021152376`, `1021350264`.
   Fix = apply the same `01`-prefix strip at the emit site.
2. **Visual-Hebrew product names on those same rows** — `טרפל תשק לדגמ` (= `מגדל קשת לפרט`),
   `ברועמ חוטיב-קלוסמ`. Note `xlsx_writer.py:482-489` deliberately does **not** reverse this
   column, with a measured justification ("191-211 logical rows per file, zero visual") and an
   explicit *do not add a reverse back without re-measuring*. The stored data contradicts that
   measurement for these rows — **re-measure before changing anything here.**

Contrast with Menora, whose policy loses two digits off the front; Migdal's gains one.
