package com.nifraim.smsforwarder

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Fetches the global company SMS templates from the backend and caches them so
 * SmsReceiver/OtpFilter can decide which SMS to forward. The templates URL is
 * derived from the webhook URL the user already configured:
 *   .../phone-forward/{token}  ->  .../phone-forward/{token}/templates
 *
 * Run once from MainActivity (on launch / after saving the URL) and periodically
 * (daily) so background-only phones stay current.
 */
object TemplateSync {

    /** Derive the templates endpoint from the saved webhook URL, or null. */
    fun templatesUrl(webhookUrl: String): String? {
        val url = webhookUrl.trim()
        if (!url.contains("/phone-forward/")) return null
        return url.trimEnd('/') + "/templates"
    }

    /** Blocking HTTP GET — must be called off the main thread. */
    fun refresh(ctx: Context): Boolean {
        val target = templatesUrl(Prefs.getWebhookUrl(ctx)) ?: return false
        return try {
            val conn = URL(target).openConnection() as HttpURLConnection
            conn.apply {
                requestMethod = "GET"
                connectTimeout = 15_000
                readTimeout = 15_000
            }
            val code = conn.responseCode
            if (code !in 200..299) {
                conn.disconnect()
                return false
            }
            val text = conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            conn.disconnect()
            val arr = JSONObject(text).optJSONArray("templates") ?: return false
            Prefs.setTemplatesJson(ctx, arr.toString())
            true
        } catch (e: Exception) {
            false
        }
    }
}

class TemplateFetchWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        if (TemplateSync.refresh(applicationContext)) Result.success() else Result.retry()
    }
}
