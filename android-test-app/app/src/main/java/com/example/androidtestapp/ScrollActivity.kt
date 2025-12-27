package com.example.androidtestapp

import android.os.Bundle
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class ScrollActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scroll)

        val container = findViewById<LinearLayout>(R.id.scroll_container)
        for (i in 1..60) {
            val textView = TextView(this)
            textView.text = "Scroll Item $i"
            textView.textSize = 16f
            textView.setPadding(0, 8, 0, 8)
            container.addView(textView)
        }
    }
}
