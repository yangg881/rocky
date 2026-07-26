(() => {
  const BASE = window.location.pathname.replace(/\/admin\/?$/, "");
  const API = `${BASE}/api`;
  const state = { token: null, user: null, users: [], records: [], tasks: [], templates: [], previewRun: 0, vendorScripts: {} };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  const formatDate = (value) => value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "";
  const formatBytes = (value) => { const size = Number(value || 0); if (size < 1024) return `${size} B`; if (size < 1024 ** 2) return `${(size / 1024).toFixed(1)} KB`; if (size < 1024 ** 3) return `${(size / 1024 ** 2).toFixed(1)} MB`; return `${(size / 1024 ** 3).toFixed(2)} GB`; };

  function toast(message, type = "success") { const element = $("#toast"); element.textContent = message; element.className = `toast show ${type === "error" ? "error" : ""}`; clearTimeout(toast.timer); toast.timer = setTimeout(() => { element.className = "toast"; }, 3200); }
  async function request(path, options = {}) { const headers = new Headers(options.headers || {}); if (state.token) headers.set("Authorization", `Bearer ${state.token}`); if (options.body) headers.set("Content-Type", "application/json"); const response = await fetch(`${API}${path}`, { ...options, headers, credentials: "same-origin" }); const data = await response.json().catch(() => ({})); if (!response.ok) throw new Error(Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join("；") : data.detail || "请求失败"); return data; }
  function logout({ notifyServer = true } = {}) { if (notifyServer) fetch(`${API}/auth/logout`, { method: "POST", credentials: "same-origin" }).catch(() => {}); state.token = null; $("#admin-app").classList.add("hidden"); $("#admin-login-view").classList.remove("hidden"); }
  function armDanger(button, callback) { if (button.dataset.armed === "true") { callback(); return; } const original = button.textContent; button.dataset.armed = "true"; button.textContent = "再次点击删除"; setTimeout(() => { button.dataset.armed = "false"; button.textContent = original; }, 3500); }
  function togglePassword(button) { const input = $(`#${button.dataset.passwordToggle}`); if (!input) return; const visible = input.type === "text"; input.type = visible ? "password" : "text"; button.setAttribute("aria-label", visible ? "显示密码" : "隐藏密码"); button.setAttribute("aria-pressed", String(!visible)); button.textContent = visible ? "◎" : "◉"; input.focus({ preventScroll: true }); }
  function itemText(item) { return typeof item === "string" ? item : Object.values(item || {}).filter(Boolean).join(" | "); }
  function preview(content) { return `<details><summary>预览内容</summary><div class="jd-content"><h3>${escapeHtml(content?.name || "个人简历")}</h3><p>${escapeHtml(content?.title || "")}</p><p>${escapeHtml(content?.summary || "")}</p>${(content?.experience || []).map((item) => `<p>${escapeHtml(itemText(item))}</p>`).join("")}</div></details>`; }
  function loadVendorScript(src, globalName) { if (globalName && window[globalName]) return Promise.resolve(window[globalName]); if (!state.vendorScripts[src]) state.vendorScripts[src] = new Promise((resolve, reject) => { const script = document.createElement("script"); script.src = src; script.defer = true; script.dataset.vendorSrc = src; script.onload = () => resolve(globalName ? window[globalName] : true); script.onerror = () => reject(new Error("预览组件加载失败")); document.head.appendChild(script); }); return state.vendorScripts[src]; }
  function ensurePromiseWithResolvers() { if (typeof Promise.withResolvers === "function") return; Promise.withResolvers = function withResolvers() { let resolve; let reject; const promise = new Promise((promiseResolve, promiseReject) => { resolve = promiseResolve; reject = promiseReject; }); return { promise, resolve, reject }; }; }
  function fitWordPreview(content) { const wrapper = content.querySelector(".docx-wrapper"); if (!wrapper) return; const availableWidth = Math.max(240, Math.floor(content.getBoundingClientRect().width) - 20); $$(".docx-wrapper > section.docx", content).forEach((page) => { page.style.transform = ""; page.style.marginBottom = ""; page.style.maxWidth = "none"; page.style.transformOrigin = "top center"; const pageWidth = Math.max(page.scrollWidth, page.getBoundingClientRect().width); const scale = Math.min(1, availableWidth / pageWidth); page.style.transform = `scale(${scale})`; page.style.marginBottom = `${Math.max(18, Math.round(24 * scale))}px`; }); }
  async function fetchAdminGenerationFile(userId, generationId, format) { const response = await fetch(`${API}/admin/generations/${encodeURIComponent(userId)}/${encodeURIComponent(generationId)}/download/${format}`, { credentials: "same-origin", headers: state.token ? { Authorization: `Bearer ${state.token}` } : {} }); if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || `${format.toUpperCase()} 文件读取失败`); } return response.arrayBuffer(); }
  async function showAdminGenerationPreview(row, format = "pdf") {
    const record = state.records.find((item) => item.id === row.dataset.recordId && item.user_id === row.dataset.recordUser);
    const normalized = format === "docx" ? "docx" : "pdf";
    const label = normalized === "docx" ? "Word" : "PDF";
    if (!record?.files?.[normalized]?.key) { toast(`${label} 文件尚未准备好`, "error"); return; }
    const run = ++state.previewRun;
    const content = $("#admin-preview-content");
    content.className = `preview-dialog__body ${normalized === "docx" ? "word-preview-body" : ""}`;
    content.innerHTML = `<div class="preview-loading"><div class="loader"></div><strong>正在读取真实 ${label} 文件</strong><span>正在还原文档内容、图片和排版层级</span></div>`;
    $("#admin-preview-title").textContent = `${record.jd?.title || "适配简历"} · ${label} 真实预览`;
    $("#admin-preview-dialog").showModal();
    try {
      if (normalized === "docx") {
        await loadVendorScript(`${BASE}/static/vendor/jszip.min.js`, "JSZip");
        const docx = await loadVendorScript(`${BASE}/static/vendor/docx-preview.min.js`, "docx");
        const buffer = await fetchAdminGenerationFile(record.user_id, record.id, "docx");
        if (run !== state.previewRun) return;
        content.replaceChildren();
        const note = document.createElement("div");
        note.className = "word-preview-note";
        note.innerHTML = "<strong>Word 预览说明</strong><span>浏览器会尽量按 A4 还原版式，但 Word/WPS 会按本机字体和分页引擎重新排版；最终页数以下载打开为准。</span>";
        content.appendChild(note);
        const host = document.createElement("div");
        host.className = "word-preview-host";
        content.appendChild(host);
        await docx.renderAsync(buffer, host, null, { className: "docx", inWrapper: true, breakPages: true, experimental: true, ignoreLastRenderedPageBreak: false, renderHeaders: true, renderFooters: true });
        fitWordPreview(content);
        return;
      }
      ensurePromiseWithResolvers();
      const [pdfjs, buffer] = await Promise.all([import(`${BASE}/static/vendor/pdf.min.mjs`), fetchAdminGenerationFile(record.user_id, record.id, "pdf")]);
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
        await page.render({ canvasContext: canvas.getContext("2d"), viewport, transform: pixelRatio === 1 ? null : [pixelRatio, 0, 0, pixelRatio, 0, 0] }).promise;
      }
    } catch (error) {
      if (run !== state.previewRun) return;
      content.innerHTML = `<div class="parse-error"><strong>${label} 预览加载失败</strong><p>${escapeHtml(error.message)}</p><small>文件仍可正常下载，请稍后重试预览。</small></div>`;
    }
  }
  function closeAdminGenerationPreview() { state.previewRun += 1; $("#admin-preview-dialog").close(); $("#admin-preview-content").replaceChildren(); }

  function taskLabel(status) { return ({ completed: "成功", failed: "失败", processing: "处理中", pending: "等待中", unknown: "未标记" })[status] || status; }
  function taskClass(status) { return status === "failed" ? "failed" : status === "completed" ? "completed" : "processing"; }
  function renderOperations(operations = {}) {
    const statuses = operations.task_statuses || {};
    const total = Object.values(statuses).reduce((sum, value) => sum + Number(value || 0), 0);
    const completed = Number(statuses.completed || 0);
    const failed = Number(statuses.failed || 0);
    const successRate = total ? Math.round((completed / total) * 100) : 0;
    $("#task-total").textContent = total ? `${total} 个任务 · 成功率 ${successRate}%` : "暂无任务";
    const order = ["completed", "processing", "failed", "pending"];
    const entries = [...order.filter((key) => statuses[key] !== undefined).map((key) => [key, statuses[key]]), ...Object.entries(statuses).filter(([key]) => !order.includes(key))];
    $("#task-status-chart").innerHTML = entries.length ? entries.map(([status, count]) => {
      const value = Number(count || 0); const width = total ? Math.max(4, Math.round((value / total) * 100)) : 0;
      return `<div class="status-chart__row"><div><span class="generation-state ${taskClass(status)}">${escapeHtml(taskLabel(status))}</span><strong>${value}</strong></div><div class="status-chart__track"><i class="${taskClass(status)}" style="width:${width}%"></i></div></div>`;
    }).join("") : '<div class="chart-empty">尚无任务数据</div>';
    const failures = operations.latest_failures || [];
    $("#admin-alert-list").innerHTML = failures.length ? failures.slice(0, 5).map((task) => `<article class="admin-alert"><span class="generation-state failed">失败</span><div><strong>${escapeHtml(task.detail || (task.task_type === "jd_parse" ? "岗位解析" : "简历生成"))}</strong><p>${escapeHtml(task.error || "未记录失败原因")}</p><small>${formatDate(task.updated_at || task.created_at)}</small></div></article>`).join("") : '<div class="chart-empty chart-empty--success"><strong>运行平稳</strong><span>暂无需要人工处理的失败任务。</span></div>';
    const recent = [...state.tasks].slice(0, 6);
    $("#recent-task-list").innerHTML = recent.length ? recent.map((task) => `<article class="recent-task"><div><span class="generation-state ${taskClass(task.status)}">${escapeHtml(taskLabel(task.status || "unknown"))}</span><strong>${escapeHtml(task.detail || "未命名任务")}</strong><p>${escapeHtml(task.username || task.user_id || "未知用户")} · ${formatDate(task.created_at)}</p></div><span class="recent-task__type">${task.task_type === "jd_parse" ? "岗位解析" : "简历生成"}</span></article>`).join("") : '<div class="chart-empty">暂无任务记录</div>';
    return { total, completed, failed, successRate };
  }
  async function loadStats() {
    try {
      const [data, operations, tasks] = await Promise.all([request("/admin/stats"), request("/admin/operations"), request("/admin/tasks")]);
      state.tasks = tasks || [];
      const operationSummary = renderOperations(operations);
      $("#stat-cards").innerHTML = [["普通用户", data.users], ["基础简历", data.resumes], ["已生成简历", data.generations], ["任务成功率", `${operationSummary.successRate}%`]].map(([label, value]) => `<div class="stat-item"><span>${label}</span><strong>${value}</strong></div>`).join("");
      const storage = data.storage || {}; const warnings = storage.warnings || {}; const healthy = !Object.values(warnings).some(Boolean);
      $("#storage-health").className = `status ${healthy ? "good" : "warn"}`; $("#storage-health").textContent = healthy ? "用量正常" : "已触发预警";
      $("#bucket-usage").innerHTML = Object.entries(storage.buckets || {}).map(([alias, item]) => `<div class="bucket-row"><strong>TOS-${alias.toUpperCase()}</strong><code title="${escapeHtml(item.bucket)}">${escapeHtml(item.bucket)}</code><span>${item.objects} 个对象 · ${formatBytes(item.bytes)}</span></div>`).join("");
      $("#storage-note").textContent = `${storage.note || ""} 当前累计请求 ${storage.requests || 0} 次，估算流出 ${formatBytes(storage.egress_bytes_estimated)}。`;
      $("#model-stats").innerHTML = Object.entries(data.models || {}).map(([model, count]) => `<div class="model-item"><code>${escapeHtml(model)}</code><strong>${count} 次</strong></div>`).join("") || '<div class="empty-state"><strong>暂无模型调用</strong></div>';
      $("#admin-updated-at").textContent = `更新于 ${new Intl.DateTimeFormat("zh-CN", { timeStyle: "short" }).format(new Date())}`;
    } catch (error) { toast(error.message, "error"); }
  }

  async function loadUsers() {
    try {
      state.users = await request("/admin/users");
      $("#users-table").innerHTML = state.users.map((user) => {
        if (user.role === "admin") {
          return `<tr data-user-id="${escapeHtml(user.id)}"><td>${escapeHtml(user.username)}</td><td>${escapeHtml(user.phone || user.phone_masked || "未绑定")}</td><td>管理员</td><td>${formatDate(user.created_at)}</td><td colspan="2">当前账号</td></tr>`;
        }
        const billing = user.billing || {};
        const available = Number(billing.available ?? billing.credits ?? 0);
        const reserved = Number(billing.reserved || 0);
        const suspended = Boolean(billing.suspended);
        const creditLabel = suspended
          ? `<span class="generation-state failed">已暂停</span> 余额 ${Number(billing.credits || 0)}（可用 0）`
          : `可用 <strong>${available}</strong> / 余额 ${Number(billing.credits || 0)}${reserved ? ` / 预扣 ${reserved}` : ""}`;
        return `<tr data-user-id="${escapeHtml(user.id)}"><td>${escapeHtml(user.username)}</td><td>${escapeHtml(user.phone || user.phone_masked || "未绑定")}</td><td>普通用户</td><td>${formatDate(user.created_at)}</td><td class="admin-credit-cell">${creditLabel}</td><td>
          <button class="button secondary" data-user-action="credit-add">+额度</button>
          <button class="button secondary" data-user-action="credit-sub">-额度</button>
          <button class="button secondary" data-user-action="credit-set">设为</button>
          <button class="button ${suspended ? "primary" : "secondary"}" data-user-action="${suspended ? "credit-resume" : "credit-suspend"}">${suspended ? "恢复" : "暂停"}</button>
          <button class="button danger" data-user-action="credit-clear">清零</button>
          <button class="button secondary" data-user-action="phone">改手机号</button>
          <button class="button secondary" data-user-action="password">代设密码</button>
          <button class="button danger" data-user-action="delete">删除</button>
        </td></tr>`;
      }).join("");
    } catch (error) { toast(error.message, "error"); }
  }

  async function updateUserCredits(userId, mode, amount = null) {
    const body = { mode, note: "管理员后台操作" };
    if (amount !== null && amount !== undefined) body.amount = Number(amount);
    await request(`/admin/users/${encodeURIComponent(userId)}/credits`, { method: "PATCH", body: JSON.stringify(body) });
    await loadUsers();
  }
  async function loadRecords() {
    try {
      state.records = await request("/admin/generations");
      $("#admin-records").innerHTML = state.records.length ? state.records.map((record) => {
        const status = record.status || "completed";
        const statusText = status === "processing" ? "生成中" : status === "failed" ? "生成失败" : "已完成";
        const statusClass = status === "processing" ? "processing" : status === "failed" ? "failed" : "completed";
        const detail = status === "processing"
          ? `<p class="generation-message">${escapeHtml(record.progress_message || "正在后台生成")}</p>`
          : status === "failed"
            ? `<p class="generation-message error">${escapeHtml(record.error || "生成失败")}</p>`
            : preview(record.optimized);
        const downloads = status === "completed" ? `<button class="button primary" data-record-preview="docx">预览 Word</button><button class="button primary" data-record-preview="pdf">预览 PDF</button><button class="button secondary" data-download-bucket="b" data-download-key="${escapeHtml(record.files?.docx?.key || "")}">下载 Word</button><button class="button secondary" data-download-bucket="b" data-download-key="${escapeHtml(record.files?.pdf?.key || "")}">下载 PDF</button>` : "";
        return `<article class="history-row" data-record-user="${escapeHtml(record.user_id)}" data-record-id="${escapeHtml(record.id)}"><div><div class="history-status"><span class="generation-state ${statusClass}">${statusText}</span><h3>${escapeHtml(record.jd?.title || "未命名岗位")}</h3></div><p>用户 ${escapeHtml(record.username || record.user_id)} · ${formatDate(record.created_at)}</p>${detail}</div><div class="history-actions">${downloads}<button class="button danger" data-record-action="delete">删除</button></div></article>`;
      }).join("") : '<div class="empty-state"><strong>暂无生成记录</strong></div>';
    } catch (error) { toast(error.message, "error"); }
  }
  async function loadTasks() {
    try {
      state.tasks = await request("/admin/tasks");
      $("#admin-tasks").innerHTML = state.tasks.length ? state.tasks.map((task) => {
        const type = task.task_type === "jd_parse" ? "岗位解析" : "简历生成";
        const statusText = task.status === "processing" ? "处理中" : task.status === "failed" ? "失败" : "成功";
        const statusClass = task.status === "processing" ? "processing" : task.status === "failed" ? "failed" : "completed";
        const meta = task.model_metadata || {};
        const diagnostic = task.error_category
          ? `<small>${escapeHtml([task.error_category, meta.model, meta.finish_reason, Number.isInteger(meta.retry_count) ? `重试 ${meta.retry_count} 次` : ""].filter(Boolean).join(" · "))}</small>`
          : "";
        return `<tr><td>${type}</td><td>${escapeHtml(task.username || task.user_id)}</td><td class="task-detail">${escapeHtml(task.detail || "未命名任务")}</td><td><span class="generation-state ${statusClass}">${statusText}</span></td><td class="task-reason ${task.error ? "error" : ""}">${escapeHtml(task.error || "—")}${diagnostic}</td><td>${formatDate(task.created_at)}</td></tr>`;
      }).join("") : '<tr><td colspan="6">暂无任务记录</td></tr>';
    } catch (error) { toast(error.message, "error"); }
  }
  async function loadTemplates() {
    try {
      state.templates = await request("/admin/resume-templates");
      const root = $("#admin-template-list");
      if (!root) return;
      root.innerHTML = state.templates.map((item) => `<article class="history-row" data-template-id="${escapeHtml(item.id)}"><div><div class="history-status"><span class="generation-state ${item.active ? "completed" : "failed"}">${item.active ? "已上架" : "已下架"}</span><h3>${escapeHtml(item.name)}</h3></div><p>${escapeHtml(item.display_category || item.category || "未分类")} · ${escapeHtml((item.tags || []).join(" / "))}</p><p class="generation-message"><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${escapeHtml(item.accent || "#284C9B")}"></i> 配色 ${escapeHtml(item.accent || "-")} · 排序 ${Number(item.sort_order || 0)} · 原文件 ${escapeHtml(item.source_file || "Word")}</p></div><div class="history-actions"><button class="button secondary" data-template-action="rename">改名称</button><button class="button secondary" data-template-action="tags">改标签</button><button class="button secondary" data-template-action="order">改排序</button><button class="button ${item.active ? "danger" : "primary"}" <button class="button secondary" data-template-action="color">改配色</button>data-template-action="toggle">${item.active ? "下架" : "上架"}</button></div></article>`).join("") || '<div class="empty-state"><strong>暂未导入模板</strong><p>请通过授权模板导入流程添加原始 Word 文件。</p></div>';
    } catch (error) { toast(error.message, "error"); }

  async function uploadTemplate() {
    const name = prompt("\u6A21\u677F\u540D\u79F0\uFF08\u4F8B\u5982\uFF1A\u6DF1\u84DD\u4E13\u4E1A\u7248\uFF09");
    if (!name) return;
    const tags = prompt("\u6807\u7B7E\uFF08\u7528\u9017\u53F7\u5206\u9694\uFF09") || "";
    const order = prompt("\u6392\u5E8F\uFF08\u6570\u5B57\u8D8A\u5C0F\u8D8A\u9760\u524D\uFF09", "10") || "10";
    try {
      await request("/admin/resume-templates", { method: "POST", body: JSON.stringify({ name: name.trim(), tags: tags.split(",").map(s=>s.trim()).filter(Boolean), order: Number(order)||10, active: true }) });
      await loadTemplates();
      toast("\u6A21\u677F\u5DF2\u65B0\u589E", "success");
    } catch (e) { toast(e.message, "error"); }
  }  }
  async function loadOrders() {
    try {
      state.orders = await request("/admin/orders");
      const root = $("#admin-orders");
      if (!root) return;
      const statusLabel = { pending: "待支付", paid: "已到账", cancelled: "已取消", refunded: "已退款" };
      const packageLabel = { starter: "入门包", pro: "进阶包", career_plus: "职业加速包" };
      root.innerHTML = state.orders.length ? state.orders.map((order) => {
        const actions = order.status === "pending"
          ? `<button class="button primary" data-order-action="paid">确认到账</button> <button class="button secondary" data-order-action="cancelled">取消</button>`
          : order.status === "paid"
            ? `<button class="button danger" data-order-action="refunded">标记退款</button>`
            : `<span class="muted">无操作</span>`;
        const username = order.username || "";
        const userLabel = username
          ? `<strong>${escapeHtml(username)}</strong><small class="order-user-id">${escapeHtml(String(order.user_id || "").slice(0, 8))}…</small>`
          : `<span class="order-user-id">${escapeHtml(order.user_id || "未知用户")}</span>`;
        const packageName = order.product_name || packageLabel[order.product_code] || order.product_code || "未知套餐";
        return `<tr data-order-user="${escapeHtml(order.user_id)}" data-order-id="${escapeHtml(order.id)}">
          <td class="order-user-cell">${userLabel}</td>
          <td class="order-package-cell">${escapeHtml(packageName)}</td>
          <td>${Number(order.credits || 0)} 次</td>
          <td>¥${(Number(order.amount_cents || 0) / 100).toFixed(2)}</td>
          <td><span class="generation-state ${order.status === "paid" ? "completed" : order.status === "pending" ? "processing" : "failed"}">${escapeHtml(statusLabel[order.status] || order.status)}</span></td>
          <td>${formatDate(order.created_at)}</td>
          <td class="order-actions-cell">${actions}</td>
        </tr>`;
      }).join("") : '<tr><td colspan="7">暂无订单</td></tr>';
    } catch (error) { toast(error.message, "error"); }
  }
  async function showApp() { $("#admin-login-view").classList.add("hidden"); $("#admin-app").classList.remove("hidden"); $("#admin-name").textContent = state.user.username; await Promise.all([loadStats(), loadUsers(), loadRecords(), loadOrders()]); }
  function navigate(page) { $$("[data-admin-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.adminPanel === page)); $$("[data-admin-page]").forEach((button) => button.classList.toggle("active", button.dataset.adminPage === page)); if (page === "dashboard") loadStats(); if (page === "users") loadUsers(); if (page === "records") loadRecords(); if (page === "tasks") loadTasks(); if (page === "templates") loadTemplates(); if (page === "orders") loadOrders(); }
  function setAdminPasswordFormExpanded(expanded) {
    const form = $("#admin-password-form");
    const card = $(".admin-security-card");
    if (!form || !card) return;
    form.classList.toggle("hidden", !expanded);
    form.setAttribute("aria-hidden", String(!expanded));
    card.classList.toggle("hidden", expanded);
    if (expanded) $("#admin-current-password")?.focus({ preventScroll: true });
  }
  async function download(key, bucket = "b") { try { const data = await request(`/file-link?bucket=${encodeURIComponent(bucket)}&key=${encodeURIComponent(key)}`); window.open(data.url, "_blank", "noopener,noreferrer"); } catch (error) { toast(error.message, "error"); } }

  $("#admin-login-form").addEventListener("submit", async (event) => { event.preventDefault(); try { const data = await request("/auth/login", { method: "POST", body: JSON.stringify({ username: $("#admin-username").value, password: $("#admin-password").value }) }); if (data.user.role !== "admin") throw new Error("该账号不是管理员"); state.token = null; state.user = data.user; showApp(); } catch (error) { $("#admin-login-message").textContent = error.message; } });
  $("#admin-logout").addEventListener("click", logout);
  $("#admin-mobile-logout")?.addEventListener("click", logout);
  $("#refresh-stats").addEventListener("click", loadStats);
  $$("[data-admin-page]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.adminPage)));
  $("#admin-password-expand")?.addEventListener("click", () => setAdminPasswordFormExpanded(true));
  $("#admin-password-cancel")?.addEventListener("click", () => {
    $("#admin-password-form")?.reset();
    setAdminPasswordFormExpanded(false);
  });
  $("#users-table").addEventListener("click", (event) => {
    const button = event.target.closest("[data-user-action]"); if (!button) return;
    const id = button.closest("[data-user-id]").dataset.userId;
    const action = button.dataset.userAction;
    if (action === "credit-add") {
      const value = window.prompt("增加多少次额度？", "10");
      if (value === null || !/^\d+$/.test(value.trim()) || Number(value) <= 0) return;
      updateUserCredits(id, "add", Number(value.trim())).then(() => toast("已增加额度")).catch((error) => toast(error.message, "error"));
      return;
    }
    if (action === "credit-sub") {
      const value = window.prompt("减少多少次可用额度？", "1");
      if (value === null || !/^\d+$/.test(value.trim()) || Number(value) <= 0) return;
      updateUserCredits(id, "sub", Number(value.trim())).then(() => toast("已减少额度")).catch((error) => toast(error.message, "error"));
      return;
    }
    if (action === "credit-set") {
      const value = window.prompt("将余额设置为多少次？", "3");
      if (value === null || !/^\d+$/.test(value.trim())) return;
      updateUserCredits(id, "set", Number(value.trim())).then(() => toast("已设置额度")).catch((error) => toast(error.message, "error"));
      return;
    }
    if (action === "credit-clear") {
      armDanger(button, async () => {
        try { await updateUserCredits(id, "clear"); toast("已清零可用额度（进行中任务预扣保留）"); }
        catch (error) { toast(error.message, "error"); }
      });
      return;
    }
    if (action === "credit-suspend") {
      updateUserCredits(id, "suspend").then(() => toast("已暂停该用户额度")).catch((error) => toast(error.message, "error"));
      return;
    }
    if (action === "credit-resume") {
      updateUserCredits(id, "resume").then(() => toast("已恢复该用户额度")).catch((error) => toast(error.message, "error"));
      return;
    }
    if (button.dataset.userAction === "phone") {
      const row = button.closest("tr");
      if (row.querySelector(".inline-phone")) return;
      row.lastElementChild.insertAdjacentHTML("beforeend", '<span class="inline-phone"><input inputmode="tel" placeholder="输入新手机号" aria-label="新手机号"><button class="button primary" data-user-action="save-phone">保存</button></span>');
    }
    if (button.dataset.userAction === "save-phone") {
      const phone = button.previousElementSibling.value;
      request(`/admin/users/${id}/phone`, { method: "PATCH", body: JSON.stringify({ phone }) }).then(() => { toast("用户手机号已更新"); loadUsers(); }).catch((error) => toast(error.message, "error"));
    }
    if (button.dataset.userAction === "password") {
      const row = button.closest("tr");
      if (row.querySelector(".inline-password")) return;
      const passwordId = `inline-password-${id}`;
      row.lastElementChild.insertAdjacentHTML("beforeend", `<span class="inline-password"><span class="password-field compact"><input id="${escapeHtml(passwordId)}" type="password" minlength="8" placeholder="输入新密码" aria-label="新密码"><button class="password-toggle" type="button" data-password-toggle="${escapeHtml(passwordId)}" aria-label="显示密码" aria-pressed="false">◎</button></span><button class="button primary" data-user-action="save-password">保存</button></span>`);
    }
    if (button.dataset.userAction === "save-password") {
      const password = button.closest(".inline-password").querySelector("input").value;
      request(`/admin/users/${id}/password`, { method: "PATCH", body: JSON.stringify({ new_password: password }) }).then(() => { toast("用户密码已更新"); loadUsers(); }).catch((error) => toast(error.message, "error"));
    }
    if (button.dataset.userAction === "delete") armDanger(button, async () => { try { await request(`/admin/users/${id}`, { method: "DELETE" }); await Promise.all([loadUsers(), loadStats()]); toast("用户及其数据已删除"); } catch (error) { toast(error.message, "error"); } });
  });
  $("#admin-records").addEventListener("click", (event) => { const previewButton = event.target.closest("[data-record-preview]"); if (previewButton) { showAdminGenerationPreview(previewButton.closest("[data-record-id]"), previewButton.dataset.recordPreview); return; } const dl = event.target.closest("[data-download-key]"); if (dl) download(dl.dataset.downloadKey, dl.dataset.downloadBucket); const button = event.target.closest('[data-record-action="delete"]'); if (button) armDanger(button, async () => { const row = button.closest("[data-record-id]"); try { await request(`/admin/generations/${row.dataset.recordUser}/${row.dataset.recordId}`, { method: "DELETE" }); await Promise.all([loadRecords(), loadStats()]); toast("记录已删除"); } catch (error) { toast(error.message, "error"); } }); });
  $("#refresh-templates")?.addEventListener("click", loadTemplates);
  $("#refresh-orders")?.addEventListener("click", loadOrders);
  $("#admin-orders")?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-order-action]");
    if (!button) return;
    const row = button.closest("[data-order-id]");
    if (!row) return;
    button.disabled = true;
    try {
      await request(`/admin/orders/${encodeURIComponent(row.dataset.orderUser)}/${encodeURIComponent(row.dataset.orderId)}`, {
        method: "PATCH",
        body: JSON.stringify({ status: button.dataset.orderAction }),
      });
      await loadOrders();
      toast(button.dataset.orderAction === "paid" ? "已确认到账并发放额度" : "订单状态已更新");
    } catch (error) {
      toast(error.message, "error");
      button.disabled = false;
    }
  });
  $("#admin-template-list")?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-template-action]"); if (!button) return;
    const row = button.closest("[data-template-id]"); const template = state.templates.find((item) => item.id === row?.dataset.templateId); if (!template) return;
    const action = button.dataset.templateAction; let patch = null;
    if (action === "toggle") patch = { active: !template.active };
    if (action === "rename") { const value = window.prompt("模板显示名称", template.name); if (value !== null && value.trim()) patch = { name: value.trim() }; }
    if (action === "tags") { const value = window.prompt("标签（使用中文逗号分隔）", (template.tags || []).join("，")); if (value !== null) patch = { tags: value.split(/[，,]/).map((item) => item.trim()).filter(Boolean) }; }
    if (action === "color") { const value = window.prompt("主题色（十六进制，如 #1a56db）", template.accent || "#284C9B"); if (value !== null && value.trim()) patch = { accent: value.trim() }; }
    if (action === "order") { const value = window.prompt("展示排序（数字越小越靠前）", String(template.sort_order || 1)); if (value !== null && /^\d+$/.test(value.trim())) patch = { sort_order: Number(value.trim()) }; }
    if (!patch) return;
    try { await request(`/admin/resume-templates/${encodeURIComponent(template.id)}`, { method: "PATCH", body: JSON.stringify(patch) }); await loadTemplates(); toast("模板配置已保存"); } catch (error) { toast(error.message, "error"); }
  });
  $("[data-admin-preview-close]")?.addEventListener("click", closeAdminGenerationPreview);
  $("#admin-preview-dialog")?.addEventListener("click", (event) => { if (event.target.id === "admin-preview-dialog") closeAdminGenerationPreview(); });
  document.addEventListener("click", (event) => { const button = event.target.closest("[data-password-toggle]"); if (button) togglePassword(button); });
  $("#admin-password-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; try { await request("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: $("#admin-current-password").value, new_password: $("#admin-new-password").value }) }); form.reset(); setAdminPasswordFormExpanded(false); toast("管理员密码已更新"); } catch (error) { toast(error.message, "error"); } });

  (async function boot() { try { state.user = await request("/auth/me"); if (state.user.role !== "admin") throw new Error(); await showApp(); } catch { logout({ notifyServer: false }); } })();
})();
