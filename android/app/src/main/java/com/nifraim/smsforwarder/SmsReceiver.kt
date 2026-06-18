package com.nifraim.smsforwarder

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import androidx.work.*
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

        val data = workDataOf(
            SmsForwardWorker.KEY_URL to url,
            SmsForwardWorker.KEY_BODY to body,
        )

        val request = OneTimeWorkRequestBuilder<SmsForwardWorker>()
            .setInputData(data)
            .setBackoffCriteria(BackoffPolicy.LINEAR, 10, TimeUnit.SECONDS)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()

        WorkManager.getInstance(ctx).enqueue(request)
    }
}
