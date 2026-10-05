package com.nifraim.smsforwarder

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.MediaStore
import androidx.core.app.NotificationCompat
import androidx.work.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import java.util.concurrent.TimeUnit

/** Scheduling for the calls pipeline. */
object CallJobs {
    private const val TRIGGER = "call-scan-trigger"
    private const val PERIODIC = "call-scan-periodic"
    private const val SETTLE = "call-scan-settle"

    /** Arm everything (or tear it down when calls are off). Safe to call often. */
    fun schedule(ctx: Context) {
        val wm = WorkManager.getInstance(ctx)
        if (!Prefs.isCallsEnabled(ctx)) {
            wm.cancelUniqueWork(TRIGGER); wm.cancelUniqueWork(PERIODIC); wm.cancelUniqueWork(SETTLE)
            return
        }
        armTrigger(ctx)
        wm.enqueueUniquePeriodicWork(
            PERIODIC, ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<CallScanWorker>(15, TimeUnit.MINUTES).build(),
        )
    }

    /** A content-URI trigger fires ONCE — CallScanWorker re-arms it after every run.
     *  It runs even when the app is closed: a new file in MediaStore wakes us. */
    fun armTrigger(ctx: Context) {
        val builder = Constraints.Builder()
            .addContentUriTrigger(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, true)
        // Some writers only notify the volume-specific URI (content://media/external_primary/…)
        if (android.os.Build.VERSION.SDK_INT >= 29) builder.addContentUriTrigger(
            MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY), true)
        val constraints = builder
            .setTriggerContentUpdateDelay(5, TimeUnit.SECONDS)
            .setTriggerContentMaxDelay(30, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(ctx).enqueueUniqueWork(
            TRIGGER, ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<CallScanWorker>().setConstraints(constraints).build(),
        )
    }

    /** Look again shortly — a recording that was still being written. */
    fun scanLater(ctx: Context, seconds: Long = 30) {
        WorkManager.getInstance(ctx).enqueueUniqueWork(
            SETTLE, ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<CallScanWorker>().setInitialDelay(seconds, TimeUnit.SECONDS).build(),
        )
    }

    fun scanNow(ctx: Context) = scanLater(ctx, 0)

    fun upload(ctx: Context, rec: CallSync.Recording, info: CallSync.CallInfo) {
        val net = if (Prefs.isWifiOnly(ctx)) NetworkType.UNMETERED else NetworkType.CONNECTED
        val data = workDataOf(
            CallUploadWorker.KEY_MEDIA_ID to rec.mediaId,
            CallUploadWorker.KEY_MIME to rec.mime,
            CallUploadWorker.KEY_DURATION_MS to rec.durationMs,
            CallUploadWorker.KEY_PHONE to (info.number ?: ""),
            CallUploadWorker.KEY_DIRECTION to (info.direction ?: ""),
            CallUploadWorker.KEY_STARTED_AT to (info.startedAtMs ?: 0L),
        )
        WorkManager.getInstance(ctx).enqueueUniqueWork(
            "call-upload-${rec.mediaId}", ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<CallUploadWorker>()
                .setInputData(data)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(net).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 1, TimeUnit.MINUTES)
                .build(),
        )
    }
}

/** Finds new dialer recordings and decides each one: customer → upload, else ask. */
class CallScanWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val ctx = applicationContext
        try {
            if (!Prefs.isCallsEnabled(ctx)) return@withContext Result.success()
            if (System.currentTimeMillis() - Prefs.getClientsFetched(ctx) > TimeUnit.HOURS.toMillis(24)) {
                CallSync.refreshClients(ctx)
            }
            var stillWriting = false
            for (rec in CallSync.findRecordings(ctx)) {
                if (Prefs.isHandled(ctx, rec.mediaId)) continue
                // MediaStore can announce a file before the dialer finished writing it.
                if (rec.pending || System.currentTimeMillis() - rec.modifiedMs < 20_000) {
                    stillWriting = true
                    continue
                }
                val info = CallSync.matchCall(ctx, rec)
                info.startedAtMs?.let { Prefs.markCallUsed(ctx, it) }
                if (CallSync.isClient(ctx, info.number)) CallJobs.upload(ctx, rec, info)
                else CallApproval.ask(ctx, rec, info)
                Prefs.markHandled(ctx, rec.mediaId)
            }
            if (stillWriting) CallJobs.scanLater(ctx)
            Result.success()
        } finally {
            if (Prefs.isCallsEnabled(ctx)) CallJobs.armTrigger(ctx)
        }
    }
}

/** Streams one recording to .../phone-forward/{token}/call as multipart/form-data. */
class CallUploadWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    companion object {
        const val KEY_MEDIA_ID = "media_id"
        const val KEY_MIME = "mime"
        const val KEY_DURATION_MS = "duration_ms"
        const val KEY_PHONE = "phone"
        const val KEY_DIRECTION = "direction"
        const val KEY_STARTED_AT = "started_at"
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val ctx = applicationContext
        val target = CallSync.uploadUrl(ctx) ?: return@withContext Result.failure()
        val mediaId = inputData.getLong(KEY_MEDIA_ID, -1)
        if (mediaId < 0) return@withContext Result.failure()
        val mime = inputData.getString(KEY_MIME) ?: "audio/mp4"
        val boundary = "----nifraim" + UUID.randomUUID().toString().replace("-", "")

        val fields = linkedMapOf(
            "phone" to (inputData.getString(KEY_PHONE) ?: ""),
            "direction" to (inputData.getString(KEY_DIRECTION) ?: ""),
            "started_at" to inputData.getLong(KEY_STARTED_AT, 0).takeIf { it > 0 }?.toString().orEmpty(),
            "duration_s" to (inputData.getLong(KEY_DURATION_MS, 0) / 1000.0).toString(),
            "source" to "phone_android",
            "source_ref" to "ms:$mediaId",
        )
        try {
            val input = ctx.contentResolver.openInputStream(CallSync.audioUri(mediaId))
                ?: return@withContext Result.failure()   // file deleted on the phone
            val conn = URL(target).openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.connectTimeout = 20_000
            conn.readTimeout = 120_000
            conn.setChunkedStreamingMode(64 * 1024)
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            DataOutputStream(conn.outputStream).use { out ->
                for ((k, v) in fields) {
                    if (v.isEmpty()) continue
                    out.write("--$boundary\r\nContent-Disposition: form-data; name=\"$k\"\r\n\r\n$v\r\n".toByteArray())
                }
                out.write(("--$boundary\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"call\"\r\n" +
                        "Content-Type: $mime\r\n\r\n").toByteArray())
                input.use { it.copyTo(out, 64 * 1024) }
                out.write("\r\n--$boundary--\r\n".toByteArray())
            }
            val code = conn.responseCode
            conn.disconnect()
            when {
                code in 200..299 -> {
                    Prefs.setLastCallUpload(ctx, System.currentTimeMillis())
                    Result.success()
                }
                code in 400..499 -> Result.failure()   // unsupported format / too long / bad token
                else -> Result.retry()
            }
        } catch (_: SecurityException) {
            Result.failure()
        } catch (_: Exception) {
            if (runAttemptCount < 6) Result.retry() else Result.failure()
        }
    }
}

/** "שיחה מוקלטת עם 050-… — להעלות?" for numbers that aren't customers. Nothing is
 *  sent unless the agent taps "העלה". */
object CallApproval {
    const val ACTION_UPLOAD = "com.nifraim.CALL_UPLOAD"
    const val ACTION_SKIP = "com.nifraim.CALL_SKIP"

    fun ask(ctx: Context, rec: CallSync.Recording, info: CallSync.CallInfo) {
        Notifications.ensureChannels(ctx)
        val id = (rec.mediaId % Int.MAX_VALUE).toInt()
        fun action(act: String) = PendingIntent.getBroadcast(
            ctx, id * 2 + if (act == ACTION_UPLOAD) 0 else 1,
            Intent(ctx, CallApprovalReceiver::class.java).setAction(act)
                .putExtra("notif_id", id)
                .putExtra(CallUploadWorker.KEY_MEDIA_ID, rec.mediaId)
                .putExtra(CallUploadWorker.KEY_MIME, rec.mime)
                .putExtra(CallUploadWorker.KEY_DURATION_MS, rec.durationMs)
                .putExtra(CallUploadWorker.KEY_PHONE, info.number)
                .putExtra(CallUploadWorker.KEY_DIRECTION, info.direction)
                .putExtra(CallUploadWorker.KEY_STARTED_AT, info.startedAtMs ?: 0L),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val who = CallSync.display(info.number) ?: "מספר לא מזוהה"
        val n = NotificationCompat.Builder(ctx, Notifications.CH_CALLS)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle("שיחה מוקלטת עם ⁦$who⁩")
            .setContentText("המספר אינו ברשימת הלקוחות. להעלות לסיכום?")
            .setAutoCancel(true)
            .addAction(0, "העלה", action(ACTION_UPLOAD))
            .addAction(0, "לא", action(ACTION_SKIP))
            .build()
        try {
            ctx.getSystemService(NotificationManager::class.java).notify(id, n)
        } catch (_: SecurityException) {
        }
    }
}

class CallApprovalReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        ctx.getSystemService(NotificationManager::class.java).cancel(intent.getIntExtra("notif_id", 0))
        if (intent.action != CallApproval.ACTION_UPLOAD) return
        val rec = CallSync.Recording(
            mediaId = intent.getLongExtra(CallUploadWorker.KEY_MEDIA_ID, -1),
            name = "", mime = intent.getStringExtra(CallUploadWorker.KEY_MIME) ?: "audio/mp4",
            modifiedMs = 0, durationMs = intent.getLongExtra(CallUploadWorker.KEY_DURATION_MS, 0), pending = false,
        )
        if (rec.mediaId < 0) return
        CallJobs.upload(ctx, rec, CallSync.CallInfo(
            intent.getStringExtra(CallUploadWorker.KEY_PHONE),
            intent.getStringExtra(CallUploadWorker.KEY_DIRECTION),
            intent.getLongExtra(CallUploadWorker.KEY_STARTED_AT, 0).takeIf { it > 0 },
        ))
    }
}
