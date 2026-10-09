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

## Resolved after the first pass

| # | Symptom | Root cause | Fix | Commit |
|---|---|---|---|---|
| 11 | `maslaka_status` said "10 open requests, nearest expected 15/10" | The expected date was the 15th after **sending**, even for requests that had already answered; the list was capped at 10 before sorting | `delta.answer_due()`: an answered 2000 is done, and an answered 2100 waits for `next_file_due`. All open requests are counted (30) and sorted. The remaining "15/10" rows are bodies that really haven't answered yet | `25ee213` |
| 12 | `test_maslaka_gateway_claim` failed (no `outbox`) | The test predates the 25–27/9 rules: a 9100 needs a recorded נספח א' consent, and every request needs contact fields | The test records consent and sets test contact values. Its DB tests **stop if pending rows they didn't create exist**: a run had claimed and failed two real local 9100s | `25ee213` |

| 13 | "עדכון מהמסלקה" / the ask form / Nifra's 9100 all said "sent" and every one failed on the Gateway ("needs the נספח א' signature dates") | Since the 25–27/9 rules a 9100 needs the signed נספח א' (both signature dates + the customer's address + excluded-product), and **no screen collected it** | `MaslakaConsentModal` opens on all three paths. The server refuses a 9100 without it (`api/maslaka.consent_record`, Hebrew 400), and `create_inquiry(consent=…)` records it **in the same transaction**, so the Gateway can never claim a 9100 without consent. Dates are never defaulted | `635669c` |
| 14 | The customer card said "נכון ל-9.10.2026" for balances as of 30/09 | `as_of` was the arrival time | `as_of` = the newest `status_date` | `635669c` |

## Several agents at the same time

- **Sending:** one Gateway worker claims one row at a time (`FOR UPDATE SKIP LOCKED`). A second
  claimer skips a locked row, so nothing is ever sent twice (covered by the gateway-claim test).
  Many agents' requests just queue and drain, bounded per tick.
- **Answers:** each product in a real production file carries the `MISPAR-MISLAKA` of the request it
  answers (checked on 6 real files), so a file routes to that exact request, and therefore that
  agent. Fallbacks (agent ID in the file → customer → insurer ח.פ) **never guess**: if two agents
  match, the file stays in IN.
- **Storage:** every key (replace, dedupe, matching, delta) is scoped by `user_id`. Two agents with
  the same customer keep separate holdings.
- **Not yet proven live:** on 9/10/2026 only **one** agent has an approved שיוך. The multi-agent
  paths are covered by code and tests, not by a real run. Watch the first months with ≥2 agents for
  files stuck in IN (the log says "not routable").

## How a 9100 is sent (since `635669c`)

- **Three ways in, one form:**
  - the customer card's **"עדכון מהמסלקה"**;
  - the tab's search, for a ת"ז with no data yet;
  - Nifra's prepared card ("אישור ושליחה למסלקה").
- **Each one opens `MaslakaConsentModal` ("טופס נספח א'")**, which collects:
  - the customer's and the agent's signature dates;
  - city, street, house number and postcode;
  - excluded product (כן/לא);
  - a ✓ for "the signed form is in hand".
- **Send is disabled** until the form is complete. Dates are capped at today and **never defaulted**,
  because they are a declaration to a regulator.
- **Server:** `POST /maslaka/inquiry` and `/office-agent/act` (kind `maslaka`) refuse a 9100 without
  `consent`, via `consent_record()`, with a Hebrew 400. `create_inquiry(consent=…)` →
  `record_consent` happens before the single commit.
- **After sending:** the Gateway claims it within ~15 minutes, and the answer usually comes back within hours.
- **Still open:** the Nifra path is wired but not render-checked (no Nifra card could be produced in the
  test run). Prod `313679227` (9/10) failed with no consent; resend it from the card. Two of Roy's
  local pending 9100s (`313679227`, `331510123`) also have no consent recorded.

## Reading a FEDBKB (משוב ב')

- `SUG-MASHOV=2` = content feedback from the operator or producer, per request GUID.
- `STATUS-RESHUMA=1` means the **מסלקה** accepted the record. `MAANE-BERAMAT-RESHUMA` is the
  producer's answer, e.g. **1032 "לא אותרו פוליסות עבור הסוכן"** (no policies found for the agent at that body).
- It is ingested automatically: `content_feedback` + `operator_refusal` audit events on the
  matching request.
- The 9/10 FEDBKB answered four **old 25/9 duplicate** production requests (520023185, Phoenix 513026484).
  The newer requests to the same bodies did bring the data. It is not a 9100 answer.

## Gateway state + testing rules (9/10/2026)

- **(superseded by the self-update below)** Gateway files on 9/10 before it: `orchestration.py` = `CA53FC2D…`, `mimshak/to_production_xlsx.py` = `86715410…`,
  `delta.py` = `2786861A…`, `models/pension_holding.py` = `446F4996…`.
  - `635669c` changed `orchestration.py` (9100 consent, card date) for the website only.
  - The **next** Gateway push must guard on `CA53FC2D…` and will bring it up to git.
- **Gateway claim test:** `test_maslaka_gateway_claim.py` claims the **oldest pending rows in the whole DB**.
  Its DB tests now stop if pending rows they didn't create exist. **Do not run it** (or any 9100 test)
  while Roy has 9100 work pending, unless he asks.

## Gateway self-update (live since 10/10/2026, `053411f`)

- **Deploy → Admin → תפעול → "גייטוויי מסלקה" → "שחרר לגייטוויי".** That's the whole procedure now.
  - The Gateway takes **only the released version**, between two rounds.
  - It stages the whole tree in `releases\<v>`, refuses a `requirements.txt` change (`needs_pip`) and
    self-tests in a separate process.
  - It switches through `current.txt`, and `gateway_launcher.py` rolls back a release that crashes
    twice or has no healthy round within 10 minutes.
  - "נעל עדכונים" pins it; `GATEWAY_AUTO_UPDATE=false` in its `.env` stops it locally.
- **Bootstrapped 9/10 21:32 UTC:** release `36750a01` passed its trial, so the Gateway matches git
  exactly. The legacy `C:\Nifraim\app\backend` tree stays as the rollback target (`previous.txt = legacy`).
- **Manual scripts are now only a fallback** (e.g. a `needs_pip` install). Rules for any `.ps1`:
  - **ASCII only, or a UTF-8 BOM.** One em-dash made PS 5.1 reject a whole script silently.
  - **Parse-check it in Windows PowerShell 5.1 first.**
  - **Print `value[].message`**, not just stdout.
  - **One run-command at a time per VM.** A concurrent call is rejected.
- **Plan and design:** `.claude/plans/gateway-self-update.md`. **Tests:** `tests/test_gateway_self_update.py`.

