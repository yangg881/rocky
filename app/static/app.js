(() => {
  const BASE = window.location.pathname.replace(/\/$/, "");
  const API = `${BASE}/api`;
  const state = {
    // Web authentication lives in an HttpOnly cookie; keep this field only
    // for the Android-compatible response shape during the migration.
    token: null,
    user: null,
    resumes: [],
    history: [],
    dashboard: null,
    jd: null,
    editingId: null,
    jdImageFiles: [],
    jdHistory: [],
    jdTaskId: localStorage.getItem("resume_ai_jd_task"),
    jdTaskTimer: null,
    jdHistoryPollTimer: null,
    generationPollTimer: null,
    radarJobs: [],
    radarFacets: null,
    radarSummary: null,
    radarCities: [],
    radarPagination: null,
    radarFilters: { query: "", city: "", publishedWithin: "all", page: 1, savedOnly: false, onlyNew: false, salaryMin: 0, sortBy: "match", experience: "", education: "", topic: "", source: "" },
    radarResumeIds: [],
    radarJobId: null,
    careerFacts: [],
    reviews: [],
    applications: [],
    templates: [],
    selectedTemplateId: localStorage.getItem("resume_ai_template_id") || "",
    templatePickerMode: "generate",
    billing: null,
    avatarCrop: null,
    previewRun: 0,
    vendorScripts: {}
  };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  function escapeHtml(value = "") {
    return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  }

  function formatDate(value) {
    if (!value) return "";
    return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  }

  function toast(message, type = "success") {
    const element = $("#toast");
    element.textContent = message;
    element.className = `toast show ${type === "error" ? "error" : ""}`;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { element.className = "toast"; }, 3200);
  }

  function loading(show, text, detail) {
    const i18n = window.__i18n;
    $("#loading-text").textContent = text || (i18n ? i18n.t("common_loading", "正在处理") : "正在处理");
    const detailElement = $("#loading-detail");
    if (detailElement) detailElement.textContent = detail || (i18n ? i18n.t("common_loading_detail", "请稍候，不要关闭页面") : "请稍候，不要关闭页面");
    $("#loading").classList.toggle("hidden", !show);
  }

  function readableResponseText(raw) {
    const text = String(raw || "").trim();
    if (!text) return "";
    if (!/<[a-z][\s\S]*>/i.test(text)) return text.replace(/\s+/g, " ").slice(0, 500);
    try {
      const documentNode = new DOMParser().parseFromString(text, "text/html");
      documentNode.querySelectorAll("script, style").forEach((node) => node.remove());
      return String(documentNode.body?.textContent || documentNode.title || "").replace(/\s+/g, " ").trim().slice(0, 500);
    } catch {
      return text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 500);
    }
  }

  function errorDetailText(detail) {
    if (Array.isArray(detail)) return detail.map(errorDetailText).filter(Boolean).join("；");
    if (detail && typeof detail === "object") {
      if (detail.loc && detail.msg) return `${Array.isArray(detail.loc) ? detail.loc.join(".") : detail.loc}：${detail.msg}`;
      return errorDetailText(detail.msg || detail.message || detail.detail || detail.error) || JSON.stringify(detail);
    }
    return detail === null || detail === undefined ? "" : String(detail).trim();
  }

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
    if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
    const response = await fetch(`${API}${path}`, { ...options, headers, credentials: "same-origin" });
    if (response.status === 401 && !path.startsWith("/auth/")) logout({ notifyServer: false });
    const raw = response.status === 204 ? "" : await response.text();
    let data = null;
    if (raw.trim()) {
      try { data = JSON.parse(raw); } catch { data = null; }
    }
    if (!response.ok) {
      const detail = errorDetailText(data?.details) || errorDetailText(data?.detail || data?.message || data?.error) || readableResponseText(raw);
      const i18n = window.__i18n;
      const t = i18n ? i18n.t : (k, fb) => fb || k;
      const statusMessage = {
        422: t("error_422", "提交内容不完整或格式不正确"),
        500: t("error_500", "服务器处理失败（500）"),
        502: t("error_502", "AI 服务暂时没有返回结果（502）"),
        504: t("error_504", "服务器处理超时（504）")
      }[response.status] || t("error_request_failed", `请求失败（${response.status}）`);
      const retryHint = t("error_retry_later", "请稍后重试");
      throw new Error(detail ? `${statusMessage}：${detail}` : `${statusMessage}，${retryHint}`);
    }
    if (raw.trim() && data === null) throw new Error(`服务器返回格式异常（${response.status}）：${readableResponseText(raw)}`);
    return data;
  }

  function setAuth(data) {
    state.token = null;
    state.user = data.user;
    showApp();
  }

  function phoneDisplay(user = state.user) {
    return user?.phone_masked || user?.phone || "未绑定";
  }

  function updateAccountView() {
    $("#sidebar-user").textContent = state.user?.username || "";
    const accountUsername = $("#account-username");
    const accountAvatar = $("#account-avatar");
    if (accountUsername) accountUsername.textContent = state.user?.username || "用户";
    if (accountAvatar) {
      accountAvatar.textContent = (state.user?.username || "用").trim().slice(0, 1).toUpperCase();
      if (state.user?.avatar_url) {
        accountAvatar.innerHTML = `<img alt="" src="${escapeHtml(state.user.avatar_url)}">`;
      }
    }
    const accountAvatarButton = $("#account-avatar-button");
    if (accountAvatarButton) accountAvatarButton.textContent = state.user?.avatar_key ? "更换账号头像" : "设置账号头像";
    const currentPhone = $("#current-phone");
    if (currentPhone) currentPhone.textContent = phoneDisplay();
  }

  function logout({ notifyServer = true } = {}) {
    if (notifyServer) fetch(`${API}/auth/logout`, { method: "POST", credentials: "same-origin" }).catch(() => {});
    clearTimeout(state.jdTaskTimer);
    clearTimeout(state.jdHistoryPollTimer);
    state.jdHistoryPollTimer = null;
    state.jdTaskTimer = null;
    state.jdTaskId = null;
    localStorage.removeItem("resume_ai_jd_task");
    clearTimeout(state.generationPollTimer);
    state.generationPollTimer = null;
    state.token = null;
    state.user = null;
    $("#app-view").classList.add("hidden");
    $("#auth-view").classList.remove("hidden");
  }

  function maybeShowOnboarding() {
    const banner = $("#path-onboarding");
    if (!banner) return;
    const dismissed = localStorage.getItem("zhiday_onboarding_v1") === "1";
    const resumeCount = Number(state.dashboard?.counts?.resumes || state.resumes?.length || 0);
    if (dismissed && resumeCount > 0) {
      banner.classList.add("hidden");
      return;
    }
    banner.classList.remove("hidden");
    const step = resumeCount <= 0 ? 1 : (state.history?.some((item) => item.status === "completed") ? 3 : 2);
    $$("#path-onboarding [data-onboard-step]").forEach((el) => {
      el.classList.toggle("is-current", Number(el.dataset.onboardStep) === step);
      el.classList.toggle("is-done", Number(el.dataset.onboardStep) < step);
    });
  }

  async function showApp() {
    $("#auth-view").classList.add("hidden");
    $("#app-view").classList.remove("hidden");
    updateAccountView();
    await Promise.all([
      loadResumes(), loadHistory(), loadDashboard(), loadRadar(), loadBilling()
    ]);
    maybeShowOnboarding();
    const resumeCount = Number(state.dashboard?.counts?.resumes || state.resumes?.length || 0);
    navigate(resumeCount <= 0 ? "resumes" : "radar");
    if (state.jdTaskId) pollJdTask(state.jdTaskId);
  }

  async function loadAppReleaseCard() {
    const version = $("#app-release-version");
    const link = $("#app-download-link");
    if (!version || !link) return;
    try {
      const response = await fetch(`${API}/app/version?platform=android&version_code=0`, { credentials: "same-origin" });
      if (!response.ok) throw new Error("版本接口暂不可用");
      const release = await response.json();
      version.textContent = `v${release.latest_version_name || "最新版"}`;
      // 网页版面向未安装 App 的新用户，优先用完整版安装包链接；
      // 回退到 download_url（App 内更新同款完整包）。
      const installerUrl = release.installer_url || release.download_url;
      if (installerUrl) link.href = installerUrl;
      link.textContent = "下载";
    } catch {
      version.textContent = "最新版本";
      link.href = "download/full";
      link.textContent = "下载完整包";
    }
  }

  function startSmsCountdown(button, seconds = 60) {
    const original = button.textContent;
    let remaining = seconds;
    button.disabled = true;
    button.textContent = `${remaining}s 后重发`;
    clearInterval(button.smsTimer);
    button.smsTimer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(button.smsTimer);
        button.disabled = false;
        button.textContent = original;
        return;
      }
      button.textContent = `${remaining}s 后重发`;
    }, 1000);
  }

  async function sendSmsCode(button) {
    const input = $(`#${button.dataset.smsTarget}`);
    const phone = input?.value?.trim();
    if (!phone) {
      toast("请先填写手机号", "error");
      input?.focus();
      return;
    }
    try {
      await request("/auth/sms-code", { method: "POST", body: JSON.stringify({ phone, scene: button.dataset.smsScene }) });
      startSmsCountdown(button);
      toast("验证码已发送，请注意查收");
    } catch (error) { toast(error.message, "error"); }
  }

  function passwordIcon(visible) {
    return visible
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.9 4.2A10.8 10.8 0 0 1 12 4c5.5 0 9 5 9 5a15.6 15.6 0 0 1-2.1 2.5M6.6 6.6C4.3 8.1 3 10 3 10s3.5 5 9 5c1 0 2-.2 2.8-.5"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
  }

  function togglePassword(button) {
    const input = $(`#${button.dataset.passwordToggle}`);
    if (!input) return;
    const visible = input.type === "text";
    input.type = visible ? "password" : "text";
    button.setAttribute("aria-label", visible ? "显示密码" : "隐藏密码");
    button.setAttribute("aria-pressed", String(!visible));
    button.innerHTML = passwordIcon(!visible);
    input.focus({ preventScroll: true });
  }

  function drawAvatarCrop() {
    const crop = state.avatarCrop;
    if (!crop?.image) return;
    const canvas = $("#avatar-crop-canvas");
    const context = canvas.getContext("2d");
    const zoom = Number($("#avatar-zoom").value || 1);
    const xPosition = Number($("#avatar-x").value || 0) / 100;
    const yPosition = Number($("#avatar-y").value || 0) / 100;
    const baseScale = Math.max(canvas.width / crop.image.naturalWidth, canvas.height / crop.image.naturalHeight);
    const width = crop.image.naturalWidth * baseScale * zoom;
    const height = crop.image.naturalHeight * baseScale * zoom;
    const maxX = Math.max(0, (width - canvas.width) / 2);
    const maxY = Math.max(0, (height - canvas.height) / 2);
    const x = (canvas.width - width) / 2 + maxX * xPosition;
    const y = (canvas.height - height) / 2 + maxY * yPosition;
    context.fillStyle = "#f4f6fa";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(crop.image, x, y, width, height);
  }

  function openAvatarCrop(file, onReady) {
    const image = new Image();
    image.onload = () => {
      state.avatarCrop = { file, image, onReady };
      $("#avatar-zoom").value = "1";
      $("#avatar-x").value = "0";
      $("#avatar-y").value = "0";
      drawAvatarCrop();
      $("#avatar-crop-dialog").showModal();
      URL.revokeObjectURL(image.src);
    };
    image.onerror = () => toast("无法读取这张头像图片", "error");
    image.src = URL.createObjectURL(file);
  }

  function loadVendorScript(src, globalName) {
    if (globalName && window[globalName]) return Promise.resolve(window[globalName]);
    if (!state.vendorScripts[src]) {
      state.vendorScripts[src] = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.defer = true;
        script.dataset.vendorSrc = src;
        script.onload = () => resolve(globalName ? window[globalName] : true);
        script.onerror = () => reject(new Error("预览组件加载失败"));
        document.head.appendChild(script);
      });
    }
    return state.vendorScripts[src];
  }

  function ensurePromiseWithResolvers() {
    if (typeof Promise.withResolvers === "function") return;
    Promise.withResolvers = function withResolvers() {
      let resolve;
      let reject;
      const promise = new Promise((promiseResolve, promiseReject) => {
        resolve = promiseResolve;
        reject = promiseReject;
      });
      return { promise, resolve, reject };
    };
  }

  function fitWordPreview(content) {
    const wrapper = content.querySelector(".docx-wrapper");
    if (!wrapper) return;
    const availableWidth = Math.max(240, Math.floor(content.getBoundingClientRect().width) - 20);
    $$(".docx-wrapper > section.docx", content).forEach((page) => {
      page.style.transform = "";
      page.style.marginBottom = "";
      page.style.maxWidth = "none";
      page.style.transformOrigin = "top center";
      const pageWidth = Math.max(page.scrollWidth, page.getBoundingClientRect().width);
      const scale = Math.min(1, availableWidth / pageWidth);
      page.style.transform = `scale(${scale})`;
      page.style.marginBottom = `${Math.max(18, Math.round(24 * scale))}px`;
    });
  }

  async function fetchGenerationFile(generationId, format) {
    const response = await fetch(`${API}/generations/${encodeURIComponent(generationId)}/download/${format}`, {
      credentials: "same-origin",
      headers: state.token ? { Authorization: `Bearer ${state.token}` } : {}
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(errorDetailText(data.detail) || `${format.toUpperCase()} 文件读取失败`);
    }
    return response.arrayBuffer();
  }

  async function showGenerationPreview(generationId, format = "pdf") {
    const record = state.history.find((item) => item.id === generationId);
    const normalized = format === "docx" ? "docx" : "pdf";
    const label = normalized === "docx" ? "Word" : "PDF";
    if (!record?.files?.[normalized]?.key) { toast(`${label} 文件尚未准备好`, "error"); return; }
    const run = ++state.previewRun;
    const content = $("#resume-preview-content");
    content.className = `preview-dialog__body ${normalized === "docx" ? "word-preview-body" : ""}`;
    content.innerHTML = `<div class="preview-loading"><div class="loader"></div><strong>正在读取真实 ${label} 文件</strong><span>正在还原文档内容、图片和排版层级</span></div>`;
    $("#resume-preview-title").textContent = `${record.jd?.title || "适配简历"} · ${label} 真实预览`;
    $("#resume-preview-dialog").showModal();
    try {
      if (normalized === "docx") {
        await loadVendorScript(`${BASE}/static/vendor/jszip.min.js`, "JSZip");
        const docx = await loadVendorScript(`${BASE}/static/vendor/docx-preview.min.js`, "docx");
        const buffer = await fetchGenerationFile(generationId, "docx");
        if (run !== state.previewRun) return;
        content.replaceChildren();
        const note = document.createElement("div");
        note.className = "word-preview-note";
        note.innerHTML = "<strong>Word 预览说明</strong><span>浏览器会尽量按 A4 还原版式，但 Word/WPS 会按本机字体和分页引擎重新排版；最终页数以下载打开为准。</span>";
        content.appendChild(note);
        const host = document.createElement("div");
        host.className = "word-preview-host";
        content.appendChild(host);
        await docx.renderAsync(buffer, host, null, {
          className: "docx",
          inWrapper: true,
          breakPages: true,
          experimental: true,
          ignoreLastRenderedPageBreak: false,
          renderHeaders: true,
          renderFooters: true
        });
        fitWordPreview(content);
        return;
      }
      ensurePromiseWithResolvers();
      const [pdfjs, buffer] = await Promise.all([
        import(`${BASE}/static/vendor/pdf.min.mjs`),
        fetchGenerationFile(generationId, "pdf")
      ]);
      pdfjs.GlobalWorkerOptions.workerSrc = `${BASE}/static/vendor/pdf.worker.compat.mjs`;
      const pdf = await pdfjs.getDocument({ data: new Uint8Array(buffer) }).promise;
      if (run !== state.previewRun) return;
      content.replaceChildren();
      const availableWidth = Math.max(240, Math.floor(content.getBoundingClientRect().width) - 20);
      for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
        const page = await pdf.getPage(pageNumber);
        if (run !== state.previewRun) return;
        const baseViewport = page.getViewport({ scale: 1 });
        const scale = Math.min(1.55, availableWidth / baseViewport.width);
        const viewport = page.getViewport({ scale });
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        const sheet = document.createElement("figure");
        sheet.className = "pdf-preview-page";
        const canvas = document.createElement("canvas");
        canvas.width = Math.ceil(viewport.width * pixelRatio);
        canvas.height = Math.ceil(viewport.height * pixelRatio);
        canvas.style.width = `${Math.round(viewport.width)}px`;
        canvas.style.height = `${Math.round(viewport.height)}px`;
        sheet.appendChild(canvas);
        const caption = document.createElement("figcaption");
        caption.textContent = `第 ${pageNumber} / ${pdf.numPages} 页`;
        sheet.appendChild(caption);
        content.appendChild(sheet);
        await page.render({
          canvasContext: canvas.getContext("2d"),
          viewport,
          transform: pixelRatio === 1 ? null : [pixelRatio, 0, 0, pixelRatio, 0, 0]
        }).promise;
      }
    } catch (error) {
      if (run !== state.previewRun) return;
      content.innerHTML = `<div class="parse-error"><strong>${label} 预览加载失败</strong><p>${escapeHtml(error.message)}</p><small>文件仍可正常下载，请稍后重试预览。</small></div>`;
    }
  }

  function closeGenerationPreview() {
    state.previewRun += 1;
    $("#resume-preview-dialog").close();
    $("#resume-preview-content").replaceChildren();
  }

  function navigate(page) {
    // Keep the old deep links working, while presenting one clear primary navigation.
    const resolvedPage = page === "overview" ? "radar" : page;
    const primaryPage = ["career", "applications"].includes(resolvedPage)
      ? "history"
      : resolvedPage === "match" ? "resumes" : resolvedPage;
    $$(".page[data-page-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.pagePanel === resolvedPage));
    $$(".nav-item[data-page]").forEach((button) => button.classList.toggle("active", button.dataset.page === primaryPage));
    $$(".record-tab[data-go]").forEach((button) => button.classList.toggle("active", button.dataset.go === resolvedPage));
    if (["radar", "resumes"].includes(resolvedPage)) {
      maybeShowOnboarding();
    } else {
      $("#path-onboarding")?.classList.add("hidden");
    }
    $(".sidebar").classList.remove("open");
    window.scrollTo(0, 0);
    $("#main-content").focus({ preventScroll: true });
    if (resolvedPage === "radar") loadRadar();
    if (resolvedPage === "resumes") loadResumes();
    if (resolvedPage === "history") loadHistory();
    if (resolvedPage === "match") loadJdHistory();
    if (resolvedPage === "career") { loadCareerFacts(); loadReviews(); }
    if (resolvedPage === "applications") loadApplications();
    if (resolvedPage === "settings") loadBilling();
  }

  function selectedResumeId() {
    return $("#match-resume")?.value || state.resumes.find((item) => item.is_default)?.id || state.resumes[0]?.id || "";
  }

  function renderCareerFacts() {
    const list = $("#career-facts-list");
    if (!list) return;
    if (!state.careerFacts.length) {
      list.innerHTML = '<div class="empty-state"><strong>还没有职业事实</strong><p>选择一份基础简历后，点击“从简历重建”。</p></div>';
      return;
    }
    list.innerHTML = state.careerFacts.map((fact) => `<article class="resource-row" data-fact-id="${escapeHtml(fact.id)}">
      <div class="resource-main"><div class="file-icon">${escapeHtml(fact.category === "experience" ? "经" : "资")}</div><div><h3>${escapeHtml(fact.display_text || fact.raw_text || "职业事实")}</h3><p>来源：基础简历 · 风险等级 ${Number(fact.risk_level || 1)} · ${fact.status === "confirmed" ? "已确认" : "已拒绝"}</p></div></div>
      <div class="resource-actions"><button class="button secondary" data-fact-action="confirmed" ${fact.status === "confirmed" ? "disabled" : ""}>确认</button><button class="button danger" data-fact-action="rejected" ${fact.status === "rejected" ? "disabled" : ""}>拒绝</button></div>
    </article>`).join("");
  }

  async function loadCareerFacts() {
    try { state.careerFacts = await request("/career/facts"); renderCareerFacts(); }
    catch (error) { if ($("#career-facts-list")) $("#career-facts-list").innerHTML = `<div class="empty-state"><strong>职业事实暂时不可用</strong><p>${escapeHtml(error.message)}</p></div>`; }
  }

  function renderReviews() {
    const list = $("#review-list");
    if (!list) return;
    if (!state.reviews.length) {
      list.innerHTML = '<div class="empty-state"><strong>暂无待审阅建议</strong><p>解析岗位后，点击“基于当前岗位创建审阅”。</p></div>';
      return;
    }
    list.innerHTML = state.reviews.slice(0, 6).map((review) => `<article class="review-card" data-review-id="${escapeHtml(review.id)}"><header><strong>${escapeHtml(review.jd?.title || "岗位审阅")}</strong><span class="pill">${review.status === "confirmed" ? "已确认" : "待确认"}</span></header><p>关键词覆盖：${Object.values(review.keyword_coverage || {}).filter(Boolean).length}/${Object.keys(review.keyword_coverage || {}).length}</p><div class="review-proposals">${(review.proposals || []).map((proposal) => `<div class="review-proposal" data-proposal-id="${escapeHtml(proposal.id)}"><strong>${escapeHtml(proposal.after || proposal.before)}</strong><small>${escapeHtml(proposal.reason || "基于已确认经历组织表达")}</small><div><button class="button secondary" data-review-action="accepted" ${proposal.decision === "accepted" ? "disabled" : ""}>接受</button><button class="button secondary" data-review-action="rejected" ${proposal.decision === "rejected" ? "disabled" : ""}>拒绝</button></div></div>`).join("")}</div></article>`).join("");
  }

  async function loadReviews() {
    try { state.reviews = await request("/reviews"); renderReviews(); }
    catch (error) { if ($("#review-list")) $("#review-list").innerHTML = `<div class="empty-state"><strong>审阅中心暂时不可用</strong><p>${escapeHtml(error.message)}</p></div>`; }
  }

  function applicationStatusLabel(value) {
    return ({ saved: "待投递", applied: "已投递", interview: "面试中", offer: "已获 Offer", rejected: "未通过", closed: "已结束" })[value] || value;
  }

  function renderApplications() {
    const list = $("#applications-list");
    if (!list) return;
    if (!state.applications.length) {
      list.innerHTML = '<div class="empty-state"><strong>还没有投递记录</strong><p>把想跟进的职位加进来，后续可随时更新状态。</p></div>';
      return;
    }
    list.innerHTML = state.applications.map((item) => `<article class="resource-row" data-application-id="${escapeHtml(item.id)}"><div class="resource-main"><div class="file-icon">投</div><div><h3>${escapeHtml(item.job_title)} <span class="pill">${escapeHtml(applicationStatusLabel(item.status))}</span></h3><p>${escapeHtml(item.company || "未填写公司")} ${item.next_action_at ? `· 下次跟进 ${escapeHtml(item.next_action_at)}` : ""}${item.note ? ` · ${escapeHtml(item.note)}` : ""}</p></div></div><div class="resource-actions"><select data-application-status aria-label="更新投递状态"><option value="saved" ${item.status === "saved" ? "selected" : ""}>待投递</option><option value="applied" ${item.status === "applied" ? "selected" : ""}>已投递</option><option value="interview" ${item.status === "interview" ? "selected" : ""}>面试中</option><option value="offer" ${item.status === "offer" ? "selected" : ""}>已获 Offer</option><option value="rejected" ${item.status === "rejected" ? "selected" : ""}>未通过</option><option value="closed" ${item.status === "closed" ? "selected" : ""}>已结束</option></select><button class="button danger" data-application-action="delete">删除</button></div></article>`).join("");
  }

  async function loadApplications() {
    try { state.applications = await request("/applications"); renderApplications(); }
    catch (error) { if ($("#applications-list")) $("#applications-list").innerHTML = `<div class="empty-state"><strong>投递记录暂时不可用</strong><p>${escapeHtml(error.message)}</p></div>`; }
  }

  function renderBilling() {
    const credits = $("#billing-credit");
    const plans = $("#billing-plans");
    const note = $("#billing-provider-note");
    if (!credits || !plans || !note || !state.billing) return;
    const available = Number(state.billing.account?.available ?? state.billing.account?.credits ?? 0);
    const reserved = Number(state.billing.account?.reserved || 0);
    const balance = Number(state.billing.account?.credits || 0);
    const suspended = Boolean(state.billing.account?.suspended);
    credits.textContent = suspended ? "已暂停" : `${available} 次可用`;
    const chip = $("#credits-chip");
    if (chip) chip.textContent = suspended ? "额度已暂停" : `额度 ${available}`;
    const headerCredit = $("#header-credits");
    if (headerCredit) headerCredit.textContent = suspended ? "额度已暂停" : `剩余 ${available} 次`;
    plans.innerHTML = Object.entries(state.billing.plans || {}).map(([code, plan]) => `<article class="billing-plan"><h3>${escapeHtml(plan.name)}</h3><strong>${Number(plan.credits || 0)} 次</strong><p>¥${(Number(plan.price_cents || 0) / 100).toFixed(2)}</p><button class="button secondary" data-order-product="${escapeHtml(code)}">创建待支付订单</button></article>`).join("");
    const orders = (state.billing.orders || []).slice(0, 5).map((order) => `<li><strong>${escapeHtml(order.product_name || order.product_code)}</strong> · ${escapeHtml(order.status)} · ${Number(order.credits || 0)} 次 · ¥${(Number(order.amount_cents || 0) / 100).toFixed(2)}</li>`).join("");
    note.innerHTML = `${escapeHtml(state.billing.payment_note || "创建订单后由管理员确认到账。")}<br>账户余额 ${balance} 次${reserved ? `（预扣中 ${reserved} 次）` : ""}；每次生成/换模板消耗 1 次，失败自动退回。${orders ? `<ul class="billing-order-list">${orders}</ul>` : ""}`;
  }

  async function loadBilling() {
    try { state.billing = await request("/billing/summary"); renderBilling(); }
    catch (error) { if ($("#billing-provider-note")) $("#billing-provider-note").textContent = error.message; }
  }

  function renderDashboard() {
    // The former overview is kept as a compatibility target for old deep links,
    // but is no longer part of the primary workspace navigation.
    if (!$("#career-greeting")) return;
    const profile = state.dashboard?.profile || {};
    const username = state.user?.username || "你";
    const ready = profile.status === "ready";
    $("#career-greeting").textContent = ready ? `你好，${username}。你的职业档案已经建立。` : `你好，${username}。先建立你的职业资产。`;
    $("#career-hero-copy").textContent = ready
      ? "AI 已完成简历分析、能力画像和岗位方向判断，可以继续帮你生成竞争版简历。"
      : "上传或填写一份基础简历后，AI 会开始分析你的经验、能力和推荐方向。";
    $("#career-score").textContent = ready ? `${profile.competitiveness || 0}` : "--";
    $("#career-direction").textContent = ready ? profile.direction || "职业方向分析中" : "等待建立职业画像";
    const done = [
      profile.resume_count > 0,
      (profile.capabilities || []).length > 0,
      (profile.recommended_roles || []).length > 0,
      profile.generation_count > 0
    ].filter(Boolean).length;
    $("#ai-done-count").textContent = `${done} 项`;
    $("#recommended-roles").textContent = (profile.recommended_roles || []).slice(0, 3).join(" / ") || "暂未生成";
    $("#next-action").textContent = (profile.next_actions || [ready ? "开始岗位适配" : "上传基础简历"])[0];
    const capabilityMarkup = (profile.capabilities || []).map((item) => `
      <li><span>${escapeHtml(item.name)}</span><strong>${escapeHtml(item.stars || "")}</strong><em>${Number(item.score || 0)}分</em></li>
    `).join("");
    const strengths = (profile.strengths || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const actions = (profile.next_actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    $("#career-profile").className = ready ? "career-profile" : "career-profile empty-state";
    $("#career-profile").innerHTML = ready
      ? `<div class="career-profile__head"><strong>${escapeHtml(profile.title || profile.direction || "职业画像")}</strong><span>${Number(profile.competitiveness || 0)}分</span></div>
        ${capabilityMarkup ? `<h3>核心能力</h3><ul class="capability-list">${capabilityMarkup}</ul>` : ""}
        ${strengths ? `<h3>优势分析</h3><ul class="insight-list">${strengths}</ul>` : ""}
        ${actions ? `<h3>下一步建议</h3><ul class="insight-list">${actions}</ul>` : ""}`
      : '<strong>暂无职业画像</strong><p>上传或填写基础简历后，AI 会自动沉淀你的职业资产。</p>';
  }

  async function loadDashboard() {
    try {
      state.dashboard = await request("/career/dashboard");
      renderDashboard();
    } catch (error) {
      if ($("#career-profile")) {
        $("#career-profile").className = "career-profile empty-state";
        $("#career-profile").innerHTML = `<strong>职业画像暂时不可用</strong><p>${escapeHtml(error.message)}</p>`;
      }
    }
  }

  function safeExternalUrl(value) {
    try {
      const url = new URL(String(value || ""));
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch { return ""; }
  }

  function radarGapHtml(gap, coverage) {
    if (!gap) return "";
    const satisfied = (gap.satisfied || []).slice(0, 4);
    const missing = (gap.missing || []).slice(0, 4);
    const pct = Math.round((coverage || 0) * 100);
    const satisfiedText = satisfied.length ? ` · 已满足：${escapeHtml(satisfied.join("、"))}` : "";
    const missingText = missing.length ? ` · <span class="gap-missing">可补强：${escapeHtml(missing.join("、"))}</span>` : "";
    return `<div class="radar-job__gap">
      <div class="radar-job__gap-bar"><span style="width:${pct}%"></span></div>
      <div class="radar-job__gap-text">任职要求覆盖 <strong>${pct}%</strong>${satisfiedText}${missingText}</div>
    </div>`;
  }

  function populateFacetSelect(selector, items, selectedValue, defaultLabel = "不限") {
    const select = document.querySelector(selector);
    if (!select) return;
    const options = [`<option value="">${defaultLabel}</option>`];
    (items || []).forEach((item) => {
      const val = typeof item === "object" ? (item.value || item.key || item.name || "") : item;
      const label = typeof item === "object" ? (item.label || item.name || item.value || item.key || "") : item;
      options.push(`<option value="${escapeHtml(val)}">${escapeHtml(label)}</option>`);
    });
    select.innerHTML = options.join("");
    select.value = selectedValue || "";
  }

  function populateTopicSelect(selector, items, selectedValue) {
    populateFacetSelect(selector, items, selectedValue, "全部方向");
  }

  function setSelectOptions(select, options, selected) {
    if (!select) return;
    select.innerHTML = options.map((opt) => `<option value="${escapeHtml(opt.value)}">${escapeHtml(opt.label)}</option>`).join("");
    select.value = selected || "";
  }

  function selectedRadarResumeIds() {
    return $$("#radar-resume-options input:checked").map((input) => input.value);
  }

  function renderRadarResumePicker() {
    const options = $("#radar-resume-options");
    const summary = $("#radar-resume-summary");
    if (!options || !summary) return;

    const availableIds = new Set(state.resumes.map((resume) => resume.id));
    state.radarResumeIds = state.radarResumeIds.filter((id) => availableIds.has(id));
    if (!state.resumes.length) {
      options.innerHTML = '<span class="radar-resume-empty">暂无可用简历，请先创建简历。</span>';
      summary.textContent = "创建简历后可选择最多 3 份合并推荐。";
      return;
    }

    const selected = new Set(state.radarResumeIds);
    options.innerHTML = state.resumes.map((resume) => `
      <label class="radar-resume-option">
        <input type="checkbox" value="${escapeHtml(resume.id)}" ${selected.has(resume.id) ? "checked" : ""}>
        <span>${escapeHtml(resume.name)}${resume.is_default ? "（默认）" : ""}</span>
      </label>`).join("");
    const selectedNames = state.resumes
      .filter((resume) => selected.has(resume.id))
      .map((resume) => resume.name);
    summary.textContent = selectedNames.length
      ? `已用 ${selectedNames.join("、")} 推荐；最多可合并 3 份简历。`
      : "使用默认简历推荐；可最多合并 3 份简历。";
  }

  function renderRadar() {
    const summary = state.radarSummary || {};
    $("#radar-available-count").textContent = Number(summary.available_jobs || 0).toLocaleString("zh-CN");
    $("#radar-saved-count").textContent = Number(summary.saved || 0).toLocaleString("zh-CN");
    $("#radar-saved-filter")?.classList.toggle("active", Boolean(state.radarFilters.savedOnly));
    $("#radar-saved-filter")?.setAttribute("aria-pressed", String(Boolean(state.radarFilters.savedOnly)));
    if ($("#radar-new-filter")) $("#radar-new-filter").checked = Boolean(state.radarFilters.onlyNew);
    const newCount = Number(summary.new_jobs || 0).toLocaleString("zh-CN");
    $("#radar-new-count").textContent = `近 24 小时 ${newCount} 个`;
    $("#radar-applied-count").textContent = Number(summary.applied || 0).toLocaleString("zh-CN");
    const citySelect = $("#radar-city");
    const cities = state.radarCities || [];
    citySelect.innerHTML = `<option value="">全部城市</option>${cities.map((city) => `<option value="${escapeHtml(city)}">${escapeHtml(city)}</option>`).join("")}`;
    citySelect.value = state.radarFilters.city;
    // Populate experience/education/topic/source from facets
    if (state.radarFacets) {
      populateFacetSelect("#radar-experience", state.radarFacets.experiences || [], state.radarFilters.experience, "不限");
      populateFacetSelect("#radar-education", state.radarFacets.educations || [], state.radarFilters.education, "不限");
      populateTopicSelect("#radar-topic", state.radarFacets.topics || [], state.radarFilters.topic);
      if (Array.isArray(state.radarFacets.sources)) {
        populateFacetSelect("#radar-source", state.radarFacets.sources, state.radarFilters.source, "全部来源");
      }
    }
    $("#radar-query").value = state.radarFilters.query;
    $("#radar-published-within").value = state.radarFilters.publishedWithin || "all";
    const salaryMinSel = $("#radar-salary-min");
    if (salaryMinSel) salaryMinSel.value = String(state.radarFilters.salaryMin || 0);
    if ($("#radar-sort")) $("#radar-sort").value = state.radarFilters.sortBy || "match";
    if ($("#radar-source")) $("#radar-source").value = state.radarFilters.source || "";
    renderRadarResumePicker();
    syncRadarFilterSummary();
    const pagination = state.radarPagination || { page: 1, total: 0, total_pages: 1, page_size: 20, matched_total: 0, is_limited: false };
    const matchedTotal = Number(pagination.matched_total ?? pagination.total ?? 0).toLocaleString("zh-CN");
    $("#radar-result-count").textContent = state.radarFilters.savedOnly
      ? `正在查看已收藏岗位：${matchedTotal} 个`
      : `匹配到 ${matchedTotal} 个岗位，共 ${pagination.total_pages} 页（每页 ${pagination.page_size} 个）`;
    const pager = $("#radar-pagination");
    pager.innerHTML = pagination.total_pages > 1
      ? `<button class="button secondary" type="button" data-radar-page="prev" ${pagination.page <= 1 ? "disabled" : ""}>上一页</button>` +
        `<span style="margin: 0 8px; font-size: 13px;">第 ${pagination.page} / ${pagination.total_pages} 页</span>` +
        `<span style="margin-left: 8px; font-size: 13px;">跳转至 <input id="radar-jump-page-input" type="number" min="1" max="${pagination.total_pages}" value="${pagination.page}" style="width: 56px; text-align: center; padding: 4px; border: 1px solid #ccc; border-radius: 6px;"> 页</span>` +
        `<button class="button secondary" type="button" id="radar-jump-page-btn" style="margin-left: 6px; padding: 4px 10px;">跳转</button>` +
        `<button class="button secondary" type="button" data-radar-page="next" style="margin-left: 10px;" ${pagination.page >= pagination.total_pages ? "disabled" : ""}>下一页</button>`
      : "";
    const list = $("#radar-list");
    if (!state.radarJobs.length) {
      const profileReady = state.dashboard?.profile?.status === "ready";
      list.innerHTML = `<div class="empty-state radar-empty"><strong>${profileReady ? "暂时没有新的可推荐岗位" : "先建立职业画像，再开始推荐"}</strong><p>${profileReady ? "岗位库同步后，符合你偏好的新岗位会出现在这里。你也可以继续手动提交岗位 JD 优化简历。" : "上传或填写一份基础简历后，岗位雷达会结合你的经历、技能和职业方向排序推荐。"}</p></div>`;
      return;
    }
    list.innerHTML = state.radarJobs.map((job) => {
      const externalUrl = safeExternalUrl(job.source_url);
      const tags = (job.tags || []).slice(0, 5).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("");
      const metadata = [job.company, job.location, job.salary, job.experience].filter(Boolean).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
      const primaryLabel = job.adapted ? "换模板重新生成" : "用此岗位优化简历";
      const primaryHint = job.adapted ? "已完成简历适配，可换模板再生成" : "基于该岗位生成专属简历";
      return `<article class="radar-job ${job.adapted ? "radar-job--adapted" : ""}" data-radar-job-id="${escapeHtml(job.id)}">
        <div class="radar-job__score"><strong>${Number(job.match_score || 0)}</strong><span>匹配度</span></div>
        <div class="radar-job__content">
          <div class="radar-job__head"><div><h2>${escapeHtml(job.title)}${job.is_new ? ' <span class="badge-new">NEW</span>' : ""}${job.adapted ? ' <span class="radar-adapted">已适配 · 简历已生成</span>' : ""}</h2><p class="radar-job__metadata">${metadata || "岗位信息待补充"}</p></div>${job.published_at ? `<time datetime="${escapeHtml(job.published_at)}">${escapeHtml(String(job.published_at).slice(0, 10))}</time>` : ""}</div>
          <p class="radar-job__reason">${escapeHtml(job.match_reason || "基于职业画像的推荐")}</p>
          ${job.gap_analysis ? radarGapHtml(job.gap_analysis, job.coverage) : ""}
          ${tags ? `<div class="tag-list">${tags}</div>` : ""}
          <div class="radar-job__actions">
            ${externalUrl ? `<a class="button secondary radar-original-link" href="${escapeHtml(externalUrl)}" target="_blank" rel="noopener noreferrer" data-external-job-id="${escapeHtml(job.id)}">↗ 查看原岗位并投递</a>` : ""}
            <button class="button primary" type="button" data-radar-action="optimize" title="${escapeHtml(primaryHint)}">${escapeHtml(primaryLabel)}</button>
            <button class="radar-more-toggle text-button" type="button" data-radar-action="toggle-more" aria-expanded="false">更多</button>
            <div class="radar-job__more hidden">
              <button class="button secondary radar-job__detail-action" type="button" data-radar-action="details">查看完整岗位信息</button>
              <button class="text-button ${job.feedback_action === "saved" ? "radar-saved-button" : ""}" type="button" data-radar-action="save" ${job.feedback_action === "saved" ? "disabled aria-pressed=\"true\"" : ""}>${job.feedback_action === "saved" ? "已收藏" : "收藏"}</button>
              <button class="text-button" type="button" data-radar-action="not-interested">不感兴趣</button>
              <button class="text-button subtle-danger" type="button" data-radar-action="block-company">不再推荐该公司</button>
            </div>
          </div>
        </div>
      </article>`;
    }).join("");
  }

  async function loadRadar() {
    try {
      const params = new URLSearchParams({
        page: String(state.radarFilters.page || 1),
        page_size: "20",
        published_within: state.radarFilters.publishedWithin || "30d"
      });
      if (state.radarFilters.query) params.set("query", state.radarFilters.query);
      if (state.radarFilters.city) params.set("city", state.radarFilters.city);
      if (state.radarFilters.savedOnly) params.set("saved_only", "true");
      if (state.radarFilters.salaryMin) params.set("salary_min", String(state.radarFilters.salaryMin));
      if (state.radarFilters.sortBy && state.radarFilters.sortBy !== "match") params.set("sort_by", state.radarFilters.sortBy);
      if (state.radarFilters.experience) params.set("experience", state.radarFilters.experience);
      if (state.radarFilters.education) params.set("education", state.radarFilters.education);
      if (state.radarFilters.topic) params.set("topic", state.radarFilters.topic);
      if (state.radarFilters.source) params.set("source", state.radarFilters.source);
      if (state.radarFilters.onlyNew) params.set("only_new", "true");
      if (Array.isArray(state.radarResumeIds) && state.radarResumeIds.length > 0) {
        params.set("resume_ids", state.radarResumeIds.join(","));
      }
      const data = await request(`/radar/recommendations?${params}`);
      state.radarJobs = data.jobs || [];
      state.radarSummary = data.summary || {};
      if (Array.isArray(data.cities) && data.cities.length) state.radarCities = data.cities;
      state.radarPagination = data.pagination || null;
      if (data.facets) state.radarFacets = data.facets;
      renderRadar();
    } catch (error) {
      const list = $("#radar-list");
      if (list) list.innerHTML = `<div class="empty-state"><strong>岗位雷达暂时不可用</strong><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  async function setRadarFeedback(jobId, action) {
    await request(`/radar/jobs/${encodeURIComponent(jobId)}/feedback`, { method: "POST", body: JSON.stringify({ action }) });
  }

  async function showRadarJobDetail(jobId) {
    const content = $("#resume-preview-content");
    content.className = "preview-dialog__body radar-detail-preview";
    content.innerHTML = `<div class="preview-loading"><div class="loader"></div><strong>正在读取原岗位信息</strong><span>会保留岗位发布页的职责、要求、福利与其它字段</span></div>`;
    $("#resume-preview-title").textContent = "岗位详情";
    $("#resume-preview-dialog").showModal();
    try {
      const job = await request(`/radar/jobs/${encodeURIComponent(jobId)}`);
      const fallback = {};
      if (job.description) fallback["岗位职责与详情"] = job.description;
      if ((job.requirements || []).length) fallback["任职要求"] = job.requirements.join("\n");
      if ((job.benefits || []).length) fallback["职位福利"] = job.benefits.join("\n");
      const sections = Object.keys(job.source_sections || {}).length ? job.source_sections : fallback;
      $("#resume-preview-title").textContent = `${job.title || "岗位详情"} · 原岗位信息`;
      const sectionHtml = Object.entries(sections).map(([title, text]) => `<section class="radar-detail-section"><h3>${escapeHtml(title)}</h3><pre>${escapeHtml(text)}</pre></section>`).join("");
      content.innerHTML = `<article class="radar-detail"><header><div><p>${escapeHtml(job.company || "")}</p><h2>${escapeHtml(job.title || "岗位详情")}</h2><span>${escapeHtml([job.salary, job.location, job.experience, job.education].filter(Boolean).join(" · "))}</span></div><b>匹配 ${Number(job.match_score || 0)}%</b></header><section class="radar-detail-reason"><strong>AI 匹配解读</strong><p>${escapeHtml(job.match_reason || "系统正基于你的职业经历与岗位信息进行匹配。")}</p></section><p class="radar-detail-source">${job.source_detail_status === "complete" ? "以下内容按岗位公开发布页采集，长内容可在此框内滚动查看。" : "当前展示已采集的岗位信息；完整内容请打开原岗位页查看。"}</p>${sectionHtml || `<p class="muted">暂未获取到岗位详情。</p>`}</article>`;
    } catch (error) {
      content.innerHTML = `<div class="parse-error"><strong>岗位详情读取失败</strong><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  function switchPanels(buttonSelector, panelSelector, dataKey, value) {
    $$(buttonSelector).forEach((button) => {
      const active = button.dataset[dataKey] === value;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    $$(panelSelector).forEach((panel) => {
      const hidden = panel.dataset[dataKey.replace("Method", "Panel")] !== value;
      panel.classList.toggle("hidden", hidden);
      panel.setAttribute("aria-hidden", String(hidden));
    });
  }

  function setResumeEditorExpanded(expanded) {
    const collapsed = $("#resume-editor-collapsed");
    const form = $("#resume-form");
    if (!collapsed || !form) return;
    collapsed.classList.toggle("hidden", expanded);
    form.classList.toggle("hidden", !expanded);
    form.setAttribute("aria-hidden", String(!expanded));
    if (expanded) {
      $("#resume-version-name")?.focus({ preventScroll: true });
    }
  }

  async function loadResumes() {
    try {
      state.resumes = await request("/resumes");
      renderResumes();
      renderRadarResumePicker();
      loadDashboard();
    } catch (error) { toast(error.message, "error"); }
  }

  function renderResumes() {
    $("#resume-count").textContent = `${state.resumes.length} 份`;
    const list = $("#resume-list");
    const select = $("#match-resume");
    select.innerHTML = '<option value="">使用默认简历</option>' + state.resumes.map((resume) => `<option value="${escapeHtml(resume.id)}">${escapeHtml(resume.name)}${resume.is_default ? "（默认）" : ""}</option>`).join("");
    if (!state.resumes.length) {
      list.innerHTML = '<div class="empty-state"><strong>简历库还是空的</strong><p>用上方任一种方式创建第一份基础简历。</p></div>';
      return;
    }
    list.innerHTML = state.resumes.map((resume) => {
      const content = resume.content || {};
      const summary = inlinePreviewText(content.title || content.summary) || "已完成结构化";
      return `<article class="resource-row" data-resume-id="${escapeHtml(resume.id)}">
        <div class="resource-main"><div class="file-icon">简</div><div><h3>${escapeHtml(resume.name)} ${resume.is_default ? `<span class="pill">${window.zhidaI18n ? window.zhidaI18n("badge_default") : "默认"}</span>` : ""} ${resume.avatar_key ? '<span class="pill avatar-pill">含头像</span>' : ""}</h3><p>${escapeHtml(summary).slice(0, 90)} · ${formatDate(resume.updated_at)}</p></div></div>
        <div class="resource-actions">
          ${resume.is_default ? "" : `<button class="button secondary" data-resume-action="default">${window.zhidaI18n ? window.zhidaI18n("btn_set_default") : "设为默认"}</button>`}
          <button class="button secondary" data-resume-action="avatar">${resume.avatar_key ? "更换头像" : "添加头像"}</button>
          <button class="button secondary" data-resume-action="preview" aria-expanded="false">${window.zhidaI18n ? window.zhidaI18n("btn_preview") : "预览"}</button>
          <button class="button secondary" data-resume-action="edit">${window.zhidaI18n ? window.zhidaI18n("btn_edit_rename") : "编辑/重命名"}</button>
          <button class="button danger" data-resume-action="delete">${window.zhidaI18n ? window.zhidaI18n("btn_delete") : "删除"}</button>
        </div>
      </article>`;
    }).join("");
  }

  function lineValues(value) {
    return String(value || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  }

  function resumePayload(form) {
    const data = new FormData(form);
    const asDetails = (value) => lineValues(value).map((details) => ({ details }));
    return {
      name: String(data.get("version_name") || "").trim(),
      content: {
        name: String(data.get("name") || "").trim(),
        title: String(data.get("title") || "").trim(),
        contact: {
          age: String(data.get("age") || "").trim(),
          phone: String(data.get("phone") || "").trim(),
          email: String(data.get("email") || "").trim()
        },
        summary: String(data.get("summary") || "").trim(),
        skills: lineValues(data.get("skills")),
        experience: asDetails(data.get("experience")),
        projects: asDetails(data.get("projects")),
        education: asDetails(data.get("education")),
        certificates: lineValues(data.get("certificates"))
      }
    };
  }

  const previewLabels = {
    age: "年龄", birth_age: "年龄", phone: "电话", mobile: "手机", telephone: "电话", email: "邮箱", mail: "邮箱",
    birth_date: "出生年月", birthday: "出生日期", birth_year: "出生年份",
    location: "所在地", address: "地址", city: "城市", wechat: "微信", website: "个人网站",
    company: "公司", organization: "机构", employer: "公司", role: "岗位", position: "职位",
    job_title: "岗位", title: "名称", period: "时间", date: "时间", date_range: "时间",
    duration: "时间", time: "时间", project: "项目", project_name: "项目", name: "名称",
    school: "学校", institution: "院校", university: "大学", degree: "学历", major: "专业",
    qualification: "资质", details: "详情", description: "说明", responsibilities: "职责",
    achievements: "成果", highlights: "亮点", bullets: "要点", content: "内容"
  };

  function isPreviewObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function hasPreviewValue(value) {
    if (value === null || value === undefined) return false;
    if (typeof value === "string") return Boolean(value.trim());
    if (Array.isArray(value)) return value.some(hasPreviewValue);
    if (isPreviewObject(value)) return Object.values(value).some(hasPreviewValue);
    return true;
  }

  function previewLabel(key) {
    const normalized = String(key || "").trim();
    return previewLabels[normalized] || normalized.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ");
  }

  function splitPreviewLines(value) {
    return String(value)
      .replace(/\r/g, "")
      .replace(/\s*[●•▪◦]\s*/g, "\n")
      .split(/\n+/)
      .map((line) => line.trim().replace(/^[-–—]\s+/, ""))
      .filter(Boolean);
  }

  function valueToPreviewLines(value) {
    if (!hasPreviewValue(value)) return [];
    if (Array.isArray(value)) return value.flatMap(valueToPreviewLines);
    if (isPreviewObject(value)) {
      return Object.entries(value).flatMap(([key, nestedValue]) => {
        const lines = valueToPreviewLines(nestedValue);
        return lines.map((line) => `${previewLabel(key)}：${line}`);
      });
    }
    return splitPreviewLines(value);
  }

  function uniquePreviewLines(lines) {
    return [...new Set(lines.map((line) => String(line).trim()).filter(Boolean))];
  }

  function previewField(source, aliases, used) {
    let selected;
    aliases.forEach((key) => {
      if (!Object.prototype.hasOwnProperty.call(source, key)) return;
      used.add(key);
      if (selected === undefined && hasPreviewValue(source[key])) selected = source[key];
    });
    return selected;
  }

  function previewFields(source, aliases, used) {
    const values = [];
    aliases.forEach((key) => {
      if (!Object.prototype.hasOwnProperty.call(source, key)) return;
      used.add(key);
      if (hasPreviewValue(source[key])) values.push(source[key]);
    });
    return values;
  }

  function inlinePreviewText(value) {
    return uniquePreviewLines(valueToPreviewLines(value)).join(" / ");
  }

  function itemText(item) {
    return inlinePreviewText(item);
  }

  function renderPreviewBullets(lines) {
    const items = uniquePreviewLines(lines);
    if (!items.length) return "";
    return `<ul class="resume-entry__bullets">${items.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
  }

  function renderSimplePreviewSection(title, value, splitSkills = false) {
    let lines = valueToPreviewLines(value);
    if (splitSkills) lines = lines.flatMap((line) => line.split(/[、,，;；|]/).map((item) => item.trim()).filter(Boolean));
    lines = uniquePreviewLines(lines);
    if (!lines.length) return "";
    const body = lines.length === 1
      ? `<p>${escapeHtml(lines[0])}</p>`
      : renderPreviewBullets(lines);
    return `<section class="resume-section"><h4>${escapeHtml(title)}</h4>${body}</section>`;
  }

  function renderSkillsPreview(value) {
    const items = uniquePreviewLines(valueToPreviewLines(value));
    if (!items.length) return "";
    const completeSentences = items.length <= 2 && items.some((item) => item.length >= 16 || /[。！；]$/.test(item));
    const text = completeSentences
      ? items.map((item) => /[。！；]$/.test(item) ? item : `${item}。`).join(" ")
      : `具备${items.slice(0, 5).join("、")}等与目标岗位相关的经验。`;
    return `<section class="resume-section"><h4>经验与能力</h4><p>${escapeHtml(text)}</p></section>`;
  }

  function renderExperienceCapabilityOverview(summary, skills) {
    const summaryLines = uniquePreviewLines(valueToPreviewLines(summary));
    if (summaryLines.length) return renderSimplePreviewSection("经验与能力概述", summaryLines);
    const skillsMarkup = renderSkillsPreview(skills);
    return skillsMarkup.replace("经验与能力", "经验与能力概述");
  }

  function renderResumeEntry(item, kind) {
    if (!hasPreviewValue(item)) return "";
    if (!isPreviewObject(item)) {
      const bullets = renderPreviewBullets(valueToPreviewLines(item));
      return bullets ? `<article class="resume-entry">${bullets}</article>` : "";
    }

    const used = new Set();
    const date = inlinePreviewText(previewField(item, ["period", "date", "date_range", "duration", "time"], used));
    let primary;
    let roleValues = [];
    if (kind === "work") {
      primary = previewField(item, ["company", "organization", "employer"], used);
      roleValues = previewFields(item, ["role", "position", "job_title", "title"], used);
    } else if (kind === "project") {
      primary = previewField(item, ["project", "project_name", "name"], used);
      roleValues = previewFields(item, ["role", "position", "job_title", "title"], used);
    } else {
      primary = previewField(item, ["school", "institution", "university"], used);
      roleValues = previewFields(item, ["degree", "major", "qualification"], used);
    }

    const primaryText = inlinePreviewText(primary);
    const role = uniquePreviewLines(roleValues.flatMap(valueToPreviewLines)).join(" · ");
    const bullets = [];
    previewFields(item, ["details", "description", "bullets", "content"], used).forEach((value) => bullets.push(...valueToPreviewLines(value)));
    [
      [["responsibilities"], "职责"],
      [["achievements"], "成果"],
      [["highlights"], "亮点"]
    ].forEach(([keys, label]) => {
      previewFields(item, keys, used).forEach((value) => {
        bullets.push(...valueToPreviewLines(value).map((line) => `${label}：${line}`));
      });
    });
    Object.entries(item).forEach(([key, value]) => {
      if (used.has(key) || !hasPreviewValue(value)) return;
      bullets.push(...valueToPreviewLines(value).map((line) => `${previewLabel(key)}：${line}`));
    });

    const headline = kind === "work" && primaryText && role ? `${primaryText}  ${role}` : primaryText || role;
    const head = headline || date
      ? `<div class="resume-entry__head"><strong>${escapeHtml(headline)}</strong>${date ? `<time>${escapeHtml(date)}</time>` : ""}</div>`
      : "";
    const roleMarkup = kind !== "work" && primaryText && role ? `<p class="resume-entry__role">${escapeHtml(role)}</p>` : "";
    const bulletMarkup = renderPreviewBullets(bullets);
    if (!head && !roleMarkup && !bulletMarkup) return "";
    return `<article class="resume-entry">${head}${roleMarkup}${bulletMarkup}</article>`;
  }

  function renderEntryPreviewSection(title, value, kind) {
    if (!hasPreviewValue(value)) return "";
    const items = Array.isArray(value) ? value : [value];
    const entries = items.map((item) => renderResumeEntry(item, kind)).filter(Boolean);
    if (!entries.length) return "";
    return `<section class="resume-section"><h4>${escapeHtml(title)}</h4><div class="resume-entry-list">${entries.join("")}</div></section>`;
  }

  function contactPreviewLines(contact, source, used) {
    const lines = [];
    if (isPreviewObject(contact)) {
      Object.entries(contact).forEach(([key, value]) => {
        valueToPreviewLines(value).forEach((line) => lines.push(`${previewLabel(key)}：${line}`));
      });
    } else {
      lines.push(...valueToPreviewLines(contact));
    }
    [
      ["电话", ["phone", "mobile", "telephone"]],
      ["邮箱", ["email", "mail"]],
      ["年龄", ["age", "birth_age"]],
      ["出生年月", ["birth_date", "birthday", "birth_year"]],
      ["所在地", ["location", "address", "city"]],
      ["微信", ["wechat", "we_chat"]],
      ["个人网站", ["website", "homepage", "portfolio"]]
    ].forEach(([label, aliases]) => {
      const value = previewField(source, aliases, used);
      valueToPreviewLines(value).forEach((line) => lines.push(`${label}：${line}`));
    });
    return uniquePreviewLines(lines);
  }

  function contentPreview(content = {}) {
    const source = isPreviewObject(content) ? content : { summary: content };
    const used = new Set();
    const name = inlinePreviewText(previewField(source, ["name", "full_name"], used)) || "个人简历";
    const title = inlinePreviewText(previewField(source, ["title", "target", "objective", "job_target", "position"], used));
    const contact = previewField(source, ["contact", "contacts", "contact_info"], used);
    const contacts = contactPreviewLines(contact, source, used);
    const summary = previewField(source, ["summary", "profile", "about", "introduction", "self_evaluation"], used);
    const skills = previewField(source, ["skills", "professional_skills", "core_skills", "competencies"], used);
    const experience = previewField(source, ["experience", "work_experience", "employment", "work_history"], used);
    const projects = previewField(source, ["projects", "project_experience"], used);
    const education = previewField(source, ["education", "education_experience", "academic_background"], used);
    const certificates = previewField(source, ["certificates", "certifications", "awards"], used);

    const sections = [
      renderExperienceCapabilityOverview(summary, skills),
      renderEntryPreviewSection("工作经历", experience, "work"),
      renderEntryPreviewSection("项目经历", projects, "project"),
      renderEntryPreviewSection("教育经历", education, "education"),
      renderSimplePreviewSection("证书与荣誉", certificates)
    ];
    Object.entries(source).forEach(([key, value]) => {
      if (used.has(key) || !hasPreviewValue(value)) return;
      sections.push(renderSimplePreviewSection(previewLabel(key), value));
    });

    const contactMarkup = contacts.length
      ? `<div class="resume-contact">${contacts.map((line) => `<span>${escapeHtml(line)}</span>`).join("")}</div>`
      : "";
    const sectionMarkup = sections.filter(Boolean).join("") || '<section class="resume-section"><p>暂无可预览的详细内容</p></section>';
    return `<div class="resume-preview"><header class="resume-preview__header"><div><h3>${escapeHtml(name)}</h3>${title ? `<p class="resume-preview__title">${escapeHtml(title)}</p>` : ""}</div>${contactMarkup}</header>${sectionMarkup}</div>`;
  }

  function fillResumeEditor(resume) {
    const form = $("#resume-form");
    const content = resume.content || {};
    const values = {
      version_name: resume.name, name: content.name, title: content.title,
      age: content.contact?.age || content.contact?.birth_age || "", phone: content.contact?.phone, email: content.contact?.email, summary: content.summary,
      skills: (content.skills || []).join("\n"), experience: (content.experience || []).map(itemText).join("\n"),
      projects: (content.projects || []).map(itemText).join("\n"), education: (content.education || []).map(itemText).join("\n"), certificates: (content.certificates || []).join("\n")
    };
    Object.entries(values).forEach(([name, value]) => { if (form.elements[name]) form.elements[name].value = value || ""; });
    state.editingId = resume.id;
    $("#cancel-edit").classList.remove("hidden");
    switchPanels("[data-resume-method]", "[data-resume-panel]", "resumeMethod", "editor");
    setResumeEditorExpanded(true);
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function resetResumeEditor() {
    state.editingId = null;
    $("#resume-form").reset();
    $("#avatar-selection-note").textContent = "支持 JPG、PNG、WebP。选择后可自主裁剪，也可保留原图；导出时始终保持原始比例。";
    $("#cancel-edit").classList.add("hidden");
    setResumeEditorExpanded(false);
  }

  function armDanger(button, callback) {
    if (button.dataset.armed === "true") { callback(); return; }
    const original = button.textContent;
    button.dataset.armed = "true";
    button.textContent = "再次点击删除";
    setTimeout(() => { button.dataset.armed = "false"; button.textContent = original; }, 3500);
  }

  async function loadHistory() {
    const previousProcessing = new Set(state.history.filter((item) => item.status === "processing").map((item) => item.id));
    try {
      state.history = await request("/generations");
      renderHistory();
      loadDashboard();
      const completed = state.history.find((item) => previousProcessing.has(item.id) && item.status === "completed");
      const failed = state.history.find((item) => previousProcessing.has(item.id) && item.status === "failed");
      if (completed) toast("适配简历已生成，可以下载了");
      if (failed) toast(failed.error || "适配简历生成失败，请稍后重试", "error");
      clearTimeout(state.generationPollTimer);
      state.generationPollTimer = state.history.some((item) => item.status === "processing")
        ? setTimeout(loadHistory, 4000)
        : null;
    } catch (error) { toast(error.message, "error"); }
  }

  function historyMarkup(record, compact = false) {
    const title = record.jd?.title || "未命名岗位";
    const status = record.status || "completed";
    const design = record.design?.label ? ` · ${record.design.label}` : "";
    const langLabel = { zh: "中文", en: "英文", bilingual: "中英双语" }[record.requested_language] || "";
    const langMarkup = langLabel ? ` · ${langLabel}` : "";
    const score = record.ai_score || {};
    const dimensions = score.dimensions || {};
    const scoreMarkup = score.overall ? `<div class="score-strip">
      <span><strong>${Number(score.overall)}</strong>综合评分</span>
      <span><strong>${Number(dimensions.job_match || 0)}</strong>岗位匹配</span>
      <span><strong>${Number(dimensions.keyword_coverage || 0)}</strong>关键词覆盖</span>
      <span><strong>${Number(dimensions.visual_professionalism || 0)}</strong>视觉专业度</span>
    </div>` : "";
    const reportMarkup = !compact && record.ai_report?.optimizations?.length
      ? `<details class="ai-report"><summary>查看 AI 优化报告</summary><ul>${record.ai_report.optimizations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></details>`
      : "";
    const progressSteps = (record.progress_steps || []).map((step) => `<li class="${escapeHtml(step.status || "pending")}">${escapeHtml(step.label || "")}</li>`).join("");
    if (status === "processing") {
      return `<article class="history-row ${compact ? "history-row--compact" : ""}" data-generation-id="${escapeHtml(record.id)}">
        <div><div class="history-status"><span class="generation-state processing">生成中</span><h3>${escapeHtml(title)}</h3></div><p>基于 ${escapeHtml(record.resume_name || "基础简历")} · ${formatDate(record.created_at)}${escapeHtml(design)}${langMarkup}</p><p class="generation-message">${escapeHtml(record.progress_message || "正在后台生成，可以离开此页面")}</p>${progressSteps ? `<ol class="ai-progress-steps">${progressSteps}</ol>` : ""}</div>
      </article>`;
    }
    if (status === "failed") {
      return `<article class="history-row ${compact ? "history-row--compact" : ""}" data-generation-id="${escapeHtml(record.id)}">
        <div><div class="history-status"><span class="generation-state failed">生成失败</span><h3>${escapeHtml(title)}</h3></div><p>基于 ${escapeHtml(record.resume_name || "基础简历")} · ${formatDate(record.created_at)}${escapeHtml(design)}${langMarkup}</p><p class="generation-message error">${escapeHtml(record.error || "生成过程中发生错误，请重试")}</p><p class="muted">失败不会扣减额度；点击重试会重新预扣 1 次可用额度。</p></div>
        ${compact ? "" : '<div class="history-actions"><button class="button primary" data-history-action="retry">重试生成</button><button class="button danger" data-history-action="delete">删除</button></div>'}
      </article>`;
    }
    const previewNote = compact ? "" : '<p class="preview-consistency-note">下方预览读取的是<strong>本次真实生成文件</strong>（与下载一致）。授权模板原件仅作风格参考，不等于最终排版。</p>';
    return `<article class="history-row ${compact ? "history-row--compact" : ""}" data-generation-id="${escapeHtml(record.id)}">
      <div><div class="history-status"><span class="generation-state completed">已完成</span><h3>${escapeHtml(title)}</h3></div><p>基于 ${escapeHtml(record.resume_name || "基础简历")} · ${formatDate(record.created_at)}${escapeHtml(design)}${langMarkup}</p>${scoreMarkup}${reportMarkup}${previewNote}</div>
      <div class="history-actions"><button class="button primary" data-generation-preview="docx">预览 Word</button><button class="button primary" data-generation-preview="pdf">预览 PDF</button>${compact ? "" : '<button class="button secondary" data-generation-regenerate>更换模板</button>'}<button class="button secondary" data-generation-download="docx" data-generation-id="${escapeHtml(record.id)}">下载 Word</button><button class="button secondary" data-generation-download="pdf" data-generation-id="${escapeHtml(record.id)}">下载 PDF</button>${compact ? "" : '<button class="button danger" data-history-action="delete">删除</button>'}</div>
    </article>`;
  }

  function renderHistory() {
    const full = $("#history-list");
    full.innerHTML = state.history.length ? state.history.map((item) => historyMarkup(item)).join("") : '<div class="empty-state"><strong>暂无生成记录</strong><p>完成岗位适配后，可在这里预览和下载。</p></div>';
    const overview = $("#overview-history");
    if (state.history.length) { overview.className = "history-list"; overview.innerHTML = state.history.slice(0, 2).map((item) => historyMarkup(item, true)).join(""); }
    else if (overview) { overview.className = "empty-state"; overview.innerHTML = "<strong>还没有生成记录</strong><p>完成第一次岗位适配后，记录会出现在这里。</p>"; }
  }

  function jdTextItems(value) {
    if (typeof value === "string") return value.trim() ? [value.trim()] : [];
    if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean);
    return [];
  }

  function isUsableJd(jd) {
    if (!jd || typeof jd !== "object") return false;
    const title = String(jd.title || "").trim();
    const company = String(jd.company || "").trim();
    const signalCount = ["responsibilities", "requirements", "preferred", "keywords"]
      .flatMap((field) => jdTextItems(jd[field]))
      .length;
    if (!title && !company && signalCount < 2) return false;
    if (!title && !jdTextItems(jd.responsibilities).length && !jdTextItems(jd.requirements).length) return false;
    return true;
  }

  function renderJd() {
    const jd = state.jd || {};
    if (!isUsableJd(jd)) {
      renderJdError("这条岗位解析结果没有识别到有效职位、公司、职责或要求。", "请改用岗位截图，或复制岗位正文粘贴后重新解析。");
      return;
    }
    const list = (value) => uniquePreviewLines(valueToPreviewLines(value)).join("；");
    const insight = jd.insight || {};
    const insightMarkup = insight.core_requirements?.length || insight.suggestions?.length
      ? `<section class="jd-insight"><div class="jd-insight__score"><span>综合匹配</span><strong>${insight.match_score || "待测"}</strong><small>${escapeHtml(insight.match_level || "基于岗位要求")}</small></div><div><h3>岗位核心需求</h3><ul>${(insight.core_requirements || []).slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul><h3>AI优化建议</h3><ul>${(insight.suggestions || []).slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div></section>`
      : "";
    $("#jd-preview").className = "jd-content";
    $("#jd-preview").innerHTML = `${insightMarkup}<dl><dt>职位</dt><dd>${escapeHtml(jd.title || "未识别")}</dd><dt>公司</dt><dd>${escapeHtml(jd.company || "未提供")}</dd><dt>职责</dt><dd>${escapeHtml(list(jd.responsibilities))}</dd><dt>要求</dt><dd>${escapeHtml(list(jd.requirements))}</dd><dt>关键词</dt><dd><div class="tag-list">${(jd.keywords || []).map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") || "未提取"}</div></dd></dl>`;
    $("#jd-status").className = "status ready";
    $("#jd-status").textContent = "解析完成";
    $("#generate-button").disabled = false;
  }

  function renderJdProgress(message = "正在后台解析岗位，可以离开此页面") {
    $("#jd-status").className = "status processing";
    $("#jd-status").textContent = "后台解析中";
    $("#jd-preview").className = "jd-content";
    $("#jd-preview").innerHTML = `<div class="parse-progress"><strong>岗位解析已在后台运行</strong><p>${escapeHtml(message)}</p></div>`;
  }

  function renderJdError(message, retryHint) {
    $("#jd-status").className = "status error";
    $("#jd-status").textContent = "解析失败";
    $("#jd-preview").className = "jd-content parse-error";
    $("#jd-preview").innerHTML = `<strong>这次没有解析成功</strong><p>${escapeHtml(message)}</p><small>${escapeHtml(retryHint)}</small>`;
    $("#generate-button").disabled = true;
  }

  function jdHistoryTitle(task) {
    if (task.result?.title) return task.result.title;
    if (task.source_detail) return task.source_detail;
    if (task.source === "image") return "岗位截图";
    if (task.source === "text") return "文本岗位描述";
    return "岗位链接";
  }

  function renderJdHistory() {
    const list = $("#jd-history-list");
    if (!list) return;
    if (!state.jdHistory.length) {
      list.innerHTML = '<div class="empty-state"><strong>暂无解析记录</strong><p>提交岗位文本、链接或截图后，每次结果都会保存在这里。</p></div>';
      return;
    }
    list.innerHTML = state.jdHistory.map((task) => {
      const status = task.status || "processing";
      const usable = status === "completed" && isUsableJd(task.result);
      const effectiveStatus = status === "completed" && !usable ? "failed" : status;
      const labels = { processing: "解析中", completed: "解析成功", failed: status === "completed" ? "解析无效" : "解析失败" };
      const message = status === "failed"
        ? `<p class="generation-message error">失败原因：${escapeHtml(task.error || "岗位解析失败，请稍后重试")}</p>`
        : status === "processing"
          ? `<p class="generation-message">${escapeHtml(task.progress_message || "正在后台解析，可以离开此页面")}</p>`
          : usable
            ? `<p class="generation-message">解析结果已保存，可直接使用或生成适配简历。</p>`
            : `<p class="generation-message error">这条记录没有识别出有效岗位信息，请改用岗位截图或复制正文粘贴。</p>`;
      const actions = status === "completed" && usable
        ? `<div class="jd-history-actions"><button class="button secondary" type="button" data-jd-history-action="use">使用此岗位</button><button class="button primary" type="button" data-jd-history-action="generate">一键适配生成</button></div>`
        : "";
      return `<article class="jd-history-row" data-jd-task-id="${escapeHtml(task.id)}"><div><div class="history-status"><span class="generation-state ${escapeHtml(effectiveStatus)}">${labels[effectiveStatus] || "解析中"}</span><h3>${escapeHtml(jdHistoryTitle(task))}</h3></div><p>${formatDate(task.created_at)} · ${task.source === "image" ? "岗位截图" : task.source === "text" ? "文本描述" : "岗位链接"}</p>${message}</div>${actions}</article>`;
    }).join("");
  }

  async function loadJdHistory() {
    try {
      state.jdHistory = await request("/jd/tasks");
      renderJdHistory();
      clearTimeout(state.jdHistoryPollTimer);
      state.jdHistoryPollTimer = state.jdHistory.some((task) => task.status === "processing")
        ? setTimeout(loadJdHistory, 4000)
        : null;
    } catch (error) { toast(error.message, "error"); }
  }

  function clearJdTaskTracking() {
    clearTimeout(state.jdTaskTimer);
    state.jdTaskTimer = null;
    state.jdTaskId = null;
    localStorage.removeItem("resume_ai_jd_task");
  }

  async function pollJdTask(taskId) {
    try {
      const task = await request(`/jd/tasks/${encodeURIComponent(taskId)}`);
      if (task.status === "processing") {
        renderJdProgress(task.progress_message);
        clearTimeout(state.jdTaskTimer);
        state.jdTaskTimer = setTimeout(() => pollJdTask(taskId), 3000);
        return;
      }
      clearJdTaskTracking();
      await loadJdHistory();
      if (task.status === "completed") {
        if (!isUsableJd(task.result)) {
          state.jd = null;
          renderJdError("这条岗位解析结果没有识别到有效职位、公司、职责或要求。", "请改用岗位截图，或复制岗位正文粘贴后重新解析。");
          toast("岗位解析结果为空，请换一种方式提交", "error");
          return;
        }
        state.jd = task.result || {};
        renderJd();
        toast("岗位要求解析完成");
        return;
      }
      state.jd = null;
      renderJdError(task.error || "岗位解析失败，请稍后重试", "原始内容仍保留，可以直接再次提交解析。", false);
      toast(task.error || "岗位解析失败，请稍后重试", "error");
    } catch (error) {
      clearJdTaskTracking();
      renderJdError(error.message, "原始内容仍保留，可以直接再次提交解析。", false);
      toast(error.message, "error");
    }
  }

  async function parseJd(payload, isFile = false) {
    state.jd = null;
    $("#generate-button").disabled = true;
    clearJdTaskTracking();
    renderJdProgress("正在提交解析任务，完成后会自动显示结果。");
    try {
      const task = await request(isFile ? "/jd/ocr" : "/jd/parse", { method: "POST", body: isFile ? payload : JSON.stringify(payload) });
      state.jdTaskId = task.id;
      localStorage.setItem("resume_ai_jd_task", task.id);
      renderJdProgress(task.progress_message);
      state.jdTaskTimer = setTimeout(() => pollJdTask(task.id), 1500);
      toast("岗位解析已在后台运行，可以离开此页面");
      await loadJdHistory();
      return true;
    } catch (error) {
      state.jd = null;
      const retryHint = isFile ? "已选图片会继续保留，可以调整顺序或移除后再次上传。" : "原始内容仍保留，可以直接再次提交解析。";
      renderJdError(error.message, retryHint);
      toast(error.message, "error");
      return false;
    }
  }

  const JD_IMAGE_LIMITS = {
    count: 10,
    singleSize: 15 * 1024 * 1024,
    totalSize: 30 * 1024 * 1024,
    types: new Set(["image/png", "image/jpeg", "image/webp"])
  };

  function formatFileSize(bytes) {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  function validJdImageType(file) {
    if (JD_IMAGE_LIMITS.types.has(String(file.type || "").toLowerCase())) return true;
    return !file.type && /\.(png|jpe?g|webp)$/i.test(file.name || "");
  }

  function validateJdImages(files) {
    if (files.length > JD_IMAGE_LIMITS.count) return `最多只能上传 ${JD_IMAGE_LIMITS.count} 张岗位截图。`;
    const wrongType = files.find((file) => !validJdImageType(file));
    if (wrongType) return `“${wrongType.name}”不是 PNG、JPG 或 WebP 图片。`;
    const oversized = files.find((file) => file.size > JD_IMAGE_LIMITS.singleSize);
    if (oversized) return `“${oversized.name}”超过单张 15MB 的限制。`;
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    if (totalSize > JD_IMAGE_LIMITS.totalSize) return `所选图片合计 ${formatFileSize(totalSize)}，不能超过 30MB。`;
    return "";
  }

  function setJdImageFeedback(message, isError = false) {
    const feedback = $("#jd-image-feedback");
    feedback.className = `file-selection-summary${isError ? " error" : ""}`;
    feedback.textContent = message;
  }

  function renderJdImageFiles() {
    const files = state.jdImageFiles;
    const list = $("#jd-image-list");
    const submit = $("#jd-image-submit");
    const input = $("#jd-image");
    list.innerHTML = files.map((file, index) => `<li class="selected-file-item">
      <div class="selected-file-info"><strong><span class="selected-file-order">${index + 1}</span>${escapeHtml(file.name)}</strong><span>${formatFileSize(file.size)}</span></div>
      <div class="selected-file-actions">
        <button class="button secondary" type="button" data-image-action="up" data-index="${index}" aria-label="上移 ${escapeHtml(file.name)}" ${index === 0 ? "disabled" : ""}>上移</button>
        <button class="button secondary" type="button" data-image-action="down" data-index="${index}" aria-label="下移 ${escapeHtml(file.name)}" ${index === files.length - 1 ? "disabled" : ""}>下移</button>
        <button class="button secondary" type="button" data-image-action="remove" data-index="${index}" aria-label="移除 ${escapeHtml(file.name)}">移除</button>
      </div>
    </li>`).join("");
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    setJdImageFeedback(files.length ? `已选择 ${files.length} 张，共 ${formatFileSize(totalSize)}，将按下方顺序识别。` : "尚未选择图片");
    submit.disabled = files.length === 0;
    submit.textContent = files.length ? `上传并识别 ${files.length} 张截图` : "上传并识别";
    input.required = files.length === 0;
    if (!files.length) input.value = "";
  }

  async function downloadGeneration(generationId, format) {
    if (!generationId || !["docx", "pdf"].includes(format)) return;
    try {
      const response = await fetch(`${API}/generations/${encodeURIComponent(generationId)}/download/${format}`, {
        credentials: "same-origin",
        headers: state.token ? { Authorization: `Bearer ${state.token}` } : {}
      });
      if (!response.ok) {
        const raw = await response.text();
        let detail = readableResponseText(raw);
        try { detail = errorDetailText(JSON.parse(raw)?.detail) || detail; } catch { /* 使用文本错误 */ }
        throw new Error(detail || `下载失败（${response.status}）`);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error("下载文件为空，请重新生成");
      const disposition = response.headers.get("Content-Disposition") || "";
      const utf8Name = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      const filename = utf8Name ? decodeURIComponent(utf8Name) : `适配简历.${format}`;
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (error) { toast(error.message, "error"); }
  }

  $$("[data-auth-tab]").forEach((button) => button.addEventListener("click", () => {
    $$("[data-auth-tab]").forEach((item) => { item.classList.toggle("active", item === button); item.setAttribute("aria-selected", String(item === button)); });
    $$("[data-auth-panel]").forEach((panel) => panel.classList.toggle("hidden", panel.dataset.authPanel !== button.dataset.authTab));
    $("#reset-form").classList.add("hidden");
    $("#auth-message").textContent = "";
  }));
  $$("[data-auth-jump]").forEach((button) => button.addEventListener("click", () => {
    $(`[data-auth-tab="${button.dataset.authJump}"]`)?.click();
  }));
  $$("[data-auth-login-mode]").forEach((button) => button.addEventListener("click", () => {
    const mode = button.dataset.authLoginMode;
    $$("[data-auth-login-mode]").forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", String(active));
    });
    $$("[data-auth-login-panel]").forEach((panel) => {
      const active = panel.dataset.authLoginPanel === mode;
      panel.classList.toggle("hidden", !active);
      $$("input", panel).forEach((input) => { input.disabled = !active; });
    });
    $(mode === "sms" ? "#login-phone" : "#login-username")?.focus();
    $("#auth-message").textContent = "";
  }));
  $("#show-reset").addEventListener("click", () => { $$("[data-auth-panel]").forEach((panel) => panel.classList.add("hidden")); $("#reset-form").classList.remove("hidden"); });
  $("#back-login").addEventListener("click", () => { $("#reset-form").classList.add("hidden"); $('[data-auth-panel="login"]').classList.remove("hidden"); });

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
    const mode = $("[data-auth-login-mode].active")?.dataset.authLoginMode || "password";
    const endpoint = mode === "sms" ? "/auth/sms-login" : "/auth/login";
    try { setAuth(await request(endpoint, { method: "POST", body: JSON.stringify(data) })); } catch (error) { $("#auth-message").textContent = error.message; }
  });
  $("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
    try { setAuth(await request("/auth/register", { method: "POST", body: JSON.stringify(data) })); } catch (error) { $("#auth-message").textContent = error.message; }
  });
  $("#reset-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
    try { await request("/auth/reset-password", { method: "POST", body: JSON.stringify(data) }); $("#auth-message").className = "form-message success"; $("#auth-message").textContent = "密码已重置，请返回登录"; } catch (error) { $("#auth-message").textContent = error.message; }
  });
  $$("[data-password-toggle]").forEach((button) => {
    button.innerHTML = passwordIcon(false);
    button.addEventListener("click", () => togglePassword(button));
  });
  $$("[data-dialog-open]").forEach((button) => button.addEventListener("click", () => {
    const dialog = $(`#${button.dataset.dialogOpen}`);
    if (dialog && !dialog.open) dialog.showModal();
  }));
  $$("[data-dialog-close]").forEach((button) => button.addEventListener("click", () => button.closest("dialog")?.close()));
  $$(".settings-dialog").forEach((dialog) => dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  }));
  $$("#avatar-zoom, #avatar-x, #avatar-y").forEach((input) => input.addEventListener("input", drawAvatarCrop));
  $$("[data-avatar-choice]").forEach((button) => button.addEventListener("click", () => {
    const crop = state.avatarCrop;
    $("#avatar-crop-dialog").close();
    if (!crop || button.dataset.avatarChoice === "cancel") { state.avatarCrop = null; return; }
    if (button.dataset.avatarChoice === "original") {
      crop.onReady(crop.file);
      state.avatarCrop = null;
      return;
    }
    $("#avatar-crop-canvas").toBlob((blob) => {
      if (!blob) { toast("头像裁剪失败，请保留原图后重试", "error"); return; }
      crop.onReady(new File([blob], `${crop.file.name.replace(/\.[^.]+$/, "")}-cropped.jpg`, { type: "image/jpeg" }));
      state.avatarCrop = null;
    }, "image/jpeg", 0.92);
  }));
  $("#resume-avatar").addEventListener("change", (event) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    input.value = "";
    openAvatarCrop(file, (selected) => {
      const transfer = new DataTransfer();
      transfer.items.add(selected);
      input.files = transfer.files;
      $("#avatar-selection-note").textContent = selected === file ? `已选择原图：${selected.name}` : `已使用裁剪头像：${selected.name}`;
    });
  });
  $("#account-avatar-button")?.addEventListener("click", () => $("#account-avatar-input")?.click());
  $("#account-avatar-input")?.addEventListener("change", (event) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    input.value = "";
    openAvatarCrop(file, async (selected) => {
      const form = new FormData();
      form.append("file", selected, selected.name);
      try {
        const result = await request("/auth/avatar", { method: "POST", body: form });
        state.user = result.user;
        updateAccountView();
        toast("账号头像已更新");
      } catch (error) {
        toast(error.message, "error");
      }
    });
  });
  $$("[data-sms-target]").forEach((button) => button.addEventListener("click", () => sendSmsCode(button)));
  $("#logout").addEventListener("click", logout);
  $("#menu-toggle").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
  $$("[data-page]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.page)));
  $$("[data-go]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.go)));
  $("#rebuild-career-facts")?.addEventListener("click", async (event) => {
    const resumeId = selectedResumeId();
    if (!resumeId) { toast("请先在职业资产库创建一份基础简历", "error"); return; }
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await request("/career/facts/rebuild", { method: "POST", body: JSON.stringify({ resume_id: resumeId }) });
      await loadCareerFacts();
      toast("职业事实已从基础简历重建");
    } catch (error) { toast(error.message, "error"); } finally { button.disabled = false; }
  });
  $("#career-facts-list")?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-fact-action]");
    if (!button) return;
    const row = button.closest("[data-fact-id]");
    if (!row) return;
    button.disabled = true;
    try {
      await request(`/career/facts/${encodeURIComponent(row.dataset.factId)}/decision`, {
        method: "POST", body: JSON.stringify({ status: button.dataset.factAction })
      });
      await loadCareerFacts();
    } catch (error) { toast(error.message, "error"); button.disabled = false; }
  });
  $("#create-review")?.addEventListener("click", async (event) => {
    const resumeId = selectedResumeId();
    if (!resumeId || !isUsableJd(state.jd)) { toast("请先选择简历，并在岗位适配中完成岗位解析", "error"); return; }
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await request("/reviews", { method: "POST", body: JSON.stringify({ resume_id: resumeId, jd: state.jd }) });
      await loadReviews();
      toast("已创建岗位审阅，请逐条确认建议");
    } catch (error) { toast(error.message, "error"); } finally { button.disabled = false; }
  });
  $("#review-list")?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-review-action]");
    if (!button) return;
    const card = button.closest("[data-review-id]");
    const proposal = button.closest("[data-proposal-id]");
    if (!card || !proposal) return;
    button.disabled = true;
    try {
      await request(`/reviews/${encodeURIComponent(card.dataset.reviewId)}/proposals/${encodeURIComponent(proposal.dataset.proposalId)}`, {
        method: "POST", body: JSON.stringify({ decision: button.dataset.reviewAction, note: "" })
      });
      await loadReviews();
    } catch (error) { toast(error.message, "error"); button.disabled = false; }
  });
  $("#application-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      await request("/applications", { method: "POST", body: JSON.stringify(payload) });
      event.currentTarget.reset();
      await loadApplications();
      toast("投递记录已保存");
    } catch (error) { toast(error.message, "error"); }
  });
  $("#refresh-applications")?.addEventListener("click", loadApplications);
  $("#applications-list")?.addEventListener("change", async (event) => {
    const select = event.target.closest("[data-application-status]");
    if (!select) return;
    const row = select.closest("[data-application-id]");
    try {
      await request(`/applications/${encodeURIComponent(row.dataset.applicationId)}`, { method: "PATCH", body: JSON.stringify({ status: select.value }) });
      await loadApplications();
    } catch (error) { toast(error.message, "error"); }
  });
  $("#applications-list")?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-application-action='delete']");
    if (!button) return;
    const row = button.closest("[data-application-id]");
    armDanger(button, async () => {
      try { await request(`/applications/${encodeURIComponent(row.dataset.applicationId)}`, { method: "DELETE" }); await loadApplications(); toast("投递记录已删除"); }
      catch (error) { toast(error.message, "error"); }
    });
  });
  $("#billing-plans")?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-order-product]");
    if (!button) return;
    button.disabled = true;
    try {
      await request("/billing/orders", { method: "POST", body: JSON.stringify({ product_code: button.dataset.orderProduct }) });
      await loadBilling();
      toast("已创建待支付订单；请联系管理员确认到账后额度生效");
    } catch (error) { toast(error.message, "error"); } finally { button.disabled = false; }
  });
  $("#dismiss-onboarding")?.addEventListener("click", () => {
    localStorage.setItem("zhiday_onboarding_v1", "1");
    $("#path-onboarding")?.classList.add("hidden");
  });

  $$("[data-resume-method]").forEach((button) => button.addEventListener("click", () => switchPanels("[data-resume-method]", "[data-resume-panel]", "resumeMethod", button.dataset.resumeMethod)));
  $("#resume-editor-expand")?.addEventListener("click", () => setResumeEditorExpanded(true));
  $$("[data-jd-method]").forEach((button) => button.addEventListener("click", () => switchPanels("[data-jd-method]", "[data-jd-panel]", "jdMethod", button.dataset.jdMethod)));

  $("#resume-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const formElement = event.currentTarget; const payload = resumePayload(formElement); const avatar = formElement.elements.avatar?.files?.[0]; loading(true, "正在保存简历");
    try {
      const saved = state.editingId
        ? await request(`/resumes/${state.editingId}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await request("/resumes", { method: "POST", body: JSON.stringify(payload) });
      if (avatar) {
        const avatarForm = new FormData();
        avatarForm.append("file", avatar, avatar.name);
        await request(`/resumes/${saved.id}/avatar`, { method: "POST", body: avatarForm });
      }
      resetResumeEditor(); await loadResumes(); toast("简历已保存");
    } catch (error) { toast(error.message, "error"); } finally { loading(false); }
  });
  $("#cancel-edit").addEventListener("click", resetResumeEditor);

  async function uploadForm(event, path, message) {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); loading(true, message);
    try { await request(path, { method: "POST", body: form }); formElement.reset(); await loadResumes(); toast("简历已加入素材库"); } catch (error) { toast(error.message, "error"); } finally { loading(false); }
  }
  $("#document-form").addEventListener("submit", (event) => uploadForm(event, "/resumes/upload", "正在解析简历文档"));
  $("#resume-image-form").addEventListener("submit", (event) => uploadForm(event, "/resumes/ocr", "正在识别简历截图"));

  $("#resume-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-resume-action]"); if (!button) return;
    const row = button.closest("[data-resume-id]"); const resume = state.resumes.find((item) => item.id === row.dataset.resumeId); if (!resume) return;
    const action = button.dataset.resumeAction;
    if (action === "preview") {
      let panel = row.nextElementSibling;
      if (!(panel?.classList.contains("resume-preview-panel") && panel.dataset.resumePreviewId === String(resume.id))) {
        row.insertAdjacentHTML("afterend", `<div class="resume-preview-panel hidden" data-resume-preview-id="${escapeHtml(resume.id)}">${contentPreview(resume.content || {})}</div>`);
        panel = row.nextElementSibling;
      }
      const opening = panel.classList.contains("hidden");
      panel.classList.toggle("hidden", !opening);
      button.textContent = opening ? "收起预览" : "预览";
      button.setAttribute("aria-expanded", String(opening));
    }
    if (action === "avatar") {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/jpeg,image/png,image/webp";
      input.addEventListener("change", async () => {
        const file = input.files?.[0];
        if (!file) return;
        openAvatarCrop(file, async (selected) => {
          const form = new FormData();
          form.append("file", selected, selected.name);
          button.disabled = true;
          try { await request(`/resumes/${resume.id}/avatar`, { method: "POST", body: form }); await loadResumes(); toast("头像已保存，生成简历时会自动带上"); } catch (error) { toast(error.message, "error"); } finally { button.disabled = false; }
        });
      }, { once: true });
      input.click();
    }
    if (action === "edit") { fillResumeEditor(resume); }
    if (action === "default") { try { await request(`/resumes/${resume.id}/default`, { method: "POST" }); await loadResumes(); toast("默认简历已更新"); } catch (error) { toast(error.message, "error"); } }
    if (action === "delete") armDanger(button, async () => { try { await request(`/resumes/${resume.id}`, { method: "DELETE" }); await loadResumes(); toast("简历已删除"); } catch (error) { toast(error.message, "error"); } });
  });

  $("#jd-text-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const text = $("#jd-text").value.trim();
    if (text.length < 20) { toast("请粘贴至少 20 个字的岗位职责或任职要求", "error"); return; }
    state.radarJobId = null;
    parseJd({ source_type: "text", text });
  });
  $("#jd-url-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const url = $("#jd-url").value.trim();
    if (!/^https?:\/\/\S+$/i.test(url)) { toast("请输入完整的公开岗位链接，例如 https://…", "error"); return; }
    state.radarJobId = null;
    parseJd({ source_type: "url", url });
  });
  $("#jd-image").addEventListener("change", (event) => {
    const selected = [...event.currentTarget.files];
    if (!selected.length) return;
    const nextFiles = [...state.jdImageFiles, ...selected];
    const error = validateJdImages(nextFiles);
    if (error) {
      event.currentTarget.value = "";
      event.currentTarget.required = state.jdImageFiles.length === 0;
      setJdImageFeedback(error, true);
      toast(error, "error");
      return;
    }
    state.jdImageFiles = nextFiles;
    event.currentTarget.value = "";
    renderJdImageFiles();
  });
  $("#jd-image-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-image-action]");
    if (!button) return;
    const index = Number.parseInt(button.dataset.index, 10);
    if (!Number.isInteger(index) || index < 0 || index >= state.jdImageFiles.length) return;
    const action = button.dataset.imageAction;
    if (action === "remove") state.jdImageFiles.splice(index, 1);
    if (action === "up" && index > 0) [state.jdImageFiles[index - 1], state.jdImageFiles[index]] = [state.jdImageFiles[index], state.jdImageFiles[index - 1]];
    if (action === "down" && index < state.jdImageFiles.length - 1) [state.jdImageFiles[index + 1], state.jdImageFiles[index]] = [state.jdImageFiles[index], state.jdImageFiles[index + 1]];
    renderJdImageFiles();
  });
  $("#jd-image-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    state.radarJobId = null;
    const formElement = event.currentTarget;
    if (!state.jdImageFiles.length) {
      setJdImageFeedback("请先选择至少一张岗位截图。", true);
      return;
    }
    const form = new FormData();
    state.jdImageFiles.forEach((file) => form.append("files", file, file.name));
    const succeeded = await parseJd(form, true);
    if (!succeeded) return;
    state.jdImageFiles = [];
    formElement.reset();
    renderJdImageFiles();
  });
  async function queueGeneration(jd, button) {
    if (!isUsableJd(jd)) {
      toast("这条解析记录没有可用的岗位结果", "error");
      return;
    }
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "正在提交…";
    try {
      const allowedThemes = new Set(["auto", "tech_indigo", "operations_terra", "executive_navy", "care_teal", "creative_plum", "ats_mono"]);
      const requestedTheme = $("#design-theme")?.value || "auto";
      const selectedTemplate = state.templates.find((item) => item.id === state.selectedTemplateId);
      const normalizedJd = {
        ...jd,
        title: String(jd.title || "").trim(),
        company: String(jd.company || "").trim(),
        responsibilities: jdTextItems(jd.responsibilities),
        requirements: jdTextItems(jd.requirements),
        preferred: jdTextItems(jd.preferred),
        keywords: jdTextItems(jd.keywords)
      };
      const requestedLanguage = $("#generation-language")?.value || "zh";
      const highlights = [
        $("#hl-result")?.value?.trim(),
        $("#hl-problem")?.value?.trim(),
        $("#hl-edge")?.value?.trim(),
      ].filter(Boolean).slice(0, 5);
      const record = await request("/generations", { method: "POST", body: JSON.stringify({ resume_id: $("#match-resume").value || null, jd: normalizedJd, radar_job_id: state.radarJobId || null, design_theme: allowedThemes.has(requestedTheme) ? requestedTheme : "auto", template_id: selectedTemplate?.id || null, language: requestedLanguage, highlights }) });
      state.history = [record, ...state.history.filter((item) => item.id !== record.id)];
      renderHistory();
      navigate("history");
      toast("任务已在后台运行，可以离开此页面");
    } catch (error) { toast(error.message, "error"); } finally { button.disabled = false; button.textContent = original; }
  }

  $("#generate-button").addEventListener("click", async () => {
    await queueGeneration(state.jd, $("#generate-button"));
  });
  $("#open-template-picker")?.addEventListener("click", () => openTemplatePicker("generate"));
  $("#template-search")?.addEventListener("input", renderTemplateList);
  $("#template-category")?.addEventListener("change", renderTemplateList);
  $("#template-list")?.addEventListener("click", (event) => {
    const preview = event.target.closest("[data-template-preview]"); if (preview) { showTemplatePreview(preview.dataset.templatePreview); return; }
    const select = event.target.closest("[data-template-select]"); if (select) chooseTemplate(select.dataset.templateSelect);
  });
  $("[data-template-close]")?.addEventListener("click", () => $("#template-dialog").close());
  const designThemePreview = {
    auto: { label: "AI 自动匹配", hint: "按岗位选择 LapisCV 模板、配色和内容密度", primary: "#284C9B", ribbon: "#5D74C5", soft: "#EAF0FF" },
    tech_indigo: { label: "技术专业", hint: "LapisCV Classic：钴蓝层级，突出技术与项目", primary: "#284C9B", ribbon: "#5D74C5", soft: "#EAF0FF" },
    operations_terra: { label: "工程运营", hint: "LapisCV Classic：青绿主色，适合制造与工程", primary: "#1F6268", ribbon: "#1F6268", soft: "#E7F2EF" },
    executive_navy: { label: "稳重商务", hint: "LapisCV Classic：海军蓝，适合商务管理", primary: "#263B59", ribbon: "#7891AA", soft: "#EDF1F5" },
    care_teal: { label: "教育医疗", hint: "LapisCV Serif：柔和青绿，亲和且正式", primary: "#16756F", ribbon: "#69A89D", soft: "#E7F5F1" },
    creative_plum: { label: "品牌创意", hint: "LapisCV Serif：梅紫点缀，更有设计感", primary: "#75416F", ribbon: "#C67883", soft: "#F7EDF4" },
    ats_mono: { label: "打印友好", hint: "LapisCV Classic：低色彩，适合打印和 ATS", primary: "#3D4654", ribbon: "#697484", soft: "#F4F5F7" }
  };
  function renderDesignThemePreview(value) {
    const item = designThemePreview[value] || designThemePreview.auto;
    $("#design-theme-preview").innerHTML = `<i class="design-theme-preview__swatch" aria-hidden="true" style="--design-primary:${item.primary};--design-ribbon:${item.ribbon};--design-soft:${item.soft}"></i><div><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.hint)}</span></div>`;
  }
  function selectedTemplate() { return state.templates.find((item) => item.id === state.selectedTemplateId) || null; }
  function renderTemplateSelection() {
    const template = selectedTemplate();
    const target = $("#design-theme-preview");
    if (!target) return;
    if (!template) { renderDesignThemePreview($("#design-theme")?.value || "auto"); return; }
    target.innerHTML = `<i class="design-theme-preview__swatch" aria-hidden="true" style="--design-primary:${escapeHtml(template.accent || "#284C9B")};--design-ribbon:${escapeHtml(template.ribbon || template.accent || "#5D74C5")};--design-soft:${escapeHtml(template.soft || "#EAF0FF")}"></i><div><strong>${escapeHtml(template.name)}</strong><span>${escapeHtml(template.display_category || template.category || "授权模板")} · ${escapeHtml((template.tags || []).join(" / "))}</span></div>`;
  }
  async function loadTemplates() {
    try {
      state.templates = await request("/resume-templates");
      if (state.selectedTemplateId && !selectedTemplate()) { state.selectedTemplateId = ""; localStorage.removeItem("resume_ai_template_id"); }
      renderTemplateSelection();
    } catch (error) { console.warn("template catalogue unavailable", error); }
  }
  function renderTemplateList() {
    const list = $("#template-list"); if (!list) return;
    const query = $("#template-search")?.value.trim().toLowerCase() || "";
    const category = $("#template-category")?.value || "";
    const filtered = state.templates.filter((item) => {
      const haystack = [item.name, item.category, item.display_category, ...(item.tags || [])].join(" ").toLowerCase();
      return (!category || item.category === category) && (!query || haystack.includes(query));
    });
    list.innerHTML = filtered.length ? filtered.map((item) => `<article class="template-card ${item.id === state.selectedTemplateId ? "selected" : ""}" data-template-id="${escapeHtml(item.id)}"><div class="template-card__sheet" style="--template-accent:${escapeHtml(item.accent || "#284C9B")};--template-soft:${escapeHtml(item.soft || "#EAF0FF")}"><span></span><b>${escapeHtml(item.display_category || item.category)}</b><i></i><i></i><i></i></div><div class="template-card__body"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml((item.tags || []).join(" · "))}</p><small>${escapeHtml(item.preview_note || "预览结构与最终生成一致")}</small><div><button class="button secondary" type="button" data-template-preview="${escapeHtml(item.id)}">真实预览</button><button class="button primary" type="button" data-template-select="${escapeHtml(item.id)}">${item.id === state.selectedTemplateId ? "当前使用" : "使用此模板"}</button></div></div></article>`).join("") : '<div class="empty-state"><strong>没有找到相符模板</strong><p>换个关键词或分类看看。</p></div>';
  }
  async function openTemplatePicker(mode = "generate") {
    state.templatePickerMode = mode;
    await loadTemplates();
    const categories = [...new Set(state.templates.map((item) => item.category).filter(Boolean))];
    const select = $("#template-category");
    if (select) {
      const current = select.value;
      select.innerHTML = `<option value="">全部分类</option>${categories.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join("")}`;
      if ([...select.options].some((opt) => opt.value === current)) select.value = current;
    }
    renderTemplateList(); $("#template-dialog").showModal();
  }
  async function showTemplatePreview(templateId) {
    const template = state.templates.find((item) => item.id === templateId);
    if (!template) return;
    const content = $("#resume-preview-content");
    const run = ++state.previewRun;
    content.className = "preview-dialog__body";
    content.innerHTML = '<div class="preview-loading"><div class="loader"></div><strong>正在生成真实版式预览</strong><span>使用与最终 PDF 相同的排版引擎，不是色块示意图。</span></div>';
    $("#resume-preview-title").textContent = `${template.name} · 真实 PDF 预览`;
    $("#resume-preview-dialog").showModal();
    try {
      ensurePromiseWithResolvers();
      const response = await fetch(`${API}/resume-templates/${encodeURIComponent(templateId)}/preview.pdf`, {
        credentials: "same-origin",
        headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(errorDetailText(err.detail) || err.message || "模板预览生成失败");
      }
      const buffer = await response.arrayBuffer();
      if (run !== state.previewRun) return;
      const [pdfjs] = await Promise.all([import(`${BASE}/static/vendor/pdf.min.mjs`)]);
      pdfjs.GlobalWorkerOptions.workerSrc = `${BASE}/static/vendor/pdf.worker.compat.mjs`;
      const pdf = await pdfjs.getDocument({ data: new Uint8Array(buffer) }).promise;
      if (run !== state.previewRun) return;
      content.replaceChildren();
      const note = document.createElement("div");
      note.className = "word-preview-note";
      note.innerHTML = `<strong>真实版式预览</strong><span>版式：${escapeHtml(template.layout_variant || "")} · 与生成结果同源引擎（示例内容仅用于展示结构）</span>`;
      content.appendChild(note);
      const availableWidth = Math.max(240, Math.floor(content.getBoundingClientRect().width) - 20);
      for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
        const page = await pdf.getPage(pageNumber);
        if (run !== state.previewRun) return;
        const baseViewport = page.getViewport({ scale: 1 });
        const scale = Math.min(1.55, availableWidth / baseViewport.width);
        const viewport = page.getViewport({ scale });
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        const sheet = document.createElement("figure");
        sheet.className = "pdf-preview-page";
        const canvas = document.createElement("canvas");
        canvas.width = Math.ceil(viewport.width * pixelRatio);
        canvas.height = Math.ceil(viewport.height * pixelRatio);
        canvas.style.width = `${Math.round(viewport.width)}px`;
        canvas.style.height = `${Math.round(viewport.height)}px`;
        sheet.appendChild(canvas);
        const caption = document.createElement("figcaption");
        caption.textContent = `第 ${pageNumber} / ${pdf.numPages} 页`;
        sheet.appendChild(caption);
        content.appendChild(sheet);
        await page.render({
          canvasContext: canvas.getContext("2d"),
          viewport,
          transform: pixelRatio === 1 ? null : [pixelRatio, 0, 0, pixelRatio, 0, 0],
        }).promise;
      }
    } catch (error) {
      content.innerHTML = `<div class="parse-error"><strong>模板预览失败</strong><p>${escapeHtml(error.message)}</p></div>`;
    }
  }
  async function chooseTemplate(templateId) {
    const template = state.templates.find((item) => item.id === templateId); if (!template) return;
    state.selectedTemplateId = templateId; localStorage.setItem("resume_ai_template_id", templateId);
    if ($("#design-theme")) $("#design-theme").value = template.base_theme || "auto";
    renderTemplateSelection(); $("#template-dialog").close();
    if (String(state.templatePickerMode).startsWith("regenerate:")) {
      const generationId = String(state.templatePickerMode).split(":", 2)[1];
      const record = state.history.find((item) => item.id === generationId);
      if (record) {
        await request(`/generations/${encodeURIComponent(record.id)}/regenerate`, { method: "POST", body: JSON.stringify({ design_theme: template.base_theme || "auto", template_id: template.id }) });
        await loadHistory();
        toast(`已按「${template.name}」在后台重新生成`);
        return;
      }
    }
    toast(`已选择「${template.name}」`);
  }
  $("#design-theme").value = localStorage.getItem("resume_ai_design_theme") || "auto";
  renderTemplateSelection();
  $("#design-theme").addEventListener("change", (event) => {
    localStorage.setItem("resume_ai_design_theme", event.currentTarget.value);
    state.selectedTemplateId = ""; localStorage.removeItem("resume_ai_template_id"); renderTemplateSelection();
  });
  $("#refresh-jd-history").addEventListener("click", loadJdHistory);
  $("#jd-history-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-jd-history-action]");
    if (!button) return;
    const row = button.closest("[data-jd-task-id]");
    const task = state.jdHistory.find((item) => item.id === row?.dataset.jdTaskId);
    if (!isUsableJd(task?.result)) {
      toast("这条解析记录没有识别到有效岗位信息", "error");
      return;
    }
    if (button.dataset.jdHistoryAction === "use") {
      state.radarJobId = null;
      state.jd = task.result;
      renderJd();
      $("#jd-preview").scrollIntoView({ behavior: "smooth", block: "center" });
      toast("已切换到这条岗位解析结果");
    }
    if (button.dataset.jdHistoryAction === "generate") { state.radarJobId = null; await queueGeneration(task.result, button); }
  });

  $("#refresh-radar").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    state.radarFilters.page = 1;
    try { await loadRadar(); toast("推荐已按最新职业画像刷新"); } finally { button.disabled = false; }
  });
  function syncRadarFilterSummary() {
    const toggle = $("#radar-filter-toggle");
    const form = $("#radar-filter-form");
    const summary = $("#radar-filter-summary");
    if (!toggle || !form || !summary) return;
    const city = $("#radar-city")?.selectedOptions?.[0]?.textContent?.trim() || "全部城市";
    const publishedWithin = $("#radar-published-within")?.selectedOptions?.[0]?.textContent?.trim() || "近 30 天";
    const sortLabel = $("#radar-sort")?.selectedOptions?.[0]?.textContent?.trim() || "匹配优先";
    const salaryLabel = $("#radar-salary-min")?.selectedOptions?.[0]?.textContent?.trim();
    const query = $("#radar-query")?.value?.trim();
    const parts = [city, publishedWithin];
    if (salaryLabel && salaryLabel !== "不限薪资") parts.push(salaryLabel);
    const sourceLabel = $("#radar-source")?.selectedOptions?.[0]?.textContent?.trim();
    if (sourceLabel && sourceLabel !== "全部来源") parts.push(sourceLabel);
    if (sortLabel && sortLabel !== "匹配优先") parts.push(sortLabel);
    summary.textContent = query ? `${query} · ${parts.join(" · ")}` : parts.join(" · ");
    toggle.setAttribute("aria-expanded", String(form.classList.contains("is-open")));
  }
  $("#radar-filter-toggle")?.addEventListener("click", () => {
    $("#radar-filter-form")?.classList.toggle("is-open");
    syncRadarFilterSummary();
  });
  $("#radar-query")?.addEventListener("input", syncRadarFilterSummary);
  $("#radar-city")?.addEventListener("change", syncRadarFilterSummary);
  $("#radar-published-within")?.addEventListener("change", syncRadarFilterSummary);
  $("#radar-salary-min")?.addEventListener("change", syncRadarFilterSummary);
  $("#radar-sort")?.addEventListener("change", syncRadarFilterSummary);
  $("#radar-source")?.addEventListener("change", syncRadarFilterSummary);
  $("#radar-resume-options")?.addEventListener("change", (event) => {
    const input = event.target.closest('input[type="checkbox"]');
    if (!input) return;
    const selected = selectedRadarResumeIds();
    if (selected.length > 3) {
      input.checked = false;
      toast("最多只能合并 3 份简历", "error");
      return;
    }
    state.radarResumeIds = selected;
    renderRadarResumePicker();
    syncRadarFilterSummary();
  });
  async function applyRadarFilters() {
    state.radarFilters = {
      query: ($("#radar-query")?.value || "").trim(),
      city: $("#radar-city")?.value || "",
      publishedWithin: $("#radar-published-within")?.value || "all",
      salaryMin: Number($("#radar-salary-min")?.value) || 0,
      sortBy: $("#radar-sort")?.value || "match",
      experience: $("#radar-experience")?.value || "",
      education: $("#radar-education")?.value || "",
      topic: $("#radar-topic")?.value || "",
      source: $("#radar-source")?.value || "",
      savedOnly: Boolean(state.radarFilters.savedOnly),
      onlyNew: Boolean($("#radar-new-filter")?.checked),
      page: 1,
    };
    state.radarResumeIds = selectedRadarResumeIds().slice(0, 3);
    $("#radar-filter-form")?.classList.remove("is-open");
    syncRadarFilterSummary();
    await loadRadar();
  }
  function resetRadarFilters() {
    state.radarFilters = { query: "", city: "", publishedWithin: "all", page: 1, savedOnly: false, onlyNew: false, salaryMin: 0, sortBy: "match", experience: "", education: "", topic: "", source: "" };
    if ($("#radar-query")) $("#radar-query").value = "";
    if ($("#radar-city")) $("#radar-city").value = "";
    if ($("#radar-published-within")) $("#radar-published-within").value = "all";
    if ($("#radar-salary-min")) $("#radar-salary-min").value = "0";
    if ($("#radar-sort")) $("#radar-sort").value = "match";
    if ($("#radar-source")) $("#radar-source").value = "";
    if ($("#radar-new-filter")) $("#radar-new-filter").checked = false;
    state.radarResumeIds = [];
    renderRadarResumePicker();
    syncRadarFilterSummary();
  }
  $("#radar-filter-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await applyRadarFilters();
  });
  $("#radar-filter-reset")?.addEventListener("click", async () => {
    resetRadarFilters();
    await loadRadar();
  });
  // Instant apply for compact selects — search still uses submit / enter.
  ["#radar-city", "#radar-published-within", "#radar-salary-min", "#radar-sort", "#radar-experience", "#radar-education", "#radar-topic", "#radar-source"].forEach((sel) => {
    $(sel)?.addEventListener("change", async () => { await applyRadarFilters(); });
  });

  async function handleRadarPageJump() {
    const input = $("#radar-jump-page-input");
    if (!input || !state.radarPagination) return;
    let target = parseInt(input.value, 10);
    if (isNaN(target)) return;
    target = Math.max(1, Math.min(target, state.radarPagination.total_pages));
    if (target !== state.radarFilters.page) {
      state.radarFilters.page = target;
      await loadRadar();
      $("#radar-list")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  $("#radar-pagination").addEventListener("click", async (event) => {
    if (event.target.id === "radar-jump-page-btn" || event.target.closest("#radar-jump-page-btn")) {
      await handleRadarPageJump();
      return;
    }
    const button = event.target.closest("[data-radar-page]");
    if (!button || button.disabled || !state.radarPagination) return;
    const delta = button.dataset.radarPage === "next" ? 1 : -1;
    state.radarFilters.page = state.radarPagination.page + delta;
    await loadRadar();
    $("#radar-list").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  $("#radar-pagination").addEventListener("keydown", async (event) => {
    if (event.target.id === "radar-jump-page-input" && event.key === "Enter") {
      event.preventDefault();
      await handleRadarPageJump();
    }
  });
  $("#radar-saved-filter")?.addEventListener("click", async () => {
    state.radarFilters.savedOnly = !state.radarFilters.savedOnly;
    state.radarFilters.page = 1;
    await loadRadar();
  });
  $("#radar-new-filter")?.addEventListener("change", async () => { await applyRadarFilters(); });
  $("#radar-list").addEventListener("click", async (event) => {
    const target = event.target.closest("[data-radar-action]");
    if (!target) return;
    const row = target.closest("[data-radar-job-id]");
    const jobId = row?.dataset.radarJobId;
    if (!jobId) return;
    const action = target.dataset.radarAction;
    target.disabled = true;
    try {
      if (action === "details") {
        await showRadarJobDetail(jobId);
        return;
      }
      if (action === "toggle-more") {
        const more = row.querySelector(".radar-job__more");
        const expanded = more && !more.classList.contains("hidden");
        more?.classList.toggle("hidden", expanded);
        row.classList.toggle("radar-job--expanded", !expanded);
        target.setAttribute("aria-expanded", String(!expanded));
        target.textContent = expanded ? "更多" : "收起";
        target.disabled = false;
        return;
      }
      if (action === "optimize") {
        const data = await request(`/radar/jobs/${encodeURIComponent(jobId)}/prepare-optimization`, { method: "POST" });
        state.radarJobId = jobId;
        state.jd = data.jd;
        navigate("match");
        renderJd();
        $("#jd-preview").scrollIntoView({ behavior: "smooth", block: "center" });
        const adapted = row.classList.contains("radar-job--adapted");
        toast(adapted ? "已带入该岗位，可换模板后重新生成" : "岗位 JD 已带入，请选择基础简历后生成专属版本");
        return;
      }
      if (action === "block-company") {
        await request(`/radar/jobs/${encodeURIComponent(jobId)}/company-preference`, { method: "POST", body: JSON.stringify({ blocked: true }) });
        toast("已按你的偏好隐藏该公司岗位");
      } else {
        await setRadarFeedback(jobId, action === "not-interested" ? "not_interested" : "saved");
        toast(action === "saved" ? "已收藏，后续可随时回来准备投递" : "已隐藏这条岗位，推荐会据此调整");
      }
      await loadRadar();
    } catch (error) { toast(error.message, "error"); } finally { target.disabled = false; }
  });

  document.addEventListener("click", (event) => {
    const externalJob = event.target.closest("[data-external-job-id]");
    if (externalJob) {
      request(`/radar/jobs/${encodeURIComponent(externalJob.dataset.externalJobId)}/feedback`, { method: "POST", body: JSON.stringify({ action: "viewed" }), keepalive: true }).catch(() => {});
      return;
    }
    const download = event.target.closest("[data-generation-download]"); if (download) downloadGeneration(download.dataset.generationId, download.dataset.generationDownload);
    const preview = event.target.closest("[data-generation-preview]");
    if (preview) showGenerationPreview(preview.closest("[data-generation-id]")?.dataset.generationId, preview.dataset.generationPreview);
    const regenerate = event.target.closest("[data-generation-regenerate]");
    if (regenerate) {
      const record = state.history.find((item) => item.id === regenerate.closest("[data-generation-id]")?.dataset.generationId);
      if (record) {
        openTemplatePicker(`regenerate:${record.id}`).catch((error) => toast(error.message, "error"));
      }
    }
    const retry = event.target.closest('[data-history-action="retry"]');
    if (retry) {
      const row = retry.closest("[data-generation-id]");
      if (!row?.dataset.generationId) return;
      retry.disabled = true;
      request(`/generations/${encodeURIComponent(row.dataset.generationId)}/retry`, { method: "POST", body: "{}" })
        .then(() => Promise.all([loadHistory(), loadBilling()]))
        .then(() => toast("已重新提交生成，可离开页面稍后查看"))
        .catch((error) => {
          toast(error.message, "error");
          retry.disabled = false;
        });
      return;
    }
    const remove = event.target.closest('[data-history-action="delete"]');
    if (remove) armDanger(remove, async () => { const row = remove.closest("[data-generation-id]"); try { await request(`/generations/${row.dataset.generationId}`, { method: "DELETE" }); await loadHistory(); toast("生成记录已删除"); } catch (error) { toast(error.message, "error"); } });
  });

  $("[data-preview-close]").addEventListener("click", closeGenerationPreview);
  $("#resume-preview-dialog").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeGenerationPreview();
  });
  $("#regenerate-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const record = state.history.find((item) => item.id === $("#regenerate-id").value);
    if (!record) { toast("原生成记录不存在", "error"); return; }
    const submit = event.currentTarget.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      await request(`/generations/${encodeURIComponent(record.id)}/regenerate`, { method: "POST", body: JSON.stringify({ design_theme: $("#regenerate-theme").value, template_id: state.selectedTemplateId || record.design?.catalog_template_id || null }) });
      event.currentTarget.closest("dialog").close();
      await loadHistory();
      toast("新模板版本已在后台生成，旧版本会继续保留");
    } catch (error) { toast(error.message, "error"); } finally { submit.disabled = false; }
  });

  $("#password-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
    try { await request("/auth/change-password", { method: "POST", body: JSON.stringify(data) }); form.reset(); form.closest("dialog")?.close(); toast("密码已更新"); } catch (error) { toast(error.message, "error"); }
  });
  $("#phone-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
    try {
      const result = await request("/auth/change-phone", { method: "POST", body: JSON.stringify(data) });
      state.user = result.user;
      form.reset();
      form.closest("dialog")?.close();
      updateAccountView();
      toast("手机号已更新");
    } catch (error) { toast(error.message, "error"); }
  });
  $("#delete-account-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      await request("/auth/delete-account", { method: "POST", body: JSON.stringify(data) });
      form.closest("dialog").close();
      logout();
      $("#auth-message").className = "form-message success";
      $("#auth-message").textContent = "账号及全部数据已永久删除";
    } catch (error) { toast(error.message, "error"); } finally { submit.disabled = false; }
  });

  renderJdImageFiles();
  loadAppReleaseCard();

  (async function boot() {
    try { state.user = await request("/auth/me"); if (state.user.role === "admin") { logout({ notifyServer: false }); return; } await showApp(); } catch { logout({ notifyServer: false }); }
  })();
})();
