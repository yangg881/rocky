package com.zhiday.resume

import android.app.Activity
import android.content.Intent
import android.net.Uri
import java.io.File
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ArrowForwardIos
import androidx.compose.material.icons.outlined.AssignmentTurnedIn
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.Block
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.Business
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.FactCheck
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Image
import androidx.compose.material.icons.outlined.InsertDriveFile
import androidx.compose.material.icons.outlined.Link
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Logout
import androidx.compose.material.icons.outlined.MoreVert
import androidx.compose.material.icons.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Palette
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.PhoneAndroid
import androidx.compose.material.icons.outlined.PhotoLibrary
import androidx.compose.material.icons.outlined.PictureAsPdf
import androidx.compose.material.icons.outlined.Radar
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Send
import androidx.compose.material.icons.outlined.Star
import androidx.compose.material.icons.outlined.SystemUpdate
import androidx.compose.material.icons.outlined.TextSnippet
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material.icons.outlined.UploadFile
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.Work
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import org.json.JSONObject

private val WorkspaceBg = Color(0xFFF8F9FC)
private val WorkspaceInk = Color(0xFF171C2A)
private val WorkspaceMuted = Color(0xFF667085)
private val WorkspaceLine = Color(0xFFE4E7EC)
private val WorkspaceBlue = Color(0xFF2F56B3)
private val WorkspaceBlueDark = Color(0xFF24469A)
private val WorkspaceBlueSoft = Color(0xFFEEF3FF)
private val WorkspaceDanger = Color(0xFFB42318)
private val WorkspaceSuccess = Color(0xFF067647)
private val WorkspaceWarning = Color(0xFFB54708)

@Composable
internal fun WorkspaceScreen(state: UiState, viewModel: MainViewModel) {
    Column(Modifier.fillMaxSize().background(WorkspaceBg)) {
        ProcessingBanner(state)
        when (state.tab) {
            AppTab.Resumes -> WorkspaceResumeScreen(state, viewModel)
            AppTab.Radar -> WorkspaceRadarScreen(state, viewModel)
            AppTab.Match -> WorkspaceMatchScreen(state, viewModel)
            AppTab.Generations -> WorkspaceGenerationScreen(state, viewModel)
            AppTab.Career -> WorkspaceCareerScreen(state, viewModel)
            AppTab.Account -> WorkspaceAccountScreen(state, viewModel)
        }
    }
}

@Composable
private fun ProcessingBanner(state: UiState) {
    val jdCount = state.jdTasks.count { it.status == "processing" }
    val generationCount = state.generations.count { it.status == "processing" }
    if (jdCount + generationCount == 0) return
    Row(
        Modifier.fillMaxWidth().background(WorkspaceBlueSoft).padding(horizontal = 18.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        LinearProgressIndicator(modifier = Modifier.width(36.dp), color = WorkspaceBlue, trackColor = Color.White)
        Text(
            listOfNotNull(
                jdCount.takeIf { it > 0 }?.let { "$it 个岗位正在解析" },
                generationCount.takeIf { it > 0 }?.let { "$it 份简历正在生成" },
            ).joinToString(" · "),
            color = WorkspaceBlueDark,
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(Modifier.weight(1f))
        Text("可离开页面", color = WorkspaceMuted, fontSize = 11.sp)
    }
}

@Composable
internal fun WorkspaceBottomBar(tab: AppTab, onTab: (AppTab) -> Unit) {
    Surface(color = Color.White, shadowElevation = 7.dp) {
        Row(
            Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 8.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            WorkspaceNavItem("简历优化", Icons.Outlined.AutoAwesome, tab == AppTab.Resumes || tab == AppTab.Match, Modifier.weight(1f)) { onTab(AppTab.Resumes) }
            WorkspaceNavItem("岗位雷达", Icons.Outlined.Radar, tab == AppTab.Radar, Modifier.weight(1f)) { onTab(AppTab.Radar) }
            WorkspaceNavItem("记录", Icons.Outlined.History, tab == AppTab.Generations, Modifier.weight(1f)) { onTab(AppTab.Generations) }
            WorkspaceNavItem("我的", Icons.Outlined.Person, tab == AppTab.Account || tab == AppTab.Career, Modifier.weight(1f)) { onTab(AppTab.Account) }
        }
    }
}

@Composable
private fun WorkspaceNavItem(label: String, icon: ImageVector, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(15.dp))
            .background(if (selected) WorkspaceBlueSoft else Color.Transparent)
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Icon(icon, label, tint = if (selected) WorkspaceBlue else WorkspaceMuted, modifier = Modifier.size(22.dp))
        Text(label, color = if (selected) WorkspaceBlue else WorkspaceMuted, fontSize = 11.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium)
    }
}

@Composable
private fun WorkspaceHeader(title: String, subtitle: String? = null, actionIcon: ImageVector? = null, actionLabel: String = "", onAction: (() -> Unit)? = null) {
    Row(
        Modifier.fillMaxWidth().statusBarsPadding().padding(start = 18.dp, end = 12.dp, top = 12.dp, bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = WorkspaceInk, fontSize = 24.sp, lineHeight = 30.sp, fontWeight = FontWeight.ExtraBold)
            subtitle?.let { Text(it, color = WorkspaceMuted, fontSize = 13.sp, lineHeight = 18.sp) }
        }
        if (actionIcon != null && onAction != null) {
            IconButton(onClick = onAction) { Icon(actionIcon, actionLabel, tint = WorkspaceInk) }
        }
    }
}

@Composable
private fun WorkspaceCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = BorderStroke(1.dp, WorkspaceLine.copy(alpha = .75f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(11.dp), content = content)
    }
}

@Composable
private fun WorkspaceSectionTitle(title: String, subtitle: String? = null, trailing: String? = null, onTrailing: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, color = WorkspaceInk, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
            subtitle?.let { Text(it, color = WorkspaceMuted, fontSize = 12.sp, lineHeight = 17.sp) }
        }
        if (trailing != null && onTrailing != null) TextButton(onClick = onTrailing) { Text(trailing, color = WorkspaceMuted) }
    }
}

@Composable
private fun WorkspaceBadge(text: String, tone: String = "blue") {
    val color = when (tone) {
        "success" -> WorkspaceSuccess
        "danger" -> WorkspaceDanger
        "warning" -> WorkspaceWarning
        else -> WorkspaceBlue
    }
    Text(
        text,
        color = color,
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier.clip(RoundedCornerShape(99.dp)).background(color.copy(alpha = .09f)).padding(horizontal = 8.dp, vertical = 4.dp),
    )
}

@Composable
private fun WorkspacePrimaryButton(text: String, icon: ImageVector? = null, enabled: Boolean = true, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(15.dp),
        colors = ButtonDefaults.buttonColors(containerColor = WorkspaceBlue, disabledContainerColor = WorkspaceLine),
    ) {
        if (icon != null) { Icon(icon, null, modifier = Modifier.size(19.dp)); Spacer(Modifier.width(8.dp)) }
        Text(text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun WorkspaceOutlinedButton(text: String, icon: ImageVector? = null, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.height(44.dp),
        shape = RoundedCornerShape(13.dp),
        border = BorderStroke(1.dp, WorkspaceLine),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = WorkspaceInk),
    ) {
        if (icon != null) { Icon(icon, null, modifier = Modifier.size(17.dp)); Spacer(Modifier.width(6.dp)) }
        Text(text, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun WorkspaceOriginalApplyButton(onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(15.dp),
        border = BorderStroke(1.5.dp, WorkspaceBlue),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = WorkspaceBlue),
    ) {
        Icon(Icons.Outlined.OpenInNew, null, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(9.dp))
        Text("查看原岗位并投递", fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun WorkspaceField(label: String, value: String, minLines: Int = 1, keyboardType: KeyboardType = KeyboardType.Text, leading: ImageVector? = null, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        leadingIcon = leading?.let { { Icon(it, null, modifier = Modifier.size(20.dp)) } },
        minLines = minLines,
        singleLine = minLines == 1,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = WorkspaceBlue,
            unfocusedBorderColor = WorkspaceLine,
            focusedContainerColor = Color.White,
            unfocusedContainerColor = Color.White,
        ),
    )
}

@Composable
private fun WorkspaceEmpty(icon: ImageVector, title: String, detail: String, action: String? = null, onAction: (() -> Unit)? = null) {
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 28.dp, vertical = 36.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(9.dp),
    ) {
        Box(Modifier.size(56.dp).clip(CircleShape).background(WorkspaceBlueSoft), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = WorkspaceBlue, modifier = Modifier.size(27.dp))
        }
        Text(title, color = WorkspaceInk, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Text(detail, color = WorkspaceMuted, fontSize = 13.sp, textAlign = TextAlign.Center, lineHeight = 19.sp)
        if (action != null && onAction != null) TextButton(onClick = onAction) { Text(action) }
    }
}

@Composable
private fun WorkspaceAvatar(text: String, url: String? = null, size: Int = 48) {
    Box(
        Modifier.size(size.dp).clip(CircleShape).background(Brush.linearGradient(listOf(WorkspaceBlue, Color(0xFF5578D1)))),
        contentAlignment = Alignment.Center,
    ) {
        if (url.isNullOrBlank()) Text(text.take(1).ifBlank { "职" }, color = Color.White, fontSize = (size * .38).sp, fontWeight = FontWeight.ExtraBold)
        else AsyncImage(model = url, contentDescription = "头像", contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
    }
}

private fun workspaceStatusLabel(status: String): String = when (status) {
    "processing" -> "处理中"
    "completed" -> "已完成"
    "failed" -> "失败"
    "cancelled" -> "已取消"
    else -> status.ifBlank { "等待处理" }
}

private fun workspaceStatusTone(status: String): String = when (status) {
    "completed" -> "success"
    "failed", "cancelled" -> "danger"
    "processing" -> "warning"
    else -> "blue"
}

private fun workspaceLines(value: String): List<String> = value.lineSequence().map { it.trim() }.filter { it.isNotBlank() }.toList()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WorkspaceResumeScreen(state: UiState, viewModel: MainViewModel) {
    var showCreateSheet by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<ResumeItem?>(null) }
    var previewing by remember { mutableStateOf<ResumeItem?>(null) }
    var actionResume by remember { mutableStateOf<ResumeItem?>(null) }
    var avatarTarget by remember { mutableStateOf<String?>(null) }
    val context = LocalContext.current
    val documentLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { it?.let(viewModel::uploadResumeDocument) }
    val imageLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { it?.let(viewModel::ocrResumeImage) }
    val cropLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val path = result.data?.getStringExtra(CropAvatarActivity.EXTRA_CROPPED_PATH)
        val target = avatarTarget
        if (result.resultCode == Activity.RESULT_OK && target != null && !path.isNullOrBlank()) viewModel.uploadAvatar(target, Uri.fromFile(File(path)))
        avatarTarget = null
    }
    val avatarLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null && avatarTarget != null) cropLauncher.launch(Intent(context, CropAvatarActivity::class.java).putExtra(CropAvatarActivity.EXTRA_SOURCE_URI, uri.toString()))
    }
    val current = state.resumes.firstOrNull { it.id == state.selectedResumeId }
        ?: state.resumes.firstOrNull { it.isDefault }
        ?: state.resumes.firstOrNull()

    Column(Modifier.fillMaxSize()) {
        WorkspaceHeader("简历优化", "一份基础简历，按不同岗位生成更有针对性的版本", Icons.Outlined.Add, "添加简历") { showCreateSheet = true }
        LazyColumn(
            Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (current != null) {
                item {
                    CurrentResumeCard(
                        current,
                        onEdit = { editing = current },
                        onPreview = { previewing = current },
                    )
                }
            }
            item {
                WorkspacePrimaryButton("从岗位雷达开始优化", Icons.Outlined.Radar) { viewModel.switchTab(AppTab.Radar) }
            }
            item {
                WorkspaceOutlinedButton("手动提交岗位信息", Icons.Outlined.Link, Modifier.fillMaxWidth()) { viewModel.switchTab(AppTab.Match) }
            }
            item { WorkspaceSectionTitle("我的基础简历", "${state.resumes.size} 个版本", "添加") { showCreateSheet = true } }
            items(state.resumes, key = { it.id }) { resume ->
                ResumeListRow(
                    resume = resume,
                    selected = resume.id == current?.id,
                    onSelect = { viewModel.selectResume(resume.id) },
                    onMore = { actionResume = resume },
                )
            }
            if (state.resumes.isEmpty() && !state.loading) {
                item { WorkspaceEmpty(Icons.Outlined.Description, "还没有基础简历", "上传 Word、PDF 或在线创建一份，之后就能开始岗位适配。", "立即创建") { showCreateSheet = true } }
            }
            item { Spacer(Modifier.height(10.dp)) }
        }
    }

    if (showCreateSheet) {
        ModalBottomSheet(onDismissRequest = { showCreateSheet = false }, containerColor = Color.White) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                WorkspaceSectionTitle("添加基础简历", "选择最方便的方式，导入后仍可继续编辑")
                SheetAction(Icons.Outlined.UploadFile, "上传 Word / PDF", "保留原文件，并自动整理为结构化内容") { showCreateSheet = false; documentLauncher.launch("*/*") }
                SheetAction(Icons.Outlined.PhotoLibrary, "上传简历图片", "识别截图或扫描件，可继续人工校对") { showCreateSheet = false; imageLauncher.launch("image/*") }
                SheetAction(Icons.Outlined.Edit, "在线新建", "从空白资料开始填写") { showCreateSheet = false; editing = ResumeItem("", "", false, "", null, null, null, ResumeContent()) }
            }
        }
    }
    editing?.let { item ->
        ResumeEditorSheet(item.takeIf { it.id.isNotBlank() }, onDismiss = { editing = null }) { version, content ->
            viewModel.saveResume(item.id.takeIf { it.isNotBlank() }, version, content)
            editing = null
        }
    }
    previewing?.let { ResumeContentDialog(it, onDismiss = { previewing = null }) }
    actionResume?.let { resume ->
        ModalBottomSheet(onDismissRequest = { actionResume = null }, containerColor = Color.White) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                WorkspaceSectionTitle(resume.name, "管理这份基础简历")
                SheetAction(Icons.Outlined.Visibility, "查看整理内容", "查看系统识别后的完整资料") { actionResume = null; previewing = resume }
                if (resume.sourceKey != null) {
                    SheetAction(Icons.Outlined.InsertDriveFile, "查看原文件", "按上传时的原始格式打开") { actionResume = null; viewModel.openOriginalResume(resume) }
                    SheetAction(Icons.Outlined.Download, "下载原文件", "保存到手机后使用其他应用打开") { actionResume = null; viewModel.downloadOriginalResume(resume) }
                }
                SheetAction(Icons.Outlined.Edit, "编辑资料", "补充或修正识别后的内容") { actionResume = null; editing = resume }
                SheetAction(Icons.Outlined.AccountCircle, if (resume.avatarKey == null) "设置简历头像" else "更换简历头像", "仅用于这份简历，不影响账号头像") {
                    actionResume = null; avatarTarget = resume.id; avatarLauncher.launch("image/*")
                }
                if (!resume.isDefault) SheetAction(Icons.Outlined.Star, "设为默认简历", "适配岗位时优先使用") { actionResume = null; viewModel.setDefault(resume.id) }
                SheetAction(Icons.Outlined.Delete, "删除这份简历", "删除后无法恢复", danger = true) { actionResume = null; viewModel.deleteResume(resume.id) }
            }
        }
    }
}

@Composable
private fun CurrentResumeCard(resume: ResumeItem, onEdit: () -> Unit, onPreview: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = WorkspaceBlueSoft),
        border = BorderStroke(1.dp, Color(0xFFD8E3FF)),
    ) {
        Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                WorkspaceAvatar(resume.content.name.ifBlank { resume.name }, size = 54)
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                        Text(resume.content.name.ifBlank { resume.name }, color = WorkspaceInk, fontSize = 19.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        WorkspaceBadge("当前使用")
                    }
                    Text(resume.content.title.ifBlank { "未填写求职方向" }, color = WorkspaceMuted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(listOf(resume.name, resume.content.age.takeIf { it.isNotBlank() }?.let { "$it 岁" }).filterNotNull().joinToString(" · "), color = WorkspaceMuted, fontSize = 12.sp)
                }
                Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(16.dp))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                WorkspaceOutlinedButton("查看内容", Icons.Outlined.Visibility, Modifier.weight(1f), onClick = onPreview)
                WorkspaceOutlinedButton("编辑资料", Icons.Outlined.Edit, Modifier.weight(1f), onClick = onEdit)
            }
        }
    }
}

@Composable
private fun QuickAction(icon: ImageVector, title: String, subtitle: String, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(16.dp)).background(Color.White).clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 13.dp),
        verticalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Icon(icon, null, tint = WorkspaceBlue, modifier = Modifier.size(23.dp))
        Text(title, color = WorkspaceInk, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = WorkspaceMuted, fontSize = 10.sp)
    }
}

@Composable
private fun ResumeListRow(resume: ResumeItem, selected: Boolean, onSelect: () -> Unit, onMore: () -> Unit) {
    WorkspaceCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(11.dp)) {
            WorkspaceAvatar(resume.content.name.ifBlank { resume.name }, size = 44)
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(resume.name, color = WorkspaceInk, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (resume.isDefault) WorkspaceBadge("默认")
                }
                Text(listOf(resume.content.name, resume.content.title).filter { it.isNotBlank() }.joinToString(" · ").ifBlank { "资料待完善" }, color = WorkspaceMuted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("更新于 ${resume.updatedAt.take(10).ifBlank { "未知时间" }}", color = WorkspaceMuted, fontSize = 11.sp)
            }
            if (!selected) TextButton(onClick = onSelect) { Text("选用") } else Icon(Icons.Outlined.CheckCircle, "已选", tint = WorkspaceBlue)
            IconButton(onClick = onMore) { Icon(Icons.Outlined.MoreVert, "更多") }
        }
    }
}

@Composable
private fun SheetAction(icon: ImageVector, title: String, subtitle: String, danger: Boolean = false, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable(onClick = onClick).padding(vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(13.dp),
    ) {
        Box(Modifier.size(42.dp).clip(CircleShape).background((if (danger) WorkspaceDanger else WorkspaceBlue).copy(alpha = .08f)), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = if (danger) WorkspaceDanger else WorkspaceBlue, modifier = Modifier.size(21.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, color = if (danger) WorkspaceDanger else WorkspaceInk, fontWeight = FontWeight.Bold)
            Text(subtitle, color = WorkspaceMuted, fontSize = 12.sp, lineHeight = 17.sp)
        }
        Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(14.dp))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ResumeEditorSheet(item: ResumeItem?, onDismiss: () -> Unit, onSave: (String, ResumeContent) -> Unit) {
    val original = item?.content ?: ResumeContent()
    var version by remember(item?.id) { mutableStateOf(item?.name.orEmpty()) }
    var name by remember(item?.id) { mutableStateOf(original.name) }
    var age by remember(item?.id) { mutableStateOf(original.age) }
    var title by remember(item?.id) { mutableStateOf(original.title) }
    var phone by remember(item?.id) { mutableStateOf(original.phone) }
    var email by remember(item?.id) { mutableStateOf(original.email) }
    var summary by remember(item?.id) { mutableStateOf(original.summary) }
    var skills by remember(item?.id) { mutableStateOf(original.skills.joinToString("\n")) }
    var experience by remember(item?.id) { mutableStateOf(original.experience.joinToString("\n")) }
    var projects by remember(item?.id) { mutableStateOf(original.projects.joinToString("\n")) }
    var education by remember(item?.id) { mutableStateOf(original.education.joinToString("\n")) }
    var certificates by remember(item?.id) { mutableStateOf(original.certificates.joinToString("\n")) }
    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = WorkspaceBg) {
        Column(Modifier.fillMaxHeight(.92f)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(if (item == null) "新建基础简历" else "编辑基础简历", color = WorkspaceInk, fontSize = 21.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.weight(1f))
                IconButton(onClick = onDismiss) { Icon(Icons.Outlined.Close, "关闭") }
            }
            LazyColumn(Modifier.weight(1f).padding(horizontal = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                item { WorkspaceField("版本名称", version) { version = it } }
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                        Box(Modifier.weight(1f)) { WorkspaceField("姓名", name) { name = it } }
                        Box(Modifier.width(102.dp)) { WorkspaceField("年龄", age, keyboardType = KeyboardType.Number) { age = it } }
                    }
                }
                item { WorkspaceField("当前职位或求职方向", title) { title = it } }
                item { WorkspaceField("手机号", phone, keyboardType = KeyboardType.Phone) { phone = it } }
                item { WorkspaceField("邮箱", email, keyboardType = KeyboardType.Email) { email = it } }
                item { WorkspaceField("经验与能力概述", summary, minLines = 3) { summary = it } }
                item { WorkspaceField("经验技能（一行一条）", skills, minLines = 3) { skills = it } }
                item { WorkspaceField("工作经历（一段一行，保留时间）", experience, minLines = 5) { experience = it } }
                item { WorkspaceField("项目经历", projects, minLines = 4) { projects = it } }
                item { WorkspaceField("教育经历", education, minLines = 3) { education = it } }
                item { WorkspaceField("证书与荣誉", certificates, minLines = 3) { certificates = it } }
                item { Spacer(Modifier.height(8.dp)) }
            }
            Surface(color = Color.White, shadowElevation = 5.dp) {
                WorkspacePrimaryButton("保存到简历库", Icons.Outlined.Check, enabled = name.isNotBlank() || version.isNotBlank(), modifier = Modifier.padding(16.dp)) {
                    onSave(
                        version.ifBlank { name.ifBlank { "在线简历" } },
                        ResumeContent(name, title, age, phone, email, summary, workspaceLines(skills), workspaceLines(experience), workspaceLines(projects), workspaceLines(education), workspaceLines(certificates)),
                    )
                }
            }
        }
    }
}

@Composable
private fun ResumeContentDialog(item: ResumeItem, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("${item.name} · 整理内容", fontWeight = FontWeight.ExtraBold) },
        text = {
            LazyColumn(Modifier.heightIn(max = 560.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                item { ResumePreviewSection("个人信息", listOf(item.content.name, item.content.title, item.content.age.takeIf { it.isNotBlank() }?.let { "$it 岁" }, item.content.phone, item.content.email).filterNotNull().filter { it.isNotBlank() }) }
                if (item.content.summary.isNotBlank()) item { ResumePreviewSection("经验与能力概述", listOf(item.content.summary)) }
                if (item.content.skills.isNotEmpty()) item { ResumePreviewSection("经验技能", item.content.skills) }
                if (item.content.experience.isNotEmpty()) item { ResumePreviewSection("工作经历", item.content.experience) }
                if (item.content.projects.isNotEmpty()) item { ResumePreviewSection("项目经历", item.content.projects) }
                if (item.content.education.isNotEmpty()) item { ResumePreviewSection("教育经历", item.content.education) }
                if (item.content.certificates.isNotEmpty()) item { ResumePreviewSection("证书荣誉", item.content.certificates) }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("关闭") } },
    )
}

@Composable
private fun ResumePreviewSection(title: String, values: List<String>) {
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(title, color = WorkspaceInk, fontWeight = FontWeight.Bold)
        values.forEach { Text(it, color = WorkspaceMuted, fontSize = 13.sp, lineHeight = 19.sp) }
        HorizontalDivider(color = WorkspaceLine)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WorkspaceRadarScreen(state: UiState, viewModel: MainViewModel) {
    var query by remember(state.radarQuery) { mutableStateOf(state.radarQuery) }
    var showFilters by remember { mutableStateOf(false) }
    var selectedJob by remember { mutableStateOf<RadarJob?>(null) }
    var showJumpDialog by remember { mutableStateOf(false) }
    var jumpPageText by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize()) {
        WorkspaceHeader("岗位雷达", "按匹配度发现更适合你的机会", Icons.Outlined.Refresh, "刷新") { viewModel.loadRadar() }
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                placeholder = { Text("搜索岗位或公司", fontSize = 13.sp) },
                leadingIcon = { Icon(Icons.Outlined.Search, null) },
                trailingIcon = if (query.isNotBlank()) ({ IconButton(onClick = { query = "" }) { Icon(Icons.Outlined.Close, "清空") } }) else null,
                singleLine = true,
                modifier = Modifier.weight(1f).height(52.dp),
                shape = RoundedCornerShape(15.dp),
                colors = OutlinedTextFieldDefaults.colors(unfocusedBorderColor = WorkspaceLine, focusedBorderColor = WorkspaceBlue, unfocusedContainerColor = Color.White, focusedContainerColor = Color.White),
            )
            IconButton(onClick = { viewModel.updateRadarFilters(query, state.radarCity, state.radarPublishedWithin, source = state.radarSource) }, modifier = Modifier.size(46.dp).clip(RoundedCornerShape(14.dp)).background(WorkspaceBlue)) {
                Icon(Icons.Outlined.Search, "搜索", tint = Color.White)
            }
            IconButton(onClick = { showFilters = true }, modifier = Modifier.size(46.dp).clip(RoundedCornerShape(14.dp)).background(Color.White)) {
                Icon(Icons.Outlined.Tune, "筛选", tint = if (state.radarCity.isNotBlank() || state.radarPublishedWithin != "30d" || state.radarSource.isNotBlank()) WorkspaceBlue else WorkspaceInk)
            }
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RadarStat("可推荐", state.radarSummary.availableJobs, Modifier.weight(1f))
            RadarStat("已收藏", state.radarSummary.saved, Modifier.weight(1f), selected = state.radarSavedOnly) { viewModel.toggleSavedRadar() }
            RadarStat("已投递", state.radarSummary.applied, Modifier.weight(1f))
        }
        RadarSearchFeedback(
            shownTotal = state.radarPagination.total,
            matchedTotal = state.radarPagination.matchedTotal,
            isLimited = state.radarPagination.isLimited,
            page = state.radarPagination.page,
            totalPages = state.radarPagination.totalPages,
            query = if (state.radarSavedOnly) "已收藏岗位" else state.radarQuery,
            city = state.radarCity,
            publishedWithin = state.radarPublishedWithin,
        )
        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            items(state.radarJobs, key = { it.id }) { job ->
                RadarJobRow(job, onClick = { selectedJob = job; viewModel.loadRadarJobDetail(job) })
            }
            if (state.radarJobs.isEmpty() && !state.loading) {
                item { WorkspaceEmpty(Icons.Outlined.Radar, "暂时没有匹配岗位", "仅展示近 30 天发布的岗位；可调整城市、发布时间、岗位来源或搜索词。", "清空筛选") { query = ""; viewModel.updateRadarFilters("", "", "30d") } }
            }
            if (state.radarPagination.totalPages > 1) {
                item {
                    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                        TextButton(onClick = { viewModel.changeRadarPage(-1) }, enabled = state.radarPagination.page > 1) { Text("上一页") }
                        Surface(onClick = { jumpPageText = state.radarPagination.page.toString(); showJumpDialog = true }, shape = RoundedCornerShape(8.dp), color = WorkspaceBlueSoft, modifier = Modifier.padding(horizontal = 8.dp)) {
                            Text("第 ${state.radarPagination.page} / ${state.radarPagination.totalPages} 页 (点击跳转)", color = WorkspaceBlue, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp))
                        }
                        TextButton(onClick = { viewModel.changeRadarPage(1) }, enabled = state.radarPagination.page < state.radarPagination.totalPages) { Text("下一页") }
                    }
                }
            }
            item { Spacer(Modifier.height(8.dp)) }
        }
    }
    if (showJumpDialog) {
        AlertDialog(
            onDismissRequest = { showJumpDialog = false },
            title = { Text("跳转到指定页码", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("当前共 ${state.radarPagination.totalPages} 页，请输入要跳转的页码：", fontSize = 13.sp, color = WorkspaceMuted)
                    OutlinedTextField(
                        value = jumpPageText,
                        onValueChange = { jumpPageText = it.filter { char -> char.isDigit() } },
                        label = { Text("页码 (1~${state.radarPagination.totalPages})") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    showJumpDialog = false
                    val pageNum = jumpPageText.toIntOrNull()
                    if (pageNum != null) {
                        viewModel.jumpToRadarPage(pageNum)
                    }
                }) {
                    Text("确认跳转", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showJumpDialog = false }) { Text("取消") }
            }
        )
    }
    if (showFilters) {
        var city by remember(state.radarCity) { mutableStateOf(state.radarCity) }
        var published by remember(state.radarPublishedWithin) { mutableStateOf(state.radarPublishedWithin) }
        var source by remember(state.radarSource) { mutableStateOf(state.radarSource) }
        ModalBottomSheet(onDismissRequest = { showFilters = false }, containerColor = Color.White) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                WorkspaceSectionTitle("筛选岗位", "缩小范围，推荐结果会更准确")
                Text("岗位来源", color = WorkspaceInk, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("" to "不限", "gxrc" to "广西人才网", "51job" to "前程无忧", "liepin" to "猎聘网", "zhipin" to "BOSS直聘", "zhaopin" to "智联招聘").forEach { (valKey, label) ->
                        item { FilterChipButton(label, source == valKey) { source = valKey } }
                    }
                }
                Text("工作城市", color = WorkspaceInk, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    item { FilterChipButton("不限", city.isBlank()) { city = "" } }
                    items(state.radarCities) { item -> FilterChipButton(item, city == item) { city = item } }
                }
                Text("发布时间", color = WorkspaceInk, fontWeight = FontWeight.Bold)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("1d" to "1天内", "3d" to "3天内", "7d" to "7天内", "30d" to "30天内").forEach { (value, label) ->
                        FilterChipButton(label, published == value) { published = value }
                    }
                }
                WorkspacePrimaryButton("应用筛选", Icons.Outlined.Check) { showFilters = false; viewModel.updateRadarFilters(query, city, published, source = source) }
            }
        }
    }
    selectedJob?.let { selected ->
        val job = state.radarJobDetails[selected.id] ?: selected
        val context = LocalContext.current
        ModalBottomSheet(onDismissRequest = { selectedJob = null }, containerColor = WorkspaceBg) {
            LazyColumn(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
                item {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                        Column(Modifier.weight(1f)) {
                            Text(job.title, color = WorkspaceInk, fontSize = 22.sp, lineHeight = 28.sp, fontWeight = FontWeight.ExtraBold)
                            Text(job.company, color = WorkspaceMuted, fontSize = 14.sp)
                        }
                        WorkspaceBadge("匹配 ${job.matchScore}%", if (job.matchScore >= 75) "success" else "blue")
                    }
                }
                item { JobMeta(job) }
                if (job.matchReason.isNotBlank()) item { WorkspaceCard { Text("推荐理由", color = WorkspaceInk, fontWeight = FontWeight.Bold); Text(job.matchReason, color = WorkspaceMuted, lineHeight = 20.sp, fontSize = 13.sp) } }
                item {
                    if (state.radarJobDetailLoadingId == job.id) {
                        WorkspaceCard {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                LinearProgressIndicator(modifier = Modifier.width(42.dp), color = WorkspaceBlue, trackColor = WorkspaceBlueSoft)
                                Text("正在补齐原岗位发布页信息…", color = WorkspaceMuted, fontSize = 12.sp)
                            }
                        }
                    } else {
                        PublisherJobDetail(job)
                    }
                }
                if (job.sourceUrl.startsWith("https://") || job.sourceUrl.startsWith("http://")) {
                    item {
                        WorkspaceOriginalApplyButton {
                            runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(job.sourceUrl))) }
                        }
                    }
                }
                item {
                    WorkspacePrimaryButton(
                        if (job.adapted) "换模板重新生成" else "用此岗位优化简历",
                        Icons.Outlined.AutoAwesome,
                    ) { selectedJob = null; viewModel.optimizeRadarJob(job) }
                }
                if (job.adapted) {
                    item {
                        Text(
                            "已完成简历适配，可更换模板后再次生成",
                            color = WorkspaceMuted,
                            fontSize = 12.sp,
                            lineHeight = 17.sp,
                        )
                    }
                }
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        WorkspaceOutlinedButton(if (job.feedbackAction == "saved") "已收藏" else "收藏", Icons.Outlined.BookmarkBorder, Modifier.weight(1f), enabled = job.feedbackAction != "saved") { viewModel.radarFeedback(job, "saved") }
                        WorkspaceOutlinedButton("已投递", Icons.Outlined.Send, Modifier.weight(1f)) { viewModel.radarFeedback(job, "applied") }
                    }
                }
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        TextButton(onClick = { selectedJob = null; viewModel.radarFeedback(job, "not_interested") }, modifier = Modifier.weight(1f)) { Text("不感兴趣", color = WorkspaceMuted) }
                        TextButton(onClick = { selectedJob = null; viewModel.blockRadarCompany(job) }, modifier = Modifier.weight(1f)) { Text("不看该公司", color = WorkspaceDanger) }
                    }
                }
            }
        }
    }
}

@Composable
private fun PublisherJobDetail(job: RadarJob) {
    val fallback = linkedMapOf<String, String>()
    if (job.description.isNotBlank()) fallback["岗位职责与详情"] = job.description
    if (job.requirements.isNotEmpty()) fallback["任职要求"] = job.requirements.joinToString("\n")
    if (job.benefits.isNotEmpty()) fallback["职位福利"] = job.benefits.joinToString("\n")
    val sections = if (job.sourceSections.isNotEmpty()) job.sourceSections else fallback
    var selectedTitle by remember(job.id, sections.keys) { mutableStateOf(sections.keys.firstOrNull().orEmpty()) }
    WorkspaceCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("原岗位完整信息", color = WorkspaceInk, fontWeight = FontWeight.ExtraBold)
                Text(
                    if (job.sourceDetailStatus == "complete") "已按招聘原页采集；长内容可在框内上下滑动" else "当前展示已采集信息；原页暂未返回更多字段",
                    color = WorkspaceMuted,
                    fontSize = 11.sp,
                    lineHeight = 16.sp,
                )
            }
            if (job.sourceDetailStatus == "complete") WorkspaceBadge("原文优先", "success")
        }
        if (sections.isEmpty()) {
            Text("该岗位暂未提供可展示的详情，请直接打开原岗位页查看。", color = WorkspaceMuted, fontSize = 13.sp)
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                items(sections.keys.toList()) { title ->
                    FilterChipButton(title, selectedTitle == title) { selectedTitle = title }
                }
            }
            val text = sections[selectedTitle].orEmpty()
            Column(
                Modifier.fillMaxWidth().heightIn(min = 128.dp, max = 240.dp)
                    .clip(RoundedCornerShape(13.dp)).background(WorkspaceBg)
                    .verticalScroll(rememberScrollState()).padding(13.dp),
            ) {
                Text(text, color = WorkspaceMuted, fontSize = 13.sp, lineHeight = 20.sp)
            }
        }
    }
}

@Composable
private fun RadarSearchFeedback(
    shownTotal: Int,
    matchedTotal: Int,
    isLimited: Boolean,
    page: Int,
    totalPages: Int,
    query: String,
    city: String,
    publishedWithin: String,
) {
    val conditions = buildList {
        if (query.isNotBlank()) add("关键词：$query")
        if (city.isNotBlank()) add(city)
        when (publishedWithin) {
            "3d" -> add("近 3 天")
            "7d" -> add("近 7 天")
            "30d" -> add("近 30 天")
        }
    }
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 2.dp)
            .clip(RoundedCornerShape(14.dp)).background(WorkspaceBlueSoft).padding(horizontal = 14.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                if (isLimited) "匹配到 $matchedTotal 个岗位" else "为你找到 $matchedTotal 个合适岗位",
                color = WorkspaceInk,
                fontSize = 14.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            Text(
                buildList {
                    if (isLimited) add("已按匹配度展示前 $shownTotal 个")
                    addAll(conditions)
                }.joinToString(" · ").ifBlank { "基于你的简历与岗位匹配度排序" },
                color = WorkspaceMuted,
                fontSize = 11.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Text("$page / $totalPages 页", color = WorkspaceBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun RadarStat(label: String, value: Int, modifier: Modifier, selected: Boolean = false, onClick: (() -> Unit)? = null) {
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(if (selected) WorkspaceBlueSoft else Color.White).then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier).padding(horizontal = 12.dp, vertical = 9.dp)) {
        Text(value.toString(), color = WorkspaceInk, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
        Text(label, color = WorkspaceMuted, fontSize = 10.sp)
    }
}

@Composable
private fun RadarJobRow(job: RadarJob, onClick: () -> Unit) {
    WorkspaceCard(Modifier.clickable(onClick = onClick)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(job.title, color = WorkspaceInk, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(job.company, color = WorkspaceMuted, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                WorkspaceBadge("${job.matchScore}%", if (job.matchScore >= 75) "success" else "blue")
                if (job.adapted) WorkspaceBadge("简历已生成", "blue")
            }
        }
        JobMeta(job)
        if (job.matchReason.isNotBlank()) Text(job.matchReason, color = WorkspaceMuted, fontSize = 12.sp, maxLines = 2, overflow = TextOverflow.Ellipsis, lineHeight = 17.sp)
    }
}

@Composable
private fun JobMeta(job: RadarJob) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        if (job.salary.isNotBlank()) Text(job.salary, color = WorkspaceBlue, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        if (job.location.isNotBlank()) { Icon(Icons.Outlined.LocationOn, null, tint = WorkspaceMuted, modifier = Modifier.size(15.dp)); Text(job.location, color = WorkspaceMuted, fontSize = 12.sp) }
        if (job.experience.isNotBlank()) Text(job.experience, color = WorkspaceMuted, fontSize = 12.sp)
        if (job.publishedAt.isNotBlank()) Text("发布：${job.publishedAt.take(10)}", color = WorkspaceMuted, fontSize = 11.sp)
    }
}

@Composable
private fun FilterChipButton(text: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (selected) WorkspaceBlue else Color.White,
        contentColor = if (selected) Color.White else WorkspaceInk,
        shape = RoundedCornerShape(99.dp),
        border = BorderStroke(1.dp, if (selected) WorkspaceBlue else WorkspaceLine),
        modifier = Modifier.clickable(onClick = onClick),
    ) { Text(text, modifier = Modifier.padding(horizontal = 13.dp, vertical = 8.dp), fontSize = 12.sp, fontWeight = FontWeight.SemiBold) }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WorkspaceMatchScreen(state: UiState, viewModel: MainViewModel) {
    var sourceType by remember { mutableStateOf("text") }
    var input by remember { mutableStateOf("") }
    var showInput by remember { mutableStateOf(false) }
    var showResumeSheet by remember { mutableStateOf(false) }
    var showThemeSheet by remember { mutableStateOf(false) }
    var showHistorySheet by remember { mutableStateOf(false) }
    val imageLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris -> if (uris.isNotEmpty()) viewModel.parseJdImages(uris) }
    val selectedResume = state.resumes.firstOrNull { it.id == state.selectedResumeId }
    val selectedTheme = designThemes.firstOrNull { it.code == state.selectedDesignTheme } ?: designThemes.first()
    val selectedTemplate = state.templates.firstOrNull { it.id == state.selectedTemplateId }
    val selectedJdTitle = state.selectedJd?.optString("title")?.takeIf { it.isNotBlank() }

    Column(Modifier.fillMaxSize()) {
        MatchWorkspaceHeader { showHistorySheet = true }
        LazyColumn(
            Modifier.weight(1f).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                WorkspaceSectionTitle("当前基础简历", "这份简历将作为本次优化的真实经历来源", "切换") { showResumeSheet = true }
                WorkspaceCard(Modifier.clickable { showResumeSheet = true }) {
                    if (selectedResume == null) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Box(Modifier.size(48.dp).clip(CircleShape).background(WorkspaceBlueSoft), contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Add, null, tint = WorkspaceBlue) }
                            Column(Modifier.weight(1f)) { Text("选择一份基础简历", color = WorkspaceInk, fontWeight = FontWeight.Bold); Text("还没有简历时，可先到简历库创建", color = WorkspaceMuted, fontSize = 12.sp) }
                            Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(15.dp))
                        }
                    } else {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            WorkspaceAvatar(selectedResume.content.name.ifBlank { selectedResume.name }, size = 48)
                            Column(Modifier.weight(1f)) {
                                Text(selectedResume.content.name.ifBlank { selectedResume.name }, color = WorkspaceInk, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
                                Text(listOf(selectedResume.name, selectedResume.content.title).filter { it.isNotBlank() }.joinToString(" · "), color = WorkspaceMuted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            }
                            Icon(Icons.Outlined.Edit, "更换", tint = WorkspaceMuted)
                            Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(15.dp))
                        }
                    }
                }
            }
            item {
                WorkspaceSectionTitle("目标岗位", "从雷达带入、粘贴链接、文本或岗位截图")
                WorkspaceCard {
                    SourceTypeTabs(sourceType) { sourceType = it; input = ""; showInput = false }
                    if (sourceType == "image") {
                        Column(
                            Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(WorkspaceBg).clickable { imageLauncher.launch("image/*") }.padding(vertical = 24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(7.dp),
                        ) {
                            Icon(Icons.Outlined.PhotoLibrary, null, tint = WorkspaceBlue, modifier = Modifier.size(28.dp))
                            Text("选择岗位截图", color = WorkspaceInk, fontWeight = FontWeight.Bold)
                            Text("支持一次选择多张，按顺序合并识别", color = WorkspaceMuted, fontSize = 12.sp)
                        }
                    } else if (!showInput) {
                        Row(
                            Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(WorkspaceBg).clickable { showInput = true }.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(if (sourceType == "url") "点击粘贴岗位详情链接" else "点击粘贴岗位职责和任职要求", color = WorkspaceMuted, modifier = Modifier.weight(1f))
                            Icon(Icons.Outlined.Edit, null, tint = WorkspaceBlue, modifier = Modifier.size(20.dp))
                        }
                    } else {
                        WorkspaceField(
                            if (sourceType == "url") "岗位链接" else "岗位职责与任职要求",
                            input,
                            minLines = if (sourceType == "url") 1 else 3,
                            keyboardType = if (sourceType == "url") KeyboardType.Uri else KeyboardType.Text,
                            leading = if (sourceType == "url") Icons.Outlined.Link else null,
                        ) { input = it }
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                            Text("${input.length} / 5000", color = WorkspaceMuted, fontSize = 11.sp)
                        }
                    }
                    if (selectedJdTitle != null) {
                        HorizontalDivider(color = WorkspaceLine)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Icon(Icons.Outlined.CheckCircle, null, tint = WorkspaceSuccess)
                            Column(Modifier.weight(1f)) {
                                Text("已选岗位", color = WorkspaceMuted, fontSize = 11.sp)
                                Text(selectedJdTitle, color = WorkspaceInk, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            }
                            WorkspaceBadge("解析完成", "success")
                        }
                    }
                }
            }
            item {
                WorkspaceSectionTitle("简历风格", "可选；不设置时会按岗位自动匹配")
                WorkspaceCard(Modifier.clickable { viewModel.loadTemplates(); showThemeSheet = true }) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Box(
                            Modifier.size(48.dp).clip(RoundedCornerShape(14.dp)).background(Brush.linearGradient(listOf(WorkspaceBlue, Color(0xFF4D72CE)))),
                            contentAlignment = Alignment.Center,
                        ) { Icon(Icons.Outlined.AutoAwesome, null, tint = Color.White) }
                        Column(Modifier.weight(1f)) {
                            Text(selectedTemplate?.name ?: selectedTheme.label, color = WorkspaceInk, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
                            Text(selectedTemplate?.let { "${it.displayCategory} · ${it.tags.joinToString(" / ")}" } ?: if (selectedTheme.code == "auto") "系统根据岗位智能匹配最优风格" else "已指定配色与排版方向", color = WorkspaceMuted, fontSize = 12.sp)
                        }
                        Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(15.dp))
                    }
                }
            }
            item {
                Row(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(WorkspaceBlueSoft).padding(15.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    LinearProgressIndicator(modifier = Modifier.width(38.dp), color = WorkspaceBlue, trackColor = Color.White)
                    Column {
                        Text("生成会在后台继续，可随时离开页面", color = WorkspaceInk, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        Text("完成后会在作品中心显示", color = WorkspaceMuted, fontSize = 11.sp)
                    }
                }
            }
            item { Spacer(Modifier.height(4.dp)) }
        }
        Surface(color = Color.White, shadowElevation = 5.dp) {
            WorkspacePrimaryButton(
                text = if (state.selectedJd != null) "生成优化版简历" else "解析岗位信息",
                icon = Icons.Outlined.AutoAwesome,
                enabled = selectedResume != null && (state.selectedJd != null || input.isNotBlank()),
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            ) {
                if (state.selectedJd != null) viewModel.generate() else viewModel.parseJd(sourceType, input)
            }
        }
    }

    if (showResumeSheet) {
        ModalBottomSheet(onDismissRequest = { showResumeSheet = false }, containerColor = Color.White) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                WorkspaceSectionTitle("选择基础简历", "这次生成会基于所选版本")
                state.resumes.forEach { resume ->
                    Row(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable { viewModel.selectResume(resume.id); showResumeSheet = false }.padding(vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(11.dp),
                    ) {
                        WorkspaceAvatar(resume.content.name.ifBlank { resume.name }, size = 42)
                        Column(Modifier.weight(1f)) { Text(resume.name, color = WorkspaceInk, fontWeight = FontWeight.Bold); Text(resume.content.title.ifBlank { "未填写方向" }, color = WorkspaceMuted, fontSize = 12.sp) }
                        if (resume.id == state.selectedResumeId) Icon(Icons.Outlined.CheckCircle, "已选", tint = WorkspaceBlue)
                    }
                }
                if (state.resumes.isEmpty()) WorkspaceEmpty(Icons.Outlined.Description, "还没有简历", "先到简历库创建或上传一份。")
            }
        }
    }
    if (showThemeSheet) {
        ModalBottomSheet(onDismissRequest = { showThemeSheet = false }, containerColor = Color.White) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                WorkspaceSectionTitle("选择简历风格", "智能匹配会综合岗位、行业和公司类型")
                designThemes.forEach { theme ->
                    Row(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable { viewModel.selectTheme(theme.code); showThemeSheet = false }.padding(vertical = 11.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(36.dp).clip(RoundedCornerShape(11.dp)).background(if (theme.code == "auto") WorkspaceBlue else WorkspaceBlueSoft), contentAlignment = Alignment.Center) {
                            Icon(if (theme.code == "auto") Icons.Outlined.AutoAwesome else Icons.Outlined.Palette, null, tint = if (theme.code == "auto") Color.White else WorkspaceBlue, modifier = Modifier.size(19.dp))
                        }
                        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) { Text(theme.label, color = WorkspaceInk, fontWeight = FontWeight.Bold); Text(if (theme.code == "auto") "推荐：让系统为岗位自动设计" else "固定此风格，再根据内容细调", color = WorkspaceMuted, fontSize = 11.sp) }
                        if (theme.code == state.selectedDesignTheme) Icon(Icons.Outlined.CheckCircle, "已选", tint = WorkspaceBlue)
                    }
                }
                if (state.templates.isNotEmpty()) {
                    HorizontalDivider(color = WorkspaceLine)
                    Text("系统真实版式模板（预览=生成结构）", color = WorkspaceInk, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    state.templates.forEach { template ->
                        Row(
                            Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable { viewModel.selectTemplate(template); showThemeSheet = false }.padding(vertical = 11.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Box(Modifier.size(36.dp).clip(RoundedCornerShape(11.dp)).background(runCatching { Color(android.graphics.Color.parseColor(template.accent)) }.getOrDefault(WorkspaceBlue)), contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Palette, null, tint = Color.White, modifier = Modifier.size(19.dp)) }
                            Column(Modifier.weight(1f).padding(horizontal = 12.dp)) { Text(template.name, color = WorkspaceInk, fontWeight = FontWeight.Bold); Text("${template.displayCategory} · ${template.tags.joinToString(" / ")}", color = WorkspaceMuted, fontSize = 11.sp) }
                            TextButton(onClick = { viewModel.openTemplatePreview(template) }) { Text("预览") }
                            if (template.id == state.selectedTemplateId) Icon(Icons.Outlined.CheckCircle, "已选", tint = WorkspaceBlue)
                        }
                    }
                }
            }
        }
    }
    if (showHistorySheet) {
        ModalBottomSheet(onDismissRequest = { showHistorySheet = false }, containerColor = WorkspaceBg) {
            LazyColumn(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                item { WorkspaceSectionTitle("岗位解析记录", "成功记录可直接带入本次适配") }
                items(state.jdTasks.take(20), key = { it.id }) { task ->
                    WorkspaceCard {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(task.result?.optString("title")?.takeIf { it.isNotBlank() } ?: task.detail.ifBlank { "岗位解析" }, color = WorkspaceInk, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                Text(task.progress ?: task.source, color = WorkspaceMuted, fontSize = 11.sp)
                            }
                            WorkspaceBadge(workspaceStatusLabel(task.status), workspaceStatusTone(task.status))
                        }
                        task.error?.takeIf { it.isNotBlank() }?.let { Text(it, color = WorkspaceDanger, fontSize = 12.sp, lineHeight = 17.sp) }
                        Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
                            if (task.status == "completed" && task.result != null) TextButton(onClick = { viewModel.useJd(task); showHistorySheet = false }) { Text("选用") }
                            TextButton(onClick = { viewModel.deleteJdTask(task.id) }) { Text("删除", color = WorkspaceDanger) }
                        }
                    }
                }
                if (state.jdTasks.isEmpty()) item { WorkspaceEmpty(Icons.Outlined.History, "暂无解析记录", "提交岗位文本、链接或截图后会显示在这里。") }
            }
        }
    }
}

@Composable
private fun MatchWorkspaceHeader(onHistory: () -> Unit) {
    Box(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 16.dp, vertical = 9.dp)) {
        Text(
            "简历优化",
            color = WorkspaceInk,
            fontSize = 22.sp,
            fontWeight = FontWeight.ExtraBold,
            modifier = Modifier.align(Alignment.Center),
        )
        TextButton(onClick = onHistory, modifier = Modifier.align(Alignment.CenterEnd)) {
            Icon(Icons.Outlined.History, null, tint = WorkspaceInk, modifier = Modifier.size(21.dp))
            Spacer(Modifier.width(5.dp))
            Text("历史", color = WorkspaceInk, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun StepProgress(current: Int) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 28.dp, vertical = 10.dp), verticalAlignment = Alignment.Top) {
        listOf("选择简历", "提交岗位", "确认生成").forEachIndexed { index, label ->
            val step = index + 1
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(76.dp)) {
                Box(Modifier.size(32.dp).clip(CircleShape).background(if (step <= current) WorkspaceBlue else Color.White).then(if (step > current) Modifier.background(Color.White) else Modifier), contentAlignment = Alignment.Center) {
                    Surface(shape = CircleShape, color = if (step <= current) WorkspaceBlue else Color.White, border = BorderStroke(1.dp, if (step <= current) WorkspaceBlue else WorkspaceLine), modifier = Modifier.fillMaxSize()) {
                        Box(contentAlignment = Alignment.Center) { Text(step.toString(), color = if (step <= current) Color.White else WorkspaceMuted, fontWeight = FontWeight.Bold) }
                    }
                }
                Text(label, color = if (step <= current) WorkspaceBlue else WorkspaceMuted, fontSize = 11.sp, fontWeight = if (step == current) FontWeight.Bold else FontWeight.Medium, modifier = Modifier.padding(top = 5.dp))
            }
            if (index < 2) HorizontalDivider(Modifier.weight(1f).padding(top = 16.dp), color = if (step < current) WorkspaceBlue else WorkspaceLine)
        }
    }
}

@Composable
private fun NumberedSection(number: Int, title: String, subtitle: String? = null, trailing: String? = null, onTrailing: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(Modifier.size(30.dp).clip(CircleShape).background(WorkspaceBlue), contentAlignment = Alignment.Center) { Text(number.toString(), color = Color.White, fontWeight = FontWeight.ExtraBold) }
        Column(Modifier.weight(1f)) {
            Text(title, color = WorkspaceInk, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
            subtitle?.let { Text(it, color = WorkspaceMuted, fontSize = 11.sp, lineHeight = 16.sp) }
        }
        if (trailing != null && onTrailing != null) TextButton(onClick = onTrailing) { Text(trailing, color = WorkspaceMuted) }
    }
}

@Composable
private fun SourceTypeTabs(selected: String, onSelected: (String) -> Unit) {
    Row(Modifier.fillMaxWidth()) {
        listOf(Triple("text", "文本", Icons.Outlined.TextSnippet), Triple("url", "链接", Icons.Outlined.Link), Triple("image", "截图", Icons.Outlined.Image)).forEach { (value, label, icon) ->
            val active = selected == value
            Column(
                Modifier.weight(1f).clickable { onSelected(value) }.padding(top = 4.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) { Icon(icon, null, tint = if (active) WorkspaceBlue else WorkspaceMuted, modifier = Modifier.size(19.dp)); Text(label, color = if (active) WorkspaceBlue else WorkspaceMuted, fontWeight = if (active) FontWeight.Bold else FontWeight.Medium) }
                HorizontalDivider(thickness = 3.dp, color = if (active) WorkspaceBlue else WorkspaceLine)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WorkspaceGenerationScreen(state: UiState, viewModel: MainViewModel) {
    var filter by remember { mutableStateOf("all") }
    var selectedItem by remember { mutableStateOf<GenerationItem?>(null) }
    var themeItem by remember { mutableStateOf<GenerationItem?>(null) }
    var selectedTheme by remember { mutableStateOf("auto") }
    var selectedCatalogTemplateId by remember { mutableStateOf<String?>(null) }
    val visible = state.generations.filter {
        when (filter) {
            "processing" -> it.status == "processing"
            "completed" -> it.status == "completed"
            "failed" -> it.status == "failed"
            else -> true
        }
    }
    Column(Modifier.fillMaxSize()) {
        WorkspaceHeader("作品中心", "预览、换模板、下载你的适配简历", Icons.Outlined.Refresh, "刷新") { viewModel.loadGenerations() }
        LazyRow(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(listOf("all" to "全部", "processing" to "进行中", "completed" to "已完成", "failed" to "失败")) { (value, label) ->
                FilterChipButton(label, filter == value) { filter = value }
            }
        }
        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            items(visible, key = { it.id }) { item ->
                GenerationWorkCard(item, onOpen = { selectedItem = item }, onTheme = { viewModel.loadTemplates(); selectedTheme = "auto"; selectedCatalogTemplateId = null; themeItem = item }, onDelete = { viewModel.deleteGeneration(item.id) })
            }
            if (visible.isEmpty() && !state.loading) {
                item { WorkspaceEmpty(Icons.Outlined.AssignmentTurnedIn, if (filter == "all") "还没有简历作品" else "这个分类暂时为空", "完成一次岗位适配后，生成的 Word 和 PDF 会统一出现在这里。", "去岗位适配") { viewModel.switchTab(AppTab.Match) } }
            }
            item { Spacer(Modifier.height(8.dp)) }
        }
    }
    selectedItem?.let { item ->
        ModalBottomSheet(onDismissRequest = { selectedItem = null }, containerColor = WorkspaceBg) {
            LazyColumn(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                item {
                    Row(verticalAlignment = Alignment.Top) {
                        Column(Modifier.weight(1f)) {
                            Text(item.title.ifBlank { "适配简历" }, color = WorkspaceInk, fontSize = 21.sp, lineHeight = 27.sp, fontWeight = FontWeight.ExtraBold)
                            Text(item.resumeName, color = WorkspaceMuted, fontSize = 13.sp)
                        }
                        WorkspaceBadge(workspaceStatusLabel(item.status), workspaceStatusTone(item.status))
                    }
                }
                if (item.status == "completed") {
                    item { GenerationScorePanel(item) }
                    if (item.optimizations.isNotEmpty()) item {
                        WorkspaceCard {
                            Text("AI 优化摘要", color = WorkspaceInk, fontWeight = FontWeight.Bold)
                            item.optimizations.take(5).forEach { Text("• $it", color = WorkspaceMuted, fontSize = 13.sp, lineHeight = 19.sp) }
                        }
                    }
                    item {
                        WorkspaceSectionTitle("真实文件预览", "直接打开服务器生成的实际 Word 或 PDF")
                        Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                            WorkspacePrimaryButton("预览 PDF", Icons.Outlined.PictureAsPdf, enabled = item.pdfKey != null, modifier = Modifier.weight(1f)) { viewModel.openFile(item, "pdf") }
                            WorkspaceOutlinedButton("预览 Word", Icons.Outlined.Description, Modifier.weight(1f)) { viewModel.openFile(item, "docx") }
                        }
                    }
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                            WorkspaceOutlinedButton("下载 PDF", Icons.Outlined.Download, Modifier.weight(1f)) { viewModel.downloadFile(item, "pdf") }
                            WorkspaceOutlinedButton("下载 Word", Icons.Outlined.Download, Modifier.weight(1f)) { viewModel.downloadFile(item, "docx") }
                        }
                    }
                    item { WorkspaceOutlinedButton("换模板再生成", Icons.Outlined.Palette, Modifier.fillMaxWidth()) { viewModel.loadTemplates(); selectedItem = null; selectedTheme = "auto"; selectedCatalogTemplateId = null; themeItem = item } }
                } else if (item.status == "processing") {
                    item {
                        WorkspaceCard {
                            LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = WorkspaceBlue, trackColor = WorkspaceBlueSoft)
                            Text(item.message?.ifBlank { "系统正在后台生成，你可以先使用其他功能。" } ?: "系统正在后台生成，你可以先使用其他功能。", color = WorkspaceMuted, fontSize = 13.sp)
                        }
                    }
                } else {
                    item {
                        WorkspaceCard {
                            Icon(Icons.Outlined.ErrorOutline, null, tint = WorkspaceDanger)
                            Text(item.error ?: "生成失败，请稍后重试", color = WorkspaceDanger, fontSize = 13.sp, lineHeight = 19.sp)
                            Text("失败不会扣额度；重试会重新预扣 1 次可用额度。", color = WorkspaceMuted, fontSize = 12.sp, lineHeight = 17.sp)
                        }
                    }
                    item {
                        WorkspacePrimaryButton("重试生成", Icons.Outlined.Refresh, modifier = Modifier.fillMaxWidth()) {
                            selectedItem = null
                            viewModel.retryGeneration(item)
                        }
                    }
                }
                item { TextButton(onClick = { selectedItem = null; viewModel.deleteGeneration(item.id) }, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Outlined.Delete, null, tint = WorkspaceDanger); Spacer(Modifier.width(6.dp)); Text("删除这条记录", color = WorkspaceDanger) } }
            }
        }
    }
    themeItem?.let { item ->
        ModalBottomSheet(onDismissRequest = { themeItem = null }, containerColor = Color.White) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                WorkspaceSectionTitle("换模板再生成", "简历内容不变，重新排版；模板原件预览仅供风格参考，最终以生成文件为准（消耗 1 次额度）")
                designThemes.forEach { theme ->
                    Row(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable { selectedTheme = theme.code }.background(if (selectedTheme == theme.code) WorkspaceBlueSoft else Color.Transparent).padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(if (theme.code == "auto") Icons.Outlined.AutoAwesome else Icons.Outlined.Palette, null, tint = WorkspaceBlue)
                        Text(theme.label, color = WorkspaceInk, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f).padding(horizontal = 12.dp))
                        if (selectedTheme == theme.code) Icon(Icons.Outlined.CheckCircle, "已选", tint = WorkspaceBlue)
                    }
                }
                if (state.templates.isNotEmpty()) {
                    HorizontalDivider(color = WorkspaceLine)
                    Text("系统版式模板（真实预览后选用）", color = WorkspaceInk, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    state.templates.forEach { template ->
                        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).clickable { selectedCatalogTemplateId = template.id; selectedTheme = template.baseTheme }.background(if (selectedCatalogTemplateId == template.id) WorkspaceBlueSoft else Color.Transparent).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Outlined.Palette, null, tint = WorkspaceBlue)
                            Column(Modifier.weight(1f).padding(horizontal = 12.dp)) { Text(template.name, color = WorkspaceInk, fontWeight = FontWeight.Bold); Text(template.displayCategory, color = WorkspaceMuted, fontSize = 11.sp) }
                            TextButton(onClick = { viewModel.openTemplatePreview(template) }) { Text("预览") }
                            if (selectedCatalogTemplateId == template.id) Icon(Icons.Outlined.CheckCircle, "已选", tint = WorkspaceBlue)
                        }
                    }
                }
                WorkspacePrimaryButton("按此模板重新生成", Icons.Outlined.AutoAwesome) { themeItem = null; viewModel.regenerate(item, selectedTheme, selectedCatalogTemplateId) }
            }
        }
    }
}

@Composable
private fun GenerationWorkCard(item: GenerationItem, onOpen: () -> Unit, onTheme: () -> Unit, onDelete: () -> Unit) {
    var menu by remember(item.id) { mutableStateOf(false) }
    WorkspaceCard(Modifier.clickable(onClick = onOpen)) {
        Row(verticalAlignment = Alignment.Top) {
            Box(
                Modifier.size(46.dp).clip(RoundedCornerShape(13.dp)).background(if (item.status == "completed") WorkspaceBlueSoft else WorkspaceBg),
                contentAlignment = Alignment.Center,
            ) { Icon(if (item.status == "completed") Icons.Outlined.Description else Icons.Outlined.History, null, tint = WorkspaceBlue) }
            Column(Modifier.weight(1f).padding(horizontal = 11.dp)) {
                Text(item.title.ifBlank { "适配简历" }, color = WorkspaceInk, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(item.resumeName, color = WorkspaceMuted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(item.createdAt.take(16).replace("T", " "), color = WorkspaceMuted, fontSize = 10.sp)
            }
            WorkspaceBadge(workspaceStatusLabel(item.status), workspaceStatusTone(item.status))
            Box {
                IconButton(onClick = { menu = true }) { Icon(Icons.Outlined.MoreVert, "更多") }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("查看详情") }, leadingIcon = { Icon(Icons.Outlined.Visibility, null) }, onClick = { menu = false; onOpen() })
                    if (item.status == "completed") DropdownMenuItem(text = { Text("换模板再生成") }, leadingIcon = { Icon(Icons.Outlined.Palette, null) }, onClick = { menu = false; onTheme() })
                    DropdownMenuItem(text = { Text("删除", color = WorkspaceDanger) }, leadingIcon = { Icon(Icons.Outlined.Delete, null, tint = WorkspaceDanger) }, onClick = { menu = false; onDelete() })
                }
            }
        }
        if (item.status == "processing") LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = WorkspaceBlue, trackColor = WorkspaceBlueSoft)
        if (item.status == "completed" && item.overallScore != null) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("AI 综合评分", color = WorkspaceMuted, fontSize = 11.sp)
                Text(" ${item.overallScore} 分", color = WorkspaceBlue, fontSize = 17.sp, fontWeight = FontWeight.ExtraBold)
                Spacer(Modifier.weight(1f))
                Text("查看预览与下载", color = WorkspaceBlue, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceBlue, modifier = Modifier.size(13.dp))
            }
        }
        item.error?.takeIf { it.isNotBlank() }?.let { Text(it, color = WorkspaceDanger, fontSize = 12.sp, maxLines = 2, overflow = TextOverflow.Ellipsis) }
    }
}

@Composable
private fun GenerationScorePanel(item: GenerationItem) {
    WorkspaceCard {
        Row(verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) { Text("AI 综合评分", color = WorkspaceMuted, fontSize = 12.sp); Text("${item.overallScore ?: "--"} 分", color = WorkspaceBlue, fontSize = 29.sp, fontWeight = FontWeight.ExtraBold) }
            WorkspaceBadge("竞争力简历", "success")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ScoreCell("岗位匹配", item.jobMatchScore, Modifier.weight(1f))
            ScoreCell("关键词", item.keywordCoverageScore, Modifier.weight(1f))
            ScoreCell("视觉", item.visualScore, Modifier.weight(1f))
        }
    }
}

@Composable
private fun ScoreCell(label: String, score: Int?, modifier: Modifier) {
    Column(modifier.clip(RoundedCornerShape(12.dp)).background(WorkspaceBg).padding(vertical = 9.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(score?.toString() ?: "--", color = WorkspaceInk, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
        Text(label, color = WorkspaceMuted, fontSize = 10.sp)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WorkspaceAccountScreen(state: UiState, viewModel: MainViewModel) {
    var dialog by remember { mutableStateOf<String?>(null) }
    val context = LocalContext.current
    val cropLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val path = result.data?.getStringExtra(CropAvatarActivity.EXTRA_CROPPED_PATH)
        if (result.resultCode == Activity.RESULT_OK && !path.isNullOrBlank()) viewModel.uploadAccountAvatar(Uri.fromFile(File(path)))
    }
    val avatarLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) cropLauncher.launch(Intent(context, CropAvatarActivity::class.java).putExtra(CropAvatarActivity.EXTRA_SOURCE_URI, uri.toString()))
    }
    Column(Modifier.fillMaxSize()) {
        WorkspaceHeader("我的", "账号、职业资产与服务设置")
        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
            item {
                WorkspaceCard {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(13.dp)) {
                        Box(Modifier.clickable { avatarLauncher.launch("image/*") }) {
                            WorkspaceAvatar(state.user?.username ?: "用", state.userAvatarUrl, 64)
                            Box(Modifier.align(Alignment.BottomEnd).size(22.dp).clip(CircleShape).background(WorkspaceBlue), contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Edit, "编辑头像", tint = Color.White, modifier = Modifier.size(13.dp)) }
                        }
                        Column(Modifier.weight(1f)) {
                            Text(state.user?.username ?: "用户", color = WorkspaceInk, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                            Text(maskWorkspacePhone(state.user?.phone), color = WorkspaceMuted, fontSize = 12.sp)
                            Text("账号头像会同步到 Web 端", color = WorkspaceBlue, fontSize = 11.sp)
                        }
                        Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(15.dp))
                    }
                }
            }
            item {
                WorkspaceSectionTitle("职业工作台")
                WorkspaceCard {
                    AccountRow(Icons.Outlined.FactCheck, "职业资产中心", "事实确认、岗位审阅与投递追踪") { viewModel.switchTab(AppTab.Career) }
                    HorizontalDivider(color = WorkspaceLine)
                    AccountRow(
                        Icons.Outlined.Payments,
                        "剩余生成额度",
                        if (state.billing?.suspended == true) "已暂停" else "${state.billing?.available ?: state.billing?.credits ?: 0} 次可用",
                    ) { viewModel.switchTab(AppTab.Career) }
                }
            }
            item {
                WorkspaceSectionTitle("账号与安全")
                WorkspaceCard {
                    AccountRow(Icons.Outlined.Lock, "修改密码", "建议定期更新密码") { dialog = "password" }
                    HorizontalDivider(color = WorkspaceLine)
                    AccountRow(Icons.Outlined.PhoneAndroid, "更换手机号", "当前：${maskWorkspacePhone(state.user?.phone)}") { dialog = "phone" }
                    HorizontalDivider(color = WorkspaceLine)
                    AccountRow(Icons.Outlined.SystemUpdate, "检查版本更新", "当前版本 ${BuildConfig.VERSION_NAME}") { viewModel.checkAppVersion() }
                }
            }
            item {
                WorkspaceCard {
                    AccountRow(Icons.Outlined.Security, "账号注销", "永久删除账号和全部个人资料", danger = true) { dialog = "delete" }
                }
            }
            item { WorkspaceOutlinedButton("退出登录", Icons.Outlined.Logout, Modifier.fillMaxWidth()) { viewModel.logout() } }
            item { Text("职达简历 Android ${BuildConfig.VERSION_NAME}", color = WorkspaceMuted, fontSize = 11.sp, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp)) }
        }
    }
    when (dialog) {
        "password" -> WorkspacePasswordDialog({ dialog = null }, viewModel)
        "phone" -> WorkspacePhoneDialog({ dialog = null }, viewModel)
        "delete" -> WorkspaceDeleteDialog(state.user?.username.orEmpty(), { dialog = null }, viewModel)
    }
}

@Composable
private fun AccountRow(icon: ImageVector, title: String, subtitle: String, danger: Boolean = false, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(Modifier.size(38.dp).clip(RoundedCornerShape(11.dp)).background((if (danger) WorkspaceDanger else WorkspaceBlue).copy(alpha = .08f)), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = if (danger) WorkspaceDanger else WorkspaceBlue, modifier = Modifier.size(20.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, color = if (danger) WorkspaceDanger else WorkspaceInk, fontWeight = FontWeight.Bold)
            Text(subtitle, color = WorkspaceMuted, fontSize = 11.sp)
        }
        Icon(Icons.Outlined.ArrowForwardIos, null, tint = WorkspaceMuted, modifier = Modifier.size(14.dp))
    }
}

@Composable
private fun WorkspacePasswordDialog(onDismiss: () -> Unit, viewModel: MainViewModel) {
    var current by remember { mutableStateOf("") }
    var next by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Outlined.Lock, null, tint = WorkspaceBlue) },
        title = { Text("修改密码", fontWeight = FontWeight.ExtraBold) },
        text = { Column(verticalArrangement = Arrangement.spacedBy(10.dp)) { WorkspaceField("当前密码", current) { current = it }; WorkspaceField("新密码", next) { next = it } } },
        confirmButton = { Button(onClick = { viewModel.changePassword(current, next); onDismiss() }, enabled = current.isNotBlank() && next.length >= 6) { Text("保存") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@Composable
private fun WorkspacePhoneDialog(onDismiss: () -> Unit, viewModel: MainViewModel) {
    var phone by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Outlined.PhoneAndroid, null, tint = WorkspaceBlue) },
        title = { Text("更换手机号", fontWeight = FontWeight.ExtraBold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                WorkspaceField("新手机号", phone, keyboardType = KeyboardType.Phone) { phone = it }
                WorkspaceField("短信验证码", code, keyboardType = KeyboardType.Number) { code = it }
                WorkspaceOutlinedButton("发送验证码", modifier = Modifier.fillMaxWidth()) { viewModel.sendSms(phone, "change_phone") }
            }
        },
        confirmButton = { Button(onClick = { viewModel.changePhone(phone, code); onDismiss() }, enabled = phone.isNotBlank() && code.isNotBlank()) { Text("确认更换") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@Composable
private fun WorkspaceDeleteDialog(username: String, onDismiss: () -> Unit, viewModel: MainViewModel) {
    var password by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Outlined.ErrorOutline, null, tint = WorkspaceDanger) },
        title = { Text("注销账号", fontWeight = FontWeight.ExtraBold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("注销后，账号、简历和生成记录将永久删除且无法恢复。", color = WorkspaceDanger, fontSize = 13.sp)
                WorkspaceField("输入用户名 $username", confirm) { confirm = it }
                WorkspaceField("当前密码", password) { password = it }
            }
        },
        confirmButton = { Button(onClick = { viewModel.deleteAccount(password, confirm); onDismiss() }, enabled = confirm == username && password.isNotBlank(), colors = ButtonDefaults.buttonColors(containerColor = WorkspaceDanger)) { Text("永久注销") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun WorkspaceCareerScreen(state: UiState, viewModel: MainViewModel) {
    var section by remember { mutableStateOf("facts") }
    var showApplicationSheet by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 8.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = { viewModel.switchTab(AppTab.Account) }) { Icon(Icons.Outlined.ArrowBack, "返回") }
            Column(Modifier.weight(1f)) { Text("职业资产中心", color = WorkspaceInk, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold); Text("确认事实、审阅表达、追踪投递", color = WorkspaceMuted, fontSize = 12.sp) }
            IconButton(onClick = { showApplicationSheet = true }) { Icon(Icons.Outlined.Add, "新增投递") }
        }
        LazyRow(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(listOf("facts" to "职业事实", "reviews" to "岗位审阅", "applications" to "投递追踪", "billing" to "套餐额度")) { (value, label) -> FilterChipButton(label, section == value) { section = value } }
        }
        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            when (section) {
                "facts" -> {
                    item { WorkspacePrimaryButton("从当前基础简历重建事实", Icons.Outlined.Refresh) { viewModel.rebuildCareerFacts() } }
                    items(state.careerFacts, key = { it.id }) { fact ->
                        WorkspaceCard {
                            Text(fact.text, color = WorkspaceInk, fontWeight = FontWeight.Bold, fontSize = 13.sp, lineHeight = 19.sp)
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                WorkspaceBadge(if (fact.status == "confirmed") "已确认" else if (fact.status == "rejected") "已拒绝" else "待确认", if (fact.status == "confirmed") "success" else if (fact.status == "rejected") "danger" else "warning")
                                Spacer(Modifier.weight(1f))
                                TextButton(onClick = { viewModel.decideCareerFact(fact.id, "rejected") }) { Text("拒绝", color = WorkspaceDanger) }
                                TextButton(onClick = { viewModel.decideCareerFact(fact.id, "confirmed") }) { Text("确认") }
                            }
                        }
                    }
                    if (state.careerFacts.isEmpty()) item { WorkspaceEmpty(Icons.Outlined.FactCheck, "暂无职业事实", "先选择一份基础简历，然后重建并逐条确认。") }
                }
                "reviews" -> {
                    item { WorkspacePrimaryButton("基于当前岗位创建审阅", Icons.Outlined.AutoAwesome) { viewModel.createReview() } }
                    items(state.reviews, key = { it.id }) { review ->
                        WorkspaceCard {
                            Text(review.title, color = WorkspaceInk, fontWeight = FontWeight.ExtraBold)
                            review.proposals.take(8).forEach { proposal ->
                                Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(WorkspaceBg).padding(11.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                    Text(proposal.text, color = WorkspaceInk, fontSize = 13.sp, lineHeight = 18.sp)
                                    Text(proposal.reason, color = WorkspaceMuted, fontSize = 11.sp)
                                    Row { TextButton(onClick = { viewModel.decideReview(review.id, proposal.id, "accepted") }) { Text("接受") }; TextButton(onClick = { viewModel.decideReview(review.id, proposal.id, "rejected") }) { Text("拒绝", color = WorkspaceDanger) } }
                                }
                            }
                        }
                    }
                    if (state.reviews.isEmpty()) item { WorkspaceEmpty(Icons.Outlined.AssignmentTurnedIn, "暂无审阅建议", "在岗位适配页选择一个岗位后，再创建岗位审阅。") }
                }
                "applications" -> {
                    item { WorkspacePrimaryButton("新增投递记录", Icons.Outlined.Add) { showApplicationSheet = true } }
                    items(state.applications, key = { it.id }) { application ->
                        WorkspaceCard {
                            Row {
                                Column(Modifier.weight(1f)) { Text(application.jobTitle, color = WorkspaceInk, fontWeight = FontWeight.ExtraBold); Text(listOf(application.company, application.note).filter { it.isNotBlank() }.joinToString(" · "), color = WorkspaceMuted, fontSize = 11.sp) }
                                WorkspaceBadge(applicationStatusLabel(application.status), if (application.status == "interview") "success" else "blue")
                            }
                            LazyRow(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                items(listOf("saved" to "待投递", "applied" to "已投递", "interview" to "面试中")) { (value, label) -> FilterChipButton(label, application.status == value) { viewModel.updateApplication(application.id, value) } }
                                item { TextButton(onClick = { viewModel.deleteApplication(application.id) }) { Text("删除", color = WorkspaceDanger) } }
                            }
                        }
                    }
                    if (state.applications.isEmpty()) item { WorkspaceEmpty(Icons.Outlined.Work, "还没有投递记录", "把准备投递和已经投递的岗位统一放在这里。") }
                }
                else -> {
                    item {
                        WorkspaceCard {
                            Text("剩余生成额度", color = WorkspaceMuted, fontSize = 12.sp)
                            Text("${state.billing?.available ?: state.billing?.credits ?: 0} 次", color = WorkspaceBlue, fontSize = 32.sp, fontWeight = FontWeight.ExtraBold)
                            Text(state.billing?.paymentNote?.ifBlank { null } ?: "创建订单后管理员确认到账；生成消耗 1 次，失败退回", color = WorkspaceMuted, fontSize = 11.sp)
                        }
                    }
                    items(state.billing?.plans.orEmpty(), key = { it.code }) { plan ->
                        WorkspaceCard {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) { Text(plan.name, color = WorkspaceInk, fontWeight = FontWeight.ExtraBold); Text("${plan.credits} 次生成额度", color = WorkspaceMuted, fontSize = 12.sp) }
                                Text("¥${"%.2f".format(plan.priceCents / 100.0)}", color = WorkspaceBlue, fontWeight = FontWeight.ExtraBold)
                            }
                            WorkspaceOutlinedButton("创建订单", Icons.Outlined.Payments, Modifier.fillMaxWidth()) { viewModel.createOrder(plan.code) }
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(8.dp)) }
        }
    }
    if (showApplicationSheet) {
        var jobTitle by remember { mutableStateOf("") }
        var company by remember { mutableStateOf("") }
        var url by remember { mutableStateOf("") }
        var note by remember { mutableStateOf("") }
        ModalBottomSheet(onDismissRequest = { showApplicationSheet = false }, containerColor = WorkspaceBg) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                WorkspaceSectionTitle("新增投递记录", "保存后可持续更新求职进度")
                WorkspaceField("岗位名称", jobTitle) { jobTitle = it }
                WorkspaceField("公司（可选）", company) { company = it }
                WorkspaceField("岗位链接（可选）", url, keyboardType = KeyboardType.Uri) { url = it }
                WorkspaceField("备注（可选）", note, minLines = 3) { note = it }
                WorkspacePrimaryButton("保存记录", Icons.Outlined.Check, enabled = jobTitle.isNotBlank()) { viewModel.createApplication(jobTitle, company, url, "saved", note); showApplicationSheet = false }
            }
        }
    }
}

private fun applicationStatusLabel(status: String): String = when (status) { "saved" -> "待投递"; "applied" -> "已投递"; "interview" -> "面试中"; else -> status }

private fun maskWorkspacePhone(phone: String?): String {
    if (phone.isNullOrBlank()) return "未绑定手机号"
    return if (phone.length >= 7) "${phone.take(3)}****${phone.takeLast(4)}" else phone
}
