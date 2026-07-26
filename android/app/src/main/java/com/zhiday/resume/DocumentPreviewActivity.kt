package com.zhiday.resume

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import java.net.URLEncoder

/** Displays the generated cloud file inside the app using the same real renderers as the web app. */
class DocumentPreviewActivity : ComponentActivity() {
    companion object {
        const val EXTRA_URL = "preview_url"
        const val EXTRA_TYPE = "preview_type"
        const val EXTRA_TITLE = "preview_title"
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val fileUrl = intent.getStringExtra(EXTRA_URL).orEmpty()
        val type = intent.getStringExtra(EXTRA_TYPE).takeIf { it in setOf("docx", "pdf", "image", "text", "file") } ?: "pdf"
        val title = intent.getStringExtra(EXTRA_TITLE).orEmpty()
        if (fileUrl.isBlank()) {
            finish()
            return
        }
        val previewBase = BuildConfig.API_BASE_URL.removeSuffix("api/") + "static/app-document-preview.html"
        val previewUrl = "$previewBase?type=${encode(type)}&title=${encode(title)}&file=${encode(fileUrl)}"
        val webView = WebView(this).apply {
            layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = WebSettings.LOAD_DEFAULT
            settings.builtInZoomControls = false
            settings.displayZoomControls = false
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
            loadUrl(previewUrl)
        }
        setContentView(webView)
    }

    private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())
}
