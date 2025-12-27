package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.ProgressBar
import android.widget.RatingBar
import android.widget.SeekBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class SliderActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_slider)

        val statusText = findViewById<TextView>(R.id.text_slider_status)
        val seekBar = findViewById<SeekBar>(R.id.seekbar)
        val ratingBar = findViewById<RatingBar>(R.id.rating_bar)
        val progressBar = findViewById<ProgressBar>(R.id.progress_bar)
        val increase = findViewById<Button>(R.id.btn_increase)
        val decrease = findViewById<Button>(R.id.btn_decrease)

        fun updateStatus() {
            statusText.text = "Progress: ${seekBar.progress} Rating: ${ratingBar.rating.toInt()}"
            progressBar.progress = seekBar.progress
        }

        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar, progress: Int, fromUser: Boolean) {
                updateStatus()
            }

            override fun onStartTrackingTouch(seekBar: SeekBar) = Unit

            override fun onStopTrackingTouch(seekBar: SeekBar) = Unit
        })

        increase.setOnClickListener {
            seekBar.progress = (seekBar.progress + 10).coerceAtMost(100)
            ratingBar.rating = (ratingBar.rating + 1).coerceAtMost(5f)
            updateStatus()
        }

        decrease.setOnClickListener {
            seekBar.progress = (seekBar.progress - 10).coerceAtLeast(0)
            ratingBar.rating = (ratingBar.rating - 1).coerceAtLeast(0f)
            updateStatus()
        }

        updateStatus()
    }
}
