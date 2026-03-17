# Stopping Points Analysis — Nifraim

Date: 2026-03-17

A comprehensive analysis of where the application flow stops, breaks, or degrades — covering backend services, API routes, parsing pipeline, and integration dependencies.

---

## Critical Stopping Points

### 1. Parser — Unknown Format Falls Through Silently
- **File:** `backend/app/services/parser_service.py` (~line 293)
- **What happens:** When `detect_format()` can't match a file's columns to any known signature, it silently falls back to `_parse_generic(df)`.
- **Impact:** User gets records with potentially wrong/incomplete column mappings. No warning that the format wasn't recognized.
- **Fix:** Return a warning flag in the upload response when format is "unknown". Show a toast in the frontend.

### 2. Comparison — No Active Production File (Blocks Entire Feature)
- **File:** `backend/app/api/comparison.py` (~line 193)
- **What happens:** `HTTPException(404, "לא נמצא קובץ פרודוקציה פעיל")` — comparison is completely blocked.
- **Impact:** Users cannot use the comparison tab at all until they upload a production file. The recruits comparison endpoint (`backend/app/api/recruits.py:301`) has the same gate.
- **Fix:** Frontend already shows a warning banner (ComparisonTab state machine step 1), but the error message could better guide the user to the production tab.

### 3. Payment — Cardcom Not Configured
- **File:** `backend/app/services/payment_service.py` (~line 39)
- **What happens:** `is_cardcom_configured()` returns false → silently returns `None, None`. No payment page is created.
- **Impact:** Subscription activation is completely broken in unconfigured environments. Users register but can never pay.
- **Fix:** Add startup validation warning. Return explicit error to frontend so it can show a "payments unavailable" message.

### 4. Email — SMTP Not Configured
- **File:** `backend/app/services/email_service.py` (~line 30)
- **What happens:** Raises `ValueError("SMTP not configured")` — unhandled in most callers.
- **Impact:** Portal link emails, password resets, and any email-dependent flow crashes.
- **Fix:** Catch at service boundary, return structured error, add fallback (e.g., show copy-link UI).

### 5. SMS — No Pre-flight Check
- **File:** `backend/app/services/sms_service.py` (~line 12)
- **What happens:** Token acquisition calls external API without validating credentials first. `raise_for_status()` throws on auth failure.
- **Impact:** Signup flow breaks if SMS provider is unreachable or misconfigured — users can't receive their password.
- **Fix:** Add config validation at startup. Provide email-based password delivery as fallback.

### 6. Scheduler — Not Implemented
- **File:** `backend/app/main.py` (~line 11, 16-18)
- **What happens:** Imports `start_scheduler`/`stop_scheduler` but the scheduler may not be fully functional.
- **Impact:** `process_renewals()` never runs — subscriptions never auto-renew.
- **Fix:** Implement APScheduler or similar with startup/shutdown hooks.

---

## High-Severity Stopping Points

### 7. Portal — Customer Data Not Found
- **File:** `backend/app/api/portal.py` (~line 91)
- **What happens:** `HTTPException(404, "לא נמצאו נתונים עבור לקוח זה")` when customer isn't in active production file.
- **Impact:** Customer opens their portal link and sees a 404. If the agent replaces the production file, portal data can vanish mid-session.
- **Fix:** Snapshot customer data at portal link creation time, or keep historical records.

### 8. AI Chat — No Data in System
- **File:** `backend/app/services/ai_service.py` (~line 451)
- **What happens:** Returns "אין נתונים במערכת" message and stops the SSE stream.
- **Impact:** AI chat is non-functional for new users who haven't uploaded files yet.
- **Fix:** Allow general insurance questions even without data; only require data for data-specific queries.

### 9. Portal AI Chat — No API Key
- **File:** `backend/app/services/portal_ai_service.py` (~line 105)
- **What happens:** Returns "שירות ה-AI אינו זמין כרגע" and closes the stream.
- **Impact:** Portal AI feature silently unavailable. No admin notification.
- **Fix:** Check at startup, log error, hide chat UI when unavailable.

### 10. Subscription Webhook — No Idempotency
- **File:** `backend/app/api/subscription.py` (~line 36-81)
- **What happens:** Duplicate Cardcom webhooks create duplicate subscription activations.
- **Impact:** Double charges possible; corrupted subscription state.
- **Fix:** Store webhook transaction ID, check before processing.

---

## Medium-Severity Gaps

### 11. Parser — Empty/Corrupted Files
- **File:** `backend/app/services/parser_service.py` (~line 237)
- Empty files parse to zero records without error. User thinks upload succeeded.
- **Fix:** Check row count after parsing; warn if zero records extracted.

### 12. Reconciliation — Shallow Cross-Reference
- **File:** `backend/app/services/reconciliation_service.py` (~line 262-417)
- `cross_reference_uploads()` matches only by `id_number`, ignoring `fund_policy_number` mismatches.
- **Fix:** Add product-level matching for deeper reconciliation.

### 13. AI Context — Unbounded Size
- **File:** `backend/app/services/ai_service.py` (~line 423)
- `build_user_context()` doesn't limit context size. Large accounts (10K+ customers) can exceed token limits.
- **Fix:** Sample/summarize data before sending to LLM; set max token budget.

### 14. File Upload — No Duplicate Content Detection
- **File:** `backend/app/api/uploads.py` (~line 57-69)
- Deduplication is by filename only, not content hash. Same-name different-content files are treated as duplicates.
- **Fix:** Add SHA-256 hash of file content for proper deduplication.

### 15. Portal Links — No Expiry Cleanup
- **File:** `backend/app/services/portal_service.py` (~line 71-100)
- Expired links checked on access but never cleaned from DB.
- **Fix:** Add periodic cleanup job (ties into scheduler gap #6).

---

## Infrastructure & Security Gaps

### 16. No Request Size Limits
- **File:** `backend/app/main.py`
- No middleware for max upload size or rate limiting.
- **Impact:** DoS via large file uploads or bulk API abuse.

### 17. No Database Connection Pool Config
- **File:** `backend/app/database.py` (~line 6)
- `create_async_engine()` with no `pool_size`/`max_overflow` — defaults may be too low for production.

### 18. Health Check — Shallow
- **File:** `backend/app/main.py` (~line 46-48)
- Returns `{"status": "ok"}` without checking DB, SMTP, SMS, or payment connectivity.
- **Fix:** Add deep health check endpoint that verifies critical dependencies.

### 19. No Transaction Rollback on Partial Insert
- **File:** `backend/app/api/uploads.py` (~line 83-93)
- If record insertion fails midway through a batch, partial records may persist.
- **Fix:** Wrap bulk insert in explicit transaction with rollback on failure.

### 20. Admin API — No Audit Trail
- **File:** `backend/app/api/admin.py` (~line 38-67)
- Admin user modifications aren't logged.
- **Fix:** Add audit log table and middleware.

---

## Summary by Priority

| Priority | # | Component | Issue |
|----------|---|-----------|-------|
| **CRITICAL** | 3 | Payment | Cardcom not configured → subscriptions broken |
| **CRITICAL** | 5 | SMS | No config validation → signup breaks |
| **CRITICAL** | 6 | Scheduler | Not implemented → renewals never run |
| **CRITICAL** | 10 | Webhook | No idempotency → double charges |
| **HIGH** | 2 | Comparison | No production file → feature blocked |
| **HIGH** | 4 | Email | SMTP missing → emails crash |
| **HIGH** | 7 | Portal | Live data → portal data can vanish |
| **HIGH** | 8 | AI Chat | No data → chat unavailable |
| **HIGH** | 16 | Security | No request limits → DoS risk |
| **MEDIUM** | 1 | Parser | Unknown format → silent wrong data |
| **MEDIUM** | 11 | Parser | Empty files → silent success |
| **MEDIUM** | 13 | AI | Unbounded context → token overflow |
| **MEDIUM** | 14 | Upload | Filename-only dedup → data loss risk |
| **MEDIUM** | 15 | Portal | No link cleanup → DB bloat |

---

## Recommended Action Order

1. **Add idempotency to subscription webhook** — prevents financial harm
2. **Implement scheduler** — enables subscription renewals
3. **Add SMS/SMTP/Cardcom startup validation** — fail-fast with clear logs
4. **Add email fallback for SMS** — unblocks signup when SMS is down
5. **Add upload response warning for unknown formats** — prevents silent bad data
6. **Add request size limits and rate limiting middleware** — security baseline
7. **Snapshot portal data at link creation** — prevents data disappearing
8. **Bound AI context size** — prevents token overflow crashes
9. **Add deep health check** — operational visibility
10. **Add transaction wrapping for bulk inserts** — data consistency
