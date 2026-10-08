package com.nifraim.smsforwarder

import android.content.Context
import androidx.core.content.edit

object Prefs {
    private const val PREF_FILE = "nifraim_sms"
    private const val KEY_WEBHOOK_URL = "webhook_url"
    private const val KEY_ENABLED = "enabled"
    private const val KEY_LAST_FORWARD = "last_forward"
    private const val KEY_TEMPLATES = "templates_json"
    private const val KEY_TEMPLATES_FETCHED = "templates_fetched"

    fun getWebhookUrl(ctx: Context): String =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .getString(KEY_WEBHOOK_URL, "") ?: ""

    fun setWebhookUrl(ctx: Context, url: String) =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .edit { putString(KEY_WEBHOOK_URL, url) }

    fun isEnabled(ctx: Context): Boolean =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .getBoolean(KEY_ENABLED, true)

    fun setEnabled(ctx: Context, enabled: Boolean) =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .edit { putBoolean(KEY_ENABLED, enabled) }

    fun setLastForward(ctx: Context, timestamp: Long) =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .edit { putLong(KEY_LAST_FORWARD, timestamp) }

    fun getLastForward(ctx: Context): Long =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .getLong(KEY_LAST_FORWARD, 0L)

    /** Cached company SMS templates (the backend's `templates` JSON array). */
    fun getTemplatesJson(ctx: Context): String =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .getString(KEY_TEMPLATES, "") ?: ""

    fun setTemplatesJson(ctx: Context, json: String) =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .edit {
                putString(KEY_TEMPLATES, json)
                putLong(KEY_TEMPLATES_FETCHED, System.currentTimeMillis())
            }

    fun getTemplatesFetched(ctx: Context): Long =
        ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)
            .getLong(KEY_TEMPLATES_FETCHED, 0L)

    // ── Calls (dialer recordings → Nifraim) ─────────────────────────────────
    private const val KEY_CALLS_ENABLED_AT = "calls_enabled_at"   // 0 = off; else ms when switched on
    private const val KEY_CALLS_WIFI_ONLY = "calls_wifi_only"
    private const val KEY_LAST_CALL = "last_call_upload"
    private const val KEY_CLIENT_HASHES = "client_hashes"
    private const val KEY_CLIENTS_FETCHED = "clients_fetched"
    private const val KEY_HANDLED = "calls_handled"               // MediaStore ids already decided

    private fun sp(ctx: Context) = ctx.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE)

    fun isCallsEnabled(ctx: Context) = sp(ctx).getLong(KEY_CALLS_ENABLED_AT, 0L) > 0L

    /** Only recordings made after this moment are ever considered — no history backfill. */
    fun callsEnabledAt(ctx: Context) = sp(ctx).getLong(KEY_CALLS_ENABLED_AT, 0L)

    /** Recordings from this long BEFORE the switch was turned on are collected too — the calls the
     *  agent had this morning, before installing. The customer filter still decides what uploads. */
    const val LOOKBACK_MS = 3 * 60 * 60 * 1000L
    private const val KEY_LOOKBACK_APPLIED = "calls_lookback_applied"

    fun setCallsEnabled(ctx: Context, on: Boolean) =
        sp(ctx).edit {
            putLong(KEY_CALLS_ENABLED_AT, if (on) System.currentTimeMillis() - LOOKBACK_MS else 0L)
            putBoolean(KEY_LOOKBACK_APPLIED, true)
        }

    /** Agents who switched calls on in 1.2 (no look-back): widen their window once, 3h before. */
    fun applyLookbackOnce(ctx: Context) {
        val p = sp(ctx)
        if (p.getBoolean(KEY_LOOKBACK_APPLIED, false)) return
        val at = p.getLong(KEY_CALLS_ENABLED_AT, 0L)
        p.edit {
            if (at > 0L) putLong(KEY_CALLS_ENABLED_AT, at - LOOKBACK_MS)
            putBoolean(KEY_LOOKBACK_APPLIED, true)
        }
    }

    fun isWifiOnly(ctx: Context) = sp(ctx).getBoolean(KEY_CALLS_WIFI_ONLY, false)
    fun setWifiOnly(ctx: Context, on: Boolean) = sp(ctx).edit { putBoolean(KEY_CALLS_WIFI_ONLY, on) }

    fun getLastCallUpload(ctx: Context) = sp(ctx).getLong(KEY_LAST_CALL, 0L)
    fun setLastCallUpload(ctx: Context, ts: Long) = sp(ctx).edit { putLong(KEY_LAST_CALL, ts) }

    fun getClientHashes(ctx: Context): Set<String> = sp(ctx).getStringSet(KEY_CLIENT_HASHES, emptySet()) ?: emptySet()
    fun getClientsFetched(ctx: Context) = sp(ctx).getLong(KEY_CLIENTS_FETCHED, 0L)
    fun setClientHashes(ctx: Context, hashes: Set<String>) = sp(ctx).edit {
        putStringSet(KEY_CLIENT_HASHES, HashSet(hashes))
        putLong(KEY_CLIENTS_FETCHED, System.currentTimeMillis())
    }

    fun isHandled(ctx: Context, mediaId: Long) =
        (sp(ctx).getString(KEY_HANDLED, "") ?: "").split(',').contains(mediaId.toString())

    /** Remember a decided recording (uploaded / waiting for approval / skipped). Keeps the last 300. */
    fun markHandled(ctx: Context, mediaId: Long) {
        val ids = (sp(ctx).getString(KEY_HANDLED, "") ?: "").split(',').filter { it.isNotBlank() }.toMutableList()
        if (ids.contains(mediaId.toString())) return
        ids.add(mediaId.toString())
        sp(ctx).edit { putString(KEY_HANDLED, ids.takeLast(300).joinToString(",")) }
    }

    private const val KEY_USED_CALLS = "calls_used_log"   // call-log start times already given to a recording

    fun isCallUsed(ctx: Context, startMs: Long) =
        (sp(ctx).getString(KEY_USED_CALLS, "") ?: "").split(',').contains(startMs.toString())

    /** One call-log entry belongs to ONE recording. Keeps the last 300. */
    fun markCallUsed(ctx: Context, startMs: Long) {
        val ids = (sp(ctx).getString(KEY_USED_CALLS, "") ?: "").split(',').filter { it.isNotBlank() }.toMutableList()
        if (ids.contains(startMs.toString())) return
        ids.add(startMs.toString())
        sp(ctx).edit { putString(KEY_USED_CALLS, ids.takeLast(300).joinToString(",")) }
    }

    // ── calls: approvals the notification could not show + the last scan's numbers ──
    private const val KEY_PENDING = "calls_pending"        // JSON array of recordings waiting for "העלה / לא"
    private const val KEY_DIAG = "calls_diag"              // last scan's counts (shown in the app, sent to the server)
    private const val KEY_LAST_UPLOAD = "calls_last_upload_result"

    fun getPending(ctx: Context): org.json.JSONArray =
        try { org.json.JSONArray(sp(ctx).getString(KEY_PENDING, "[]") ?: "[]") } catch (_: Exception) { org.json.JSONArray() }

    fun setPending(ctx: Context, arr: org.json.JSONArray) = sp(ctx).edit { putString(KEY_PENDING, arr.toString()) }

    fun getDiag(ctx: Context): org.json.JSONObject =
        try { org.json.JSONObject(sp(ctx).getString(KEY_DIAG, "{}") ?: "{}") } catch (_: Exception) { org.json.JSONObject() }

    fun setDiag(ctx: Context, o: org.json.JSONObject) = sp(ctx).edit { putString(KEY_DIAG, o.toString()) }

    fun getLastUploadResult(ctx: Context): String = sp(ctx).getString(KEY_LAST_UPLOAD, "") ?: ""
    fun setLastUploadResult(ctx: Context, v: String) = sp(ctx).edit { putString(KEY_LAST_UPLOAD, v) }

    // ── recordings left out (not a customer) — re-checked when a new customer is added ──
    private const val KEY_SKIPPED = "calls_skipped"           // JSON array, pruned to the last 24h
    private const val KEY_CLIENTS_VERSION = "calls_clients_version"

    fun getSkipped(ctx: Context): org.json.JSONArray =
        try { org.json.JSONArray(sp(ctx).getString(KEY_SKIPPED, "[]") ?: "[]") } catch (_: Exception) { org.json.JSONArray() }

    fun setSkipped(ctx: Context, arr: org.json.JSONArray) = sp(ctx).edit { putString(KEY_SKIPPED, arr.toString()) }

    fun getClientsVersion(ctx: Context): String = sp(ctx).getString(KEY_CLIENTS_VERSION, "") ?: ""
    fun setClientsVersion(ctx: Context, v: String) = sp(ctx).edit { putString(KEY_CLIENTS_VERSION, v) }

    // ── the decision trail: what happened to each recording (NO numbers) — sent with calls-diag
    //    so "where is my 14:40 call?" is answered from the server logs ──
    private const val KEY_TRAIL = "calls_trail"               // JSON object mediaId → {t,dur,m,d,u}

    private fun getTrail(ctx: Context): org.json.JSONObject =
        try { org.json.JSONObject(sp(ctx).getString(KEY_TRAIL, "{}") ?: "{}") } catch (_: Exception) { org.json.JSONObject() }

    /** Merge fields into one recording's trail entry. Keeps the last 24h, at most 40 entries. */
    fun trail(ctx: Context, mediaId: Long, vararg kv: Pair<String, Any>) {
        if (mediaId < 0) return
        val all = getTrail(ctx)
        val e = all.optJSONObject(mediaId.toString()) ?: org.json.JSONObject()
        for ((k, v) in kv) e.put(k, v)
        all.put(mediaId.toString(), e)
        val now = System.currentTimeMillis()
        val keys = all.keys().asSequence().toList()
            .filter { now - all.getJSONObject(it).optLong("t", now) < 24 * 60 * 60 * 1000L }
            .sortedByDescending { all.getJSONObject(it).optLong("t") }.take(40)
        val keep = org.json.JSONObject()
        for (k in keys) keep.put(k, all.getJSONObject(k))
        sp(ctx).edit { putString(KEY_TRAIL, keep.toString()) }
    }

    /** Entries newest first: (time ms, entry). */
    fun trailEntries(ctx: Context): List<org.json.JSONObject> {
        val all = getTrail(ctx)
        return all.keys().asSequence().map { all.getJSONObject(it) }.sortedByDescending { it.optLong("t") }.toList()
    }

    // ── never-upload numbers (hashes) — their recordings never leave the phone ──
    private const val KEY_BLOCK_HASHES = "calls_block_hashes"
    fun getBlockHashes(ctx: Context): Set<String> = sp(ctx).getStringSet(KEY_BLOCK_HASHES, emptySet()) ?: emptySet()
    fun setBlockHashes(ctx: Context, h: Set<String>) = sp(ctx).edit { putStringSet(KEY_BLOCK_HASHES, h) }
}
