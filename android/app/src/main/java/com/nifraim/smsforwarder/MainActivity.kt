package com.nifraim.smsforwarder

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import androidx.core.content.ContextCompat
import androidx.core.graphics.drawable.DrawableCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.work.*
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var urlEdit: EditText
    private lateinit var enableSwitch: SwitchCompat
    private lateinit var callsSwitch: SwitchCompat
    private lateinit var wifiSwitch: SwitchCompat
    private lateinit var statusDot: View
    private lateinit var statusTitle: TextView
    private lateinit var statusSub: TextView
    private lateinit var lastForwardText: TextView
    private lateinit var lastCallText: TextView
    private lateinit var clientsCountText: TextView
    private lateinit var setupCard: View
    private lateinit var callsBody: View
    private lateinit var callsWarn: View
    private lateinit var callsWarnText: TextView
    private lateinit var advancedBody: View

    private val requestPermissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { onPermissionsChanged() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        applyWindowInsets()
        Notifications.ensureChannels(this)

        urlEdit = findViewById(R.id.urlEdit)
        enableSwitch = findViewById(R.id.enableSwitch)
        callsSwitch = findViewById(R.id.callsSwitch)
        wifiSwitch = findViewById(R.id.wifiSwitch)
        statusDot = findViewById(R.id.statusDot)
        statusTitle = findViewById(R.id.statusTitle)
        statusSub = findViewById(R.id.statusSub)
        lastForwardText = findViewById(R.id.lastForwardText)
        lastCallText = findViewById(R.id.lastCallText)
        clientsCountText = findViewById(R.id.clientsCountText)
        setupCard = findViewById(R.id.setupCard)
        callsBody = findViewById(R.id.callsBody)
        callsWarn = findViewById(R.id.callsWarn)
        callsWarnText = findViewById(R.id.callsWarnText)
        advancedBody = findViewById(R.id.advancedBody)

        findViewById<TextView>(R.id.wordmark).text = SpannableStringBuilder("Nifraim App").apply {
            setSpan(ForegroundColorSpan(color(R.color.sky_deep)), 8, 11, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }

        urlEdit.setText(Prefs.getWebhookUrl(this))
        enableSwitch.isChecked = Prefs.isEnabled(this)
        callsSwitch.isChecked = Prefs.isCallsEnabled(this)
        wifiSwitch.isChecked = Prefs.isWifiOnly(this)

        findViewById<Button>(R.id.saveBtn).setOnClickListener {
            Prefs.setWebhookUrl(this, urlEdit.text.toString().trim())
            Toast.makeText(this, "נשמר", Toast.LENGTH_SHORT).show()
            refreshTemplates()
            updateStatus()
        }
        findViewById<View>(R.id.advancedHeader).setOnClickListener { toggleAdvanced() }
        findViewById<Button>(R.id.stepAccountBtn).setOnClickListener { toggleAdvanced(open = true) }
        findViewById<Button>(R.id.stepSmsBtn).setOnClickListener { checkAndRequestPermissions() }
        findViewById<Button>(R.id.stepBatteryBtn).setOnClickListener { requestBatteryExemption() }
        findViewById<Button>(R.id.callsWarnBtn).setOnClickListener { requestCallPermissions() }

        enableSwitch.setOnCheckedChangeListener { _, checked ->
            Prefs.setEnabled(this, checked)
            updateStatus()
        }
        callsSwitch.setOnCheckedChangeListener { _, checked ->
            Prefs.setCallsEnabled(this, checked)
            CallJobs.schedule(this)
            if (checked) {
                requestCallPermissions()
                refreshClients()
            }
            updateStatus()
        }
        wifiSwitch.setOnCheckedChangeListener { _, checked -> Prefs.setWifiOnly(this, checked) }

        findViewById<Button>(R.id.testBtn).setOnClickListener {
            val url = Prefs.getWebhookUrl(this)
            if (url.isBlank()) {
                Toast.makeText(this, "יש לחבר את החשבון תחילה", Toast.LENGTH_SHORT).show()
                toggleAdvanced(open = true)
                return@setOnClickListener
            }
            val data = workDataOf(
                SmsForwardWorker.KEY_URL to url,
                SmsForwardWorker.KEY_BODY to "Nifraim test — קוד אימות: 123456",
            )
            WorkManager.getInstance(this)
                .enqueue(OneTimeWorkRequestBuilder<SmsForwardWorker>().setInputData(data).build())
            Toast.makeText(this, "קוד בדיקה נשלח", Toast.LENGTH_SHORT).show()
        }

        checkAndRequestPermissions()
        refreshTemplates()
        schedulePeriodicTemplateRefresh()
        CallJobs.schedule(this)
        updateStatus()

        // If the agent installed via their personalized Play link, the webhook URL
        // arrives in the install referrer — fill it in automatically (first launch
        // only, never clobbering a manually-pasted URL).
        InstallReferrerHelper.maybeConfigureFromReferrer(this) {
            runOnUiThread {
                urlEdit.setText(Prefs.getWebhookUrl(this))
                refreshTemplates()
                updateStatus()
                Toast.makeText(this, "החשבון חובר אוטומטית", Toast.LENGTH_SHORT).show()
            }
        }
    }

    /**
     * Pad the root view by the system-bar insets.
     *
     * Apps targeting API 36 (Android 16) are drawn edge-to-edge and the
     * `windowOptOutEdgeToEdgeEnforcement` escape hatch no longer works, so without
     * this the header sits under the status bar and the footer under the gesture
     * nav bar.
     */
    private fun applyWindowInsets() {
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.root)) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        // The canvas is light — keep the status-bar icons dark.
        WindowInsetsControllerCompat(window, window.decorView).isAppearanceLightStatusBars = true
    }

    /** Fetch the latest company SMS templates now (off the main thread).
     *  NOT expedited: TemplateFetchWorker has no getForegroundInfo(), which API <= 30
     *  needs for expedited work. A normal one-time request fetches within seconds. */
    private fun refreshTemplates() {
        val request = OneTimeWorkRequestBuilder<TemplateFetchWorker>()
            .setConstraints(
                Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
            )
            .build()
        WorkManager.getInstance(this).enqueue(request)
    }

    private fun refreshClients() {
        Thread {
            CallSync.refreshClients(this)
            runOnUiThread { updateStatus() }
        }.start()
    }

    /** Keep templates (and the customer-phone list) current on background-only phones. */
    private fun schedulePeriodicTemplateRefresh() {
        val request = PeriodicWorkRequestBuilder<TemplateFetchWorker>(24, TimeUnit.HOURS)
            .setConstraints(
                Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
            )
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "template-refresh",
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }

    override fun onResume() {
        super.onResume()
        // Opening the app catches up on any recording the background trigger missed.
        if (Prefs.isCallsEnabled(this) && CallSync.hasAudioPermission(this)) CallJobs.scanNow(this)
        updateStatus()
    }

    private fun onPermissionsChanged() {
        if (Prefs.isCallsEnabled(this) && CallSync.hasAudioPermission(this)) CallJobs.scanNow(this)
        updateStatus()
    }

    private fun toggleAdvanced(open: Boolean? = null) {
        val show = open ?: (advancedBody.visibility != View.VISIBLE)
        advancedBody.visibility = if (show) View.VISIBLE else View.GONE
        findViewById<View>(R.id.advancedChevron).rotation = if (show) 180f else 0f
        if (show) urlEdit.requestFocus()
    }

    private fun updateStatus() {
        val connected = Prefs.getWebhookUrl(this).isNotBlank()
        val sms = hasSmsPermission()
        val battery = !isBatteryOptimized()
        val enabled = Prefs.isEnabled(this)

        step(R.id.stepAccountIcon, R.id.stepAccountBtn, connected)
        step(R.id.stepSmsIcon, R.id.stepSmsBtn, sms)
        step(R.id.stepBatteryIcon, R.id.stepBatteryBtn, battery)
        setupCard.visibility = if (connected && sms && battery) View.GONE else View.VISIBLE

        val ok = connected && sms && enabled
        statusTitle.text = when {
            !connected -> "עוד לא מחובר"
            !sms -> "חסרה הרשאה"
            !enabled -> "מושהה"
            else -> "פועל"
        }
        statusSub.text = when {
            !connected -> "חברו את האפליקציה לחשבון Nifraim שלכם."
            !sms -> "בלי הרשאת SMS הקודים לא יגיעו לרובוט."
            !enabled -> "העברת קודי אימות כבויה."
            !battery -> "פועל. כדי שלא יתעכב ברקע, אפשרו פעולה ללא הגבלת סוללה."
            else -> "קודי אימות מגיעים לרובוט אוטומטית."
        }
        DrawableCompat.setTint(
            DrawableCompat.wrap(statusDot.background.mutate()),
            color(if (ok) R.color.ok else R.color.warn),
        )

        lastForwardText.text = time(Prefs.getLastForward(this))

        // Calls card
        val calls = Prefs.isCallsEnabled(this)
        callsBody.visibility = if (calls) View.VISIBLE else View.GONE
        lastCallText.text = time(Prefs.getLastCallUpload(this))
        val clients = Prefs.getClientHashes(this).size
        clientsCountText.text = if (clients > 0) clients.toString() else "עוד לא נטען"
        val missing = when {
            !connected -> "חברו את החשבון קודם."
            !CallSync.hasAudioPermission(this) -> "צריך הרשאה לקבצי אודיו כדי למצוא את הקלטות השיחה."
            !CallSync.hasCallLogPermission(this) -> "צריך הרשאה ליומן השיחות כדי לדעת עם מי דיברתם."
            else -> null
        }
        callsWarn.visibility = if (calls && missing != null) View.VISIBLE else View.GONE
        callsWarnText.text = missing ?: ""
        findViewById<View>(R.id.callsWarnBtn).visibility = if (connected) View.VISIBLE else View.GONE
    }

    private fun step(iconId: Int, btnId: Int, done: Boolean) {
        findViewById<ImageView>(iconId).apply {
            setImageResource(if (done) R.drawable.ic_check_circle else R.drawable.ic_circle)
            setColorFilter(color(if (done) R.color.ok else R.color.border))
        }
        findViewById<View>(btnId).visibility = if (done) View.GONE else View.VISIBLE
    }

    private fun time(ts: Long) =
        if (ts == 0L) "עדיין לא" else SimpleDateFormat("dd/MM HH:mm", Locale.getDefault()).format(Date(ts))

    private fun color(id: Int) = ContextCompat.getColor(this, id)

    private fun hasSmsPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) ==
                PackageManager.PERMISSION_GRANTED

    private fun isBatteryOptimized(): Boolean {
        val pm = getSystemService(android.os.PowerManager::class.java)
        return !pm.isIgnoringBatteryOptimizations(packageName)
    }

    private fun requestBatteryExemption() {
        startActivity(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
            data = Uri.parse("package:$packageName")
        })
    }

    private fun checkAndRequestPermissions() {
        val needed = mutableListOf<String>()
        if (!hasSmsPermission()) needed.add(Manifest.permission.RECEIVE_SMS)
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) needed.add(Manifest.permission.POST_NOTIFICATIONS)
        if (needed.isNotEmpty()) requestPermissions.launch(needed.toTypedArray())
    }

    /** Asked only when the agent turns the calls card on. */
    private fun requestCallPermissions() {
        val needed = mutableListOf<String>()
        if (!CallSync.hasAudioPermission(this)) needed.add(
            if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO
            else Manifest.permission.READ_EXTERNAL_STORAGE
        )
        if (!CallSync.hasCallLogPermission(this)) needed.add(Manifest.permission.READ_CALL_LOG)
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) needed.add(Manifest.permission.POST_NOTIFICATIONS)
        if (needed.isNotEmpty()) requestPermissions.launch(needed.toTypedArray())
        else onPermissionsChanged()
    }
}
