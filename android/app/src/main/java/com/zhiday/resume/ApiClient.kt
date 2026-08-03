package com.zhiday.resume

import android.content.Context
import android.os.Environment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

data class User(
    val id: String,
    val username: String,
    val phone: String?,
    val role: String?,
    val avatarKey: String?,
    val avatarUrl: String?,
)
data class AuthSession(val token: String, val user: User)

data class ResumeContent(
    val name: String = "",
    val title: String = "",
    val age: String = "",
    val phone: String = "",
    val email: String = "",
    val summary: String = "",
    val skills: List<String> = emptyList(),
    val experience: List<String> = emptyList(),
    val projects: List<String> = emptyList(),
    val education: List<String> = emptyList(),
    val certificates: List<String> = emptyList(),
)

data class ResumeItem(
    val id: String,
    val name: String,
    val isDefault: Boolean,
    val updatedAt: String,
    val avatarKey: String?,
    val sourceType: String?,
    val sourceKey: String?,
    val content: ResumeContent,
)

data class JdTask(
    val id: String,
    val status: String,
    val source: String,
    val detail: String,
    val progress: String?,
    val error: String?,
    val result: JSONObject?,
)

data class GenerationItem(
    val id: String,
    val status: String,
    val resumeName: String,
    val createdAt: String,
    val title: String,
    val error: String?,
    val message: String?,
    val docxKey: String?,
    val pdfKey: String?,
    val overallScore: Int?,
    val jobMatchScore: Int?,
    val keywordCoverageScore: Int?,
    val visualScore: Int?,
    val optimizations: List<String>,
)
data class ResumeTemplate(
    val id: String,
    val name: String,
    val category: String,
    val displayCategory: String,
    val tags: List<String>,
    val accent: String,
    val baseTheme: String,
    val previewNote: String,
    val layoutVariant: String = "top_profile",
)

data class PickedFile(
    val name: String,
    val mimeType: String,
    val bytes: ByteArray,
)

data class AppUpdateInfo(
    val latestVersionCode: Int,
    val latestVersionName: String,
    val minimumVersionCode: Int,
    val updateAvailable: Boolean,
    val forceUpdate: Boolean,
    val downloadUrl: String,
    val downloadUrls: List<String>,
    val filename: String,
    val size: Long?,
    val releaseNotes: List<String>,
)

data class RadarSummary(
    val availableJobs: Int = 0,
    val saved: Int = 0,
    val applied: Int = 0,
    val notInterested: Int = 0,
)

data class RadarJob(
    val id: String,
    val title: String,
    val company: String,
    val location: String,
    val salary: String,
    val experience: String,
    val education: String,
    val description: String,
    val requirements: List<String>,
    val benefits: List<String>,
    val sourceSections: Map<String, String>,
    val sourceDetailStatus: String,
    val sourceDetailUpdatedAt: String,
    val tags: List<String>,
    val sourceUrl: String,
    val publishedAt: String,
    val matchScore: Int,
    val matchReason: String,
    val feedbackAction: String?,
    val adapted: Boolean = false,
    val adaptedAt: String = "",
)

data class RadarPagination(
    val page: Int = 1,
    val pageSize: Int = 20,
    val total: Int = 0,
    val totalPages: Int = 1,
    val matchedTotal: Int = 0,
    val isLimited: Boolean = false,
)

data class RadarRecommendationPage(
    val jobs: List<RadarJob>,
    val summary: RadarSummary,
    val cities: List<String>,
    val pagination: RadarPagination,
)

data class CareerFact(val id: String, val text: String, val category: String, val status: String, val riskLevel: Int)
data class ReviewProposal(val id: String, val text: String, val reason: String, val decision: String)
data class CareerReview(val id: String, val title: String, val status: String, val proposals: List<ReviewProposal>)
data class ApplicationItem(val id: String, val jobTitle: String, val company: String, val status: String, val nextActionAt: String, val note: String)
data class BillingPlan(val code: String, val name: String, val credits: Int, val priceCents: Int)
data class BillingSummary(
    val credits: Int,
    val available: Int,
    val reserved: Int,
    val suspended: Boolean = false,
    val plans: List<BillingPlan>,
    val paymentConfigured: Boolean,
    val paymentNote: String = "",
)

class ApiException(message: String) : RuntimeException(message)

class ApiClient(private val context: Context) {
    private val prefs = context.getSharedPreferences("zhiday_resume", Context.MODE_PRIVATE)
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    // Primary = IP HTTP (avoids mobile carrier RST on HTTPS domain); fallback = HTTPS domain.
    private val baseUrls = listOf(BuildConfig.API_BASE_URL, BuildConfig.API_FALLBACK_URL)

    var token: String?
        get() = prefs.getString("token", null)
        set(value) {
            prefs.edit().apply {
                if (value == null) remove("token") else putString("token", value)
            }.apply()
        }

    private fun url(path: String, baseUrl: String = baseUrls.first()): String = baseUrl + path.removePrefix("/")

    private fun requestWithBase(request: Request, baseUrl: String): Request {
        val oldUrl = request.url.toString()
        val currentBase = baseUrls.firstOrNull { oldUrl.startsWith(it) } ?: baseUrls.first()
        val newUrl = if (oldUrl.startsWith(currentBase)) baseUrl + oldUrl.removePrefix(currentBase) else baseUrl + oldUrl
        return request.newBuilder().url(newUrl).build()
    }

    private suspend fun <T> executeWithFallback(request: Request, once: suspend (Request) -> T): T = withContext(Dispatchers.IO) {
        var lastError: IOException? = null
        for (baseUrl in baseUrls) {
            try {
                return@withContext once(requestWithBase(request, baseUrl))
            } catch (e: IOException) {
                lastError = e
            }
        }
        throw ApiException("网络连接失败，请检查网络：${lastError?.message ?: "Connection reset"}")
    }

    private suspend fun executeOnce(request: Request): JSONObject = withContext(Dispatchers.IO) {
        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw ApiException(errorMessage(text).ifBlank { "请求失败：${response.code}" })
            }
            if (text.isBlank()) JSONObject() else JSONObject(text)
        }
    }

    private suspend fun execute(request: Request): JSONObject = executeWithFallback(request) { executeOnce(it) }

    private suspend fun executeArrayOnce(request: Request): JSONArray = withContext(Dispatchers.IO) {
        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw ApiException(errorMessage(text).ifBlank { "请求失败：${response.code}" })
            }
            if (text.isBlank()) JSONArray() else JSONArray(text)
        }
    }

    private suspend fun executeArray(request: Request): JSONArray = executeWithFallback(request) { executeArrayOnce(it) }

    private fun builder(path: String): Request.Builder {
        val builder = Request.Builder().url(url(path))
        token?.takeIf { it.isNotBlank() }?.let { builder.header("Authorization", "Bearer $it") }
        return builder
    }

    private fun postJson(path: String, json: JSONObject): Request {
        return builder(path).post(json.toString().toRequestBody(jsonType)).build()
    }

    private fun patchJson(path: String, json: JSONObject): Request {
        return builder(path).patch(json.toString().toRequestBody(jsonType)).build()
    }

    private fun multipartRequest(path: String, multipart: MultipartBody): Request {
        return builder(path).post(multipart).build()
    }

    suspend fun sendSms(phone: String, scene: String) {
        execute(postJson("/auth/sms-code", JSONObject().put("phone", phone).put("scene", scene)))
    }

    suspend fun register(username: String, phone: String, code: String, password: String, confirmPassword: String): AuthSession {
        val json = JSONObject()
            .put("username", username)
            .put("phone", phone)
            .put("code", code)
            .put("password", password)
            .put("confirm_password", confirmPassword)
        return parseAuth(execute(postJson("/auth/register", json))).also { token = it.token }
    }

    suspend fun login(username: String, password: String): AuthSession {
        val json = JSONObject().put("username", username).put("password", password)
        return parseAuth(execute(postJson("/auth/login", json))).also { token = it.token }
    }

    suspend fun smsLogin(phone: String, code: String): AuthSession {
        val json = JSONObject().put("phone", phone).put("code", code)
        return parseAuth(execute(postJson("/auth/sms-login", json))).also { token = it.token }
    }

    suspend fun resetPassword(phone: String, code: String, password: String) {
        val json = JSONObject()
            .put("phone", phone)
            .put("code", code)
            .put("new_password", password)
            .put("confirm_password", password)
        execute(postJson("/auth/reset-password", json))
    }

    suspend fun me(): User = parseUser(execute(builder("/auth/me").get().build()))

    suspend fun changePassword(currentPassword: String, newPassword: String) {
        execute(postJson("/auth/change-password", JSONObject().put("current_password", currentPassword).put("new_password", newPassword)))
    }

    suspend fun changePhone(phone: String, code: String): User {
        return parseUser(execute(postJson("/auth/change-phone", JSONObject().put("phone", phone).put("code", code))).getJSONObject("user"))
    }

    suspend fun uploadAccountAvatar(file: PickedFile): User {
        return parseUser(execute(multipartRequest("/auth/avatar", multipart("file", file))).getJSONObject("user"))
    }

    suspend fun deleteAccount(currentPassword: String, confirmUsername: String) {
        execute(postJson("/auth/delete-account", JSONObject().put("current_password", currentPassword).put("confirm_username", confirmUsername)))
        token = null
    }

    suspend fun resumes(): List<ResumeItem> {
        val array = executeArray(builder("/resumes").get().build())
        return List(array.length()) { parseResume(array.getJSONObject(it)) }
    }

    suspend fun saveResume(id: String?, versionName: String, content: ResumeContent): ResumeItem {
        val payload = JSONObject().put("name", versionName).put("content", content.toJson())
        val response = if (id == null) {
            execute(postJson("/resumes", payload))
        } else {
            execute(patchJson("/resumes/${encode(id)}", payload))
        }
        return parseResume(response)
    }

    suspend fun deleteResume(id: String) {
        execute(builder("/resumes/${encode(id)}").delete().build())
    }

    suspend fun setDefaultResume(id: String) {
        execute(builder("/resumes/${encode(id)}/default").post(FormBody.Builder().build()).build())
    }

    suspend fun uploadResumeDocument(file: PickedFile): ResumeItem {
        return parseResume(execute(multipartRequest("/resumes/upload", multipart("file", file))))
    }

    suspend fun ocrResumeImage(file: PickedFile): ResumeItem {
        return parseResume(execute(multipartRequest("/resumes/ocr", multipart("file", file))))
    }

    suspend fun uploadAvatar(resumeId: String, file: PickedFile): ResumeItem {
        return parseResume(execute(multipartRequest("/resumes/${encode(resumeId)}/avatar", multipart("file", file))))
    }

    suspend fun resumeTemplates(): List<ResumeTemplate> {
        val array = executeArray(builder("/resume-templates").get().build())
        return List(array.length()) { parseResumeTemplate(array.getJSONObject(it)) }
    }

    suspend fun resumeTemplateSourceLink(templateId: String): String {
        // Prefer same-origin authenticated PDF rendered by the real layout engine.
        val json = execute(builder("/resume-templates/${encode(templateId)}/preview-link").get().build())
        val url = json.optString("url")
        if (url.isBlank()) throw ApiException("模板预览链接为空")
        return absoluteUrl(url)
    }

    suspend fun downloadTemplatePreviewPdf(templateId: String): File = withContext(Dispatchers.IO) {
        val request = builder("/resume-templates/${encode(templateId)}/preview.pdf").get().build()
        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                val text = response.body?.string().orEmpty()
                throw ApiException(errorMessage(text).ifBlank { "模板预览失败：${response.code}" })
            }
            val bytes = response.body?.bytes() ?: throw ApiException("模板预览内容为空")
            val directory = File(context.cacheDir, "template-previews").apply { mkdirs() }
            val output = File(directory, "${safeFilename(templateId)}-preview.pdf")
            output.writeBytes(bytes)
            output
        }
    }

    suspend fun parseJd(sourceType: String, textOrUrl: String): JdTask {
        val json = JSONObject().put("source_type", sourceType)
        if (sourceType == "url") json.put("url", textOrUrl) else json.put("text", textOrUrl)
        return parseJdTask(execute(postJson("/jd/parse", json)))
    }

    suspend fun parseJdImages(files: List<PickedFile>): JdTask {
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
        files.forEach { file -> body.addFilePart("files", file) }
        return parseJdTask(execute(multipartRequest("/jd/ocr", body.build())))
    }

    suspend fun jdTasks(): List<JdTask> {
        val array = executeArray(builder("/jd/tasks").get().build())
        return List(array.length()) { parseJdTask(array.getJSONObject(it)) }
    }

    suspend fun deleteJdTask(id: String) {
        execute(builder("/jd/tasks/${encode(id)}").delete().build())
    }

    suspend fun generate(resumeId: String?, jd: JSONObject, designTheme: String, radarJobId: String? = null, templateId: String? = null): GenerationItem {
        val json = JSONObject()
            .put("resume_id", resumeId ?: JSONObject.NULL)
            .put("jd", jd)
            .put("design_theme", designTheme)
            .put("template_id", templateId ?: JSONObject.NULL)
            .put("radar_job_id", radarJobId ?: JSONObject.NULL)
        return parseGeneration(execute(postJson("/generations", json)))
    }

    suspend fun radarRecommendations(
        query: String = "",
        city: String = "",
        publishedWithin: String = "30d",
        page: Int = 1,
        savedOnly: Boolean = false,
        experience: String = "",
        education: String = "",
        salaryMin: Int = 0,
        sortBy: String = "match",
        topic: String = "",
        source: String = "",
    ): RadarRecommendationPage {
        val params = listOf(
            "limit=10000",
            "page_size=20",
            "page=${page.coerceAtLeast(1)}",
            "published_within=${encode(publishedWithin)}",
            "query=${encode(query)}",
            "city=${encode(city)}",
            "saved_only=$savedOnly",
            "experience=${encode(experience)}",
            "education=${encode(education)}",
            "salary_min=$salaryMin",
            "sort_by=${encode(sortBy)}",
            "topic=${encode(topic)}",
            "source=${encode(source)}",
        ).joinToString("&")
        val response = execute(builder("/radar/recommendations?$params").get().build())
        val jobs = response.optJSONArray("jobs")
        return RadarRecommendationPage(
            jobs = List(jobs?.length() ?: 0) { parseRadarJob(jobs!!.getJSONObject(it)) },
            summary = parseRadarSummary(response.optJSONObject("summary") ?: JSONObject()),
            cities = response.optJSONArray("cities").toStringList(),
            pagination = parseRadarPagination(response.optJSONObject("pagination") ?: JSONObject()),
        )
    }

    suspend fun radarFeedback(jobId: String, action: String) {
        execute(postJson("/radar/jobs/${encode(jobId)}/feedback", JSONObject().put("action", action)))
    }

    suspend fun radarJobDetail(jobId: String): RadarJob {
        return parseRadarJob(execute(builder("/radar/jobs/${encode(jobId)}").get().build()))
    }

    suspend fun setRadarCompanyBlocked(jobId: String, blocked: Boolean) {
        execute(postJson("/radar/jobs/${encode(jobId)}/company-preference", JSONObject().put("blocked", blocked)))
    }

    suspend fun prepareRadarOptimization(jobId: String): JSONObject {
        return execute(postJson("/radar/jobs/${encode(jobId)}/prepare-optimization", JSONObject()))
    }

    suspend fun regenerate(generationId: String, designTheme: String, templateId: String? = null): GenerationItem {
        return parseGeneration(execute(postJson("/generations/${encode(generationId)}/regenerate", JSONObject().put("design_theme", designTheme).put("template_id", templateId ?: JSONObject.NULL))))
    }

    suspend fun retryGeneration(generationId: String): GenerationItem {
        return parseGeneration(execute(postJson("/generations/${encode(generationId)}/retry", JSONObject())))
    }

    suspend fun generations(): List<GenerationItem> {
        val array = executeArray(builder("/generations").get().build())
        return List(array.length()) { parseGeneration(array.getJSONObject(it)) }
    }

    suspend fun deleteGeneration(id: String) {
        execute(builder("/generations/${encode(id)}").delete().build())
    }

    suspend fun careerFacts(): List<CareerFact> {
        val array = executeArray(builder("/career/facts").get().build())
        return List(array.length()) { parseCareerFact(array.getJSONObject(it)) }
    }

    suspend fun rebuildCareerFacts(resumeId: String): List<CareerFact> {
        val array = executeArray(postJson("/career/facts/rebuild", JSONObject().put("resume_id", resumeId)))
        return List(array.length()) { parseCareerFact(array.getJSONObject(it)) }
    }

    suspend fun decideCareerFact(id: String, status: String) {
        execute(postJson("/career/facts/${encode(id)}/decision", JSONObject().put("status", status)))
    }

    suspend fun reviews(): List<CareerReview> {
        val array = executeArray(builder("/reviews").get().build())
        return List(array.length()) { parseCareerReview(array.getJSONObject(it)) }
    }

    suspend fun createReview(resumeId: String, jd: JSONObject): CareerReview {
        return parseCareerReview(execute(postJson("/reviews", JSONObject().put("resume_id", resumeId).put("jd", jd))))
    }

    suspend fun decideReview(reviewId: String, proposalId: String, decision: String) {
        execute(postJson("/reviews/${encode(reviewId)}/proposals/${encode(proposalId)}", JSONObject().put("decision", decision).put("note", "")))
    }

    suspend fun applications(): List<ApplicationItem> {
        val array = executeArray(builder("/applications").get().build())
        return List(array.length()) { parseApplication(array.getJSONObject(it)) }
    }

    suspend fun createApplication(jobTitle: String, company: String, sourceUrl: String, status: String, note: String) {
        execute(postJson("/applications", JSONObject().put("job_title", jobTitle).put("company", company).put("source_url", sourceUrl).put("status", status).put("note", note)))
    }

    suspend fun updateApplication(id: String, status: String) {
        execute(patchJson("/applications/${encode(id)}", JSONObject().put("status", status)))
    }

    suspend fun deleteApplication(id: String) {
        execute(builder("/applications/${encode(id)}").delete().build())
    }

    suspend fun billingSummary(): BillingSummary = parseBillingSummary(execute(builder("/billing/summary").get().build()))

    suspend fun createOrder(productCode: String) {
        execute(postJson("/billing/orders", JSONObject().put("product_code", productCode)))
    }

    suspend fun fileLink(bucket: String, key: String): String {
        val path = "/file-link?bucket=${encode(bucket)}&key=${encode(key)}"
        val json = execute(builder(path).get().build())
        val proxy = json.optString("proxy_url")
        return absoluteUrl(proxy.ifBlank { json.optString("url") })
    }

    suspend fun downloadGenerationFile(item: GenerationItem, type: String): File = withContext(Dispatchers.IO) {
        val filename = "${safeFilename(item.title)}-${item.id.take(8)}.${if (type == "docx") "docx" else "pdf"}"
        val directory = File(context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "documents").apply { mkdirs() }
        val output = File(directory, filename)
        downloadAuthorized("/generations/${encode(item.id)}/download/${if (type == "docx") "docx" else "pdf"}", output)
    }

    suspend fun downloadResumeOriginal(item: ResumeItem): File = withContext(Dispatchers.IO) {
        val suffix = item.sourceKey?.substringAfterLast('.', "bin")?.ifBlank { "bin" } ?: "bin"
        val output = File(File(context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "documents").apply { mkdirs() }, "${safeFilename(item.name)}-原文件.$suffix")
        downloadAuthorized("/resumes/${encode(item.id)}/download-original", output)
    }

    suspend fun appVersion(versionCode: Int): AppUpdateInfo {
        val json = execute(builder("/app/version?platform=android&version_code=$versionCode").get().build())
        return parseAppUpdateInfo(json)
    }

    suspend fun downloadUpdateApk(info: AppUpdateInfo, onProgress: (Float) -> Unit): File = withContext(Dispatchers.IO) {
        val directory = File(context.getExternalFilesDir(null), "updates").apply { mkdirs() }
        val apk = File(directory, info.filename.ifBlank { "zhiday-resume-android.apk" })
        val urls = info.downloadUrls.ifEmpty { listOf(info.downloadUrl) }.filter { it.startsWith("http://") || it.startsWith("https://") }
        var lastError: IOException? = null
        for (url in urls) {
            try {
                val request = Request.Builder().url(url).get().build()
                http.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) {
                        throw ApiException("更新包下载失败：${response.code}")
                    }
                    val body = response.body ?: throw ApiException("更新包内容为空")
                    val total = body.contentLength().takeIf { it > 0 } ?: info.size ?: -1L
                    body.byteStream().use { input ->
                        apk.outputStream().use { output ->
                            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                            var copied = 0L
                            while (true) {
                                val read = input.read(buffer)
                                if (read == -1) break
                                output.write(buffer, 0, read)
                                copied += read
                                if (total > 0) onProgress((copied.toFloat() / total).coerceIn(0f, 1f))
                            }
                        }
                    }
                    onProgress(1f)
                    return@withContext apk
                }
            } catch (e: IOException) {
                lastError = e
            }
        }
        throw ApiException("更新包下载失败，请检查网络：${lastError?.message ?: "Connection reset"}")
    }

    fun logout() {
        token = null
    }

    private fun downloadAuthorized(path: String, output: File): File {
        val request = builder(path).get().build()
        return downloadWithFallback(request, output)
    }

    private fun downloadWithFallback(request: Request, output: File): File {
        var lastError: IOException? = null
        for (baseUrl in baseUrls) {
            try {
                http.newCall(requestWithBase(request, baseUrl)).execute().use { response ->
                    if (!response.isSuccessful) {
                        throw ApiException("文件下载失败：${response.code}")
                    }
                    val body = response.body ?: throw ApiException("文件内容为空")
                    body.byteStream().use { input ->
                        output.outputStream().use { input.copyTo(it) }
                    }
                    return output
                }
            } catch (e: IOException) {
                lastError = e
            }
        }
        throw ApiException("文件下载失败，请检查网络：${lastError?.message ?: "Connection reset"}")
    }
}

private fun MultipartBody.Builder.addFilePart(fieldName: String, file: PickedFile): MultipartBody.Builder {
    val type = file.mimeType.ifBlank { "application/octet-stream" }.toMediaTypeOrNull()
    return addFormDataPart(fieldName, file.name, file.bytes.toRequestBody(type))
}

private fun multipart(fieldName: String, file: PickedFile): MultipartBody {
    return MultipartBody.Builder()
        .setType(MultipartBody.FORM)
        .addFilePart(fieldName, file)
        .build()
}

private fun errorMessage(text: String): String {
    if (text.isBlank()) return ""
    return runCatching {
        val detail = JSONObject(text).opt("detail")
        when (detail) {
            is String -> detail
            is JSONArray -> detail.optJSONObject(0)?.optString("msg").orEmpty()
            else -> detail?.toString().orEmpty()
        }
    }.getOrDefault(text)
}

private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())

private fun parseAuth(json: JSONObject): AuthSession {
    return AuthSession(
        token = json.optString("token"),
        user = parseUser(json.getJSONObject("user")),
    )
}

private fun parseUser(json: JSONObject): User {
    return User(
        id = json.optString("id"),
        username = json.optString("username"),
        phone = json.optString("phone_masked", json.optString("phone")).takeIf { it.isNotBlank() && it != "null" },
        role = json.optString("role").takeIf { it.isNotBlank() && it != "null" },
        avatarKey = json.optString("avatar_key").takeIf { it.isNotBlank() && it != "null" },
        avatarUrl = absoluteUrl(json.optString("avatar_url")).takeIf { it.isNotBlank() },
    )
}

private fun parseResume(json: JSONObject): ResumeItem {
    val content = json.optJSONObject("content") ?: JSONObject()
    return ResumeItem(
        id = json.optString("id"),
        name = json.optString("name", "未命名简历"),
        isDefault = json.optBoolean("is_default"),
        updatedAt = json.optString("updated_at"),
        avatarKey = json.optString("avatar_key").takeIf { it.isNotBlank() && it != "null" },
        sourceType = json.optString("source_type").takeIf { it.isNotBlank() && it != "null" },
        sourceKey = json.optString("source_key").takeIf { it.isNotBlank() && it != "null" },
        content = parseContent(content),
    )
}

private fun parseResumeTemplate(json: JSONObject): ResumeTemplate {
    return ResumeTemplate(
        id = json.optString("id"),
        name = json.optString("name", "授权模板"),
        category = json.optString("category"),
        displayCategory = json.optString("display_category", json.optString("category")),
        tags = json.optJSONArray("tags").toStringList(),
        accent = json.optString("accent", "#2F56B3"),
        baseTheme = json.optString("base_theme", "auto"),
        previewNote = json.optString("preview_note"),
        layoutVariant = json.optString("layout_variant", "top_profile"),
    )
}

private fun parseContent(json: JSONObject): ResumeContent {
    val contact = json.optJSONObject("contact") ?: JSONObject()
    return ResumeContent(
        name = json.optString("name"),
        title = json.optString("title"),
        age = contact.optString("age"),
        phone = firstNonBlank(contact.optString("phone"), contact.optString("mobile"), contact.optString("telephone")),
        email = contact.optString("email"),
        summary = firstNonBlank(json.optString("summary"), json.optString("profile"), json.optString("overview")),
        skills = json.optJSONArray("skills").toStringList(),
        experience = json.optJSONArray("experience").toEntryLines("company"),
        projects = json.optJSONArray("projects").toEntryLines("project"),
        education = json.optJSONArray("education").toEntryLines("school"),
        certificates = json.optJSONArray("certificates").toStringList(),
    )
}

private fun parseJdTask(json: JSONObject): JdTask {
    return JdTask(
        id = json.optString("id"),
        status = json.optString("status"),
        source = json.optString("source"),
        detail = json.optString("source_detail"),
        progress = json.optString("progress_message").takeIf { it.isNotBlank() && it != "null" },
        error = json.optString("error").takeIf { it.isNotBlank() && it != "null" },
        result = json.optJSONObject("result"),
    )
}

private fun parseGeneration(json: JSONObject): GenerationItem {
    val jd = json.optJSONObject("jd")
    val files = json.optJSONObject("files")
    val score = json.optJSONObject("ai_score")
    val dimensions = score?.optJSONObject("dimensions")
    val report = json.optJSONObject("ai_report")
    return GenerationItem(
        id = json.optString("id"),
        status = json.optString("status"),
        resumeName = json.optString("resume_name"),
        createdAt = json.optString("created_at"),
        title = jd?.optString("title")?.takeIf { it.isNotBlank() } ?: "适配简历",
        error = json.optString("error").takeIf { it.isNotBlank() && it != "null" },
        message = json.optString("progress_message").takeIf { it.isNotBlank() && it != "null" },
        docxKey = files?.optJSONObject("docx")?.optString("key")?.takeIf { it.isNotBlank() },
        pdfKey = files?.optJSONObject("pdf")?.optString("key")?.takeIf { it.isNotBlank() },
        overallScore = score?.optInt("overall")?.takeIf { it > 0 },
        jobMatchScore = dimensions?.optInt("job_match")?.takeIf { it > 0 },
        keywordCoverageScore = dimensions?.optInt("keyword_coverage")?.takeIf { it > 0 },
        visualScore = dimensions?.optInt("visual_professionalism")?.takeIf { it > 0 },
        optimizations = report?.optJSONArray("optimizations").toStringList(),
    )
}

private fun parseAppUpdateInfo(json: JSONObject): AppUpdateInfo {
    val notes = json.optJSONArray("release_notes").toStringList()
    val primaryUrl = json.optString("download_url")
    val altUrls = json.optJSONArray("download_urls").toStringList().filter { it.startsWith("http://") || it.startsWith("https://") }
    val allUrls = if (primaryUrl.isNotBlank() && primaryUrl !in altUrls) listOf(primaryUrl) + altUrls else altUrls
    return AppUpdateInfo(
        latestVersionCode = json.optInt("latest_version_code"),
        latestVersionName = json.optString("latest_version_name"),
        minimumVersionCode = json.optInt("minimum_version_code"),
        updateAvailable = json.optBoolean("update_available"),
        forceUpdate = json.optBoolean("force_update"),
        downloadUrl = allUrls.firstOrNull() ?: primaryUrl,
        downloadUrls = allUrls,
        filename = json.optString("filename", "zhiday-resume-android.apk"),
        size = if (json.isNull("size")) null else json.optLong("size"),
        releaseNotes = notes,
    )
}

private fun parseRadarSummary(json: JSONObject): RadarSummary {
    return RadarSummary(
        availableJobs = json.optInt("available_jobs"),
        saved = json.optInt("saved"),
        applied = json.optInt("applied"),
        notInterested = json.optInt("not_interested"),
    )
}

private fun parseRadarPagination(json: JSONObject): RadarPagination {
    return RadarPagination(
        page = json.optInt("page", 1),
        pageSize = json.optInt("page_size", 20),
        total = json.optInt("total"),
        totalPages = json.optInt("total_pages", 1),
        matchedTotal = json.optInt("matched_total", json.optInt("total")),
        isLimited = json.optBoolean("is_limited"),
    )
}

private fun parseRadarJob(json: JSONObject): RadarJob {
    return RadarJob(
        id = json.optString("id"),
        title = json.optString("title", "未命名岗位"),
        company = json.optString("company"),
        location = json.optString("location"),
        salary = json.optString("salary"),
        experience = json.optString("experience"),
        education = json.optString("education"),
        description = json.optString("description"),
        requirements = json.optJSONArray("requirements").toStringList(),
        benefits = json.optJSONArray("benefits").toStringList(),
        sourceSections = json.optJSONObject("source_sections").toStringMap(),
        sourceDetailStatus = json.optString("source_detail_status"),
        sourceDetailUpdatedAt = json.optString("source_detail_updated_at"),
        tags = json.optJSONArray("tags").toStringList(),
        sourceUrl = json.optString("source_url"),
        publishedAt = json.optString("published_at"),
        matchScore = json.optInt("match_score"),
        matchReason = json.optString("match_reason"),
        feedbackAction = json.optString("feedback_action").takeIf { it.isNotBlank() && it != "null" },
        adapted = json.optBoolean("adapted"),
        adaptedAt = json.optString("adapted_at"),
    )
}

private fun parseCareerFact(json: JSONObject): CareerFact = CareerFact(
    id = json.optString("id"),
    text = json.optString("display_text", json.optString("raw_text")),
    category = json.optString("category"),
    status = json.optString("status"),
    riskLevel = json.optInt("risk_level", 1),
)

private fun parseCareerReview(json: JSONObject): CareerReview {
    val jd = json.optJSONObject("jd") ?: JSONObject()
    val array = json.optJSONArray("proposals")
    val proposals = List(array?.length() ?: 0) { index ->
        val item = array!!.getJSONObject(index)
        ReviewProposal(
            id = item.optString("id"),
            text = item.optString("after", item.optString("before")),
            reason = item.optString("reason"),
            decision = item.optString("decision", "pending"),
        )
    }
    return CareerReview(json.optString("id"), jd.optString("title", "岗位审阅"), json.optString("status"), proposals)
}

private fun parseApplication(json: JSONObject): ApplicationItem = ApplicationItem(
    id = json.optString("id"),
    jobTitle = json.optString("job_title"),
    company = json.optString("company"),
    status = json.optString("status"),
    nextActionAt = json.optString("next_action_at"),
    note = json.optString("note"),
)

private fun parseBillingSummary(json: JSONObject): BillingSummary {
    val account = json.optJSONObject("account") ?: JSONObject()
    val plans = json.optJSONObject("plans") ?: JSONObject()
    val keys = plans.keys().asSequence().toList()
    val credits = account.optInt("credits")
    val available = if (account.has("available")) account.optInt("available") else credits
    val suspended = account.optBoolean("suspended")
    return BillingSummary(
        credits = credits,
        available = if (suspended) 0 else available,
        reserved = account.optInt("reserved"),
        suspended = suspended,
        plans = keys.map { code ->
            val item = plans.optJSONObject(code) ?: JSONObject()
            BillingPlan(code, item.optString("name", code), item.optInt("credits"), item.optInt("price_cents"))
        },
        paymentConfigured = json.optString("payment_provider") !in setOf("not_configured", ""),
        paymentNote = when {
            suspended -> "账号额度已被管理员暂停，请联系管理员恢复。"
            else -> json.optString(
                "payment_note",
                "创建订单后由管理员确认到账；每次生成消耗 1 次额度，失败自动退回。",
            )
        },
    )
}

private fun ResumeContent.toJson(): JSONObject {
    return JSONObject()
        .put("name", name)
        .put("title", title)
        .put("contact", JSONObject().put("age", age).put("phone", phone).put("email", email))
        .put("summary", summary)
        .put("skills", JSONArray(skills))
        .put("experience", entriesFromLines(experience, "company"))
        .put("projects", entriesFromLines(projects, "project"))
        .put("education", entriesFromLines(education, "school"))
        .put("certificates", JSONArray(certificates))
}

private fun entriesFromLines(lines: List<String>, primaryKey: String): JSONArray {
    val array = JSONArray()
    lines.filter { it.isNotBlank() }.forEach { line ->
        val parts = line.split("｜", "|", limit = 3).map { it.trim() }
        val item = JSONObject()
        if (parts.size >= 2) {
            item.put(primaryKey, parts[0])
            item.put("role", parts[1])
            if (parts.size == 3) item.put("details", JSONArray(listOf(parts[2])))
        } else {
            item.put("details", JSONArray(listOf(line)))
        }
        array.put(item)
    }
    return array
}

private fun JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return List(length()) { optString(it) }.filter { it.isNotBlank() && it != "null" }
}

private fun JSONObject?.toStringMap(): Map<String, String> {
    if (this == null) return emptyMap()
    val result = linkedMapOf<String, String>()
    val keys = keys()
    while (keys.hasNext()) {
        val key = keys.next()
        val value = optString(key).trim()
        if (key.isNotBlank() && value.isNotBlank()) result[key] = value
    }
    return result
}

private fun JSONArray?.toEntryLines(primaryKey: String): List<String> {
    if (this == null) return emptyList()
    return List(length()) { index ->
        val item = optJSONObject(index)
        if (item == null) {
            optString(index)
        } else {
            val head = listOf(
                item.optString(primaryKey),
                item.optString("role"),
                item.optString("period"),
            ).filter { it.isNotBlank() && it != "null" }.joinToString(" ｜ ")
            val details = item.optJSONArray("details").toStringList().joinToString("；")
            listOf(head, details).filter { it.isNotBlank() }.joinToString("：")
        }
    }.filter { it.isNotBlank() }
}

private fun firstNonBlank(vararg values: String): String {
    return values.firstOrNull { it.isNotBlank() && it != "null" }.orEmpty()
}

private fun safeFilename(value: String): String {
    return value.ifBlank { "职达简历" }.replace(Regex("""[\\/:*?"<>|]+"""), "_").take(48)
}

private fun absoluteUrl(value: String): String {
    if (value.isBlank()) return ""
    if (value.startsWith("http://") || value.startsWith("https://")) return value
    return BuildConfig.API_BASE_URL.toHttpUrl().resolve(value)?.toString()
        ?: throw ApiException("Invalid server file URL")
}
