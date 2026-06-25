package com.nifraim.smsforwarder

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import androidx.work.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        if (!Prefs.isEnabled(ctx)) return

        val url = Prefs.getWebhookUrl(ctx)
        if (url.isBlank()) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent) ?: return
        if (messages.isEmpty()) return
        val body = messages.joinToString("") { it.messageBody }
        val sender = messages[0].displayOriginatingAddress ?: messages[0].originatingAddress

        // PRIVACY GATE: only forward insurance-portal OTP messages, using the
        // company templates cached from the backend. Personal SMS never leave
        // the device.
        if (!OtpFilter.shouldForward(ctx, sender, body)) return

        // FAST PATH — forward the OTP IMMEDIATELY. A WorkManager job can be
        // deferred for minutes by Doze/battery optimization, and a Phoenix OTP
        // expires in ~90s, so a deferred forward arrives dead. goAsync() gives
        // ~10s of guaranteed background time — plenty for one quick POST. Only
        // if that instant POST fails do we fall back to WorkManager (retry +
        // backoff + network constraint) so nothing is silently dropped.
        val pending = goAsync()
        Thread {
            var ok = false
            try {
                ok = postWebhook(url, body)
            } catch (_: Exception) {
            }
            if (!ok) enqueueFallback(ctx, url, body)
            try { pending.finish() } catch (_: Exception) {}
        }.start()
    }

    /** Direct, immediate POST of the SMS body to the webhook. Returns true on 2xx. */
    private fun postWebhook(url: String, body: String): Boolean {
        val payload = JSONObject().put("message", body).toString().toByteArray(Charsets.UTF_8)
        val conn = URL(url).openConnection() as HttpURLConnection
        return try {
            conn.apply {
                requestMethod = "POST"
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Content-Length", payload.size.toString())
                connectTimeout = 8_000
                readTimeout = 8_000
            }
            conn.outputStream.use { it.write(payload) }
            val code = conn.responseCode
            code in 200..299
        } finally {
            try { conn.disconnect() } catch (_: Exception) {}
        }
    }

    /** Backup path: only used when the instant POST failed (e.g. no network yet). */
    private fun enqueueFallback(ctx: Context, url: String, body: String) {
        val data = workDataOf(
            SmsForwardWorker.KEY_URL to url,
            SmsForwardWorker.KEY_BODY to body,
        )
        val request = OneTimeWorkRequestBuilder<SmsForwardWorker>()
            .setInputData(data)
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .setBackoffCriteria(BackoffPolicy.LINEAR, 10, TimeUnit.SECONDS)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        WorkManager.getInstance(ctx).enqueue(request)
    }
}
