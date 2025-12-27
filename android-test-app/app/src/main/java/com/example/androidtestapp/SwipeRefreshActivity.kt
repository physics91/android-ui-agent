package com.example.androidtestapp

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class SwipeRefreshActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_swipe_refresh)

        val swipeRefresh = findViewById<SwipeRefreshLayout>(R.id.swipe_refresh)
        val statusText = findViewById<TextView>(R.id.text_refresh_status)
        val triggerButton = findViewById<Button>(R.id.btn_trigger_refresh)
        val recyclerView = findViewById<RecyclerView>(R.id.refresh_list)

        val items = (1..30).map { index -> "Refresh Item $index" }
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = SimpleStringAdapter(items)

        val handler = Handler(Looper.getMainLooper())

        fun completeRefresh() {
            statusText.text = "Status: Refreshed"
            swipeRefresh.isRefreshing = false
        }

        swipeRefresh.setOnRefreshListener {
            statusText.text = "Status: Refreshing"
            handler.postDelayed({ completeRefresh() }, 600)
        }

        triggerButton.setOnClickListener {
            swipeRefresh.isRefreshing = true
            statusText.text = "Status: Refreshing"
            handler.postDelayed({ completeRefresh() }, 600)
        }
    }
}
