package com.example.androidtestapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.bottomnavigation.BottomNavigationView

class BottomNavActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_bottom_nav)

        val bottomNav = findViewById<BottomNavigationView>(R.id.bottom_navigation)

        if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.bottom_nav_container, SimpleTextFragment.newInstance("Home Screen"))
                .commit()
        }

        bottomNav.setOnItemSelectedListener { item ->
            val text = when (item.itemId) {
                R.id.nav_home -> "Home Screen"
                R.id.nav_dashboard -> "Dashboard Screen"
                R.id.nav_settings -> "Settings Screen"
                else -> "Home Screen"
            }
            supportFragmentManager.beginTransaction()
                .replace(R.id.bottom_nav_container, SimpleTextFragment.newInstance(text))
                .commit()
            true
        }

        bottomNav.selectedItemId = R.id.nav_home
    }
}
