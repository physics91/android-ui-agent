package com.example.androidtestapp

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.RadioGroup
import android.widget.Spinner
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat

class ControlsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_controls)

        val emailInput = findViewById<EditText>(R.id.input_email)
        val passwordInput = findViewById<EditText>(R.id.input_password)
        val termsCheck = findViewById<CheckBox>(R.id.checkbox_terms)
        val newsletterSwitch = findViewById<SwitchCompat>(R.id.switch_newsletter)
        val tierGroup = findViewById<RadioGroup>(R.id.radio_group)
        val spinner = findViewById<Spinner>(R.id.spinner_planet)
        val submitButton = findViewById<Button>(R.id.btn_submit)
        val resultText = findViewById<TextView>(R.id.text_result)

        val adapter = ArrayAdapter.createFromResource(
            this,
            R.array.planets,
            android.R.layout.simple_spinner_item,
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinner.adapter = adapter

        submitButton.setOnClickListener {
            val email = emailInput.text.toString().trim()
            val passwordLength = passwordInput.text?.length ?: 0
            val terms = termsCheck.isChecked
            val newsletter = newsletterSwitch.isChecked
            val tierId = tierGroup.checkedRadioButtonId
            val tier = if (tierId == R.id.radio_premium) "premium" else "basic"
            val planet = spinner.selectedItem?.toString() ?: "unknown"

            resultText.text = "SUBMITTED email=$email passwordLen=$passwordLength terms=$terms " +
                "newsletter=$newsletter tier=$tier planet=$planet"
        }
    }
}
