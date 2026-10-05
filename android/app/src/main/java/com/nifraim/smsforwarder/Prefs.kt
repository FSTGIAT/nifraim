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

    fun setCallsEnabled(ctx: Context, on: Boolean) =
        sp(ctx).edit { putLong(KEY_CALLS_ENABLED_AT, if (on) System.currentTimeMillis() else 0L) }

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
}
