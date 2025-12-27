package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.snackbar.Snackbar

class SnackbarToastActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_snackbar_toast)

        val statusText = findViewById<TextView>(R.id.text_feedback_status)
        val snackbarButton = findViewById<Button>(R.id.btn_show_snackbar)
        val toastButton = findViewById<Button>(R.id.btn_show_toast)

        snackbarButton.setOnClickListener {
            statusText.text = "Status: SNACKBAR_SHOWN"
            Snackbar.make(it, "Snackbar Message", Snackbar.LENGTH_LONG)
                .setAction("Action") {
                    statusText.text = "Status: SNACKBAR_ACTION"
                }
                .show()
        }

        toastButton.setOnClickListener {
            Toast.makeText(this, "Toast Message", Toast.LENGTH_SHORT).show()
            statusText.text = "Status: TOAST_SHOWN"
        }
    }
}
