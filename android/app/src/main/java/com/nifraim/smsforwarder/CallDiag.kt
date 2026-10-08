package com.nifraim.smsforwarder

import android.content.Context
import android.provider.CallLog
import androidx.core.app.NotificationManagerCompat
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.net.HttpURLConnection
import java.net.URL

/**
 * What the last call scan saw — COUNTS ONLY (never numbers or names). Shown in the calls card and
 * POSTed to .../phone-forward/{token}/calls-diag so support can see where calls stop on an agent's
 * phone without asking them to debug it (2026-10-06: a phone with recording on uploaded nothing,
 * and nothing on the server could say why).
 *
 * 1.6+: also a per-recording TRAIL (phone-local time, length, how the number was found, the decision,
 * the agent's answer, the upload result) and the call-log calls of the last 3 hours that have NO
 * recording — still no numbers or names. 2026-10-07: a customer's 14:40 call never reached the server
 * and the counts couldn't say whether it was never recorded, unmatched, or answered "לא".
 */
object CallDiag {
    fun save(ctx: Context, found: List<CallSync.Recording>, fresh: Int, matched: Int, clients: Int,
             asked: Int, pendingInApp: Int, writing: Int, blocked: Int = 0) {
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
            .put("never_upload", blocked)
            .put("trail", trail(ctx))
            .put("calls_without_recording", callsWithoutRecording(ctx))
        Prefs.setDiag(ctx, o)
        send(ctx)
    }

    private fun hhmm(ms: Long) = SimpleDateFormat("HH:mm", Locale.US).format(Date(ms))

    /** "14:40|95s|log|cust|200" — time|length|number from (log/name/none)|decision|upload or answer. */
    private fun trail(ctx: Context): JSONArray {
        val out = JSONArray()
        for (e in Prefs.trailEntries(ctx).take(20)) {
            val parts = mutableListOf(hhmm(e.optLong("t")), "${e.optLong("dur")}s", e.optString("m"), e.optString("d"))
            e.optString("a").takeIf { it.isNotEmpty() }?.let { parts += it }
            e.optString("u").takeIf { it.isNotEmpty() }?.let { parts += it }
            out.put(parts.joinToString("|"))
        }
        return out
    }

    /** Connected calls of the last 3 hours that no recording was matched to: "14:40|95s|out".
     *  The dialer didn't record them (or the recording couldn't be tied to the call). */
    private fun callsWithoutRecording(ctx: Context): JSONArray {
        val out = JSONArray()
        if (!CallSync.hasCallLogPermission(ctx)) return out
        val now = System.currentTimeMillis()
        val from = maxOf(now - Prefs.LOOKBACK_MS, Prefs.callsEnabledAt(ctx))
        try {
            ctx.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.DATE, CallLog.Calls.DURATION, CallLog.Calls.TYPE),
                "${CallLog.Calls.DATE} >= ? AND ${CallLog.Calls.DURATION} > 0", arrayOf(from.toString()),
                "${CallLog.Calls.DATE} DESC",
            )?.use { c ->
                while (c.moveToNext() && out.length() < 15) {
                    val start = c.getLong(0)
                    val durS = c.getLong(1)
                    if (now - (start + durS * 1000) < 5 * 60_000L) continue   // the recording may still be on its way
                    if (Prefs.isCallUsed(ctx, start)) continue
                    val dir = when (c.getInt(2)) { CallLog.Calls.OUTGOING_TYPE -> "out"; CallLog.Calls.INCOMING_TYPE -> "in"; else -> "other" }
                    out.put("${hhmm(start)}|${durS}s|$dir")
                }
            }
        } catch (_: SecurityException) {
        }
        return out
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
