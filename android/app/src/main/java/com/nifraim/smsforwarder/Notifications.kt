package com.nifraim.smsforwarder

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import androidx.core.app.NotificationCompat

/** Notification channels: a silent one for background work, one for "upload this call?". */
object Notifications {
    const val CH_SYNC = "sync"
    const val CH_CALLS = "calls"

    fun ensureChannels(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CH_SYNC, "פעולה ברקע", NotificationManager.IMPORTANCE_MIN)
        )
        nm.createNotificationChannel(
            NotificationChannel(CH_CALLS, "שיחות לאישור", NotificationManager.IMPORTANCE_DEFAULT).apply {
                description = "שיחה מוקלטת עם מספר שאינו לקוח — לשאול לפני העלאה"
            }
        )
    }

    /** The small notification WorkManager shows if it runs expedited work as a
     *  foreground service (API <= 30). */
    fun syncNotification(ctx: Context, text: String) =
        NotificationCompat.Builder(ctx, CH_SYNC)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle("Nifraim")
            .setContentText(text)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setOngoing(true)
            .build()
}
