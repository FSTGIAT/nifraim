package com.nifraim.smsforwarder

import android.content.Context
import android.util.Log
import com.android.installreferrer.api.InstallReferrerClient
import com.android.installreferrer.api.InstallReferrerStateListener

/**
 * Auto-configures the agent's webhook on first launch from the Play Store install
 * referrer. When an agent installs via their personalized "התקן את Nifraim" link in
 * the Nifraim web UI, that link carries `referrer=token=<their-token>`; we read it
 * here and build the webhook URL so there's nothing to copy/paste.
 *
 * Safe by construction: runs only when no webhook is set yet (never clobbers a manual
 * value), and a missing / token-less / search-installed referrer is a silent no-op —
 * the manual paste flow in MainActivity still works.
 */
object InstallReferrerHelper {

    private const val TAG = "InstallReferrer"

    /** Production webhook base — real Play installs always reach Railway. */
    private const val WEBHOOK_BASE =
        "https://nifraim-production.up.railway.app/api/portal-automation/phone-forward/"

    /** [onConfigured] is invoked (on a binder thread) only when the webhook was set. */
    fun maybeConfigureFromReferrer(ctx: Context, onConfigured: () -> Unit) {
        if (Prefs.getWebhookUrl(ctx).isNotBlank()) return

        val client = InstallReferrerClient.newBuilder(ctx).build()
        client.startConnection(object : InstallReferrerStateListener {
            override fun onInstallReferrerSetupFinished(responseCode: Int) {
                try {
                    if (responseCode == InstallReferrerClient.InstallReferrerResponse.OK) {
                        val referrer = client.installReferrer.installReferrer ?: ""
                        val token = parseToken(referrer)
                        // Re-check the guard — the user may have pasted in the meantime.
                        if (!token.isNullOrBlank() && Prefs.getWebhookUrl(ctx).isBlank()) {
                            Prefs.setWebhookUrl(ctx, WEBHOOK_BASE + token)
                            onConfigured()
                        }
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "install referrer read failed", e)
                } finally {
                    try { client.endConnection() } catch (_: Exception) { /* ignore */ }
                }
            }

            override fun onInstallReferrerServiceDisconnected() { /* no retry needed */ }
        })
    }

    /** Referrer is "token=ABC" (possibly &-joined with other params). */
    private fun parseToken(referrer: String): String? {
        for (part in referrer.split('&')) {
            val kv = part.split('=', limit = 2)
            if (kv.size == 2 && kv[0] == "token" && kv[1].isNotBlank()) return kv[1]
        }
        return null
    }
}
