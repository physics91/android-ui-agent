package com.example.androidtestapp

import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class FilePickerActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_file_picker)

        val statusText = findViewById<TextView>(R.id.text_file_result)
        val openButton = findViewById<Button>(R.id.btn_open_document)

        val launcher = registerForActivityResult(
            ActivityResultContracts.OpenDocument(),
        ) { uri: Uri? ->
            statusText.text = if (uri != null) {
                "Result: ${uri.lastPathSegment ?: "Selected"}"
            } else {
                "Result: Cancelled"
            }
        }

        openButton.setOnClickListener {
            launcher.launch(arrayOf("*/*"))
        }
    }
}
