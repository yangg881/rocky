/*
 * 职达简历 · 外观与语言 单一系统 (ui-prefs)
 * ---------------------------------------------------------------
 * 合并旧双轨系统（ui-preferences.js + global-theme-i18n.js）为唯一实现：
 *   - 三态主题：auto(跟随系统) / light / dark，默认 auto
 *   - 双语：zh / en，完整词条
 *   - 分段控制条（SVG 图标）注入 [data-ui-preferences] 容器
 *   - MutationObserver 增量翻译（替代 TreeWalker 全文扫描 + setInterval 轮询）
 *   - 兼容旧接口：window.__i18n.{t,translate,setLang,setTheme,prefs}、window.zhidaI18n(key)
 *   - 一次性迁移旧 key（zhida_global_theme / zhida_global_lang）
 * 持久化：localStorage['zhiday_ui_prefs'] = { theme, lang }
 */
(function () {
  "use strict";

  var STORAGE_KEY = "zhiday_ui_prefs";
  var LEGACY_THEME_KEY = "zhida_global_theme";
  var LEGACY_LANG_KEY = "zhida_global_lang";
  var THEME_ORDER = ["auto", "light", "dark"];
  var DEFAULTS = { theme: "auto", lang: "zh" };

  /* ---------------- 词条（内嵌以保证 window.zhidaI18n 同步可用） ---------------- */
  var DICTIONARY = {
    zh: {
      // 主题/语言控制条
      theme_auto: "自动", theme_light: "浅色", theme_dark: "深色",
      lang_label: "语言", lang_zh: "中", lang_en: "EN",

      // 旧 global-theme-i18n 键（app.js 依赖）
      app_title: "职达简历",
      nav_remaining: "剩余额度", unit_times: "次",
      nav_overview: "求职驾驶舱", nav_resumes: "简历优化", nav_radar: "岗位雷达",
      nav_history: "生成记录", nav_settings: "套餐与额度", nav_admin: "管理后台",
      nav_logout: "退出登录", nav_login: "登录 / 注册",
      btn_set_default: "设为默认", btn_preview: "预览",
      btn_edit_rename: "编辑/重命名", btn_delete: "删除", badge_default: "默认",

      // auth 页
      auth_title: "让每一份经历，匹配下一份机会。",
      auth_lead: "基于 AI 岗位分析，优化简历表达，自动生成求职材料，让你的优势被看见，也让机会主动找到你。",
      auth_login: "登录", auth_register: "注册",
      auth_welcome_back: "欢迎回来", auth_login_sub: "登录后继续你的简历优化之旅",
      auth_password: "账号密码", auth_sms: "手机验证码",
      auth_username: "用户名", auth_username_placeholder: "请输入用户名",
      auth_password_label: "密码", auth_password_placeholder: "请输入密码",
      auth_remember: "记住我",
      auth_legal_consent_prefix: "登录即代表你已阅读并同意 ",
      auth_legal_terms: "用户服务协议", auth_legal_privacy: "隐私保护政策", auth_legal_disclaimer: "免责声明",
      auth_forgot: "忘记密码?",
      auth_phone: "手机号", auth_phone_placeholder: "请输入已绑定手机号",
      auth_code: "短信验证码", auth_code_placeholder: "请输入验证码",
      auth_send_code: "发送验证码", auth_sms_tip: "验证码仅用于登录已绑定的账号。",
      auth_enter: "进入工作台",
      auth_create_account: "创建账号", auth_create_sub: "手机号验证后即可开始使用",
      auth_no_account: "没有账号，", auth_go_register: "去注册",
      auth_reset: "重置密码", auth_reset_sub: "通过账号绑定手机号验证身份，再设置一个新的登录密码。",
      auth_new_password: "新密码", auth_new_password_placeholder: "至少 8 位密码",
      auth_confirm_password: "确认密码", auth_confirm_placeholder: "再次输入密码",
      auth_save_password: "保存新密码", auth_back: "返回登录",
      auth_app_download: "Android App 完整安装包", auth_app_reading: "正在读取版本…", auth_app_download_btn: "下载",

      // nav
      nav_section_workbench: "求职工作台", nav_job_radar: "岗位雷达", nav_resume: "简历优化",
      nav_history_nav: "求职记录", nav_credits: "额度",

      // onboarding
      onboard_eyebrow: "最短路径", onboard_title: "三步做出一份能投的简历",
      onboard_step1: "1. 准备基础简历", onboard_step1_desc: "上传或在线填写真实经历", onboard_step1_btn: "去准备",
      onboard_step2: "2. 选目标岗位", onboard_step2_desc: "岗位雷达一键带入，或手动粘贴 JD", onboard_step2_btn: "去选岗",
      onboard_step3: "3. 生成并下载", onboard_step3_desc: "AI 只优化表达，不编造；预览后下载 Word/PDF", onboard_step3_btn: "看作品",
      onboard_dismiss: "知道了，先藏起来",

      // common
      common_save: "保存", common_cancel: "取消", common_delete: "删除", common_edit: "编辑",
      common_close: "关闭", common_refresh: "刷新", common_loading: "正在处理",
      common_loading_detail: "请稍候，不要关闭页面", common_submit: "提交", common_confirm: "确认",
      common_back: "返回", common_yes: "是", common_no: "否",

      // errors
      error_422: "提交内容不完整或格式不正确", error_500: "服务器处理失败（500）",
      error_502: "AI 服务暂时没有返回结果（502）", error_504: "服务器处理超时（504）",
      error_request_failed: "请求失败（{status}）", error_retry_later: "请稍后重试",

      // admin
      admin_page_title: "职达简历 · 管理后台", admin_subtitle: "独立管理后台", admin_brand: "系统管理",
      admin_title: "系统运维控制台", admin_sub: "用户、生成记录、模型调用与对象存储状态集中管理。",
      admin_username: "管理员账号", admin_login: "登录后台", admin_back_user: "返回用户端",
      admin_overview: "数据总览", admin_users: "用户管理", admin_orders: "订单与额度",
      admin_records: "生成记录", admin_tasks: "任务记录", admin_templates: "模板管理",
      admin_security: "修改密码", admin_logout: "退出后台"
    },
    en: {
      // 主题/语言控制条
      theme_auto: "Auto", theme_light: "Light", theme_dark: "Dark",
      lang_label: "Language", lang_zh: "中", lang_en: "EN",

      // 旧 global-theme-i18n 键（app.js 依赖）
      app_title: "Zhida Resume AI",
      nav_remaining: "Remaining", unit_times: "credits",
      nav_overview: "Career Dashboard", nav_resumes: "Resumes", nav_radar: "Job Radar",
      nav_history: "Generations", nav_settings: "Plans & Credits", nav_admin: "Admin Panel",
      nav_logout: "Sign Out", nav_login: "Sign In / Register",
      btn_set_default: "Set Default", btn_preview: "Preview",
      btn_edit_rename: "Edit / Rename", btn_delete: "Delete", badge_default: "Default",

      // auth 页
      auth_title: "Turn every experience into your next opportunity.",
      auth_lead: "AI-powered job matching and resume optimization. Generate editable Word and PDF resumes that make your strengths stand out.",
      auth_login: "Sign In", auth_register: "Sign Up",
      auth_welcome_back: "Welcome back", auth_login_sub: "Log in to continue optimizing your resume",
      auth_password: "Password", auth_sms: "SMS Code",
      auth_username: "Username", auth_username_placeholder: "Enter username",
      auth_password_label: "Password", auth_password_placeholder: "Enter password",
      auth_remember: "Remember me",
      auth_legal_consent_prefix: "By logging in you agree to our ",
      auth_legal_terms: "Terms of Service", auth_legal_privacy: "Privacy Policy", auth_legal_disclaimer: "Disclaimer",
      auth_forgot: "Forgot password?",
      auth_phone: "Phone", auth_phone_placeholder: "Enter registered phone",
      auth_code: "SMS Code", auth_code_placeholder: "Enter code",
      auth_send_code: "Send Code", auth_sms_tip: "Code is only used to log in to a bound account.",
      auth_enter: "Enter Workbench",
      auth_create_account: "Create Account", auth_create_sub: "Start using after phone verification",
      auth_no_account: "No account? ", auth_go_register: "Sign up",
      auth_reset: "Reset Password", auth_reset_sub: "Verify with the bound phone number, then set a new password.",
      auth_new_password: "New Password", auth_new_password_placeholder: "At least 8 characters",
      auth_confirm_password: "Confirm Password", auth_confirm_placeholder: "Enter password again",
      auth_save_password: "Save Password", auth_back: "Back to Sign In",
      auth_app_download: "Android App Full Installer", auth_app_reading: "Reading version…", auth_app_download_btn: "Download",

      // nav
      nav_section_workbench: "Workbench", nav_job_radar: "Job Radar", nav_resume: "Resume",
      nav_history_nav: "History", nav_credits: "Credits",

      // onboarding
      onboard_eyebrow: "FAST TRACK", onboard_title: "Three steps to an application-ready resume",
      onboard_step1: "1. Prepare resume", onboard_step1_desc: "Upload or fill in your real experience", onboard_step1_btn: "Prepare",
      onboard_step2: "2. Pick target job", onboard_step2_desc: "Use Job Radar or paste a JD manually", onboard_step2_btn: "Pick Job",
      onboard_step3: "3. Generate & download", onboard_step3_desc: "AI polishes wording without inventing; preview and download Word/PDF", onboard_step3_btn: "View Work",
      onboard_dismiss: "Got it, hide this",

      // common
      common_save: "Save", common_cancel: "Cancel", common_delete: "Delete", common_edit: "Edit",
      common_close: "Close", common_refresh: "Refresh", common_loading: "Processing",
      common_loading_detail: "Please wait, do not close the page", common_submit: "Submit", common_confirm: "Confirm",
      common_back: "Back", common_yes: "Yes", common_no: "No",

      // errors
      error_422: "Submission incomplete or invalid", error_500: "Server failed (500)",
      error_502: "AI service returned nothing (502)", error_504: "Server timed out (504)",
      error_request_failed: "Request failed ({status})", error_retry_later: "Please retry later",

      // admin
      admin_page_title: "ZhiDa Resume · Admin", admin_subtitle: "Admin Console", admin_brand: "System Admin",
      admin_title: "System Operations Console", admin_sub: "Manage users, generation records, model calls and object storage in one place.",
      admin_username: "Admin Username", admin_login: "Sign In to Admin", admin_back_user: "Back to user site",
      admin_overview: "Overview", admin_users: "Users", admin_orders: "Orders & Credits",
      admin_records: "Records", admin_tasks: "Tasks", admin_templates: "Templates",
      admin_security: "Password", admin_logout: "Log out"
    }
  };

  /* ---------------- SVG 图标 ---------------- */
  var ICONS = {
    auto: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="14" rx="2"/><path d="M8 21h8M12 18v3"/></svg>',
    light: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    dark: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
    globe: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'
  };

  /* ---------------- 偏好读写（含旧 key 一次性迁移） ---------------- */
  function loadPrefs() {
    var p;
    try { p = JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch (e) { p = null; }
    if (!p || typeof p !== "object") p = {};
    // 一次性迁移旧 key
    var legacyTheme = localStorage.getItem(LEGACY_THEME_KEY);
    if (!p.theme && legacyTheme) p.theme = legacyTheme === "light" ? "light" : legacyTheme === "auto" ? "auto" : "dark";
    var legacyLang = localStorage.getItem(LEGACY_LANG_KEY);
    if (!p.lang && legacyLang) p.lang = legacyLang === "en" ? "en" : "zh";
    return { theme: THEME_ORDER.indexOf(p.theme) >= 0 ? p.theme : DEFAULTS.theme,
             lang: p.lang === "en" ? "en" : DEFAULTS.lang };
  }
  function savePrefs() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch (e) {}
  }
  // 迁移完成后清理旧 key（避免将来误读）
  function cleanupLegacyKeys() {
    try {
      if (localStorage.getItem(LEGACY_THEME_KEY) !== null || localStorage.getItem(LEGACY_LANG_KEY) !== null) {
        localStorage.removeItem(LEGACY_THEME_KEY);
        localStorage.removeItem(LEGACY_LANG_KEY);
      }
    } catch (e) {}
  }

  var prefs = loadPrefs();
  var mediaDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function resolveTheme(t) {
    if (t === "auto") {
      if (mediaDark && typeof mediaDark.matches === "boolean") return mediaDark.matches ? "dark" : "light";
      return "dark"; // 无 matchMedia 环境回退深色（产品默认深色）
    }
    return t === "light" ? "light" : "dark";
  }

  /* ---------------- 主题应用 + 平滑过渡 ---------------- */
  var TRANSITIONING = false;
  function applyTheme(theme, opts) {
    var valid = THEME_ORDER.indexOf(theme) >= 0 ? theme : DEFAULTS.theme;
    prefs.theme = valid;
    savePrefs();
    var resolved = resolveTheme(valid);
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.style.colorScheme = resolved;

    // 平滑过渡（尊重 reduced-motion）
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var root = document.documentElement;
    if (opts && opts.smooth && !reduce && !TRANSITIONING) {
      TRANSITIONING = true;
      root.classList.add("theme-transition");
      setTimeout(function () {
        root.classList.remove("theme-transition");
        TRANSITIONING = false;
      }, 260);
    }
    updateControls();
  }

  /* ---------------- 语言应用 + 翻译 ---------------- */
  function applyLang(lang) {
    var valid = lang === "en" ? "en" : "zh";
    prefs.lang = valid;
    savePrefs();
    document.documentElement.lang = valid === "zh" ? "zh-CN" : "en";
    document.body.setAttribute("data-lang", valid);
    translateDom(document);
    translateReactRoot();
    updateControls();
  }

  function t(key, fallback) {
    return (DICTIONARY[prefs.lang] && DICTIONARY[prefs.lang][key]) || fallback || key;
  }

  // 仅替换第一个非空文本节点，保留子图标/span
  function setTextPreservingChildren(el, value) {
    var nodes = el.childNodes;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].nodeType === Node.TEXT_NODE && nodes[i].textContent.trim().length > 0) {
        nodes[i].textContent = value;
        return;
      }
    }
    if (el.childNodes.length === 0 || el.textContent.trim().length === 0) {
      el.textContent = value;
    }
  }

  var TRANSLATED_MARK = "data-prefs-translated";
  function translateDom(root) {
    var scope = root && root.querySelectorAll ? root : document;
    // 1) data-i18n 属性元素
    scope.querySelectorAll("[data-i18n]").forEach(function (el) {
      var keys = el.getAttribute("data-i18n").split(";");
      keys.forEach(function (pair) {
        var parts = pair.split(":");
        var attr = parts.length > 1 ? parts[0] : "text";
        var key = parts.length > 1 ? parts[1] : parts[0];
        if (!key) return;
        var value = t(key, attr === "text" ? el.textContent.trim() : el.getAttribute(attr));
        if (attr === "text") setTextPreservingChildren(el, value);
        else el.setAttribute(attr, value);
      });
      el.setAttribute(TRANSLATED_MARK, "1");
    });
    // 2) data-i18n-placeholder 元素
    scope.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      el.placeholder = t(el.getAttribute("data-i18n-placeholder"), el.placeholder);
      el.setAttribute(TRANSLATED_MARK, "1");
    });
  }

  /* ---------------- React 登录卡 有界文本翻译 ----------------
     登录卡由 React 硬编码中文（无 data-i18n），历史包袱。为兼顾语言切换，
     仅对 #auth-react-root 内部做有界 TreeWalker：只替换纯文本节点，不扫
     全站，避免旧方案的全文档扫描误伤。React 重渲染会覆盖，由
     translateReactRoot 重新补齐（MutationObserver 已覆盖 #auth-react-root）。
     切换语言时对 data-lang="zh" 跳过，避免无谓扫描。 */
  var REACT_TEXT_MAP = {
    zh: {
      // 反向映射（en → zh，用于切回中文时恢复）
      "Turn every experience into ": "让每一份经历，",
      "the match for ": "匹配",
      "your next opportunity.": "下一份机会。",
      "AI understands your background, tracks the job market in real time, and brings resume optimization, matching and outreach into one career system.": "AI 深度理解你的经历与优势，实时洞察岗位市场，把简历优化、机会匹配和投递推进放进同一个职业系统。",
      "AI Career OS": "AI 职业操作系统",
      "AI is connecting to opportunities": "AI 正在连接职业机会",
      "Keyword Coverage": "岗位关键词覆盖",
      "Resume Optimization": "完成简历优化",
      "Real-time Matching": "实时岗位匹配",
      "Sign In": "登录", "Sign Up": "注册",
      "Password": "密码", "SMS Code": "手机验证码",
      "Username": "用户名",
      "Remember me": "记住我", "Forgot?": "忘记密码？",
      "Welcome Back": "欢迎回来",
      "Let AI work for your career": "继续让 AI 为你的职业机会持续工作",
      "Create your career entry": "创建你的职业入口",
      "Verify your phone to build your personal job system": "完成手机号验证后，即可建立专属求职系统",
      "Reset Password": "重设登录密码",
      "Verify your phone to set a new password": "验证绑定手机号后，安全设置新密码",
      "Phone": "手机号", "Enter code": "请输入验证码",
      "Send Code": "发送验证码", "Confirm Password": "确认密码",
      "New Password": "新密码", "Confirm New Password": "确认新密码",
      "Set Password": "设置密码", "Enter Workspace": "进入工作台",
      "Create Entry": "创建职业入口", "Save Password": "保存新密码",
      "No account? ": "还没有账号？", "Sign Up Now": "立即注册",
      "Back to Sign In": "返回登录", "Android App Installer": "Android App 完整安装包",
      "Download": "下载", "Latest": "最新版本", "Verifying…": "正在验证…",
      "Enter username": "请输入用户名", "Enter password": "请输入密码",
      "Enter phone": "请输入手机号",
      "3 to 40 characters": "3 至 40 个字符", "At least 8 characters": "至少 8 位密码",
      "Confirm password": "再次输入密码", "Re-enter new password": "再次输入新密码",
      "Enter a valid 11-digit phone": "请先输入正确的 11 位手机号",
      "Code sent, check your phone": "验证码已发送，请注意查收",
      "Passwords do not match": "两次输入的密码不一致",
      "New passwords do not match": "两次输入的新密码不一致",
      "Verified, entering your workspace…": "验证成功，正在进入你的职业工作台…",
      "Password updated, sign in with the new one": "密码已更新，请使用新密码登录",
      "Admins: use the admin console": "管理员请从后台入口登录",
      "s resend": "s 后重发"
    },
    en: {
      // App.jsx 首屏（文本节点片段）
      "AI 职业操作系统": "AI Career OS",
      "AI 正在连接职业机会": "AI is connecting to opportunities",
      "让每一份经历，": "Turn every experience into ",
      "匹配": "the match for ",
      "下一份机会。": "your next opportunity.",
      "AI 深度理解你的经历与优势，实时洞察岗位市场，把简历优化、机会匹配和投递推进放进同一个职业系统。": "AI understands your background, tracks the job market in real time, and brings resume optimization, matching and outreach into one career system.",
      // 岗位关键词覆盖等统计
      "岗位关键词覆盖": "Keyword Coverage",
      "完成简历优化": "Resume Optimization",
      "实时岗位匹配": "Real-time Matching",
      // 登录卡
      "登录": "Sign In", "注册": "Sign Up",
      "账号密码": "Password", "手机验证码": "SMS Code",
      "用户名": "Username", "密码": "Password",
      "记住我": "Remember me", "忘记密码？": "Forgot?",
      "欢迎回来": "Welcome Back",
      "继续让 AI 为你的职业机会持续工作": "Let AI work for your career",
      "创建你的职业入口": "Create your career entry",
      "完成手机号验证后，即可建立专属求职系统": "Verify your phone to build your personal job system",
      "重设登录密码": "Reset Password",
      "验证绑定手机号后，安全设置新密码": "Verify your phone to set a new password",
      "手机号": "Phone", "短信验证码": "SMS Code",
      "发送验证码": "Send Code", "确认密码": "Confirm Password",
      "新密码": "New Password", "确认新密码": "Confirm New Password",
      "设置密码": "Set Password", "进入工作台": "Enter Workspace",
      "创建职业入口": "Create Entry", "保存新密码": "Save Password",
      "还没有账号？": "No account? ", "立即注册": "Sign Up Now",
      "返回登录": "Back to Sign In", "Android App 完整安装包": "Android App Installer",
      "下载": "Download", "最新版本": "Latest", "正在验证…": "Verifying…",
      // placeholders
      "请输入用户名": "Enter username", "请输入密码": "Enter password",
      "请输入手机号": "Enter phone", "请输入验证码": "Enter code",
      "3 至 40 个字符": "3 to 40 characters", "至少 8 位密码": "At least 8 characters",
      "再次输入密码": "Confirm password", "再次输入新密码": "Re-enter new password",
      "记住我": "Remember me",
      // 校验/状态消息
      "请先输入正确的 11 位手机号": "Enter a valid 11-digit phone",
      "验证码已发送，请注意查收": "Code sent, check your phone",
      "两次输入的密码不一致": "Passwords do not match",
      "两次输入的新密码不一致": "New passwords do not match",
      "验证成功，正在进入你的职业工作台…": "Verified, entering your workspace…",
      "密码已更新，请使用新密码登录": "Password updated, sign in with the new one",
      "管理员请从后台入口登录": "Admins: use the admin console",
      // cooldown 后缀
      "s 后重发": "s resend"
    }
  };
  function translateReactRoot() {
    var root = document.getElementById("auth-react-root");
    if (!root) return;
    var map = REACT_TEXT_MAP[prefs.lang] || REACT_TEXT_MAP.en;
    if (!map) return;
    // 纯文本节点（仅在 textContent 完全命中词典时替换，避免切割 HTML）
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
    var node;
    while ((node = walker.nextNode())) {
      var text = node.nodeValue;
      if (!text) continue;
      var trimmed = text.trim();
      if (trimmed && map[trimmed]) {
        node.nodeValue = text.replace(trimmed, map[trimmed]);
      }
    }
    // placeholder 属性（只命中完全匹配，不误伤）
    root.querySelectorAll("input[placeholder]").forEach(function (input) {
      var ph = input.placeholder.trim();
      if (ph && map[ph]) input.placeholder = map[ph];
    });
  }

  /* ---------------- MutationObserver 增量翻译（替代轮询+TreeWalker） ---------------- */
  var observer = null;
  function startObserver() {
    if (!window.MutationObserver || observer) return;
    observer = new MutationObserver(function (mutations) {
      var dirty = [];
      var reactDirty = false;
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
          if (node.nodeType !== Node.ELEMENT_NODE) return;
          // React 登录卡区域：任何新增节点都触发登录卡文本翻译
          if (node.id === "auth-react-root" || node.classList && node.classList.contains("ai-login-shell")) {
            reactDirty = true;
          }
          // 新增元素内若含未翻译的 data-i18n 节点则处理
          if (node.querySelectorAll && (node.querySelectorAll("[data-i18n]").length ||
              node.querySelectorAll("[data-i18n-placeholder]").length)) {
            dirty.push(node);
          }
        });
      });
      if (dirty.length) {
        dirty.forEach(function (node) {
          if (prefs.lang !== "zh") translateDom(node);
        });
      }
      // React 登录卡挂载/重渲染后补齐文本翻译（有界，仅 React 区域）
      if (prefs.lang === "en" && (reactDirty || dirty.length)) {
        translateReactRoot();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* ---------------- 分段控制条渲染 ---------------- */
  function setControlLabels(container) {
    container.querySelectorAll(".ui-prefs-theme-btn").forEach(function (btn) {
      var mode = btn.getAttribute("data-theme-mode");
      btn.innerHTML = ICONS[mode] + "<span>" + t("theme_" + mode, mode) + "</span>";
      btn.setAttribute("aria-pressed", prefs.theme === mode ? "true" : "false");
      btn.classList.toggle("is-active", prefs.theme === mode);
    });
    container.querySelectorAll(".ui-prefs-lang-btn").forEach(function (btn) {
      var lg = btn.getAttribute("data-lang-mode");
      btn.textContent = t("lang_" + lg, lg.toUpperCase());
      btn.setAttribute("aria-pressed", prefs.lang === lg ? "true" : "false");
      btn.classList.toggle("is-active", prefs.lang === lg);
    });
  }

  function updateControls() {
    document.querySelectorAll(".ui-prefs").forEach(setControlLabels);
  }

  function renderControls(container) {
    if (!container) return;
    if (container.querySelector(".ui-prefs")) return; // 已渲染

    var wrap = document.createElement("div");
    wrap.className = "ui-prefs";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", t("lang_label", "外观与语言"));
    wrap.innerHTML =
      '<div class="ui-prefs__group ui-prefs__theme" role="tablist" aria-label="' + t("theme_auto", "主题") + '">' +
        '<button type="button" class="ui-prefs-btn ui-prefs-theme-btn" data-theme-mode="auto" role="tab" aria-selected="false"></button>' +
        '<button type="button" class="ui-prefs-btn ui-prefs-theme-btn" data-theme-mode="light" role="tab" aria-selected="false"></button>' +
        '<button type="button" class="ui-prefs-btn ui-prefs-theme-btn" data-theme-mode="dark" role="tab" aria-selected="false"></button>' +
      '</div>' +
      '<div class="ui-prefs__group ui-prefs__lang" role="group" aria-label="' + t("lang_label", "语言") + '">' +
        '<button type="button" class="ui-prefs-btn ui-prefs-lang-btn" data-lang-mode="zh" aria-pressed="false"></button>' +
        '<button type="button" class="ui-prefs-btn ui-prefs-lang-btn" data-lang-mode="en" aria-pressed="false"></button>' +
      '</div>';

    wrap.querySelectorAll(".ui-prefs-theme-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        applyTheme(btn.getAttribute("data-theme-mode"), { smooth: true });
      });
    });
    wrap.querySelectorAll(".ui-prefs-lang-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        applyLang(btn.getAttribute("data-lang-mode"));
      });
    });

    container.appendChild(wrap);
    setControlLabels(wrap);
  }

  function mountAll() {
    document.querySelectorAll("[data-ui-preferences]").forEach(renderControls);
    mountAuthCorner();
    updateControls();
  }

  /* ---------------- 登录页右上角控件（React 外稳定节点） ----------------
     登录/落地页的 React 登录卡由 auth-login.js 渲染，其内部节点归 React 管理，
     不可直接注入。旧 global-theme-i18n.js 的做法是注入 #auth-view（React 外
     main 节点），固定右上角；登录后 app.js 隐藏 #auth-view，控件随之消失。 */
  function mountAuthCorner() {
    var authView = document.getElementById("auth-view");
    if (!authView) return;
    if (authView.querySelector(".ui-prefs-auth-corner")) return;
    var corner = document.createElement("div");
    corner.className = "ui-prefs-auth-corner";
    authView.appendChild(corner);
    renderControls(corner);
  }

  /* ---------------- 兼容旧接口 ---------------- */
  window.__i18n = {
    t: t,
    translate: translateDom,
    prefs: function () { return { theme: prefs.theme, lang: prefs.lang }; },
    setLang: applyLang,
    setTheme: applyTheme
  };
  // app.js 的 window.zhidaI18n(key) 同步接口
  window.zhidaI18n = function (key) { return t(key); };

  /* ---------------- auto 实时跟随系统 ---------------- */
  if (mediaDark && typeof mediaDark.addEventListener === "function") {
    mediaDark.addEventListener("change", function (e) {
      if (prefs.theme === "auto") applyTheme("auto", { smooth: true });
    });
  } else if (mediaDark && typeof mediaDark.addListener === "function") {
    mediaDark.addListener(function () { if (prefs.theme === "auto") applyTheme("auto", { smooth: true }); });
  }

  /* ---------------- 初始化 ---------------- */
  function init() {
    cleanupLegacyKeys();
    applyTheme(prefs.theme, { smooth: false });
    applyLang(prefs.lang);
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mountAll);
    } else {
      mountAll();
    }
    startObserver();
    // React 挂载完成后立即翻译登录卡（延迟到微任务后，确保 React 首帧已渲染）
    if (document.readyState !== "loading") {
      setTimeout(function () { if (prefs.lang === "en") translateReactRoot(); }, 80);
    }
    // React 路由切换后重挂载控件（轻量，不再做全文 TreeWalker 翻译）
    window.addEventListener("load", mountAll);
    if (document.addEventListener) {
      document.addEventListener("visibilitychange", function () {
        if (!document.hidden) mountAll();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
