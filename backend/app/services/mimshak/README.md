# Mimshak DAT / MBT POC

Standalone research parser for the Israeli insurance **"מבנה אחיד"** (Mimshak / uniform structure) file format used by insurers to hand holdings data to agents. Each delivery is a folder containing one main XML payload saved with a `.DAT` extension (filename encodes sender + timestamp + report type) plus several `.MBT` lookup tables.

Goal of this POC: answer two questions **before** we touch any production code.

1. **Can we build the `.xlsx` extraction ourselves and skip the SaaS middleman the user currently uses?**
2. **Is there data inside the DAT/MBT bundle that those `.xlsx` files don't expose?**

No app integration, no DB writes, no routes. Two outputs — a big JSON dump of every (customer × policy) record the sample contains, and a markdown report classifying every XML element as mapped / unmapped / "rich structure the flat `ClientRecord` can't hold".

## Running

```bash
cd backend && source venv/bin/activate
python scripts/mimshak_poc/parse_dat.py /mnt/c/test
```

(Works with stdlib only — no new requirements. Python 3.10+.)

## Output

Default output dir: `backend/scripts/mimshak_poc/out/` (gitignored).

| File | What it is |
|------|------------|
| `records.json` | One fully-enriched record per `(customer × policy)`. Includes the raw XML leaves, the nested coverage → beneficiary/fund trees, the matched `PERSON.MBT` row (email/DOB/city/marital status/gender), and a `clientrecord_equivalent` block showing what a DAT→`ClientRecord` writer would produce. |
| `field_coverage.md` | Three-section report: (A) every XML leaf tag seen + its `ClientRecord` target column, (B) rich structures + flat fields present in DAT but not in any current Excel parser, (C) priority-ordered recommendations for follow-up persistence work. |

## Sample findings (on `/mnt/c/test` — Migdal HOLDNG file, 6 policies, 5 customers)

- The POC extracts the same columns the current Excel flow populates: `id_number`, `first_name`, `last_name`, `product`, `fund_policy_number`, `product_status`, `sign_date`, `receiving_company`, `total_premium`, `accumulation`, `management_fee`, `management_fee_amount`, `client_phone`, `client_email`. Direct drop-in writes to `ClientRecord` are viable.
- Everything in the `PERSON.MBT` master (email, DOB, gender, marital status, city/address, agent code) lines up 1:1 with the XML's customer ID and can be merged as enrichment.
- Data in the DAT that has **no** place in `ClientRecord` today:
  - per-policy beneficiaries (name, DOB, national ID, share %, relationship code)
  - per-policy fund allocations (fund code, name, allocation %, holding %)
  - per-policy surrender / redemption value (`ERECH-PIDYON-SOF-SHANA`)
  - per-policy net/gross yield (`SHEUR-TSUA-NETO`, `SHEUR-TSUA-BRUTO-CHS-1`)
  - per-policy P/L after deductions (`REVACH-HEFSED-BENIKOI-HOZAHOT`)
  - flags like `KAYAM-CHOV-O-PIGUR`, `KAYAM-MEYUPE-KOACH`, `IND-SCHUM-BITUAH-KOLEL-CHISACHON`
  - per-coverage rider lifecycle (start/end dates per rider)
  - loan blocks (`Halvaa`)
  - annual deposit history (`HafkadotShnatiyot`)
- The MBT files also carry `PERSON.MBT` fields not captured by any current parser: email, DOB, gender, marital status, city, address — useful for future portal / marketing features.

See `out/field_coverage.md` Section C for the concrete persist-target recommendations.

## Files in this POC

| File | Role |
|------|------|
| `parse_dat.py` | Entry point. Walks the DAT, builds enriched records, emits outputs. |
| `mbt.py` | One decoder per MBT file type (AGENTS, COMPANY, PERSON, LIFE, LIFEHLTH, COVRLIFE). Handles UTF-8 + Windows-1255 + visual-order Hebrew. |
| `xml_fields.py` | Hard-coded map of known Mimshak element names → English label + meaning + target `ClientRecord` column. Anything not in this map shows up as "(unmapped)" in the report — that list is the worklist for follow-up cataloguing. |
| `out/` | Generated (gitignored). Delete and re-run safely. |

## Design notes

- Standalone by design — no imports from `app/`. If we decide to promote this into production, we'll port the XML walk into `backend/app/services/mimshak_parser.py`, reuse `utils/sanitize.py`, and wire it into the existing upload pipeline (alongside the Excel parser, not replacing it).
- Customer ID resolution: `YeshutLakoach` holds the customer master and sits under `NetuneiMutzar` — *not* as an ancestor of the policy. Each `HeshbonOPolisa` references its customer via `NetuneiAmitOmevutach/MISPAR-ZIHUY`. We build a customer-ID → master map once, then look up by that field per policy.
- Beneficiary vs fund allocation: both use the `<Mutav>` element. Heuristic — if the block has a `MISPAR-ZIHUY-MUTAV` or `SHEM-*-MUTAV`, it's a beneficiary; otherwise it's a fund allocation. Same policy may legitimately have the same beneficiary repeated once per coverage (duplicates in the JSON are intentional — dedup will be an application-layer decision).
- Encodings: Mimshak DAT files are UTF-8 XML. MBT files vary (UTF-8, Windows-1255, ISO-8859-8) and some store Hebrew in visual order (display-order bytes). `mbt._read_text` tries UTF-8 → CP1255 → ISO-8859-8 → latin-1; `_maybe_reverse_hebrew` un-reverses visual-order Hebrew for the fields we display.
