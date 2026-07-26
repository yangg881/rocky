/**
 * Global Theme & i18n Manager for 职达简历 (Zhida Resume)
 * Embedded Controls & Full i18n Translation Engine
 */

(function () {
  const STORAGE_THEME_KEY = "zhida_global_theme";
  const STORAGE_LANG_KEY = "zhida_global_lang";

  const i18nDict = {
    zh: {
      app_title: "职达简历",
      nav_remaining: "剩余额度",
      unit_times: "次",
      nav_overview: "求职驾驶舱",
      nav_resumes: "简历优化",
      nav_radar: "岗位雷达",
      nav_history: "生成记录",
      nav_settings: "套餐与额度",
      nav_admin: "管理后台",
      nav_logout: "退出登录",
      nav_login: "登录 / 注册",
      btn_set_default: "设为默认",
      btn_preview: "预览",
      btn_edit_rename: "编辑/重命名",
      btn_delete: "删除",
      badge_default: "默认",
      theme_dark: "🌙 深色",
      theme_light: "☀️ 浅色",
      lang_zh: "中文",
      lang_en: "English"
    },
    en: {
      app_title: "Zhida Resume AI",
      nav_remaining: "Remaining",
      unit_times: "credits",
      nav_overview: "Career Dashboard",
      nav_resumes: "Resumes",
      nav_radar: "Job Radar",
      nav_history: "Generations",
      nav_settings: "Plans & Credits",
      nav_admin: "Admin Panel",
      nav_logout: "Sign Out",
      nav_login: "Sign In / Register",
      btn_set_default: "Set Default",
      btn_preview: "Preview",
      btn_edit_rename: "Edit / Rename",
      btn_delete: "Delete",
      badge_default: "Default",
      theme_dark: "🌙 Dark",
      theme_light: "☀️ Light",
      lang_zh: "中文",
      lang_en: "English"
    }
  };

  // Text mappings for translating React rendered Auth components
  const reactTranslations = {
    en: {
      "欢迎回来": "Welcome Back",
      "继续让 AI 为你的职业机会持续工作": "Let AI work for your career opportunities continuously",
      "账号密码": "Password Login",
      "手机验证码": "SMS Code",
      "用户名": "Username",
      "密码": "Password",
      "请输入用户名": "Enter username",
      "请输入密码": "Enter password",
      "记住我": "Remember me",
      "忘记密码?": "Forgot Password?",
      "进入工作台 →": "Enter Workspace →",
      "还没有账号？ 立即注册": "No account? Register now",
      "没有账号， 去注册": "No account? Register",
      "立即注册": "Register Now",
      "去注册": "Register",
      "创建账号": "Create Account",
      "手机号验证后即可开始使用": "Verify phone to get started",
      "手机号": "Phone Number",
      "短信验证码": "SMS Code",
      "发送验证码": "Send Code",
      "Android App 完整安装包": "Android App Full Installer",
      "Android App": "Android App",
      "下载": "Download",
      "正在读取版本…": "Loading version...",
      "登录": "Sign In",
      "注册": "Register",
      "让每一份经历，匹配下一份机会。": "Make Every Experience Match Your Next Opportunity.",
      "让每一份经历，匹配下一份机会": "Match Every Experience To Next Opportunity",
      "AI 深度理解你的经历与优势，实时洞察岗位市场，把简历优化、机会匹配和投递推进放进同一个职业系统。": "AI understands your background, insights into market jobs, and optimizes resumes seamlessly.",
      "岗位关键词覆盖": "Job Keywords Coverage",
      "完成简历优化": "Resume Optimization",
      "实时岗位匹配": "Real-time Job Matching",
      "三步做出一份能投的简历": "Create a Tailored Resume in 3 Steps",
      "1. 准备基础简历": "1. Prepare Base Resume",
      "2. 选目标岗位": "2. Select Target Job",
      "3. 生成并下载": "3. Generate & Download",
      "用一份基础简历，生成多份岗位专属版本": "Generate Multiple Tailored Resumes from One Base Resume",
      "先保存真实经历，再从岗位雷达带入岗位；AI 只优化表达，不会编造事实。": "Save real experiences first, then match jobs from Job Radar. AI refines expression without fabricating facts.",
      "手动适配岗位": "Manually Adapt Job",
      "在线填写": "Online Form",
      "上传文档": "Upload File",
      "截图识别": "Screenshot OCR",
      "在线填写职业资料": "Fill Out Career Details Online",
      "开始填写": "Start Filling",
      "已保存的简历": "Saved Resumes",
      "设为默认": "Set Default",
      "更换头像": "Change Avatar",
      "预览": "Preview",
      "编辑/重命名": "Edit / Rename",
      "删除": "Delete",
      "默认": "Default"
    }
  };

  function getSavedTheme() {
    return localStorage.getItem(STORAGE_THEME_KEY) || "dark";
  }

  function applyTheme(theme) {
    const validTheme = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", validTheme);
    if (document.body) {
      document.body.setAttribute("data-theme", validTheme);
      document.body.classList.toggle("theme-light", validTheme === "light");
      document.body.classList.toggle("theme-dark", validTheme === "dark");
    }
    localStorage.setItem(STORAGE_THEME_KEY, validTheme);
    updateToggleButtonsUI();
  }

  function toggleTheme() {
    const current = getSavedTheme();
    applyTheme(current === "dark" ? "light" : "dark");
  }

  function getSavedLang() {
    return localStorage.getItem(STORAGE_LANG_KEY) || "zh";
  }

  function applyLanguage(lang) {
    const validLang = lang === "en" ? "en" : "zh";
    localStorage.setItem(STORAGE_LANG_KEY, validLang);
    const dict = i18nDict[validLang];

    // 1. Update data-i18n elements
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (dict[key]) {
        if (el.tagName === "INPUT" && el.hasAttribute("placeholder")) {
          el.placeholder = dict[key];
        } else {
          el.innerHTML = dict[key];
        }
      }
    });

    // 2. Translate React rendered text nodes if language is English
    if (validLang === "en") {
      const map = reactTranslations.en;
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
      let node;
      while ((node = walker.nextNode())) {
        const text = node.nodeValue ? node.nodeValue.trim() : "";
        if (text && map[text]) {
          node.nodeValue = map[text];
        }
      }
      // Also placeholders
      document.querySelectorAll("input[placeholder]").forEach((input) => {
        const ph = input.placeholder.trim();
        if (map[ph]) {
          input.placeholder = map[ph];
        }
      });
    }

    updateToggleButtonsUI();
  }

  function toggleLanguage() {
    const current = getSavedLang();
    applyLanguage(current === "zh" ? "en" : "zh");
  }

  function updateToggleButtonsUI() {
    const theme = getSavedTheme();
    const lang = getSavedLang();

    document.querySelectorAll(".zhida-theme-toggle-btn").forEach((btn) => {
      btn.innerHTML = theme === "dark" ? "🌙 " + i18nDict[lang].theme_dark.split(" ")[1] : "☀️ " + i18nDict[lang].theme_light.split(" ")[1];
    });

    document.querySelectorAll(".zhida-lang-toggle-btn").forEach((btn) => {
      btn.innerHTML = lang === "zh" ? "🌐 English" : "🌐 中文";
    });
  }

  window.zhidaI18n = function (key) {
    const lang = getSavedLang();
    return (i18nDict[lang] && i18nDict[lang][key]) || (i18nDict["zh"][key] || key);
  };

  // Embed controls seamlessly inside Auth page corner or Workspace Sidebar
  function injectEmbeddedControls() {
    // 1. Landing / Login Page — pin controls to the TOP-RIGHT corner of the page.
    //    IMPORTANT: inject into #auth-view (a stable node from index.html), NOT into
    //    .ai-login-shell. The shell lives inside React's root (#auth-react-root), so
    //    React's reconciliation strips any foreign child on re-render and the buttons
    //    vanish. #auth-view is outside React's control and is only visible before login
    //    (app.js hides it once the workspace shows), so the buttons appear immediately
    //    and persist for logged-out visitors.
    const authView = document.getElementById("auth-view");
    if (authView && !document.getElementById("auth-pref-group")) {
      const group = document.createElement("div");
      group.id = "auth-pref-group";
      group.className = "zhida-embedded-pref-group auth-corner-pref";
      group.innerHTML = `
        <button type="button" class="zhida-embedded-btn zhida-theme-toggle-btn">🌙 深色</button>
        <button type="button" class="zhida-embedded-btn zhida-lang-toggle-btn">🌐 English</button>
      `;
      authView.appendChild(group);

      group.querySelector(".zhida-theme-toggle-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        toggleTheme();
      });
      group.querySelector(".zhida-lang-toggle-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        toggleLanguage();
      });
    }

    // 2. Logged in Workspace Sidebar — place controls in the sidebar FOOT as a
    //    dedicated row. NEVER inject into .sidebar-brand: a width:100% group there
    //    squeezes the brand text into vertical stacking and clutters the logo.
    const sidebarFoot = document.querySelector(".sidebar-foot");
    if (sidebarFoot && !document.getElementById("sidebar-pref-group")) {
      const group = document.createElement("div");
      group.id = "sidebar-pref-group";
      group.className = "sidebar-pref-row";
      group.innerHTML = `
        <button type="button" class="zhida-embedded-btn zhida-theme-toggle-btn">🌙 深色</button>
        <button type="button" class="zhida-embedded-btn zhida-lang-toggle-btn">🌐 English</button>
      `;
      sidebarFoot.appendChild(group);

      group.querySelector(".zhida-theme-toggle-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        toggleTheme();
      });
      group.querySelector(".zhida-lang-toggle-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        toggleLanguage();
      });
    }

    updateToggleButtonsUI();
  }

  function init() {
    applyTheme(getSavedTheme());
    applyLanguage(getSavedLang());
    injectEmbeddedControls();

    // Check periodically for React re-renders or navigation changes
    setInterval(() => {
      injectEmbeddedControls();
      if (getSavedLang() === "en") {
        applyLanguage("en");
      }
    }, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.setZhidaTheme = applyTheme;
  window.setZhidaLang = applyLanguage;
  window.toggleZhidaTheme = toggleTheme;
  window.toggleZhidaLang = toggleLanguage;
})();
