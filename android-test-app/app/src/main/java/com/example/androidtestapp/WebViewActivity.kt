package com.example.androidtestapp

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class WebViewActivity : AppCompatActivity() {
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_webview)

        val webView = findViewById<WebView>(R.id.web_view)
        val resultText = findViewById<TextView>(R.id.text_web_result)
        val runButton = findViewById<Button>(R.id.btn_run_js)

        webView.webViewClient = WebViewClient()
        webView.settings.javaScriptEnabled = true
        webView.loadUrl("file:///android_asset/sample.html")

        runButton.setOnClickListener {
            val script = "document.getElementById('web-button').click();" +
                "document.getElementById('status').innerText;"
            webView.evaluateJavascript(script) { value ->
                val cleaned = value?.trim('"') ?: "null"
                resultText.text = "Web Result: $cleaned"
            }
        }
    }
}
