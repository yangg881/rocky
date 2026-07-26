/*
 * UI Preferences: theme (light/dark) and language (zh/en) toggles.
 * Persisted to localStorage. Applied immediately across pages.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "zhiday_ui_prefs";
  const DEFAULTS = { theme: "auto", lang: "zh" };

  const DICTIONARY = {
    zh: {
      // theme/lang toggles
      theme_auto: "自动",
      theme_light: "浅色",
      theme_dark: "深色",
      lang_label: "语言",

      // auth page
      auth_title: "让每一份经历，匹配下一份机会。",
      auth_lead: "基于 AI 岗位分析，优化简历表达，自动生成求职材料，让你的优势被看见，也让机会主动找到你。",
      auth_login: "登录",
      auth_register: "注册",
      auth_welcome_back: "欢迎回来",
      auth_login_sub: "登录后继续你的简历优化之旅",
      auth_password: "账号密码",
      auth_sms: "手机验证码",
      auth_username: "用户名",
      auth_username_placeholder: "请输入用户名",
      auth_password_label: "密码",
      auth_password_placeholder: "请输入密码",
      auth_remember: "记住我",
      auth_legal_consent_prefix: "登录即代表你已阅读并同意 ",
      auth_legal_terms: "用户服务协议",
      auth_legal_privacy: "隐私保护政策",
      auth_legal_disclaimer: "免责声明",
      auth_forgot: "忘记密码?",
      auth_phone: "手机号",
      auth_phone_placeholder: "请输入已绑定手机号",
      auth_code: "短信验证码",
      auth_code_placeholder: "请输入验证码",
      auth_send_code: "发送验证码",
      auth_sms_tip: "验证码仅用于登录已绑定的账号。",
      auth_enter: "进入工作台",
      auth_create_account: "创建账号",
      auth_create_sub: "手机号验证后即可开始使用",
      auth_no_account: "没有账号，",
      auth_go_register: "去注册",
      auth_reset: "重置密码",
      auth_reset_sub: "通过账号绑定手机号验证身份，再设置一个新的登录密码。",
      auth_new_password: "新密码",
      auth_new_password_placeholder: "至少 8 位密码",
      auth_confirm_password: "确认密码",
      auth_confirm_placeholder: "再次输入密码",
      auth_save_password: "保存新密码",
      auth_back: "返回登录",
      auth_app_download: "Android App 完整安装包",
      auth_app_reading: "正在读取版本…",
      auth_app_download_btn: "下载",

      // nav
      nav_section_workbench: "求职工作台",
      nav_job_radar: "岗位雷达",
      nav_resume: "简历优化",
      nav_history: "求职记录",
      nav_settings: "我的",
      nav_logout: "退出账号",
      nav_credits: "额度",
      nav_remaining: "剩余",
      unit_times: "次",

      // onboarding
      onboard_eyebrow: "最短路径",
      onboard_title: "三步做出一份能投的简历",
      onboard_step1: "1. 准备基础简历",
      onboard_step1_desc: "上传或在线填写真实经历",
      onboard_step1_btn: "去准备",
      onboard_step2: "2. 选目标岗位",
      onboard_step2_desc: "岗位雷达一键带入，或手动粘贴 JD",
      onboard_step2_btn: "去选岗",
      onboard_step3: "3. 生成并下载",
      onboard_step3_desc: "AI 只优化表达，不编造；预览后下载 Word/PDF",
      onboard_step3_btn: "看作品",
      onboard_dismiss: "知道了，先藏起来",

      // common
      common_save: "保存",
      common_cancel: "取消",
      common_delete: "删除",
      common_edit: "编辑",
      common_close: "关闭",
      common_refresh: "刷新",
      common_loading: "正在处理",
      common_loading_detail: "请稍候，不要关闭页面",
      common_submit: "提交",
      common_confirm: "确认",
      common_back: "返回",
      common_yes: "是",
      common_no: "否",

      // errors
      error_422: "提交内容不完整或格式不正确",
      error_500: "服务器处理失败（500）",
      error_502: "AI 服务暂时没有返回结果（502）",
      error_504: "服务器处理超时（504）",
      error_request_failed: "请求失败（{status}）",
      error_retry_later: "请稍后重试",

      // admin
      admin_page_title: "职达简历 · 管理后台",
      admin_subtitle: "独立管理后台",
      admin_brand: "系统管理",
      admin_title: "系统运维控制台",
      admin_sub: "用户、生成记录、模型调用与对象存储状态集中管理。",
      admin_username: "管理员账号",
      admin_login: "登录后台",
      admin_back_user: "返回用户端",
      admin_overview: "数据总览",
      admin_users: "用户管理",
      admin_orders: "订单与额度",
      admin_records: "生成记录",
      admin_tasks: "任务记录",
      admin_templates: "模板管理",
      admin_security: "修改密码",
      admin_logout: "退出后台",
    },
    en: {
      // theme/lang toggles
      theme_auto: "Auto",
      theme_light: "Light",
      theme_dark: "Dark",
      lang_label: "Language",

      // auth page
      auth_title: "Turn every experience into your next opportunity.",
      auth_lead: "AI-powered job matching and resume optimization. Generate editable Word and PDF resumes that make your strengths stand out.",
      auth_login: "Sign In",
      auth_register: "Sign Up",
      auth_welcome_back: "Welcome back",
      auth_login_sub: "Log in to continue optimizing your resume",
      auth_password: "Password",
      auth_sms: "SMS Code",
      auth_username: "Username",
      auth_username_placeholder: "Enter username",
      auth_password_label: "Password",
      auth_password_placeholder: "Enter password",
      auth_remember: "Remember me",
      auth_legal_consent_prefix: "By logging in you agree to our ",
      auth_legal_terms: "Terms of Service",
      auth_legal_privacy: "Privacy Policy",
      auth_legal_disclaimer: "Disclaimer",
      auth_forgot: "Forgot password?",
      auth_phone: "Phone",
      auth_phone_placeholder: "Enter registered phone",
      auth_code: "SMS Code",
      auth_code_placeholder: "Enter code",
      auth_send_code: "Send Code",
      auth_sms_tip: "Code is only used to log in to a bound account.",
      auth_enter: "Enter Workbench",
      auth_create_account: "Create Account",
      auth_create_sub: "Start using after phone verification",
      auth_no_account: "No account? ",
      auth_go_register: "Sign up",
      auth_reset: "Reset Password",
      auth_reset_sub: "Verify with the bound phone number, then set a new password.",
      auth_new_password: "New Password",
      auth_new_password_placeholder: "At least 8 characters",
      auth_confirm_password: "Confirm Password",
      auth_confirm_placeholder: "Enter password again",
      auth_save_password: "Save Password",
      auth_back: "Back to Sign In",
      auth_app_download: "Android App Full Installer",
      auth_app_reading: "Reading version…",
      auth_app_download_btn: "Download",

      // nav
      nav_section_workbench: "Workbench",
      nav_job_radar: "Job Radar",
      nav_resume: "Resume",
      nav_history: "History",
      nav_settings: "Settings",
      nav_logout: "Log out",
      nav_credits: "Credits",
      nav_remaining: "Remaining",
      unit_times: "times",

      // onboarding
      onboard_eyebrow: "FAST TRACK",
      onboard_title: "Three steps to an application-ready resume",
      onboard_step1: "1. Prepare resume",
      onboard_step1_desc: "Upload or fill in your real experience",
      onboard_step1_btn: "Prepare",
      onboard_step2: "2. Pick target job",
      onboard_step2_desc: "Use Job Radar or paste a JD manually",
      onboard_step2_btn: "Pick Job",
      onboard_step3: "3. Generate & download",
      onboard_step3_desc: "AI polishes wording without inventing; preview and download Word/PDF",
      onboard_step3_btn: "View Work",
      onboard_dismiss: "Got it, hide this",

      // common
      common_save: "Save",
      common_cancel: "Cancel",
      common_delete: "Delete",
      common_edit: "Edit",
      common_close: "Close",
      common_refresh: "Refresh",
      common_loading: "Processing",
      common_loading_detail: "Please wait, do not close the page",
      common_submit: "Submit",
      common_confirm: "Confirm",
      common_back: "Back",
      common_yes: "Yes",
      common_no: "No",

      // admin
      admin_page_title: "ZhiDa Resume · Admin",
      admin_subtitle: "Admin Console",
      admin_brand: "System Admin",
      admin_title: "System Operations Console",
      admin_sub: "Manage users, generation records, model calls and object storage in one place.",
      admin_username: "Admin Username",
      admin_login: "Sign In to Admin",
      admin_back_user: "Back to user site",
      admin_overview: "Overview",
      admin_users: "Users",
      admin_orders: "Orders & Credits",
      admin_records: "Records",
      admin_tasks: "Tasks",
      admin_templates: "Templates",
      admin_security: "Password",
      admin_logout: "Log out",
    }
  };

  function loadPrefs() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
    } catch {}
    return { ...DEFAULTS };
  }

  function savePrefs(prefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch {}
  }

  const prefs = loadPrefs();

  function applyTheme(theme) {
    const resolved = theme === "auto"
      ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : theme;
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.style.colorScheme = resolved;
  }

  function applyLang(lang) {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    document.body.setAttribute("data-lang", lang);
    translateDom();
    updateToggleLabels();
  }

  function t(key, fallback) {
    return (DICTIONARY[prefs.lang] && DICTIONARY[prefs.lang][key]) || fallback || key;
  }

  function setTextPreservingChildren(el, value) {
    // Replace only the first non-empty text node, preserving icons/spans.
    for (const node of el.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) {
        node.textContent = value;
        return;
      }
    }
    // Fallback: if no text node found (e.g. only whitespace), prepend text.
    if (el.childNodes.length === 0 || el.textContent.trim().length === 0) {
      el.textContent = value;
    }
  }

  function translateDom(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach(el => {
      const keys = el.getAttribute("data-i18n").split(";");
      keys.forEach(pair => {
        const [attr, key] = pair.includes(":") ? pair.split(":") : ["text", pair];
        const value = t(key, attr === "text" ? el.textContent.trim() : el.getAttribute(attr));
        if (attr === "text") setTextPreservingChildren(el, value);
        else el.setAttribute(attr, value);
      });
    });
    scope.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      el.placeholder = t(el.getAttribute("data-i18n-placeholder"), el.placeholder);
    });
  }

  function cycleTheme() {
    const order = ["auto", "light", "dark"];
    const idx = order.indexOf(prefs.theme);
    prefs.theme = order[(idx + 1) % order.length];
    savePrefs(prefs);
    applyTheme(prefs.theme);
    updateToggleLabels();
  }

  function toggleLang() {
    prefs.lang = prefs.lang === "zh" ? "en" : "zh";
    savePrefs(prefs);
    applyLang(prefs.lang);
  }

  function updateToggleLabels() {
    document.querySelectorAll(".ui-theme-toggle").forEach(btn => {
      btn.textContent = t(`theme_${prefs.theme}`, prefs.theme);
      btn.setAttribute("aria-label", `${t("lang_label", "Language") === "语言" ? "外观" : "Theme"}: ${btn.textContent}`);
    });
    document.querySelectorAll(".ui-lang-toggle").forEach(btn => {
      btn.textContent = prefs.lang.toUpperCase();
      btn.setAttribute("aria-label", `${t("lang_label", "Language")}: ${prefs.lang}`);
    });
  }

  function renderToggles(container) {
    if (!container) return;
    const existing = container.querySelector(".ui-preferences");
    if (existing) return;

    const wrap = document.createElement("div");
    wrap.className = "ui-preferences";
    wrap.innerHTML = `
      <button type="button" class="ui-theme-toggle" aria-live="polite" title="Theme">Auto</button>
      <button type="button" class="ui-lang-toggle" aria-live="polite" title="Language">ZH</button>
    `;
    wrap.querySelector(".ui-theme-toggle").addEventListener("click", cycleTheme);
    wrap.querySelector(".ui-lang-toggle").addEventListener("click", toggleLang);
    container.appendChild(wrap);
    updateToggleLabels();
  }

  function init() {
    applyTheme(prefs.theme);

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        applyLang(prefs.lang);
        document.querySelectorAll("[data-ui-preferences]").forEach(renderToggles);
      });
    } else {
      applyLang(prefs.lang);
      document.querySelectorAll("[data-ui-preferences]").forEach(renderToggles);
    }

    // Re-apply translations after dynamic content changes by calling __i18n.translate().
    window.__i18n = { t, translate: translateDom, prefs: () => ({ ...prefs }), setLang: applyLang, setTheme: applyTheme };
  }

  init();
})();
