package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class CounterActivity : AppCompatActivity() {
    private var count = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_counter)

        val counterText = findViewById<TextView>(R.id.text_counter)
        val plusButton = findViewById<Button>(R.id.btn_plus)
        val minusButton = findViewById<Button>(R.id.btn_minus)

        fun update() {
            counterText.text = "Count: $count"
        }

        plusButton.setOnClickListener {
            count += 1
            update()
        }

        minusButton.setOnClickListener {
            count -= 1
            update()
        }

        update()
    }
}
