package com.example.androidtestapp

import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.bottomsheet.BottomSheetDialog
import java.util.Calendar

class DialogActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dialog)

        val resultText = findViewById<TextView>(R.id.dialog_result)

        findViewById<Button>(R.id.btn_alert).setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("Confirm")
                .setMessage("Proceed with action?")
                .setPositiveButton("OK") { _, _ ->
                    resultText.text = "ALERT_OK"
                }
                .setNegativeButton("Cancel") { _, _ ->
                    resultText.text = "ALERT_CANCEL"
                }
                .show()
        }

        findViewById<Button>(R.id.btn_bottom_sheet).setOnClickListener {
            val dialog = BottomSheetDialog(this)
            val view = layoutInflater.inflate(R.layout.layout_bottom_sheet, null)
            view.findViewById<Button>(R.id.btn_sheet_ok).setOnClickListener {
                resultText.text = "SHEET_OK"
                dialog.dismiss()
            }
            dialog.setContentView(view)
            dialog.show()
        }

        findViewById<Button>(R.id.btn_date_picker).setOnClickListener {
            val cal = Calendar.getInstance()
            DatePickerDialog(
                this,
                { _, year, month, day ->
                    resultText.text = String.format("DATE %04d-%02d-%02d", year, month + 1, day)
                },
                cal.get(Calendar.YEAR),
                cal.get(Calendar.MONTH),
                cal.get(Calendar.DAY_OF_MONTH),
            ).show()
        }

        findViewById<Button>(R.id.btn_time_picker).setOnClickListener {
            val cal = Calendar.getInstance()
            TimePickerDialog(
                this,
                { _, hour, minute ->
                    resultText.text = String.format("TIME %02d:%02d", hour, minute)
                },
                cal.get(Calendar.HOUR_OF_DAY),
                cal.get(Calendar.MINUTE),
                true,
            ).show()
        }
    }
}
