package com.zhiday.resume

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.max
import kotlin.math.roundToInt

/** A local, touch-first square cropper. The original image never leaves the device before Save. */
class CropAvatarActivity : ComponentActivity() {
    companion object {
        const val EXTRA_SOURCE_URI = "source_uri"
        const val EXTRA_CROPPED_PATH = "cropped_path"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val source = intent.getStringExtra(EXTRA_SOURCE_URI)?.let(Uri::parse)
        if (source == null) {
            finish()
            return
        }
        lifecycleScope.launch {
            val bitmap = runCatching { loadBitmap(source) }.getOrNull()
            if (bitmap == null) {
                setResult(RESULT_CANCELED)
                finish()
            } else {
                setContent {
                    CropAvatarScreen(
                        bitmap = bitmap,
                        onCancel = { finish() },
                        onSave = { scale, offset, viewport -> saveCrop(bitmap, scale, offset, viewport) },
                    )
                }
            }
        }
    }

    private suspend fun loadBitmap(uri: Uri): Bitmap = withContext(Dispatchers.IO) {
        val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: error("无法读取图片")
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        var sample = 1
        while (max(bounds.outWidth / sample, bounds.outHeight / sample) > 2048) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options) ?: error("图片格式不支持")
    }

    private fun saveCrop(bitmap: Bitmap, scale: Float, offset: Offset, viewport: IntSize) {
        lifecycleScope.launch {
            val file = withContext(Dispatchers.Default) {
                val outputSize = 1080
                val ratio = outputSize.toFloat() / viewport.width
                val result = Bitmap.createBitmap(outputSize, outputSize, Bitmap.Config.ARGB_8888)
                val canvas = android.graphics.Canvas(result)
                canvas.drawColor(android.graphics.Color.WHITE)
                val paint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG or android.graphics.Paint.FILTER_BITMAP_FLAG)
                val width = bitmap.width * scale * ratio
                val height = bitmap.height * scale * ratio
                val left = ((viewport.width - bitmap.width * scale) / 2f + offset.x) * ratio
                val top = ((viewport.height - bitmap.height * scale) / 2f + offset.y) * ratio
                canvas.drawBitmap(bitmap, null, android.graphics.RectF(left, top, left + width, top + height), paint)
                File(cacheDir, "avatar-${System.currentTimeMillis()}.jpg").also { output ->
                    output.outputStream().use { stream -> result.compress(Bitmap.CompressFormat.JPEG, 92, stream) }
                }
            }
            setResult(RESULT_OK, Intent().putExtra(EXTRA_CROPPED_PATH, file.absolutePath))
            finish()
        }
    }
}

@Composable
private fun CropAvatarScreen(
    bitmap: Bitmap,
    onCancel: () -> Unit,
    onSave: (Float, Offset, IntSize) -> Unit,
) {
    var viewport by remember { mutableStateOf(IntSize.Zero) }
    var zoom by remember { mutableFloatStateOf(1f) }
    var pan by remember { mutableStateOf(Offset.Zero) }
    val baseScale = if (viewport.width > 0) max(viewport.width.toFloat() / bitmap.width, viewport.height.toFloat() / bitmap.height) else 1f
    val scale = baseScale * zoom
    fun constrained(value: Offset, newScale: Float = scale): Offset {
        val maxX = max(0f, (bitmap.width * newScale - viewport.width) / 2f)
        val maxY = max(0f, (bitmap.height * newScale - viewport.height) / 2f)
        return Offset(value.x.coerceIn(-maxX, maxX), value.y.coerceIn(-maxY, maxY))
    }
    MaterialTheme {
        Surface(Modifier.fillMaxSize(), color = Color(0xFFF7F7F4)) {
            Column(Modifier.fillMaxSize().padding(20.dp)) {
                Text("裁剪简历头像", style = MaterialTheme.typography.headlineSmall, color = Color(0xFF1D2330))
                Spacer(Modifier.height(6.dp))
                Text("拖动调整位置，双指缩放。保存后会按头像区域自动适配简历。", color = Color(0xFF697386), style = MaterialTheme.typography.bodyMedium)
                Spacer(Modifier.height(24.dp))
                Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .aspectRatio(1f)
                            .clip(RoundedCornerShape(24.dp))
                            .background(Color(0xFF202638))
                            .onSizeChanged { size -> viewport = size }
                            .pointerInput(bitmap, viewport, zoom) {
                                detectTransformGestures { _, gesturePan, gestureZoom, _ ->
                                    val nextZoom = (zoom * gestureZoom).coerceIn(1f, 4f)
                                    val nextScale = baseScale * nextZoom
                                    zoom = nextZoom
                                    pan = constrained(pan + gesturePan, nextScale)
                                }
                            },
                    ) {
                        if (viewport.width > 0) {
                            Canvas(Modifier.fillMaxSize()) {
                                val width = (bitmap.width * scale).roundToInt()
                                val height = (bitmap.height * scale).roundToInt()
                                val left = ((size.width - width) / 2f + pan.x).roundToInt()
                                val top = ((size.height - height) / 2f + pan.y).roundToInt()
                                drawImage(bitmap.asImageBitmap(), dstOffset = IntOffset(left, top), dstSize = IntSize(width, height))
                            }
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
                Text("提示：头像会保持正方形，避免在简历中被拉伸成不协调的长方形。", color = Color(0xFF697386), style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.weight(1f))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f), shape = RoundedCornerShape(14.dp)) { Text("取消") }
                    Button(
                        onClick = { if (viewport.width > 0) onSave(scale, pan, viewport) },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(14.dp),
                    ) { Text("保存头像") }
                }
            }
        }
    }
}
