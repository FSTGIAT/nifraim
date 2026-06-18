package com.nifraim.smsforwarder

import android.content.Context
import androidx.core.content.edit

object Prefs {
    private const val PREF_FILE = "nifraim_sms"
    private const val KEY_WEBHOOK_URL = "webhook_url"
    private const val KEY_ENABLED = "enabled"
    private const val KEY_LAST_FORWARD = "last_forward"

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
}
