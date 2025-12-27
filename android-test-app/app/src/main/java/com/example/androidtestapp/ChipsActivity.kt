package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.chip.Chip

class ChipsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chips)

        val chipA = findViewById<Chip>(R.id.chip_filter_a)
        val chipB = findViewById<Chip>(R.id.chip_filter_b)
        val chipC = findViewById<Chip>(R.id.chip_filter_c)
        val result = findViewById<TextView>(R.id.chip_result)

        findViewById<Button>(R.id.btn_chip_apply).setOnClickListener {
            val selected = listOf(chipA, chipB, chipC)
                .filter { it.isChecked }
                .map { it.text.toString() }
            result.text = if (selected.isEmpty()) {
                "Selected: None"
            } else {
                "Selected: ${selected.joinToString(", ")}"
            }
        }
    }
}
