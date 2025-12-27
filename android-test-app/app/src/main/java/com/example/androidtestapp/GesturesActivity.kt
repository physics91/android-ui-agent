package com.example.androidtestapp

import android.os.Bundle
import android.view.GestureDetector
import android.view.MotionEvent
import android.widget.FrameLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class GesturesActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_gestures)

        val resultText = findViewById<TextView>(R.id.gesture_result)
        val gestureArea = findViewById<FrameLayout>(R.id.gesture_area)

        val detector = GestureDetector(
            this,
            object : GestureDetector.SimpleOnGestureListener() {
                override fun onSingleTapConfirmed(e: MotionEvent): Boolean {
                    resultText.text = "SINGLE_TAP"
                    return true
                }

                override fun onDoubleTap(e: MotionEvent): Boolean {
                    resultText.text = "DOUBLE_TAP"
                    return true
                }

                override fun onLongPress(e: MotionEvent) {
                    resultText.text = "LONG_PRESS"
                }

                override fun onScroll(
                    e1: MotionEvent?,
                    e2: MotionEvent,
                    distanceX: Float,
                    distanceY: Float,
                ): Boolean {
                    resultText.text = "SCROLL"
                    return true
                }
            },
        )

        gestureArea.setOnTouchListener { _, event ->
            detector.onTouchEvent(event)
            true
        }
    }
}
