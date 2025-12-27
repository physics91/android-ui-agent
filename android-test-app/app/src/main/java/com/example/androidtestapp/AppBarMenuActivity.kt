package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.appbar.MaterialToolbar

class AppBarMenuActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_app_bar_menu)

        val toolbar = findViewById<MaterialToolbar>(R.id.menu_toolbar)
        val status = findViewById<TextView>(R.id.menu_status)
        val overflowButton = findViewById<Button>(R.id.btn_open_overflow)

        toolbar.title = "App Bar Menu"
        toolbar.inflateMenu(R.menu.app_bar_menu)
        toolbar.setOnMenuItemClickListener { item ->
            val action = when (item.itemId) {
                R.id.action_search -> "Search"
                R.id.action_favorite -> "Favorite"
                R.id.action_share -> "Share"
                else -> "Unknown"
            }
            status.text = "Last Action: $action"
            true
        }

        overflowButton.setOnClickListener {
            toolbar.showOverflowMenu()
        }
    }
}
