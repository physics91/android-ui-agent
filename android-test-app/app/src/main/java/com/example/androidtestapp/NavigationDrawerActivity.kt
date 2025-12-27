package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.navigation.NavigationView

class NavigationDrawerActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_navigation_drawer)

        val drawerLayout = findViewById<DrawerLayout>(R.id.drawer_layout)
        val toolbar = findViewById<MaterialToolbar>(R.id.drawer_toolbar)
        val navView = findViewById<NavigationView>(R.id.navigation_view)
        val status = findViewById<TextView>(R.id.drawer_selection)
        val openButton = findViewById<Button>(R.id.btn_open_drawer)

        toolbar.title = "Navigation Drawer"

        openButton.setOnClickListener {
            drawerLayout.openDrawer(GravityCompat.START)
        }

        navView.setNavigationItemSelectedListener { item ->
            status.text = "Selected: ${item.title}"
            drawerLayout.closeDrawer(GravityCompat.START)
            true
        }
    }
}
