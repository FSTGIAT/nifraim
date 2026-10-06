package com.nifraim.smsforwarder

import android.content.Context
import androidx.core.app.NotificationManagerCompat
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * What the last call scan saw — COUNTS ONLY (never numbers or names). Shown in the calls card and
 * POSTed to .../phone-forward/{token}/calls-diag so support can see where calls stop on an agent's
 * phone without asking them to debug it (2026-10-06: a phone with recording on uploaded nothing,
 * and nothing on the server could say why).
 */
object CallDiag {
    fun save(ctx: Context, found: List<CallSync.Recording>, fresh: Int, matched: Int, clients: Int,
             asked: Int, pendingInApp: Int, writing: Int) {
        val newest = found.maxOfOrNull { it.modifiedMs } ?: 0L
        val o = JSONObject()
            .put("at", System.currentTimeMillis())
            .put("app", BuildConfigCompat.versionName(ctx))
            .put("perm_audio", CallSync.hasAudioPermission(ctx))
            .put("perm_call_log", CallSync.hasCallLogPermission(ctx))
            .put("perm_notifications", NotificationManagerCompat.from(ctx).areNotificationsEnabled())
            .put("window_from_min_ago", ((System.currentTimeMillis() - Prefs.callsEnabledAt(ctx)) / 60_000))
            .put("recordings_in_window", found.size)
            .put("new_this_scan", fresh)
            .put("still_writing", writing)
            .put("matched_call_log", matched)
            .put("customers", clients)
            .put("asked_by_notification", asked)
            .put("waiting_in_app", Prefs.getPending(ctx).length())
            .put("newest_recording_min_ago", if (newest > 0) (System.currentTimeMillis() - newest) / 60_000 else -1)
            .put("known_customer_phones", Prefs.getClientHashes(ctx).size)
            .put("last_upload_result", Prefs.getLastUploadResult(ctx))
            .put("added_to_app_list", pendingInApp)
        Prefs.setDiag(ctx, o)
        send(ctx)
    }

    /** Fire-and-forget POST of the saved counts. Never blocks or fails the scan. */
    fun send(ctx: Context) {
        val base = Prefs.getWebhookUrl(ctx).trim().trimEnd('/')
        if (!base.contains("/phone-forward/")) return
        val body = Prefs.getDiag(ctx).toString().toByteArray(Charsets.UTF_8)
        Thread {
            try {
                val c = URL("$base/calls-diag").openConnection() as HttpURLConnection
                c.requestMethod = "POST"; c.doOutput = true; c.connectTimeout = 10_000; c.readTimeout = 10_000
                c.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                c.outputStream.use { it.write(body) }
                c.responseCode
                c.disconnect()
            } catch (_: Exception) {
            }
        }.start()
    }
}

object BuildConfigCompat {
    fun versionName(ctx: Context): String = try {
        ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName ?: ""
    } catch (_: Exception) { "" }
}
