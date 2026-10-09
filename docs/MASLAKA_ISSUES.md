# מסלקה — issues & fixes log

What broke when the first real מסלקה production answers (2000/2100) arrived, 6–9/10/2026,
why, how it was fixed, and the rule each fix leaves behind. Read this before touching
`services/maslaka/`, `services/mimshak/to_production_xlsx.py`, or the Gateway.
Architecture: `docs/ARCHITECTURE.md` §12. Gateway ops: the `maslaka-gateway` skill.

| # | Symptom | Root cause | Fix | Commit |
|---|---|---|---|---|
| 1 | Every login returned 500 sitewide ("database system is in recovery mode") | `postgres-volume` was **500MB** and never grown; the first holdings files (~3–5MB each) filled it. Postgres PANICked (`No space left on device`) and crash-looped | Volume grown to **10GB** in the Railway dashboard (the CLI and API have no resize) | — |
| 2 | 1,219MB of stored payloads for 258MB of real files | `_ingest_holdings` stored the full file once **per routed request**: one file answers many requests, so up to 8 copies were kept | Store it once **per agent**. Prod duplicates were deleted | `477c5a3` |
| 3 | 3 Phoenix files archived but missing from the DB | The poll **archived each file before its single end-of-poll commit**. The crash rolled the rows back after the files were already gone from IN | Commit each file **before** archiving it; an error rolls back only that file, which stays in IN. The 3 were requeued | `477c5a3` |
| 4 | 5,682 holdings for 1,199 products; a customer's צבירה summed up to 8× | The מסלקה **re-sends the same snapshot** (a 2000, a 2100, and again in later rounds), and each copy became another holding | One holding per product **per valuation date** (`status_date` = the file's `TAARICH-NECHONUT`). A re-send replaces; a new date is kept as the next month's snapshot | `cff725d` |
| 5 | "Next file by 15.10" after September's had already arrived | The rule was "the next 15th" | A month's data arrives by the 15th of the **month after it**; once September's is in, the next is due 15/11. One rule: `delta.next_file_due()` | `519e922`, `d3a969c` |
| 6 | Production ₪10,500 vs מסלקה ₪763,295 shown as one ₪752,795 "change" | **Two accounts under one policy number** (an inactive and an active one). The parser dropped the second as a "repeat", and the comparison keyed one row per policy | The parser's repeat key gains `STATUS-POLISA-O-CHESHBON`. `pension_holdings.account_status` (migration `maslaka_holding_01`). The comparison pairs accounts per customer + policy: same status first, then the closest balance | `0f5316f` |
| 7 | Two **active** accounts still collapsed (`304888373`: ₪347,912 + ₪53,849) | Same status, different fund: `KIDOD-ACHID` `…1328…` vs `…1329…` | The parser key gains `KIDOD-ACHID`. Each production row matches **one** holding (closest balance) | `eafe4ef` |
| 8 | Every Nifra question mentioning "מסלקה" got the same canned status line | The fast-lane regex sent anything with `מסלק` to `maslaka_status`, so `maslaka_delta` and `customer_holdings` were never reached | Only plain status questions stay instant; questions about changes, new or removed products, or one customer go to the agent lane | `d3a969c` |
| 9 | Nifra: "some Mor products aren't in your production" (false: all 7 matched) | The מסלקה lines in the customer card carried no match status, so the model guessed from company names | Each line says `בפרודוקציה` / `לא בפרודוקציה` + the account status | `0d6a8f2` |
| 10 | Nifra called removed products customers "who left" (עזבו) | Model wording | The tool rule says "removed" = not in this file; never "left" | `f2d7497` |

## Rules that stay

- **A מסלקה product = agent + customer + policy + company + account (status, fund).** One saver can
  hold several accounts under one number. Never collapse on customer + policy alone, in the parser,
  ingest, matching or the comparison.
- **Snapshots are per valuation date.** Every reader that sums holdings takes the newest snapshot only
  (`delta.latest_per_company`, `production-files`, admin distinct counts). Otherwise צבירה doubles
  every month.
- **Durable before archived.** A vault file leaves IN only after its rows are committed.
- **The comparison counts a company only if it answered on both sides**, scoped by production company
  **+ product type**. Production lists all of Altshuler as one company; the מסלקה answered its pension only.
- **Watch the volume.** Monthly snapshots grow the DB. Check `railway volume list`, and
  `pension_raw_payloads` first.

## Gateway procedure (code pushes + re-ingest)

- **Pushing code:** `az vm run-command` writes are blocked for Claude, so Roy runs a short wrapper
  (`~/gwN.sh`), because a long pasted line gets split in the terminal. Each push checks every
  target file's **current Gateway hash** first (ABORT otherwise), backs up `.bak-<date>`, writes, and
  restarts the "Nifraim Maslaka Worker" task.
- **Prove what's live by hash, not by assumption:** the Gateway file must equal a known git version.
  A worker restart in the log is not proof that new code is running.
- **Re-ingest after a parser or key change:**
  1. Dry-run the counts.
  2. Delete the affected `pension_holdings` and their `pension_raw_payloads` (only the 2000/2100
     files; keep the 9100 rows).
  3. Requeue the same files ARCHIVE → IN (strip the `^\d+_` prefix, and copy each name once).
  4. Wait until all files are back.
  5. Verify: file count, no duplicate keys, the known multi-account policies.
- **Data is "missing" while a re-ingest is pending.** Delete only right before the push runs.
- **Read raw files on the Gateway** (read-only run-command) to settle what the מסלקה actually sent.
  It's the only place the payloads can be decrypted or read. That is how #6 and #7 were found.

## Verification state (9/10/2026, kikohib)

- 67/67 files; 1,208 holdings, all dated; 0 duplicate keys; 8 products with two accounts.
- 1,176 holdings matched to production.
- Delta vs production July: 27 new / 18 removed / 888 changed / 288 unchanged.
- Nifra answers checked against the DB.
- The מסלקה data is **not embedded**: it's structured data read through tools. Only `call_chunks`
  and `doc_chunks` (policies) are embedded.

## Open

- `maslaka_status` still reports the original 2000/2100 requests as "expected 15/10".
- `test_maslaka_gateway_claim` fails on a missing temp `outbox` directory in the outbound test.
  Unrelated to ingest, but not yet proven to be pre-existing.
