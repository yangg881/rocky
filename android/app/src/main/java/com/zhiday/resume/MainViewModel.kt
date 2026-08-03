package com.zhiday.resume

import android.app.Application
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Environment
import android.provider.OpenableColumns
import android.provider.Settings
import androidx.core.content.FileProvider
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

enum class AppTab { Resumes, Radar, Match, Generations, Career, Account }

data class DesignTheme(val code: String, val label: String)

val designThemes = listOf(
    DesignTheme("auto", "智能匹配"),
    DesignTheme("tech_indigo", "科技蓝紫"),
    DesignTheme("operations_terra", "运营暖棕"),
    DesignTheme("executive_navy", "高管深蓝"),
    DesignTheme("care_teal", "医疗青绿"),
    DesignTheme("creative_plum", "创意紫调"),
    DesignTheme("ats_mono", "ATS 黑白"),
)

data class UiState(
    val loading: Boolean = false,
    val message: String? = null,
    val tokenReady: Boolean = false,
    val user: User? = null,
    val userAvatarUrl: String? = null,
    val tab: AppTab = AppTab.Radar,
    val resumes: List<ResumeItem> = emptyList(),
    val jdTasks: List<JdTask> = emptyList(),
    val generations: List<GenerationItem> = emptyList(),
    val radarJobs: List<RadarJob> = emptyList(),
    val radarJobDetails: Map<String, RadarJob> = emptyMap(),
    val radarJobDetailLoadingId: String? = null,
    val radarSummary: RadarSummary = RadarSummary(),
    val radarCities: List<String> = emptyList(),
    val radarPagination: RadarPagination = RadarPagination(),
    val radarQuery: String = "",
    val radarCity: String = "",
    val radarPublishedWithin: String = "30d",
    val radarSavedOnly: Boolean = false,
    val radarExperience: String = "",
    val radarEducation: String = "",
    val radarSalaryMin: Int = 0,
    val radarSortBy: String = "match",
    val radarTopic: String = "",
    val radarSource: String = "",
    val selectedRadarJobId: String? = null,
    val selectedJd: JSONObject? = null,
    val selectedResumeId: String? = null,
    val selectedDesignTheme: String = "auto",
    val templates: List<ResumeTemplate> = emptyList(),
    val selectedTemplateId: String? = null,
    val careerFacts: List<CareerFact> = emptyList(),
    val reviews: List<CareerReview> = emptyList(),
    val applications: List<ApplicationItem> = emptyList(),
    val billing: BillingSummary? = null,
    val updateInfo: AppUpdateInfo? = null,
    val showUpdateDialog: Boolean = false,
    val updateDownloading: Boolean = false,
    val updateProgress: Float = 0f,
    val updateError: String? = null,
)

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val api = ApiClient(app)
    private val prefs = app.getSharedPreferences("zhiday_resume", Context.MODE_PRIVATE)
    private var pollJob: Job? = null
    private var updatePollJob: Job? = null
    private var radarRequestVersion = 0
    private val _state = MutableStateFlow(UiState(tokenReady = api.token != null))
    val state: StateFlow<UiState> = _state

    init {
        checkAppVersion(manual = false)
        resumePendingUpdate()
        if (api.token != null) refreshAll()
    }

    fun clearMessage() = _state.update { it.copy(message = null) }

    fun switchTab(tab: AppTab) {
        _state.update { it.copy(tab = tab) }
        when (tab) {
            AppTab.Resumes -> loadResumes()
            AppTab.Radar -> loadRadar()
            AppTab.Match -> {
                loadResumes()
                loadJdTasks()
                loadTemplates()
            }
            AppTab.Generations -> loadGenerations()
            AppTab.Career -> refreshCareerCenter()
            AppTab.Account -> refreshMe()
        }
    }

    fun login(username: String, password: String) = launch("登录中") {
        val session = api.login(username.trim(), password)
        _state.update { it.copy(user = session.user, tokenReady = true, message = "登录成功") }
        refreshAll()
    }

    fun smsLogin(phone: String, code: String) = launch("登录中") {
        val session = api.smsLogin(phone.trim(), code.trim())
        _state.update { it.copy(user = session.user, tokenReady = true, message = "登录成功") }
        refreshAll()
    }

    fun sendSms(phone: String, scene: String) = launch("发送验证码") {
        api.sendSms(phone.trim(), scene)
        _state.update { it.copy(message = "验证码已发送") }
    }

    fun register(username: String, phone: String, code: String, password: String, confirmPassword: String) {
        if (password != confirmPassword) {
            _state.update { it.copy(message = "两次输入的密码不一致") }
            return
        }
        launch("注册中") {
            val session = api.register(username.trim(), phone.trim(), code.trim(), password, confirmPassword)
            _state.update { it.copy(user = session.user, tokenReady = true, message = "注册成功") }
            refreshAll()
        }
    }

    fun resetPassword(phone: String, code: String, password: String) = launch("重置密码") {
        api.resetPassword(phone.trim(), code.trim(), password)
        _state.update { it.copy(message = "密码已重置，请重新登录") }
    }

    fun logout() {
        api.logout()
        pollJob?.cancel()
        _state.value = UiState()
    }

    fun refreshAll() {
        refreshMe()
        loadResumes()
        loadJdTasks()
        loadGenerations()
        loadRadar()
        loadTemplates()
        refreshCareerCenter()
    }

    fun refreshMe() = launch(null) {
        val user = api.me()
        _state.update { it.copy(user = user, userAvatarUrl = user.avatarUrl, tokenReady = true) }
    }

    fun loadResumes() = launch(null) {
        val resumes = api.resumes()
        _state.update { state ->
            state.copy(
                resumes = resumes,
                selectedResumeId = state.selectedResumeId ?: resumes.firstOrNull { it.isDefault }?.id ?: resumes.firstOrNull()?.id,
            )
        }
    }

    fun saveResume(id: String?, versionName: String, content: ResumeContent) = launch("保存简历") {
        api.saveResume(id, versionName.ifBlank { content.name.ifBlank { "在线简历" } }, content)
        _state.update { it.copy(message = "简历已保存") }
        loadResumes()
    }

    fun deleteResume(id: String) = launch("删除简历") {
        api.deleteResume(id)
        _state.update { it.copy(message = "简历已删除", selectedResumeId = null) }
        loadResumes()
    }

    fun setDefault(id: String) = launch("设置默认简历") {
        api.setDefaultResume(id)
        _state.update { it.copy(message = "默认简历已更新", selectedResumeId = id) }
        loadResumes()
    }

    fun uploadResumeDocument(uri: Uri) = launch("解析简历文档") {
        api.uploadResumeDocument(readPickedFileAsync(uri, "application/octet-stream"))
        _state.update { it.copy(message = "简历文档解析完成") }
        loadResumes()
    }

    fun ocrResumeImage(uri: Uri) = launch("识别简历截图") {
        api.ocrResumeImage(readPickedFileAsync(uri, "image/*"))
        _state.update { it.copy(message = "简历截图识别完成") }
        loadResumes()
    }

    fun uploadAvatar(resumeId: String, uri: Uri) = launch("上传头像") {
        api.uploadAvatar(resumeId, readPickedFileAsync(uri, "image/*"))
        _state.update { it.copy(message = "头像已保存，生成时会自动带上") }
        loadResumes()
    }

    fun uploadAccountAvatar(uri: Uri) = launch("上传账号头像") {
        val user = api.uploadAccountAvatar(readPickedFileAsync(uri, "image/*"))
        _state.update { it.copy(user = user, userAvatarUrl = user.avatarUrl, message = "账号头像已更新") }
    }

    fun selectResume(id: String?) {
        _state.update { it.copy(selectedResumeId = id) }
    }

    fun selectTheme(code: String) {
        _state.update { it.copy(selectedDesignTheme = code, selectedTemplateId = null) }
    }

    fun loadTemplates() = launch(null) { _state.update { it.copy(templates = api.resumeTemplates()) } }

    fun selectTemplate(template: ResumeTemplate?) {
        _state.update { it.copy(selectedTemplateId = template?.id, selectedDesignTheme = template?.baseTheme ?: "auto") }
    }

    fun parseJd(sourceType: String, textOrUrl: String) = launch("提交岗位解析") {
        _state.update { it.copy(selectedRadarJobId = null) }
        api.parseJd(sourceType, textOrUrl.trim())
        _state.update { it.copy(message = "岗位解析已提交后台，可离开页面") }
        startPolling()
    }

    fun parseJdImages(uris: List<Uri>) = launch("提交截图解析") {
        if (uris.isEmpty()) throw ApiException("请至少选择一张岗位截图")
        _state.update { it.copy(selectedRadarJobId = null) }
        val files = uris.mapIndexed { index, uri ->
            readPickedFileAsync(uri, "image/*").let { file ->
                file.copy(name = file.name.ifBlank { "jd-${index + 1}.png" })
            }
        }
        api.parseJdImages(files)
        _state.update { it.copy(message = "岗位截图已提交后台解析，可离开页面") }
        startPolling()
    }

    fun loadJdTasks() = launch(null) {
        val tasks = api.jdTasks()
        _state.update { state ->
            state.copy(
                jdTasks = tasks,
                selectedJd = state.selectedJd ?: tasks.firstOrNull { it.status == "completed" && it.result != null }?.result,
            )
        }
    }

    fun deleteJdTask(id: String) = launch("删除岗位解析记录") {
        api.deleteJdTask(id)
        _state.update { state ->
            state.copy(
                jdTasks = state.jdTasks.filterNot { it.id == id },
                selectedJd = if (state.selectedJd != null && state.jdTasks.any { it.id == id && it.result == state.selectedJd }) null else state.selectedJd,
                message = "岗位解析记录已删除",
            )
        }
        loadJdTasks()
    }

    fun useJd(task: JdTask) {
        if (task.result != null) {
            _state.update { it.copy(selectedJd = task.result, selectedRadarJobId = null, message = "已选用岗位：${task.result.optString("title", "未命名岗位")}") }
        }
    }

    fun loadRadar(page: Int? = null) = launch(null) {
        val current = _state.value
        val requestVersion = ++radarRequestVersion
        val result = api.radarRecommendations(
            query = current.radarQuery,
            city = current.radarCity,
            publishedWithin = current.radarPublishedWithin,
            page = page ?: current.radarPagination.page,
            savedOnly = current.radarSavedOnly,
            experience = current.radarExperience,
            education = current.radarEducation,
            salaryMin = current.radarSalaryMin,
            sortBy = current.radarSortBy,
            topic = current.radarTopic,
            source = current.radarSource,
        )
        _state.update { state ->
            if (requestVersion != radarRequestVersion) state
            else state.copy(
                radarJobs = result.jobs,
                radarSummary = result.summary,
                radarCities = result.cities,
                radarPagination = result.pagination,
            )
        }
    }

    fun updateRadarFilters(query: String, city: String, publishedWithin: String, experience: String = "", education: String = "", salaryMin: Int = 0, sortBy: String = "match", topic: String = "", source: String = "") {
        _state.update {
            it.copy(
                radarQuery = query.trim(),
                radarCity = city,
                radarPublishedWithin = publishedWithin,
                radarExperience = experience,
                radarEducation = education,
                radarSalaryMin = salaryMin,
                radarSortBy = sortBy,
                radarTopic = topic,
                radarSource = source,
                radarPagination = RadarPagination(),
            )
        }
        loadRadar(page = 1)
    }

    fun toggleSavedRadar() {
        _state.update { it.copy(radarSavedOnly = !it.radarSavedOnly, radarPagination = RadarPagination()) }
        loadRadar(page = 1)
    }

    fun changeRadarPage(delta: Int) {
        val pagination = _state.value.radarPagination
        val target = (pagination.page + delta).coerceIn(1, pagination.totalPages)
        if (target != pagination.page) loadRadar(page = target)
    }

    fun jumpToRadarPage(targetPage: Int) {
        val pagination = _state.value.radarPagination
        val target = targetPage.coerceIn(1, pagination.totalPages)
        if (target != pagination.page) loadRadar(page = target)
    }

    fun radarFeedback(job: RadarJob, action: String) = launch(null) {
        api.radarFeedback(job.id, action)
        _state.update { state ->
            state.copy(
                radarJobs = if (action == "not_interested") state.radarJobs.filterNot { it.id == job.id }
                else state.radarJobs.map { if (it.id == job.id) it.copy(feedbackAction = action) else it },
                message = when (action) {
                    "saved" -> "已收藏，后续会优先保留这类岗位"
                    "applied" -> "已记录投递，系统不会再推荐这个岗位"
                    "not_interested" -> "已降低同类岗位的推荐优先级"
                    else -> null
                },
            )
        }
        loadRadar()
    }

    fun blockRadarCompany(job: RadarJob) = launch("更新公司偏好") {
        api.setRadarCompanyBlocked(job.id, true)
        _state.update { state ->
            state.copy(radarJobs = state.radarJobs.filterNot { it.company == job.company }, message = "已不再推荐 ${job.company} 的岗位")
        }
        loadRadar()
    }

    fun loadRadarJobDetail(job: RadarJob) = launch(null) {
        _state.update { it.copy(radarJobDetailLoadingId = job.id) }
        try {
            val detail = api.radarJobDetail(job.id)
            // Recommendation scores belong to the selected resume/profile and are only
            // present in the list response. Keep them when enriching a job detail.
            val detailWithMatch = detail.copy(
                matchScore = job.matchScore,
                matchReason = job.matchReason,
                feedbackAction = job.feedbackAction,
                adapted = job.adapted,
                adaptedAt = job.adaptedAt,
            )
            _state.update { state ->
                state.copy(
                    radarJobDetails = state.radarJobDetails + (job.id to detailWithMatch),
                    radarJobDetailLoadingId = null,
                )
            }
        } catch (error: Exception) {
            _state.update { it.copy(radarJobDetailLoadingId = null) }
            throw error
        }
    }

    fun optimizeRadarJob(job: RadarJob) = launch("准备岗位优化") {
        val response = api.prepareRadarOptimization(job.id)
        _state.update {
            it.copy(
                selectedJd = response.optJSONObject("jd"),
                selectedRadarJobId = job.id,
                tab = AppTab.Match,
                message = "已带入 ${job.title}，选择简历后即可生成",
            )
        }
    }

    fun generate() = launch("提交生成任务") {
        val jd = _state.value.selectedJd ?: throw ApiException("请先选择一个解析成功的岗位")
        api.generate(_state.value.selectedResumeId, jd, _state.value.selectedDesignTheme, _state.value.selectedRadarJobId, _state.value.selectedTemplateId)
        _state.update { it.copy(tab = AppTab.Generations, message = "已提交后台生成（预扣 1 次额度，失败自动退回）") }
        loadBilling()
        startPolling()
    }

    fun regenerate(item: GenerationItem, theme: String, templateId: String? = null) = launch("重新生成") {
        api.regenerate(item.id, theme, templateId)
        _state.update { it.copy(message = "已按新模板重新生成（预扣 1 次额度）") }
        loadBilling()
        startPolling()
    }

    fun retryGeneration(item: GenerationItem) = launch("重试生成") {
        api.retryGeneration(item.id)
        _state.update { it.copy(message = "已重新提交生成任务") }
        loadBilling()
        startPolling()
    }

    fun loadGenerations() = launch(null) {
        _state.update { it.copy(generations = api.generations()) }
    }

    fun deleteGeneration(id: String) = launch("删除生成记录") {
        api.deleteGeneration(id)
        _state.update { it.copy(message = "生成记录已删除") }
        loadGenerations()
    }

    fun refreshCareerCenter() {
        loadCareerFacts()
        loadReviews()
        loadApplications()
        loadBilling()
    }

    fun loadCareerFacts() = launch(null) { _state.update { it.copy(careerFacts = api.careerFacts()) } }

    fun rebuildCareerFacts() = launch("重建职业事实") {
        val resumeId = _state.value.selectedResumeId ?: throw ApiException("请先选择一份基础简历")
        api.rebuildCareerFacts(resumeId)
        _state.update { it.copy(message = "职业事实已从基础简历重建") }
        loadCareerFacts()
    }

    fun decideCareerFact(id: String, status: String) = launch(null) {
        api.decideCareerFact(id, status)
        loadCareerFacts()
    }

    fun loadReviews() = launch(null) { _state.update { it.copy(reviews = api.reviews()) } }

    fun createReview() = launch("创建岗位审阅") {
        val resumeId = _state.value.selectedResumeId ?: throw ApiException("请先选择基础简历")
        val jd = _state.value.selectedJd ?: throw ApiException("请先解析并选择一个岗位")
        api.createReview(resumeId, jd)
        _state.update { it.copy(message = "岗位审阅已创建，请逐条确认") }
        loadReviews()
    }

    fun decideReview(reviewId: String, proposalId: String, decision: String) = launch(null) {
        api.decideReview(reviewId, proposalId, decision)
        loadReviews()
    }

    fun loadApplications() = launch(null) { _state.update { it.copy(applications = api.applications()) } }

    fun createApplication(jobTitle: String, company: String, url: String, status: String, note: String) = launch("保存投递记录") {
        api.createApplication(jobTitle, company, url, status, note)
        _state.update { it.copy(message = "投递记录已保存") }
        loadApplications()
    }

    fun updateApplication(id: String, status: String) = launch(null) { api.updateApplication(id, status); loadApplications() }

    fun deleteApplication(id: String) = launch("删除投递记录") {
        api.deleteApplication(id)
        _state.update { it.copy(message = "投递记录已删除") }
        loadApplications()
    }

    fun loadBilling() = launch(null) { _state.update { it.copy(billing = api.billingSummary()) } }

    fun createOrder(productCode: String) = launch("创建待支付订单") {
        api.createOrder(productCode)
        _state.update { it.copy(message = "已创建待支付订单，支付通道接入前不会产生扣款") }
        loadBilling()
    }

    fun openFile(item: GenerationItem, type: String) = launch("准备真实预览") {
        val key = if (type == "pdf") item.pdfKey else item.docxKey
        if (key.isNullOrBlank()) throw ApiException("文件尚未生成")
        val link = api.fileLink("b", key)
        val intent = Intent(getApplication<Application>(), DocumentPreviewActivity::class.java)
            .putExtra(DocumentPreviewActivity.EXTRA_URL, link)
            .putExtra(DocumentPreviewActivity.EXTRA_TYPE, type)
            .putExtra(DocumentPreviewActivity.EXTRA_TITLE, item.title)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        getApplication<Application>().startActivity(intent)
    }

    fun openTemplatePreview(template: ResumeTemplate) = launch("准备真实模板预览") {
        // Download with Bearer auth first — WebView cannot attach API tokens.
        val file = api.downloadTemplatePreviewPdf(template.id)
        openLocalFile(file, "application/pdf")
        _state.update { it.copy(message = "已打开「${template.name}」真实版式预览") }
    }

    fun downloadFile(item: GenerationItem, type: String) = launch("下载文件") {
        val file = api.downloadGenerationFile(item, type)
        _state.update { it.copy(message = "已下载：${file.name}") }
        openLocalFile(file, if (type == "docx") "application/vnd.openxmlformats-officedocument.wordprocessingml.document" else "application/pdf")
    }

    fun openOriginalResume(item: ResumeItem) = launch("打开原简历文件") {
        val key = item.sourceKey ?: throw ApiException("这份简历没有原始文件")
        val bucket = if (item.sourceType == "image") "c" else "b"
        val link = api.fileLink(bucket, key)
        val type = when {
            item.sourceType == "image" -> "image"
            key.endsWith(".docx", ignoreCase = true) -> "docx"
            key.endsWith(".pdf", ignoreCase = true) -> "pdf"
            key.endsWith(".txt", ignoreCase = true) -> "text"
            else -> "file"
        }
        val intent = Intent(getApplication<Application>(), DocumentPreviewActivity::class.java)
            .putExtra(DocumentPreviewActivity.EXTRA_URL, link)
            .putExtra(DocumentPreviewActivity.EXTRA_TYPE, type)
            .putExtra(DocumentPreviewActivity.EXTRA_TITLE, "${item.name} · 原文件")
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        getApplication<Application>().startActivity(intent)
    }

    fun downloadOriginalResume(item: ResumeItem) = launch("下载原简历文件") {
        val file = api.downloadResumeOriginal(item)
        _state.update { it.copy(message = "已下载：${file.name}") }
        openLocalFile(file, contentTypeForFile(file.name))
    }

    fun changePassword(currentPassword: String, newPassword: String) = launch("修改密码") {
        api.changePassword(currentPassword, newPassword)
        _state.update { it.copy(message = "密码已更新") }
    }

    fun changePhone(phone: String, code: String) = launch("更换手机号") {
        val user = api.changePhone(phone.trim(), code.trim())
        _state.update { it.copy(user = user, message = "手机号已更新") }
    }

    fun deleteAccount(currentPassword: String, confirmUsername: String) = launch("注销账号") {
        api.deleteAccount(currentPassword, confirmUsername.trim())
        pollJob?.cancel()
        _state.value = UiState(message = "账号已注销")
    }

    fun checkAppVersion(manual: Boolean = true) {
        viewModelScope.launch {
            if (manual) _state.update { it.copy(loading = true, message = "检查更新") }
            runCatching {
                val info = api.appVersion(BuildConfig.VERSION_CODE)
                if (info.updateAvailable || info.forceUpdate) {
                    val dismissedVersionCode = prefs.getInt(DISMISSED_UPDATE_VERSION_CODE, 0)
                    if (manual || dismissedVersionCode != info.latestVersionCode) {
                        _state.update {
                            it.copy(
                                updateInfo = info,
                                showUpdateDialog = true,
                                updateDownloading = false,
                                updateProgress = 0f,
                                updateError = null,
                                message = if (manual) "发现新版本 ${info.latestVersionName}" else it.message,
                            )
                        }
                    }
                } else if (manual) {
                    _state.update { it.copy(message = "当前已是最新版本：${BuildConfig.VERSION_NAME}") }
                }
            }.onFailure { error ->
                if (manual) _state.update { it.copy(message = error.message ?: "检查更新失败") }
            }
            if (manual) _state.update { it.copy(loading = false) }
        }
    }

    fun dismissUpdateDialog() {
        _state.update { state ->
            state.updateInfo?.let { info ->
                prefs.edit().putInt(DISMISSED_UPDATE_VERSION_CODE, info.latestVersionCode).apply()
            }
            state.copy(showUpdateDialog = false)
        }
    }

    fun downloadAndInstallUpdate() {
        val info = _state.value.updateInfo
        if (info == null) {
            _state.update { it.copy(message = "没有可用更新") }
            return
        }
        val app = getApplication<Application>()
        if (!app.packageManager.canRequestPackageInstalls()) {
            openUnknownSourcesSettings(app)
            _state.update { it.copy(message = "请先允许本 App 安装更新包，返回后再点一次更新") }
            return
        }
        // Do not delegate update packages to DownloadManager. Several Android
        // builds keep a stale entry for the stable APK URL, which can open the
        // installer with an older package. We download a versioned package into
        // our own directory, validate its manifest, and only then invoke install.
        launch("下载更新包") {
            _state.update { it.copy(updateDownloading = true, updateProgress = 0f, updateError = null, message = "正在下载更新包") }
            try {
                val apk = api.downloadUpdateApk(info) { progress ->
                    _state.update { state -> state.copy(updateDownloading = true, updateProgress = progress.coerceIn(0f, 1f)) }
                }
                val signingFlag = if (android.os.Build.VERSION.SDK_INT >= 28)
                    android.content.pm.PackageManager.GET_SIGNING_CERTIFICATES
                else
                    @Suppress("DEPRECATION") android.content.pm.PackageManager.GET_SIGNATURES
                val archive = app.packageManager.getPackageArchiveInfo(apk.absolutePath, signingFlag)
                    ?: error("下载文件不是有效安装包")
                if (archive.packageName != app.packageName || archive.longVersionCode < info.latestVersionCode.toLong()) {
                    apk.delete()
                    error("更新包版本校验失败，已拒绝安装旧包")
                }
                // P0-5: the downloaded APK must be signed by the SAME certificate as the
                // currently-installed app. Without this, a compromised backend or a MITM
                // on the (previously plaintext) update channel could hand us a foreign APK
                // that we then ask the system to install.
                val apkDigests = signatureDigests(archive)
                val currentDigests = signatureDigests(app.packageManager.getPackageInfo(app.packageName, signingFlag))
                if (apkDigests.isEmpty() || currentDigests.isEmpty() || apkDigests.intersect(currentDigests).isEmpty()) {
                    apk.delete()
                    error("更新包签名校验失败，已拒绝安装（可能被篡改）")
                }
                _state.update { it.copy(updateDownloading = false, updateProgress = 1f, updateError = null, message = "更新包已校验，正在打开安装界面") }
                installApk(apk)
            } catch (error: Throwable) {
                _state.update { it.copy(updateDownloading = false, updateProgress = 0f, updateError = "更新下载或校验失败：${friendlyErrorMessage(error)}", message = "更新失败，可重试") }
            }
        }
    }

    /** SHA-256 digests of an APK/package's signing certificates (API 26+ compatible). */
    private fun signatureDigests(pkgInfo: android.content.pm.PackageInfo?): Set<String> {
        if (pkgInfo == null) return emptySet()
        val signatures: Array<android.content.pm.Signature> = if (android.os.Build.VERSION.SDK_INT >= 28) {
            val signingInfo = pkgInfo.signingInfo ?: return emptySet()
            if (signingInfo.hasMultipleSigners()) signingInfo.apkContentsSigners else signingInfo.signingCertificateHistory
        } else {
            @Suppress("DEPRECATION") pkgInfo.signatures
        } ?: return emptySet()
        val md = java.security.MessageDigest.getInstance("SHA-256")
        return signatures.mapNotNull { sig ->
            md.reset()
            md.digest(sig.toByteArray()).joinToString("") { "%02x".format(it) }
        }.toSet()
    }

    private fun resumePendingUpdate() {
        val downloadId = prefs.getLong(UPDATE_DOWNLOAD_ID, -1L)
        if (downloadId > 0) observeUpdateDownload(downloadId, null)
    }

    private fun observeUpdateDownload(downloadId: Long, versionName: String?) {
        updatePollJob?.cancel()
        updatePollJob = viewModelScope.launch {
            val app = getApplication<Application>()
            val manager = app.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            while (true) {
                val snapshot = withContext(Dispatchers.IO) { readUpdateDownload(manager, downloadId) }
                when (snapshot.status) {
                    DownloadManager.STATUS_PENDING,
                    DownloadManager.STATUS_RUNNING,
                    DownloadManager.STATUS_PAUSED -> {
                        _state.update {
                            it.copy(
                                updateDownloading = true,
                                updateProgress = snapshot.progress,
                                updateError = null,
                                message = "正在下载 ${versionName?.let { name -> "更新包 $name" } ?: "更新包"}",
                            )
                        }
                        delay(800)
                    }
                    DownloadManager.STATUS_SUCCESSFUL -> {
                        prefs.edit().remove(UPDATE_DOWNLOAD_ID).apply()
                        _state.update { it.copy(updateDownloading = false, updateProgress = 1f, updateError = null, message = "更新包已下载，正在打开安装界面") }
                        val uri = manager.getUriForDownloadedFile(downloadId)
                        if (uri == null) {
                            _state.update { it.copy(updateError = "更新包已下载，但系统未返回安装文件，请重新下载。", message = "安装准备失败，可重试") }
                            return@launch
                        }
                        installApk(uri)
                        return@launch
                    }
                    else -> {
                        prefs.edit().remove(UPDATE_DOWNLOAD_ID).apply()
                        _state.update {
                            it.copy(
                                updateDownloading = false,
                                updateProgress = 0f,
                                updateError = "下载失败（${downloadFailureReason(snapshot.reason)}），可直接重试。",
                                message = "更新下载失败，可重试",
                            )
                        }
                        return@launch
                    }
                }
            }
        }
    }

    private data class UpdateDownloadSnapshot(val status: Int, val progress: Float, val reason: Int)

    private fun readUpdateDownload(manager: DownloadManager, downloadId: Long): UpdateDownloadSnapshot {
        manager.query(DownloadManager.Query().setFilterById(downloadId)).use { cursor ->
            if (!cursor.moveToFirst()) return UpdateDownloadSnapshot(DownloadManager.STATUS_FAILED, 0f, 0)
            val status = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
            val downloaded = cursor.getLong(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR))
            val total = cursor.getLong(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES))
            val reason = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_REASON))
            val progress = if (total > 0) (downloaded.toFloat() / total).coerceIn(0f, 1f) else 0f
            return UpdateDownloadSnapshot(status, progress, reason)
        }
    }

    private fun downloadFailureReason(reason: Int): String = when (reason) {
        DownloadManager.ERROR_INSUFFICIENT_SPACE -> "手机存储空间不足"
        DownloadManager.ERROR_DEVICE_NOT_FOUND -> "存储设备不可用"
        DownloadManager.ERROR_CANNOT_RESUME -> "下载中断，无法继续"
        DownloadManager.ERROR_FILE_ALREADY_EXISTS -> "旧更新包冲突"
        DownloadManager.ERROR_HTTP_DATA_ERROR -> "网络数据异常"
        DownloadManager.ERROR_TOO_MANY_REDIRECTS -> "下载地址重定向异常"
        DownloadManager.ERROR_UNHANDLED_HTTP_CODE -> "下载地址响应异常"
        else -> "网络或系统下载服务异常"
    }

    private fun installApk(uri: Uri) {
        val app = getApplication<Application>()
        if (!app.packageManager.canRequestPackageInstalls()) {
            openUnknownSourcesSettings(app)
            _state.update { it.copy(message = "请先允许本 App 安装更新包，返回后再点一次更新") }
            return
        }
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        runCatching { app.startActivity(intent) }
            .onFailure { error ->
                _state.update { it.copy(updateError = "安装界面未能打开：${friendlyErrorMessage(error)}", message = "更新包已下载，请重试安装") }
            }
    }

    private fun installApk(file: java.io.File) {
        val app = getApplication<Application>()
        val uri = FileProvider.getUriForFile(app, "${BuildConfig.APPLICATION_ID}.fileprovider", file)
        installApk(uri)
    }

    private fun openUnknownSourcesSettings(app: Application) {
        val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
            .setData(Uri.parse("package:${app.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        app.startActivity(intent)
    }

    private fun openLocalFile(file: java.io.File, mimeType: String) {
        val app = getApplication<Application>()
        val uri = FileProvider.getUriForFile(app, "${BuildConfig.APPLICATION_ID}.fileprovider", file)
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, mimeType)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        runCatching { app.startActivity(intent) }
            .onFailure { _state.update { state -> state.copy(message = "文件已下载，但手机上没有可打开该格式的应用") } }
    }

    private fun contentTypeForFile(name: String): String = when {
        name.endsWith(".pdf", ignoreCase = true) -> "application/pdf"
        name.endsWith(".docx", ignoreCase = true) -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        name.endsWith(".jpg", ignoreCase = true) || name.endsWith(".jpeg", ignoreCase = true) -> "image/jpeg"
        name.endsWith(".png", ignoreCase = true) -> "image/png"
        name.endsWith(".webp", ignoreCase = true) -> "image/webp"
        name.endsWith(".txt", ignoreCase = true) -> "text/plain"
        else -> "application/octet-stream"
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            repeat(60) {
                delay(3000)
                runCatching {
                    val jd = api.jdTasks()
                    val generations = api.generations()
                    _state.update { state ->
                        state.copy(
                            jdTasks = jd,
                            generations = generations,
                            selectedJd = state.selectedJd ?: jd.firstOrNull { it.status == "completed" && it.result != null }?.result,
                        )
                    }
                }
                val hasProcessing = _state.value.jdTasks.any { it.status == "processing" } ||
                    _state.value.generations.any { it.status == "processing" }
                if (!hasProcessing) return@launch
            }
        }
    }

    private fun readPickedFile(uri: Uri, fallbackMime: String): PickedFile {
        val app = getApplication<Application>()
        val resolver = app.contentResolver
        val mime = resolver.getType(uri) ?: fallbackMime
        val name = resolver.query(uri, null, null, null, null).use { cursor ->
            cursor?.displayName()
        } ?: uri.lastPathSegment?.substringAfterLast("/") ?: "upload"
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
            ?: throw ApiException("无法读取所选文件")
        return PickedFile(name = name, mimeType = mime, bytes = bytes)
    }

    private suspend fun readPickedFileAsync(uri: Uri, fallbackMime: String): PickedFile {
        return withContext(Dispatchers.IO) { readPickedFile(uri, fallbackMime) }
    }

    private fun Cursor.displayName(): String? {
        return if (moveToFirst()) {
            val index = getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0) getString(index) else null
        } else {
            null
        }
    }

    private fun launch(label: String?, block: suspend () -> Unit) {
        viewModelScope.launch {
            if (label != null) _state.update { it.copy(loading = true, message = label) }
            runCatching { block() }
                .onFailure { error ->
                    val message = friendlyErrorMessage(error)
                    _state.update { it.copy(message = message) }
                }
            _state.update { it.copy(loading = false) }
        }
    }

    companion object {
        private const val DISMISSED_UPDATE_VERSION_CODE = "dismissed_update_version_code"
        private const val UPDATE_DOWNLOAD_ID = "update_download_id"
    }
}

private fun friendlyErrorMessage(error: Throwable): String {
    val raw = error.message.orEmpty()
    val lower = raw.lowercase()
    return when {
        lower.contains("unable to resolve host") || lower.contains("failed to connect") || lower.contains("connection refused") -> "网络连接失败，请检查网络后重试"
        lower.contains("timeout") || lower.contains("timed out") -> "网络响应较慢，请稍后重试；后台任务不会丢失"
        lower.contains("canceled") || lower.contains("cancelled") -> "操作已取消"
        lower.contains("unauthorized") || lower.contains("401") -> "登录状态已失效，请重新登录"
        lower.contains("forbidden") || lower.contains("403") -> "当前账号没有执行此操作的权限"
        lower.contains("payload too large") || lower.contains("413") -> "上传文件过大，请压缩后重试"
        lower.contains("server error") || Regex("\\b5\\d\\d\\b").containsMatchIn(lower) -> "服务暂时繁忙，请稍后重试"
        raw.isBlank() -> "操作失败，请稍后重试"
        else -> raw
    }
}
