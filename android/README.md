# 职达简历 Android 原生 App

这是“职达简历”用户端的 Kotlin + Jetpack Compose 原生 Android 工程，复用当前 FastAPI 后端：

`http://115.120.206.64/resume-ai/api/`

## 已接入的用户端能力

- 手机号验证码注册
- 用户名密码登录
- 忘记密码，通过短信验证码重置
- 简历库列表、创建、编辑、删除、设为默认
- 年龄字段编辑
- 简历文档上传解析
- 简历截图 OCR 识别
- 个人头像上传
- 岗位文本解析
- 岗位链接解析
- 岗位截图多图解析
- 岗位解析记录列表
- 选择解析成功的岗位后一键生成适配简历
- 选择简历模板风格生成
- 生成记录列表
- 重新选择模板风格再生成
- 打开 PDF / Word 文件
- 修改密码
- 更换手机号
- 用户自主注销账号

## 构建方式

当前这台 Windows 电脑还没有安装 Java、Gradle、Android SDK，所以这里先生成完整源码工程，暂时没有在本机打出 APK。

安装 Android Studio 后：

1. 用 Android Studio 打开 `android/`
2. 等待 Gradle Sync 完成
3. 运行 `app`，或执行 `:app:assembleDebug`

## 发布前建议

- 正式上线前建议给后端配置 HTTPS 域名。
- 然后把 `android/app/build.gradle.kts` 里的 `BuildConfig.API_BASE_URL` 改成 HTTPS 正式地址。
- 目前为了连接现有 IP 后端，`AndroidManifest.xml` 暂时允许了明文 HTTP。
