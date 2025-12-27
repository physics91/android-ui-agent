package com.example.androidtestapp

import android.Manifest
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class PermissionActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_permission)

        val requestButton = findViewById<Button>(R.id.btn_request_permission)
        val statusText = findViewById<TextView>(R.id.text_permission_status)

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            statusText.text = "Status: NOT_REQUIRED"
            requestButton.isEnabled = false
            return
        }

        val launcher = registerForActivityResult(
            ActivityResultContracts.RequestPermission(),
        ) { granted ->
            statusText.text = if (granted) "Status: GRANTED" else "Status: DENIED"
        }

        requestButton.setOnClickListener {
            launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
