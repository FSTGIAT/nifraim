package com.nifraim.smsforwarder

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import androidx.core.content.ContextCompat
import androidx.work.*
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var urlEdit: EditText
    private lateinit var saveBtn: Button
    private lateinit var testBtn: Button
    private lateinit var batteryBtn: Button
    private lateinit var enableSwitch: SwitchCompat
    private lateinit var statusText: TextView
    private lateinit var lastForwardText: TextView
    private lateinit var batteryWarning: LinearLayout

    private val requestPermissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { updateStatus() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        urlEdit = findViewById(R.id.urlEdit)
        saveBtn = findViewById(R.id.saveBtn)
        testBtn = findViewById(R.id.testBtn)
        batteryBtn = findViewById(R.id.batteryBtn)
        enableSwitch = findViewById(R.id.enableSwitch)
        statusText = findViewById(R.id.statusText)
        lastForwardText = findViewById(R.id.lastForwardText)
        batteryWarning = findViewById(R.id.batteryWarning)

        urlEdit.setText(Prefs.getWebhookUrl(this))
        enableSwitch.isChecked = Prefs.isEnabled(this)

        saveBtn.setOnClickListener {
            Prefs.setWebhookUrl(this, urlEdit.text.toString().trim())
            Toast.makeText(this, "נשמר", Toast.LENGTH_SHORT).show()
            updateStatus()
        }

        enableSwitch.setOnCheckedChangeListener { _, checked ->
            Prefs.setEnabled(this, checked)
            updateStatus()
        }

        testBtn.setOnClickListener {
            val url = Prefs.getWebhookUrl(this)
            if (url.isBlank()) {
                Toast.makeText(this, "יש להזין כתובת Webhook תחילה", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val data = workDataOf(
                SmsForwardWorker.KEY_URL to url,
                SmsForwardWorker.KEY_BODY to "Nifraim test — קוד אימות: 123456",
            )
            WorkManager.getInstance(this)
                .enqueue(OneTimeWorkRequestBuilder<SmsForwardWorker>().setInputData(data).build())
            Toast.makeText(this, "הודעת בדיקה נשלחה", Toast.LENGTH_SHORT).show()
        }

        batteryBtn.setOnClickListener {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            startActivity(intent)
        }

        checkAndRequestPermissions()
        updateStatus()
    }

    override fun onResume() {
        super.onResume()
        updateStatus()
    }

    private fun updateStatus() {
        val url = Prefs.getWebhookUrl(this)
        val enabled = Prefs.isEnabled(this)
        val hasPerms = hasSmsPermission()
        val batteryOptimized = isBatteryOptimized()

        batteryWarning.visibility = if (batteryOptimized) android.view.View.VISIBLE else android.view.View.GONE

        val ok = url.isNotBlank() && enabled && hasPerms
        statusText.text = when {
            !hasPerms -> "⚠ חסרה הרשאת SMS — לחץ לאישור"
            url.isBlank() -> "לא מוגדר — הדבק כתובת Webhook"
            !enabled -> "מושבת"
            else -> "פעיל — מעביר הודעות SMS לשרת"
        }
        statusText.setTextColor(
            ContextCompat.getColor(this, if (ok) R.color.status_ok else R.color.status_warn)
        )

        if (!hasPerms) {
            statusText.setOnClickListener { checkAndRequestPermissions() }
        } else {
            statusText.setOnClickListener(null)
        }

        val lastTs = Prefs.getLastForward(this)
        lastForwardText.text = if (lastTs == 0L) "—"
        else SimpleDateFormat("dd/MM HH:mm", Locale.getDefault()).format(Date(lastTs))
    }

    private fun hasSmsPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) ==
                PackageManager.PERMISSION_GRANTED

    private fun isBatteryOptimized(): Boolean {
        val pm = getSystemService(android.os.PowerManager::class.java)
        return !pm.isIgnoringBatteryOptimizations(packageName)
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
}
