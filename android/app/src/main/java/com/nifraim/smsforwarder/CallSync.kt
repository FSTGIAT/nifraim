package com.nifraim.smsforwarder

import android.Manifest
import android.content.ContentUris
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.CallLog
import android.provider.MediaStore
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Calls: the phone's own dialer records the call (Android 10+ forbids apps from
 * recording calls themselves — Samsung saves to Recordings/Call/). We only COLLECT
 * those files, and only the ones with the agent's customers leave the phone:
 *
 *   number's hash ∈ customer hashes → upload by itself
 *   anything else                   → a notification asks first ("להעלות?")
 *
 * Same privacy rule as OtpFilter: personal calls never leave the device on their own.
 * The customer list arrives as sha256(phoneKey) from .../phone-forward/{token}/client-phones.
 */
object CallSync {

    /** One recording found on the device. */
    data class Recording(
        val mediaId: Long,
        val name: String,
        val mime: String,
        val modifiedMs: Long,     // ≈ when the call ended
        val durationMs: Long,
        val pending: Boolean,
    )

    /** What we know about the other side of the call. */
    data class CallInfo(val number: String?, val direction: String?, val startedAtMs: Long?)

    private fun base(ctx: Context): String? {
        val url = Prefs.getWebhookUrl(ctx).trim().trimEnd('/')
        return if (url.contains("/phone-forward/")) url else null
    }

    fun uploadUrl(ctx: Context) = base(ctx)?.let { "$it/call" }

    /** National number without its 0 — mirrors backend services/calls/ingest.py::phone_key. */
    fun phoneKey(raw: String?): String? {
        var d = (raw ?: "").filter { it.isDigit() }
        if (d.startsWith("00")) d = d.substring(2)
        if (d.startsWith("972") && d.length >= 11) d = d.substring(3)
        d = d.trimStart('0')
        return if (d.length in 8..9) d else null
    }

    fun display(raw: String?): String? = phoneKey(raw)?.let { "0$it" }

    fun hash(key: String): String =
        MessageDigest.getInstance("SHA-256").digest(key.toByteArray()).joinToString("") { "%02x".format(it) }

    fun isClient(ctx: Context, number: String?): Boolean {
        val key = phoneKey(number) ?: return false
        return Prefs.getClientHashes(ctx).contains(hash(key))
    }

    /** Blocking GET of the customer phone hashes — call off the main thread. */
    fun refreshClients(ctx: Context): Boolean {
        val target = base(ctx)?.let { "$it/client-phones" } ?: return false
        return try {
            val conn = URL(target).openConnection() as HttpURLConnection
            conn.connectTimeout = 15_000
            conn.readTimeout = 20_000
            if (conn.responseCode !in 200..299) { conn.disconnect(); return false }
            val text = conn.inputStream.bufferedReader().use { it.readText() }
            conn.disconnect()
            val o = JSONObject(text)
            val arr = o.optJSONArray("hashes") ?: return false
            val fresh = (0 until arr.length()).map { arr.getString(it) }.toSet()
            val before = Prefs.getClientHashes(ctx)
            Prefs.setClientHashes(ctx, fresh)
            Prefs.setClientsVersion(ctx, o.optString("version"))
            // a customer added on the site (walk-in): their recordings from the last 3 hours
            // that were left out now upload
            val added = fresh - before
            if (before.isNotEmpty() && added.isNotEmpty()) Skipped.recheck(ctx, added)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun hasAudioPermission(ctx: Context): Boolean {
        val perm = if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO
                   else Manifest.permission.READ_EXTERNAL_STORAGE
        return ContextCompat.checkSelfPermission(ctx, perm) == PackageManager.PERMISSION_GRANTED
    }

    fun hasCallLogPermission(ctx: Context) =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED

    fun audioUri(mediaId: Long) = ContentUris.withAppendedId(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, mediaId)

    /** Dialer recordings added since the feature was switched on, oldest first. */
    @Suppress("DEPRECATION")  // MediaStore DATA is the only path column below API 29
    fun findRecordings(ctx: Context): List<Recording> {
        val since = Prefs.callsEnabledAt(ctx) / 1000
        if (since <= 0 || !hasAudioPermission(ctx)) return emptyList()
        val cols = mutableListOf(
            MediaStore.Audio.Media._ID, MediaStore.Audio.Media.DISPLAY_NAME, MediaStore.Audio.Media.MIME_TYPE,
            MediaStore.Audio.Media.DATE_MODIFIED, MediaStore.Audio.Media.DURATION,
            MediaStore.Audio.Media.DATE_ADDED,
        )
        val q29 = Build.VERSION.SDK_INT >= 29
        if (q29) { cols += MediaStore.Audio.Media.RELATIVE_PATH; cols += MediaStore.Audio.Media.IS_PENDING }  // 6, 7
        else cols += MediaStore.Audio.Media.DATA

        val out = mutableListOf<Recording>()
        ctx.contentResolver.query(
            MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, cols.toTypedArray(),
            "${MediaStore.Audio.Media.DATE_ADDED} >= ?", arrayOf(since.toString()),
            "${MediaStore.Audio.Media.DATE_ADDED} ASC",
        )?.use { c ->
            while (c.moveToNext()) {
                val path = c.getString(6) ?: ""
                val name = c.getString(1) ?: ""
                // Samsung: Recordings/Call/ · Xiaomi: MIUI/sound_recorder/call_rec/ · others: "Call…"
                if (!path.contains("call", ignoreCase = true) && !name.startsWith("call", ignoreCase = true)) continue
                out += Recording(
                    mediaId = c.getLong(0), name = name, mime = c.getString(2) ?: "audio/mp4",
                    // DATE_MODIFIED can be NULL until the scanner reads the file — fall back to DATE_ADDED
                    modifiedMs = (if (c.isNull(3)) c.getLong(5) else c.getLong(3)) * 1000,
                    durationMs = c.getLong(4),
                    pending = q29 && c.getInt(7) == 1,
                )
            }
        }
        return out
    }

    /** The call-log entry this recording belongs to. A wrong match would upload a
     *  personal call as a customer's, so every check must agree:
     *   - the call ended within 3 min of the file's last write,
     *   - the recording's length fits the call's length,
     *   - the entry wasn't already given to another recording,
     *   - a number in the file name ("Call recording 050-1234567_…"), if any, is the same number.
     *  No such entry → only the file-name number, or nothing (→ the agent is asked). */
    fun matchCall(ctx: Context, rec: Recording): CallInfo {
        val fromName = Regex("""\+?\d[\d\- ]{7,15}\d""").find(rec.name)?.value
        val nameKey = phoneKey(fromName)
        if (hasCallLogPermission(ctx) && rec.modifiedMs > 0) {
            val window = 3 * 60_000L
            val from = rec.modifiedMs - rec.durationMs - window - 60 * 60_000L
            try {
                ctx.contentResolver.query(
                    CallLog.Calls.CONTENT_URI,
                    arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION),
                    "${CallLog.Calls.DATE} >= ? AND ${CallLog.Calls.DATE} <= ?",
                    arrayOf(from.toString(), (rec.modifiedMs + window).toString()),
                    "${CallLog.Calls.DATE} DESC",
                )?.use { c ->
                    var best: CallInfo? = null
                    var bestGap = Long.MAX_VALUE
                    while (c.moveToNext()) {
                        val start = c.getLong(2)
                        val callMs = c.getLong(3) * 1000
                        val gap = kotlin.math.abs(start + callMs - rec.modifiedMs)
                        if (gap > window || gap >= bestGap) continue
                        if (Prefs.isCallUsed(ctx, start)) continue
                        if (rec.durationMs > 0 && !durationsFit(rec.durationMs, callMs)) continue
                        val number = c.getString(0)
                        if (nameKey != null && phoneKey(number) != nameKey) continue
                        bestGap = gap
                        val dir = when (c.getInt(1)) {
                            CallLog.Calls.OUTGOING_TYPE -> "out"
                            CallLog.Calls.INCOMING_TYPE -> "in"
                            else -> null
                        }
                        best = CallInfo(number, dir, start)
                    }
                    best?.let { return it }
                }
            } catch (_: SecurityException) {
            }
        }
        return CallInfo(fromName, null, null)
    }

    /** A recording covers the connected part of the call: about as long, never much longer. */
    private fun durationsFit(recMs: Long, callMs: Long): Boolean {
        val slack = maxOf(5_000L, callMs / 5)
        return recMs <= callMs + slack && recMs >= callMs - slack
    }
}
