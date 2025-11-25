package com.example.mywebapp

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    // TODO: Modify your IP address or URL here
    // Note: If it starts with HTTP, you must configure android:usesCleartextTraffic="true" in AndroidManifest.xml
    private val targetUrl = "http://47.245.121.54:5173"

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)

        // Configure WebView settings
        webView.settings.apply {
            javaScriptEnabled = true // Enable JS, required by most web pages
            domStorageEnabled = true // Enable DOM storage to prevent some pages from loading blank
            useWideViewPort = true   // Adjust images to fit WebView size
            loadWithOverviewMode = true // Scale to screen size
        }

        // Set WebViewClient to ensure links open within the app, not in Chrome
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                // Return false means the WebView handles the URL itself
                return false
            }
        }

        // Set WebChromeClient (optional, used for page title, progress bar, etc.)
        webView.webChromeClient = WebChromeClient()

        // Load web page
        webView.loadUrl(targetUrl)

        // Handle physical back button logic (recommended for Android 13+)
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    // If the web page can go back, go back
                    webView.goBack()
                } else {
                    // Otherwise, exit the app
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }
}
