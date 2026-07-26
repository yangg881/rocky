package com.zhiday.resume

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import java.io.File
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import org.json.JSONObject

private val AppBg = Color(0xFFF7F7F4)
private val Ink = Color(0xFF1D2330)
private val Muted = Color(0xFF697386)
private val SoftLine = Color(0xFFE5E5DF)
private val PrimaryBlue = Color(0xFF2F4A96)
private val Lavender = Color(0xFFEAF0FF)
private val Mint = Color(0xFFE8F5F1)
private val Warm = Color(0xFFFFF2E6)
private val InkSoft = Color(0xFF4B4E61)
private val Accent = PrimaryBlue

class MainActivity : ComponentActivity() {
    private val viewModel by viewModels<MainViewModel>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ZhidayTheme {
                val state by viewModel.state.collectAsState()
                val snackbar = remember { SnackbarHostState() }
                val scope = rememberCoroutineScope()
                LaunchedEffect(state.message) {
                    val message = state.message
                    if (!message.isNullOrBlank()) {
                        scope.launch { snackbar.showSnackbar(message) }
                        viewModel.clearMessage()
                    }
                }
                Scaffold(
                    containerColor = AppBg,
                    snackbarHost = { SnackbarHost(snackbar) },
                    bottomBar = { if (state.tokenReady) WorkspaceBottomBar(state.tab, viewModel::switchTab) },
                ) { padding ->
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(AppBg)
                            .padding(padding),
                    ) {
                        if (!state.tokenReady) {
                            AuthScreen(viewModel)
                        } else {
                            WorkspaceScreen(state, viewModel)
                        }
                        if (state.loading) LoadingOverlay()
                        val updateInfo = state.updateInfo
                        if (state.showUpdateDialog && updateInfo != null) {
                            UpdateDialog(
                                info = updateInfo,
                                downloading = state.updateDownloading,
                                progress = state.updateProgress,
                                error = state.updateError,
                                onUpdate = viewModel::downloadAndInstallUpdate,
                                onDismiss = viewModel::dismissUpdateDialog,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ZhidayTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = PrimaryBlue,
            secondary = Color(0xFF14B8A6),
            surface = Color.White,
            background = AppBg,
        ),
        content = content,
    )
}

@Composable
private fun AuthScreen(viewModel: MainViewModel) {
    var mode by remember { mutableStateOf("login") }
    var loginMethod by remember { mutableStateOf("password") }
    var username by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    listOf(Color(0xFFF8FBFF), Color(0xFFEFF4FF), Color(0xFFF8F8F4)),
                ),
            )
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        item {
            Spacer(Modifier.height(38.dp))
            AuthHeroShowcase()
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(28.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = .96f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
            ) {
                Column(
                    Modifier.padding(horizontal = 24.dp, vertical = 24.dp),
                    verticalArrangement = Arrangement.spacedBy(17.dp),
                ) {
                SegmentRow(
                    options = listOf("login" to "登录", "register" to "注册"),
                    selected = if (mode == "reset") "login" else mode,
                    onSelected = { mode = it },
                )
                Text(
                    when (mode) {
                        "register" -> "创建账号"
                        "reset" -> "找回密码"
                        else -> "欢迎回来"
                    },
                    fontSize = 28.sp,
                    lineHeight = 34.sp,
                    color = Ink,
                    fontWeight = FontWeight.Black,
                )
                Text(
                    when (mode) {
                        "register" -> "手机号验证后即可开始生成简历"
                        "reset" -> "用短信验证码重新设置密码"
                        else -> "登录后继续你的简历优化之旅"
                    },
                    color = Muted,
                    fontSize = 15.sp,
                )
                if (mode == "login") {
                    SegmentRow(
                        options = listOf("password" to "账号密码", "sms" to "手机验证码"),
                        selected = loginMethod,
                        onSelected = { loginMethod = it },
                    )
                }
                if (mode == "register" || (mode == "login" && loginMethod == "password")) {
                    AuthTextField("♙", "请输入用户名", username) { username = it }
                }
                if (mode != "login" || loginMethod == "sms") {
                    AuthTextField("☎", "请输入手机号", phone) { phone = it }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.weight(1f)) { AuthTextField("✦", "验证码", code) { code = it } }
                        OutlinedButton(
                            onClick = {
                                val scene = when (mode) {
                                    "reset" -> "reset_password"
                                    "register" -> "register"
                                    else -> "login"
                                }
                                viewModel.sendSms(phone, scene)
                            },
                            modifier = Modifier.height(58.dp),
                            shape = RoundedCornerShape(16.dp),
                        ) { Text("发送") }
                    }
                }
                if (mode != "login" || loginMethod == "password") {
                    AuthPasswordField(if (mode == "reset") "请输入新密码" else "请输入密码", password) { password = it }
                }
                if (mode == "register") {
                    AuthPasswordField("请再次输入密码", confirmPassword) { confirmPassword = it }
                }
                GradientActionButton(
                    text = when (mode) {
                        "register" -> "注册并登录"
                        "reset" -> "重置密码"
                        else -> "进入工作台"
                    },
                    onClick = {
                        when (mode) {
                            "register" -> viewModel.register(username, phone, code, password, confirmPassword)
                            "reset" -> viewModel.resetPassword(phone, code, password)
                            else -> if (loginMethod == "sms") viewModel.smsLogin(phone, code) else viewModel.login(username, password)
                        }
                    },
                )
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                    TextButton(onClick = { mode = if (mode == "register") "login" else "register" }) {
                        Text(if (mode == "register") "已有账号，去登录" else "没有账号，去注册")
                    }
                    Text("｜", color = SoftLine, modifier = Modifier.padding(top = 13.dp))
                    TextButton(onClick = { mode = if (mode == "reset") "login" else "reset" }) {
                        Text(if (mode == "reset") "返回登录" else "忘记密码")
                    }
                }
                Row(
                    Modifier.fillMaxWidth().padding(top = 4.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("◇", color = Muted, fontSize = 16.sp)
                    Text(" 安全加密登录，保护账号隐私", color = Muted, fontSize = 13.sp)
                }
                // ---- 法律条款链接 ----
                var showLegalDialog by remember { mutableStateOf<Pair<String, String>?>(null) }
                if (showLegalDialog != null) {
                    LegalDialog(showLegalDialog!!.first, showLegalDialog!!.second) { showLegalDialog = null }
                }
                Row(
                    Modifier.fillMaxWidth().padding(top = 6.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("登录即代表你已阅读并同意 ",
                         color = Muted, fontSize = 11.sp, lineHeight = 16.sp)
                    TextButton(
                        onClick = { showLegalDialog = "用户服务协议" to LEGAL_TERMS },
                        modifier = Modifier.height(24.dp).defaultMinSize(minWidth = 0.dp),
                        contentPadding = PaddingValues(horizontal = 2.dp),
                    ) { Text("用户服务协议", color = Accent, fontSize = 11.sp) }
                    Text(" · ", color = Muted, fontSize = 11.sp, lineHeight = 16.sp)
                    TextButton(
                        onClick = { showLegalDialog = "隐私保护政策" to LEGAL_PRIVACY },
                        modifier = Modifier.height(24.dp).defaultMinSize(minWidth = 0.dp),
                        contentPadding = PaddingValues(horizontal = 2.dp),
                    ) { Text("隐私保护政策", color = Accent, fontSize = 11.sp) }
                    Text(" · ", color = Muted, fontSize = 11.sp, lineHeight = 16.sp)
                    TextButton(
                        onClick = { showLegalDialog = "免责声明" to LEGAL_DISCLAIMER },
                        modifier = Modifier.height(24.dp).defaultMinSize(minWidth = 0.dp),
                        contentPadding = PaddingValues(horizontal = 2.dp),
                    ) { Text("免责声明", color = Accent, fontSize = 11.sp) }
                }
                }
            }
            Spacer(Modifier.height(32.dp))
        }
    }
}

@Composable
private fun AuthHeroShowcase() {
    Box(
        Modifier
            .fillMaxWidth()
            .height(232.dp)
            .clip(RoundedCornerShape(28.dp))
            .background(
                Brush.linearGradient(
                    listOf(Color(0xFF111A3A), Color(0xFF1E3172), Color(0xFF5637EA)),
                ),
            )
            .padding(24.dp),
    ) {
        Column(Modifier.align(Alignment.CenterStart), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                "AI 简历适配工具",
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
                modifier = Modifier
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color(0xFF536DFF).copy(alpha = .55f))
                    .padding(horizontal = 14.dp, vertical = 8.dp),
            )
            Text("职达简历", color = Color.White, fontSize = 42.sp, lineHeight = 46.sp, fontWeight = FontWeight.Black)
            Text("把真实经历，讲成岗位听得懂的语言。", color = Color.White.copy(alpha = .88f), fontSize = 16.sp)
            Box(
                Modifier
                    .width(44.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(Color(0xFF5FA8FF)),
            )
        }
        Box(
            Modifier
                .align(Alignment.CenterEnd)
                .padding(end = 10.dp)
                .size(112.dp)
                .clip(RoundedCornerShape(22.dp))
                .background(Color(0xFF7EA2FF).copy(alpha = .42f))
                .border(1.dp, Color.White.copy(alpha = .28f), RoundedCornerShape(22.dp))
                .padding(18.dp),
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Box(Modifier.size(22.dp).clip(CircleShape).background(Color.White.copy(alpha = .9f)))
                repeat(4) {
                    Box(
                        Modifier
                            .fillMaxWidth(if (it == 0) .85f else if (it == 3) .55f else 1f)
                            .height(7.dp)
                            .clip(RoundedCornerShape(999.dp))
                            .background(Color.White.copy(alpha = .33f)),
                    )
                }
            }
        }
        Text(
            "AI",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Black,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .clip(RoundedCornerShape(14.dp))
                .background(Color.White.copy(alpha = .16f))
                .border(1.dp, Color.White.copy(alpha = .24f), RoundedCornerShape(14.dp))
                .padding(horizontal = 14.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun AuthTextField(icon: String, placeholder: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        placeholder = { Text(placeholder, color = Color(0xFFA6ADBA), fontWeight = FontWeight.SemiBold) },
        leadingIcon = { Text(icon, color = Muted, fontSize = 20.sp) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        shape = RoundedCornerShape(18.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = Color(0xFF4A72FF),
            unfocusedBorderColor = Color(0xFFD7DCE8),
            focusedContainerColor = Color.White,
            unfocusedContainerColor = Color.White,
        ),
    )
}

@Composable
private fun AuthPasswordField(placeholder: String, value: String, onChange: (String) -> Unit) {
    var visible by remember { mutableStateOf(false) }
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        placeholder = { Text(placeholder, color = Color(0xFFA6ADBA), fontWeight = FontWeight.SemiBold) },
        leadingIcon = { Text("▣", color = Muted, fontSize = 19.sp) },
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        trailingIcon = {
            TextButton(onClick = { visible = !visible }) {
                Text(if (visible) "隐藏" else "◎", color = Muted, fontWeight = FontWeight.Black)
            }
        },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        shape = RoundedCornerShape(18.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = Color(0xFF4A72FF),
            unfocusedBorderColor = Color(0xFFD7DCE8),
            focusedContainerColor = Color.White,
            unfocusedContainerColor = Color.White,
        ),
    )
}

@Composable
private fun GradientActionButton(text: String, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .height(58.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(Brush.linearGradient(listOf(Color(0xFF4F86FF), Color(0xFF2F55F6), Color(0xFF6438FF))))
            .clickable(onClick = onClick)
            .padding(horizontal = 22.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(text, color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Black)
        Spacer(Modifier.width(18.dp))
        Text("→", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun MainScreen(state: UiState, viewModel: MainViewModel) {
    when (state.tab) {
        AppTab.Resumes -> ResumeScreen(state, viewModel)
        AppTab.Radar -> RadarScreen(state, viewModel)
        AppTab.Match -> MatchScreen(state, viewModel)
        AppTab.Generations -> GenerationScreen(state, viewModel)
        AppTab.Career -> CareerCenterScreen(state, viewModel)
        AppTab.Account -> AccountScreen(state, viewModel)
    }
}

@Composable
private fun RadarScreen(state: UiState, viewModel: MainViewModel) {
    val context = LocalContext.current
    var searchQuery by remember(state.radarQuery) { mutableStateOf(state.radarQuery) }
    LazyColumn(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("岗位雷达", "根据你的简历与反馈持续学习；岗位详情会在广西人才网打开，由你自主投递。") }
        item {
            HeroCard(
                title = "${state.radarSummary.availableJobs} 个在招岗位",
                subtitle = "每一次收藏、投递或不感兴趣，都会只影响你的下一轮推荐。",
                kicker = "职达岗位雷达 · 广西人才网",
            )
        }
        item {
            AppCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    RadarStat("收藏", state.radarSummary.saved)
                    RadarStat("已投", state.radarSummary.applied)
                    RadarStat("不感兴趣", state.radarSummary.notInterested)
                }
                OutlinedButton(onClick = viewModel::loadRadar, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) {
                    Text("刷新推荐")
                }
            }
        }
        item {
            AppCard {
                SectionHeader("筛选岗位", "筛选只缩小当前展示范围，匹配排序仍由你的职业画像决定。")
                AppTextField("搜索岗位或公司", searchQuery) { searchQuery = it }
                Text("工作城市", color = Muted, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    item { ChoiceChip("全部", state.radarCity.isBlank()) { viewModel.updateRadarFilters(searchQuery, "", state.radarPublishedWithin) } }
                    items(state.radarCities.take(80), key = { it }) { city ->
                        ChoiceChip(city, state.radarCity == city) { viewModel.updateRadarFilters(searchQuery, city, state.radarPublishedWithin) }
                    }
                }
                Text("发布时间", color = Muted, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(listOf("all" to "不限", "1d" to "近1天", "3d" to "近3天", "7d" to "近7天", "30d" to "近30天"), key = { it.first }) { option ->
                        ChoiceChip(option.second, state.radarPublishedWithin == option.first) {
                            viewModel.updateRadarFilters(searchQuery, state.radarCity, option.first)
                        }
                    }
                }
                Button(
                    onClick = { viewModel.updateRadarFilters(searchQuery, state.radarCity, state.radarPublishedWithin) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                ) { Text("筛选并按匹配度排序") }
            }
        }
        item { SectionLabel("为你推荐 · 前 ${state.radarPagination.total} 个岗位，第 ${state.radarPagination.page}/${state.radarPagination.totalPages} 页") }
        items(state.radarJobs, key = { it.id }) { job ->
            RadarJobCard(
                job = job,
                onOpen = {
                    viewModel.radarFeedback(job, "viewed")
                    if (job.sourceUrl.isNotBlank()) {
                        runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(job.sourceUrl))) }
                            .onFailure { viewModel.radarFeedback(job, "later") }
                    }
                },
                onOptimize = { viewModel.optimizeRadarJob(job) },
                onSave = { viewModel.radarFeedback(job, "saved") },
                onApplied = { viewModel.radarFeedback(job, "applied") },
                onNotInterested = { viewModel.radarFeedback(job, "not_interested") },
                onBlockCompany = { viewModel.blockRadarCompany(job) },
            )
        }
        if (state.radarJobs.isEmpty()) {
            item { EmptyHint("暂时没有可展示的推荐。先完善基础简历，或稍后刷新岗位库后再试。") }
        }
        if (state.radarPagination.totalPages > 1) {
            item { RadarPaginationControls(state.radarPagination, viewModel::changeRadarPage) }
        }
        item { Spacer(Modifier.height(12.dp)) }
    }
}

@Composable
private fun RadarPaginationControls(pagination: RadarPagination, onChange: (Int) -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        OutlinedButton(onClick = { onChange(-1) }, enabled = pagination.page > 1, shape = RoundedCornerShape(999.dp)) { Text("上一页") }
        Text("第 ${pagination.page} / ${pagination.totalPages} 页", color = Muted, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        OutlinedButton(onClick = { onChange(1) }, enabled = pagination.page < pagination.totalPages, shape = RoundedCornerShape(999.dp)) { Text("下一页") }
    }
}

@Composable
private fun RadarStat(label: String, value: Int) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value.toString(), color = PrimaryBlue, fontSize = 22.sp, fontWeight = FontWeight.Black)
        Text(label, color = Muted, fontSize = 12.sp)
    }
}

@Composable
private fun RadarJobCard(
    job: RadarJob,
    onOpen: () -> Unit,
    onOptimize: () -> Unit,
    onSave: () -> Unit,
    onApplied: () -> Unit,
    onNotInterested: () -> Unit,
    onBlockCompany: () -> Unit,
) {
    AppCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(job.title, color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(job.company.ifBlank { "招聘企业未披露" }, color = Muted, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            SmallBadge("匹配 ${job.matchScore}%")
        }
        val meta = listOf(job.salary, job.location, job.experience, job.education).filter { it.isNotBlank() }
        if (meta.isNotEmpty()) Text(meta.joinToString(" · "), color = Muted, fontSize = 13.sp)
        if (job.matchReason.isNotBlank()) {
            Text(job.matchReason, color = PrimaryBlue, fontSize = 13.sp, lineHeight = 19.sp)
        }
        if (job.tags.isNotEmpty()) Text(job.tags.take(8).joinToString(" · "), color = Muted, fontSize = 12.sp)
        if (job.description.isNotBlank()) Text(job.description, color = Muted, maxLines = 2, overflow = TextOverflow.Ellipsis, lineHeight = 20.sp)
        if (!job.feedbackAction.isNullOrBlank()) SmallBadge(feedbackLabel(job.feedbackAction))
        Button(
            onClick = onOpen,
            enabled = job.sourceUrl.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
        ) { Text("查看详情并自主投递") }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onOptimize, modifier = Modifier.weight(1f), shape = RoundedCornerShape(999.dp)) {
                Text(if (job.adapted) "换模板重新生成" else "用此岗位优化简历")
            }
            OutlinedButton(onClick = onSave, modifier = Modifier.weight(1f), shape = RoundedCornerShape(999.dp)) { Text("收藏") }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onApplied) { Text("已投递") }
            TextButton(onClick = onNotInterested) { Text("不感兴趣") }
            if (job.company.isNotBlank()) TextButton(onClick = onBlockCompany) { Text("不看该公司") }
        }
    }
}

@Composable
private fun ResumeScreen(state: UiState, viewModel: MainViewModel) {
    var showEditor by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<ResumeItem?>(null) }
    var versionName by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var age by remember { mutableStateOf("") }
    var title by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var summary by remember { mutableStateOf("") }
    var skills by remember { mutableStateOf("") }
    var experience by remember { mutableStateOf("") }
    var projects by remember { mutableStateOf("") }
    var education by remember { mutableStateOf("") }
    var certificates by remember { mutableStateOf("") }
    var avatarTargetId by remember { mutableStateOf<String?>(null) }
    val context = LocalContext.current

    val documentLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let(viewModel::uploadResumeDocument)
    }
    val resumeImageLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let(viewModel::ocrResumeImage)
    }
    val avatarCropLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val target = avatarTargetId
        val path = result.data?.getStringExtra(CropAvatarActivity.EXTRA_CROPPED_PATH)
        if (result.resultCode == Activity.RESULT_OK && target != null && !path.isNullOrBlank()) {
            viewModel.uploadAvatar(target, Uri.fromFile(File(path)))
        }
        avatarTargetId = null
    }
    val avatarLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        val target = avatarTargetId
        if (uri != null && target != null) {
            avatarCropLauncher.launch(Intent(context, CropAvatarActivity::class.java).putExtra(CropAvatarActivity.EXTRA_SOURCE_URI, uri.toString()))
        } else {
            avatarTargetId = null
        }
    }

    fun fill(item: ResumeItem?) {
        editing = item
        val content = item?.content ?: ResumeContent()
        versionName = item?.name ?: ""
        name = content.name
        age = content.age
        title = content.title
        phone = content.phone
        email = content.email
        summary = content.summary
        skills = content.skills.joinToString("\n")
        experience = content.experience.joinToString("\n")
        projects = content.projects.joinToString("\n")
        education = content.education.joinToString("\n")
        certificates = content.certificates.joinToString("\n")
        showEditor = true
    }

    LazyColumn(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("简历库", "先把基础资料放好，后面就像点外卖一样选岗位、选风格、生成。") }
        item {
            val selected = state.resumes.firstOrNull { it.id == state.selectedResumeId }
                ?: state.resumes.firstOrNull { it.isDefault }
                ?: state.resumes.firstOrNull()
            FocusResumeCard(
                resume = selected,
                onEdit = { selected?.let { fill(it) } ?: fill(null) },
                onAvatar = {
                    selected?.let {
                        avatarTargetId = it.id
                        avatarLauncher.launch("image/*")
                    }
                },
            )
        }
        item {
            QuickActionsCard(
                onUpload = { documentLauncher.launch("*/*") },
                onOcr = { resumeImageLauncher.launch("image/*") },
                onCreate = { fill(null) },
            )
        }
        if (showEditor) {
            item {
                AppCard {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text(if (editing == null) "新建简历" else "编辑简历", style = MaterialTheme.typography.titleLarge, color = Ink, fontWeight = FontWeight.Black)
                        TextButton(onClick = { showEditor = false; editing = null }) { Text("收起") }
                    }
                    AppTextField("版本名称", versionName) { versionName = it }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Box(Modifier.weight(1f)) { AppTextField("姓名", name) { name = it } }
                        Box(Modifier.width(110.dp)) { AppTextField("年龄", age) { age = it } }
                    }
                    AppTextField("当前职位或求职方向", title) { title = it }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Box(Modifier.weight(1f)) { AppTextField("电话", phone) { phone = it } }
                        Box(Modifier.weight(1f)) { AppTextField("邮箱", email) { email = it } }
                    }
                    AppTextField("经验与能力概述", summary, minLines = 3) { summary = it }
                    AppTextField("经验技能（一行一条，少而准）", skills, minLines = 2) { skills = it }
                    AppTextField("工作经历", experience, minLines = 4) { experience = it }
                    AppTextField("项目经历", projects, minLines = 3) { projects = it }
                    AppTextField("教育经历", education, minLines = 2) { education = it }
                    AppTextField("证书", certificates, minLines = 2) { certificates = it }
                    Button(
                        onClick = {
                            viewModel.saveResume(
                                editing?.id,
                                versionName,
                                ResumeContent(
                                    name = name,
                                    title = title,
                                    age = age,
                                    phone = phone,
                                    email = email,
                                    summary = summary,
                                    skills = lines(skills),
                                    experience = lines(experience),
                                    projects = lines(projects),
                                    education = lines(education),
                                    certificates = lines(certificates),
                                ),
                            )
                            showEditor = false
                            editing = null
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(18.dp),
                    ) { Text("保存到简历库") }
                }
            }
        }
        item {
            SectionLabel("全部简历")
        }
        items(state.resumes, key = { it.id }) { resume ->
            ResumeCard(
                resume,
                selected = state.selectedResumeId == resume.id,
                onSelect = { viewModel.selectResume(resume.id) },
                onEdit = { fill(resume) },
                onDefault = { viewModel.setDefault(resume.id) },
                onAvatar = {
                    avatarTargetId = resume.id
                    avatarLauncher.launch("image/*")
                },
                onOriginal = { viewModel.openOriginalResume(resume) },
                onDownloadOriginal = { viewModel.downloadOriginalResume(resume) },
                onDelete = { viewModel.deleteResume(resume.id) },
            )
        }
        if (state.resumes.isEmpty()) {
            item { EmptyHint("还没有简历。可以上传 Word/PDF，也可以先在线新建一份。") }
        }
    }
}

@Composable
private fun FocusResumeCard(resume: ResumeItem?, onEdit: () -> Unit, onAvatar: () -> Unit) {
    val content = resume?.content
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = PrimaryBlue),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("当前使用", color = Color.White.copy(alpha = 0.78f), fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Text(content?.name?.takeIf { it.isNotBlank() } ?: resume?.name ?: "还没有基础简历", color = Color.White, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
            Text(
                listOfNotNull(content?.title?.takeIf { it.isNotBlank() }, content?.age?.takeIf { it.isNotBlank() }?.let { "$it 岁" })
                    .joinToString(" · ")
                    .ifBlank { "上传或填写后，系统会按岗位自动适配。" },
                color = Color.White.copy(alpha = 0.84f),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = onEdit, shape = RoundedCornerShape(10.dp), border = BorderStroke(1.dp, Color.White.copy(alpha = .65f)), colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)) { Text(if (resume == null) "新建简历" else "编辑资料") }
                if (resume != null) OutlinedButton(onClick = onAvatar, shape = RoundedCornerShape(10.dp), border = BorderStroke(1.dp, Color.White.copy(alpha = .65f)), colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)) { Text(if (resume.avatarKey == null) "上传头像" else "更换头像") }
            }
        }
    }
}

@Composable
private fun QuickActionsCard(onUpload: () -> Unit, onOcr: () -> Unit, onCreate: () -> Unit) {
    AppCard {
        Text("快速开始", style = MaterialTheme.typography.titleMedium, color = Ink, fontWeight = FontWeight.Black)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ActionTile("上传文档", "Word / PDF", Mint, Modifier.weight(1f), onUpload)
            ActionTile("截图识别", "图片导入", Warm, Modifier.weight(1f), onOcr)
        }
        ActionTile("手动补充", "只在需要时打开完整表单", Lavender, Modifier.fillMaxWidth(), onCreate)
    }
}

@Composable
private fun ActionTile(title: String, subtitle: String, color: Color, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier
            .clip(RoundedCornerShape(18.dp))
            .background(color)
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, color = Ink, fontWeight = FontWeight.Black)
        Text(subtitle, color = Muted, fontSize = 12.sp)
    }
}

@Composable
private fun ResumeCard(
    item: ResumeItem,
    selected: Boolean,
    onSelect: () -> Unit,
    onEdit: () -> Unit,
    onDefault: () -> Unit,
    onAvatar: () -> Unit,
    onOriginal: () -> Unit,
    onDownloadOriginal: () -> Unit,
    onDelete: () -> Unit,
) {
    var showStructured by remember(item.id) { mutableStateOf(false) }
    AppCard {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AvatarBubble(item.content.name.ifBlank { item.name })
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(item.name, color = Ink, fontWeight = FontWeight.Black, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (item.isDefault) SmallBadge("默认")
                    if (selected) SmallBadge("已选")
                }
                Text("${item.content.name}  ${item.content.title}".trim().ifBlank { "未填写核心信息" }, color = Muted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    listOfNotNull(item.content.age.takeIf { it.isNotBlank() }?.let { "年龄：$it" }, if (item.avatarKey != null) "已带头像" else "未上传头像").joinToString(" · "),
                    color = Muted,
                    fontSize = 12.sp,
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (!selected) OutlinedButton(onClick = onSelect, shape = RoundedCornerShape(999.dp)) { Text("选用") }
            if (!item.isDefault) OutlinedButton(onClick = onDefault, shape = RoundedCornerShape(999.dp)) { Text("设默认") }
            if (item.sourceKey != null) OutlinedButton(onClick = onOriginal, shape = RoundedCornerShape(999.dp)) { Text("原文件") }
            OutlinedButton(onClick = { showStructured = !showStructured }, shape = RoundedCornerShape(999.dp)) { Text(if (showStructured) "收起整理" else "整理预览") }
            OutlinedButton(onClick = onAvatar, shape = RoundedCornerShape(999.dp)) { Text("头像") }
            OutlinedButton(onClick = onEdit, shape = RoundedCornerShape(999.dp)) { Text("编辑") }
            TextButton(onClick = onDelete) { Text("删除") }
        }
        if (item.sourceKey != null) {
            TextButton(onClick = onDownloadOriginal) { Text("下载原简历文件") }
        }
        if (showStructured) {
            StructuredResumePreview(item.content)
        }
    }
}

@Composable
private fun StructuredResumePreview(content: ResumeContent) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Color(0xFFF3F5FA))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("系统整理后的内容", color = Ink, fontWeight = FontWeight.Black)
        previewLine("姓名", content.name)
        previewLine("方向", content.title)
        previewLine("年龄", content.age)
        previewLine("电话", content.phone)
        previewLine("邮箱", content.email)
        previewLine("概述", content.summary)
        previewList("经验技能", content.skills)
        previewList("工作经历", content.experience)
        previewList("项目经历", content.projects)
        previewList("教育经历", content.education)
        previewList("证书荣誉", content.certificates)
    }
}

@Composable
private fun previewLine(label: String, value: String) {
    if (value.isNotBlank()) Text("$label：$value", color = Muted, lineHeight = 20.sp)
}

@Composable
private fun previewList(label: String, values: List<String>) {
    if (values.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("$label：", color = Ink, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            values.forEach { value ->
                Text("• $value", color = Muted, lineHeight = 20.sp)
            }
        }
    }
}

@Composable
private fun MatchScreen(state: UiState, viewModel: MainViewModel) {
    var sourceType by remember { mutableStateOf("text") }
    var showInput by remember { mutableStateOf(false) }
    var jdInput by remember { mutableStateOf("") }
    val jdImageLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris: List<Uri> ->
        if (uris.isNotEmpty()) viewModel.parseJdImages(uris)
    }

    LazyColumn(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("岗位适配", "提交后自动在后台跑，手机不用一直停在当前页面。") }
        item {
            AppCard {
                SectionHeader("基础简历", "选择这次要拿去适配的版本")
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(state.resumes, key = { it.id }) { resume ->
                        ChoiceChip(resume.name, state.selectedResumeId == resume.id) { viewModel.selectResume(resume.id) }
                    }
                }
                if (state.resumes.isEmpty()) Text("请先在简历库创建或上传一份基础简历。", color = Color(0xFFB45309))
            }
        }
        item {
            AppCard {
                SectionHeader("简历风格", "先选方向，系统再根据岗位细化配色")
                ThemeStrip(state.selectedDesignTheme, viewModel::selectTheme)
            }
        }
        item {
            AppCard {
                SegmentRow(
                    options = listOf("text" to "文本", "url" to "链接", "image" to "截图"),
                    selected = sourceType,
                    onSelected = {
                        sourceType = it
                        showInput = false
                    },
                )
                if (!showInput) {
                    Text(
                        when (sourceType) {
                            "url" -> "粘贴岗位链接后解析，适合招聘网站详情页。"
                            "image" -> "一次可选多张岗位截图，系统会按顺序识别。"
                            else -> "粘贴岗位职责和任职要求，适合手里已有 JD 文本。"
                        },
                        color = Muted,
                    )
                    Button(
                        onClick = { if (sourceType == "image") jdImageLauncher.launch("image/*") else showInput = true },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(18.dp),
                    ) { Text(if (sourceType == "image") "选择岗位截图" else "填写${if (sourceType == "url") "链接" else "文本"}") }
                } else {
                    AppTextField(if (sourceType == "url") "岗位链接" else "岗位描述", jdInput, minLines = if (sourceType == "url") 1 else 5) { jdInput = it }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        OutlinedButton(onClick = { showInput = false }, modifier = Modifier.weight(1f), shape = RoundedCornerShape(18.dp)) { Text("收起") }
                        Button(
                            onClick = { viewModel.parseJd(sourceType, jdInput) },
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(18.dp),
                        ) { Text("解析岗位") }
                    }
                }
            }
        }
        state.selectedJd?.let { jd ->
            item { JdResultCard(jd) { viewModel.generate() } }
        }
        item { SectionLabel("最近解析") }
        items(state.jdTasks.take(8), key = { it.id }) { task ->
            JdTaskCard(
                task,
                onUse = { viewModel.useJd(task) },
                onGenerate = {
                    viewModel.useJd(task)
                    viewModel.generate()
                },
                onDelete = { viewModel.deleteJdTask(task.id) },
            )
        }
    }
}

@Composable
private fun JdResultCard(jd: JSONObject, onGenerate: () -> Unit) {
    AppCard {
        SectionHeader("已选岗位", "确认后直接生成适配简历")
        Text(jd.optString("title", "未识别岗位").ifBlank { "未识别岗位" }, style = MaterialTheme.typography.titleLarge, color = Ink, fontWeight = FontWeight.Black)
        jd.optString("company", "").takeIf { it.isNotBlank() }?.let { Text(it, color = Muted) }
        KeywordText(jd)
        Button(onClick = onGenerate, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) { Text("生成适配简历") }
    }
}

@Composable
private fun JdTaskCard(task: JdTask, onUse: () -> Unit, onGenerate: () -> Unit, onDelete: () -> Unit) {
    var expanded by remember(task.id) { mutableStateOf(false) }
    AppCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(task.result?.optString("title")?.takeIf { it.isNotBlank() } ?: task.detail.ifBlank { "岗位解析任务" }, color = Ink, fontWeight = FontWeight.Black, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
            SmallBadge(statusLabel(task.status))
        }
        Text("${sourceLabel(task.source)} · ${task.progress ?: "等待处理"}", color = Muted)
        task.error?.takeIf { it.isNotBlank() }?.let { Text(it, color = Color(0xFFB42318)) }
        if (task.status == "completed" && task.result != null) {
            if (expanded) {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFFF3F5FA))
                        .padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(task.result.optString("title", "未识别岗位"), color = Ink, fontWeight = FontWeight.Black)
                    task.result.optString("company").takeIf { it.isNotBlank() }?.let { Text(it, color = Muted) }
                    KeywordText(task.result)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { expanded = !expanded }, shape = RoundedCornerShape(999.dp)) { Text(if (expanded) "收起" else "查看解析") }
                OutlinedButton(onClick = onUse, shape = RoundedCornerShape(999.dp)) { Text("选用") }
                Button(onClick = onGenerate, shape = RoundedCornerShape(999.dp)) { Text("一键生成") }
            }
        }
        TextButton(onClick = onDelete) { Text("删除记录") }
    }
}

@Composable
private fun GenerationScreen(state: UiState, viewModel: MainViewModel) {
    LazyColumn(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("AI简历作品中心", "每份作品都带评分、岗位匹配度和AI优化报告，满意后再下载。") }
        items(state.generations, key = { it.id }) { item ->
            GenerationCard(item, viewModel)
        }
        if (state.generations.isEmpty()) {
            item { EmptyHint("还没有生成记录。去“适配”页解析岗位后，就能生成第一版。") }
        }
    }
}

@Composable
private fun GenerationCard(item: GenerationItem, viewModel: MainViewModel) {
    var theme by remember(item.id) { mutableStateOf("auto") }
    var showThemes by remember(item.id) { mutableStateOf(false) }
    AppCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(item.title, color = Ink, fontWeight = FontWeight.Black, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text("${item.resumeName} · ${statusLabel(item.status)}", color = Muted)
            }
            SmallBadge(statusLabel(item.status))
        }
        item.message?.takeIf { it.isNotBlank() }?.let { Text(it, color = Muted) }
        item.error?.takeIf { it.isNotBlank() }?.let { Text(it, color = Color(0xFFB42318)) }
        if (item.status == "completed") {
            if (item.overallScore != null) {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(18.dp))
                        .background(Color(0xFFF3F6FF))
                        .padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text("AI综合评分", color = Muted, fontSize = 12.sp)
                            Text("${item.overallScore}分", color = PrimaryBlue, fontWeight = FontWeight.Black, fontSize = 28.sp)
                        }
                        SmallBadge("竞争版简历")
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        ScorePill("岗位匹配", item.jobMatchScore, Modifier.weight(1f))
                        ScorePill("关键词", item.keywordCoverageScore, Modifier.weight(1f))
                        ScorePill("视觉", item.visualScore, Modifier.weight(1f))
                    }
                }
            }
            if (item.optimizations.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("AI优化报告", color = Ink, fontWeight = FontWeight.Bold)
                    item.optimizations.take(3).forEach { Text("• $it", color = Muted, lineHeight = 19.sp) }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(onClick = { viewModel.openFile(item, "pdf") }, shape = RoundedCornerShape(999.dp), modifier = Modifier.weight(1f)) { Text("预览 PDF") }
                OutlinedButton(onClick = { viewModel.openFile(item, "docx") }, shape = RoundedCornerShape(999.dp), modifier = Modifier.weight(1f)) { Text("预览 Word") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = { viewModel.downloadFile(item, "pdf") }, shape = RoundedCornerShape(999.dp), modifier = Modifier.weight(1f)) { Text("下载 PDF") }
                OutlinedButton(onClick = { viewModel.downloadFile(item, "docx") }, shape = RoundedCornerShape(999.dp), modifier = Modifier.weight(1f)) { Text("下载 Word") }
            }
            TextButton(onClick = { showThemes = !showThemes }) { Text(if (showThemes) "收起模板" else "换模板再生成") }
            if (showThemes) {
                ThemeStrip(theme) { theme = it }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { viewModel.regenerate(item, theme) }, modifier = Modifier.weight(1f), shape = RoundedCornerShape(999.dp)) { Text("按此模板生成") }
                    TextButton(onClick = { viewModel.deleteGeneration(item.id) }) { Text("删除") }
                }
            }
        }
    }
}

@Composable
private fun ScorePill(label: String, score: Int?, modifier: Modifier = Modifier) {
    Column(
        modifier
            .clip(RoundedCornerShape(14.dp))
            .background(Color.White)
            .padding(vertical = 9.dp, horizontal = 10.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("${score ?: "--"}", color = Ink, fontWeight = FontWeight.Black, fontSize = 18.sp)
        Text(label, color = Muted, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun CareerCenterScreen(state: UiState, viewModel: MainViewModel) {
    var jobTitle by remember { mutableStateOf("") }
    var company by remember { mutableStateOf("") }
    var sourceUrl by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("职业中心", "把真实经历、岗位审阅、投递进度和套餐额度统一放在这里。") }
        item {
            AppCard {
                SectionHeader("职业事实", "只保留你确认过的经历，再用于岗位表达和简历生成。")
                Button(onClick = viewModel::rebuildCareerFacts, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) { Text("从当前基础简历重建事实") }
                if (state.careerFacts.isEmpty()) EmptyHint("暂时没有职业事实；先保存一份基础简历后即可重建。")
                state.careerFacts.take(12).forEach { fact ->
                    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Lavender).padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(fact.text, color = Ink, fontWeight = FontWeight.Bold)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            SmallBadge(if (fact.status == "confirmed") "已确认" else "已拒绝")
                            Text("风险 ${fact.riskLevel}", color = Muted, fontSize = 12.sp)
                            Spacer(Modifier.weight(1f))
                            TextButton(onClick = { viewModel.decideCareerFact(fact.id, "confirmed") }) { Text("确认") }
                            TextButton(onClick = { viewModel.decideCareerFact(fact.id, "rejected") }) { Text("拒绝") }
                        }
                    }
                }
            }
        }
        item {
            AppCard {
                SectionHeader("岗位审阅", "先在岗位适配页解析并选用一个岗位，再创建审阅。")
                OutlinedButton(onClick = viewModel::createReview, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) { Text("基于当前岗位创建审阅") }
                if (state.reviews.isEmpty()) EmptyHint("暂无待审阅建议。")
                state.reviews.take(3).forEach { review ->
                    Column(Modifier.fillMaxWidth().padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(review.title, color = Ink, fontWeight = FontWeight.Black)
                        review.proposals.take(6).forEach { proposal ->
                            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Mint).padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(proposal.text, color = Ink, fontWeight = FontWeight.Bold)
                                Text(proposal.reason, color = Muted, fontSize = 12.sp)
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    TextButton(onClick = { viewModel.decideReview(review.id, proposal.id, "accepted") }) { Text("接受") }
                                    TextButton(onClick = { viewModel.decideReview(review.id, proposal.id, "rejected") }) { Text("拒绝") }
                                }
                            }
                        }
                    }
                }
            }
        }
        item {
            AppCard {
                SectionHeader("新增投递", "记录岗位与跟进状态，后续可以随时修改或删除。")
                AppTextField("岗位名称", jobTitle) { jobTitle = it }
                AppTextField("公司（可选）", company) { company = it }
                AppTextField("岗位链接（可选）", sourceUrl) { sourceUrl = it }
                AppTextField("备注（可选）", note) { note = it }
                Button(onClick = { if (jobTitle.isNotBlank()) { viewModel.createApplication(jobTitle, company, sourceUrl, "saved", note); jobTitle = ""; company = ""; sourceUrl = ""; note = "" } }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp)) { Text("保存投递记录") }
            }
        }
        item {
            AppCard {
                SectionHeader("我的投递", "点击状态可快速更新；删除后不可恢复。")
                if (state.applications.isEmpty()) EmptyHint("还没有投递记录。")
                state.applications.forEach { item ->
                    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color(0xFFF7F8FC)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(item.jobTitle, color = Ink, fontWeight = FontWeight.Black)
                        Text(listOf(item.company, item.nextActionAt, item.note).filter { it.isNotBlank() }.joinToString(" · "), color = Muted, fontSize = 12.sp)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            ChoiceChip("待投递", item.status == "saved") { viewModel.updateApplication(item.id, "saved") }
                            ChoiceChip("已投递", item.status == "applied") { viewModel.updateApplication(item.id, "applied") }
                            ChoiceChip("面试中", item.status == "interview") { viewModel.updateApplication(item.id, "interview") }
                            Spacer(Modifier.weight(1f))
                            TextButton(onClick = { viewModel.deleteApplication(item.id) }) { Text("删除", color = Color(0xFFB42318)) }
                        }
                    }
                }
            }
        }
        item {
            AppCard {
                val billing = state.billing
                SectionHeader("套餐与额度", if (billing?.paymentConfigured == true) "支付通道已配置。" else "支付通道未接入；创建订单不会发生真实扣款。")
                Text("${billing?.credits ?: 0} 次可用", color = PrimaryBlue, fontSize = 28.sp, fontWeight = FontWeight.Black)
                billing?.plans?.forEach { plan ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column { Text(plan.name, color = Ink, fontWeight = FontWeight.Bold); Text("${plan.credits} 次 · ¥${"%.2f".format(plan.priceCents / 100.0)}", color = Muted, fontSize = 13.sp) }
                        OutlinedButton(onClick = { viewModel.createOrder(plan.code) }, shape = RoundedCornerShape(14.dp)) { Text("创建订单") }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(12.dp)) }
    }
}

@Composable
private fun AccountScreen(state: UiState, viewModel: MainViewModel) {
    var dialog by remember { mutableStateOf<String?>(null) }
    val accountAvatarLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let(viewModel::uploadAccountAvatar)
    }
    LazyColumn(
        Modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item { PageTitle("我的", "账号安全放到操作卡片里，平时页面保持清爽。") }
        item {
            AppCard {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    AvatarBubble(state.user?.username ?: "用", state.userAvatarUrl)
                    Column(Modifier.weight(1f)) {
                        Text(state.user?.username ?: "用户", style = MaterialTheme.typography.titleLarge, color = Ink, fontWeight = FontWeight.Black)
                        Text("绑定手机：${maskPhone(state.user?.phone)}", color = Muted)
                    }
                    OutlinedButton(onClick = { accountAvatarLauncher.launch("image/*") }, shape = RoundedCornerShape(999.dp)) {
                        Text(if (state.user?.avatarKey == null) "设置头像" else "更换头像")
                    }
                }
            }
        }
        item {
            AppCard {
                SettingRow("职业中心", "审阅真实经历、追踪投递与查看套餐额度") { viewModel.switchTab(AppTab.Career) }
                SettingRow("修改密码", "定期更新，保护账号安全") { dialog = "password" }
                SettingRow("更换手机号", "用于短信验证和找回密码") { dialog = "phone" }
                SettingRow("检查版本更新", "当前版本 ${BuildConfig.VERSION_NAME}") { viewModel.checkAppVersion() }
                SettingRow("注销账号", "永久删除账号和资料") { dialog = "delete" }
                Button(onClick = viewModel::logout, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp)) { Text("退出登录") }
            }
        }
    }
    when (dialog) {
        "password" -> ChangePasswordDialog(onDismiss = { dialog = null }, viewModel = viewModel)
        "phone" -> ChangePhoneDialog(onDismiss = { dialog = null }, viewModel = viewModel)
        "delete" -> DeleteAccountDialog(
            username = state.user?.username.orEmpty(),
            onDismiss = { dialog = null },
            viewModel = viewModel,
        )
    }
}

@Composable
private fun UpdateDialog(
    info: AppUpdateInfo,
    downloading: Boolean,
    progress: Float,
    error: String?,
    onUpdate: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = { if (!downloading) onDismiss() },
        title = { Text("发现新版本 ${info.latestVersionName}") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("当前版本 ${BuildConfig.VERSION_NAME}，最新版本 ${info.latestVersionName}。", color = Muted)
                Text("你可以现在在线更新，也可以先关闭提示，之后到“我的 - 检查版本更新”里自己更新。", color = Muted, lineHeight = 20.sp)
                info.releaseNotes.take(4).forEach { note ->
                    Text("· $note", color = Ink, lineHeight = 20.sp)
                }
                if (downloading) {
                    LinearProgressIndicator(
                        progress = { progress.coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text("${(progress.coerceIn(0f, 1f) * 100).toInt()}%", color = Muted, fontSize = 13.sp)
                }
                error?.let { Text(it, color = Color(0xFFB42318), fontSize = 12.sp, lineHeight = 18.sp) }
            }
        },
        confirmButton = {
            Button(onClick = onUpdate, enabled = !downloading) {
                Text(if (downloading) "下载中" else "现在更新")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !downloading) { Text("稍后再说") }
        },
    )
}

@Composable
private fun ChangePasswordDialog(onDismiss: () -> Unit, viewModel: MainViewModel) {
    var current by remember { mutableStateOf("") }
    var next by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("修改密码") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                PasswordField("当前密码", current) { current = it }
                PasswordField("新密码", next) { next = it }
            }
        },
        confirmButton = {
            Button(onClick = {
                viewModel.changePassword(current, next)
                onDismiss()
            }) { Text("保存") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@Composable
private fun ChangePhoneDialog(onDismiss: () -> Unit, viewModel: MainViewModel) {
    var phone by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("更换手机号") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                AppTextField("新手机号", phone) { phone = it }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.weight(1f)) { AppTextField("验证码", code) { code = it } }
                    OutlinedButton(onClick = { viewModel.sendSms(phone, "change_phone") }) { Text("发送") }
                }
            }
        },
        confirmButton = {
            Button(onClick = {
                viewModel.changePhone(phone, code)
                onDismiss()
            }) { Text("保存") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@Composable
private fun DeleteAccountDialog(username: String, onDismiss: () -> Unit, viewModel: MainViewModel) {
    var password by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("注销账号") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("这个操作会永久删除账号、简历和生成记录。请输入用户名确认：$username", color = Color(0xFFB42318))
                AppTextField("确认用户名", confirm) { confirm = it }
                PasswordField("当前密码", password) { password = it }
            }
        },
        confirmButton = {
            Button(onClick = {
                viewModel.deleteAccount(password, confirm)
                onDismiss()
            }) { Text("确认注销") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@Composable
private fun BottomNav(tab: AppTab, onTab: (AppTab) -> Unit) {
    Surface(color = Color.White, shadowElevation = 4.dp) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 7.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            NavPill("简历", "简", tab == AppTab.Resumes, Modifier.weight(1f)) { onTab(AppTab.Resumes) }
            NavPill("雷达", "雷", tab == AppTab.Radar, Modifier.weight(1f)) { onTab(AppTab.Radar) }
            NavPill("适配", "岗", tab == AppTab.Match, Modifier.weight(1f)) { onTab(AppTab.Match) }
            NavPill("记录", "记", tab == AppTab.Generations, Modifier.weight(1f)) { onTab(AppTab.Generations) }
            NavPill("我的", "我", tab == AppTab.Account, Modifier.weight(1f)) { onTab(AppTab.Account) }
        }
    }
}

@Composable
private fun NavPill(label: String, icon: String, selected: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(14.dp)).background(if (selected) Lavender else Color.Transparent).clickable(onClick = onClick).padding(vertical = 7.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(icon, color = if (selected) PrimaryBlue else Color(0xFF4B4E61), fontSize = 17.sp, fontWeight = FontWeight.Black)
        Text(label, color = if (selected) PrimaryBlue else Color(0xFF4B4E61), fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun AppCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

@Composable
private fun HeroCard(title: String, subtitle: String, kicker: String) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Ink)
            .padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(kicker, color = Color.White.copy(alpha = .72f), fontWeight = FontWeight.Bold, fontSize = 12.sp)
        Text(title, color = Color.White, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Black)
        Text(subtitle, color = Color.White.copy(alpha = .86f), lineHeight = 21.sp)
    }
}

@Composable
private fun PageTitle(title: String, subtitle: String) {
    Column(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 2.dp)) {
        Text(title, color = Ink, fontSize = 28.sp, lineHeight = 34.sp, fontWeight = FontWeight.ExtraBold)
        Text(subtitle, color = Muted, fontSize = 15.sp, lineHeight = 22.sp)
    }
}

@Composable
private fun SectionHeader(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(title, color = Ink, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
        Text(subtitle, color = Muted, fontSize = 13.sp)
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(text, color = Ink, fontWeight = FontWeight.Black, modifier = Modifier.padding(top = 4.dp, start = 4.dp))
}

@Composable
private fun AppTextField(label: String, value: String, minLines: Int = 1, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        modifier = Modifier.fillMaxWidth(),
        minLines = minLines,
        singleLine = minLines == 1,
        shape = RoundedCornerShape(16.dp),
    )
}

@Composable
private fun PasswordField(label: String, value: String, onChange: (String) -> Unit) {
    var visible by remember { mutableStateOf(false) }
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        trailingIcon = {
            TextButton(onClick = { visible = !visible }) {
                Text(if (visible) "隐藏" else "显示")
            }
        },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        shape = RoundedCornerShape(16.dp),
    )
}

@Composable
private fun SegmentRow(options: List<Pair<String, String>>, selected: String, onSelected: (String) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(Color(0xFFF1F3FA))
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        options.forEach { (value, label) ->
            val active = selected == value
            Box(
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(14.dp))
                    .background(if (active) Color.White else Color.Transparent)
                    .clickable { onSelected(value) }
                    .padding(vertical = 10.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(label, color = if (active) PrimaryBlue else Muted, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun ThemeStrip(selected: String, onSelected: (String) -> Unit) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        items(designThemes, key = { it.code }) { theme ->
            ChoiceChip(theme.label, selected == theme.code) { onSelected(theme.code) }
        }
    }
}

@Composable
private fun ChoiceChip(text: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(if (selected) PrimaryBlue else Color.White)
            .border(1.dp, if (selected) PrimaryBlue else SoftLine, RoundedCornerShape(999.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
    ) {
        Text(text, color = if (selected) Color.White else PrimaryBlue, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun SmallBadge(text: String) {
    Text(
        text,
        color = PrimaryBlue,
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Lavender)
            .padding(horizontal = 8.dp, vertical = 4.dp),
    )
}

@Composable
private fun AvatarBubble(text: String, imageUrl: String? = null) {
    Box(
        Modifier
            .size(48.dp)
            .clip(CircleShape)
            .background(PrimaryBlue),
        contentAlignment = Alignment.Center,
    ) {
        if (!imageUrl.isNullOrBlank()) {
            AsyncImage(
                model = imageUrl,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            Text(text.take(1).ifBlank { "职" }, color = Color.White, fontWeight = FontWeight.Black, fontSize = 20.sp)
        }
    }
}

@Composable
private fun SettingRow(title: String, subtitle: String, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = Ink, fontWeight = FontWeight.Black)
            Text(subtitle, color = Muted, fontSize = 13.sp)
        }
        Text("›", color = Muted, fontSize = 26.sp, fontWeight = FontWeight.Light)
    }
}

@Composable
private fun EmptyHint(text: String) {
    AppCard {
        Text(text, color = Muted, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun KeywordText(jd: JSONObject) {
    val keywords = jd.optJSONArray("keywords")?.let { array ->
        List(array.length()) { array.optString(it) }.filter { it.isNotBlank() }
    }.orEmpty()
    if (keywords.isNotEmpty()) {
        Text(keywords.take(12).joinToString("、"), color = Muted, lineHeight = 21.sp)
    }
}

@Composable
private fun LoadingOverlay() {
    Surface(color = Color.Black.copy(alpha = 0.18f), modifier = Modifier.fillMaxSize()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Card(shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(modifier = Modifier.size(28.dp))
                    Spacer(Modifier.width(12.dp))
                    Text("处理中…", color = Ink, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun LegalDialog(title: String, content: String, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title, fontWeight = FontWeight.Bold, color = Ink) },
        text = { Text(content, fontSize = 14.sp, lineHeight = 22.sp, color = InkSoft) },
        confirmButton = { TextButton(onClick = onDismiss) { Text("关闭", color = Accent) } },
        containerColor = Color.White,
        shape = RoundedCornerShape(20.dp),
    )
}

private val LEGAL_TERMS = """用户服务协议
1. 本协议是用户与职达简历平台之间关于使用AI简历优化、岗位适配服务的法律协议。
2. 注册即表示你已阅读、理解并同意受本协议约束。
3. 用户须提供真实有效的手机号完成注册，妥善保管账号安全。
4. 禁止利用本平台生成或编造虚假履历、伪造身份文件。
5. 本平台软件代码、UI界面设计、商标标识及AI算法的知识产权归平台所有。
"""

private val LEGAL_PRIVACY = """隐私保护政策
1. 我们收集的信息：手机号、用户名、登录凭证、职业履历资料、使用偏好与操作日志。
2. 信息仅用于：AI简历润色与格式导出、岗位智能匹配、账号安全风控、产品优化。
3. 采用 TLS/SSL 加密传输，简历数据存储于云端高安全级别加密集群中。
4. 未经你的明确授权，绝不会将你的隐私信息出售或共享给第三方广告商。
5. 你随时有权在工作台中查看、修改或删除简历数据。若需销毁账号，可提交申请。
"""

private val LEGAL_DISCLAIMER = """免责与备案声明
1. AI生成的简历诊断、描述优化与岗位匹配度仅供求职参考，投递前请务必核对内容准确性。
2. 平台不承诺或保证使用本服务后必然获得特定面试机会、求职成功率或薪资水平。
3. 因电信网络故障、黑客攻击、维护或不可抗力导致的服务中断，平台不承担衍生损害赔偿责任。
4. 本平台严格遵守《网络安全法》等法律法规，已完成工信部全国互联网安全管理备案。
"""

private fun lines(text: String): List<String> = text.split("\n").map { it.trim() }.filter { it.isNotBlank() }

private fun statusLabel(status: String): String = when (status) {
    "processing" -> "处理中"
    "completed" -> "已完成"
    "failed" -> "失败"
    else -> status
}

private fun sourceLabel(source: String): String = when (source) {
    "url" -> "链接"
    "text" -> "文本"
    "image" -> "截图"
    else -> source
}

private fun feedbackLabel(action: String): String = when (action) {
    "saved" -> "已收藏"
    "applied" -> "已投递"
    "viewed" -> "已查看"
    else -> action
}

private fun maskPhone(phone: String?): String {
    if (phone.isNullOrBlank()) return "未绑定"
    return if (phone.length >= 7) "${phone.take(3)}****${phone.takeLast(4)}" else phone
}
