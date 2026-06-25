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
}
