package com.nifraim.smsforwarder

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ForegroundInfo
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class SmsForwardWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    companion object {
        const val KEY_URL = "url"
        const val KEY_BODY = "body"
        private const val FOREGROUND_ID = 4101
    }

    /** SmsReceiver enqueues this EXPEDITED (an OTP dies in ~90s). On API <= 30
     *  WorkManager runs expedited work as a foreground service and asks for this;
     *  CoroutineWorker's default throws — which crashed the app. */
    override suspend fun getForegroundInfo(): ForegroundInfo {
        Notifications.ensureChannels(applicationContext)
        return ForegroundInfo(FOREGROUND_ID, Notifications.syncNotification(applicationContext, "מעביר קוד אימות…"))
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val webhookUrl = inputData.getString(KEY_URL) ?: return@withContext Result.failure()
        val smsBody = inputData.getString(KEY_BODY) ?: return@withContext Result.failure()

        try {
            val payload = JSONObject().put("message", smsBody).toString().toByteArray(Charsets.UTF_8)
            val conn = URL(webhookUrl).openConnection() as HttpURLConnection
            conn.apply {
                requestMethod = "POST"
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Content-Length", payload.size.toString())
                connectTimeout = 15_000
                readTimeout = 15_000
            }
            conn.outputStream.use { it.write(payload) }
            val code = conn.responseCode
            conn.disconnect()

            if (code in 200..299) {
                Prefs.setLastForward(applicationContext, System.currentTimeMillis())
                Result.success()
            } else Result.retry()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
