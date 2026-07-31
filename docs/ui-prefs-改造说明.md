# 外观与语言模块 · 改造落地说明

> 项目：职达简历 (JD Resume AI) · 模块：颜色外观 + 语言切换
> 日期：2026-08-01 · 状态：已上线（https://zhidajob.top）

## 一、改造动因（原方案的 5 个问题）

| # | 问题 | 原实现 |
|---|------|--------|
| 1 | **双轨系统冲突** | `global-theme-i18n.js` 与 `ui-preferences.js` 并存，后者被前者覆盖（二态主题 + 仅 12 词条，清空完整翻译） |
| 2 | **无「跟随系统」** | 现代主题第一需求缺失（旧 A 系统无 auto，B 系统有但被覆盖） |
| 3 | **脆弱翻译** | `setInterval(1.5s)` 轮询 + 全文档 `TreeWalker` 硬替换文本节点 |
| 4 | **emoji 图标 + 小触控** | `🌙/☀️/🌐` 当图标，按钮高仅 ~28px |
| 5 | **硬编码覆盖堆叠** | CSS 大量 `:root[data-theme=dark] .xxx` 逐条 `!important` 覆盖 |

## 二、新方案核心

### 1. 单一系统 `ui-prefs.js`
- **合并**旧双轨为唯一实现，存储统一为 `localStorage['zhiday_ui_prefs'] = { theme, lang }`
- **一次性迁移**旧 key（`zhida_global_theme` / `zhida_global_lang`）后清理
- **兼容接口保留**：`window.__i18n.{t,translate,setLang,setTheme,prefs}` 与 `window.zhidaI18n(key)`（app.js 依赖）

### 2. 三态主题（默认 auto）
`auto`（跟随系统）→ `light` → `dark` 循环切换
- `auto` 监听 `prefers-color-scheme` 变化，**OS 切换实时跟随**
- 无 matchMedia 环境回退深色（产品默认）

### 3. 分段控制条（替代 emoji 按钮）
```
[◐ 自动] [☀ 浅色] [☾ 深色]  │  [中] [EN]
```
- **SVG 线条图标**（Lucide 风格），非 emoji
- 激活态用 accent 胶囊，触控目标 ≥40px
- 登录页右上角、工作台侧边栏/顶栏、管理后台顶栏三处复用

### 4. 翻译引擎（弃 TreeWalker 全文扫描）
- **MutationObserver 增量翻译**：只处理带 `data-i18n` / `data-i18n-placeholder` 的元素
- **有界 React 登录卡翻译**：仅 `#auth-react-root` 区域、双向词典（zh↔en），替换纯文本节点与 placeholder
- 移除 `setInterval` 轮询与全文档 TreeWalker

### 5. 平滑过渡
- 切主题时加 `.theme-transition`，对 color/background/border/shadow 做 240ms 过渡
- 遵循 `prefers-reduced-motion`

## 三、文件变更

| 文件 | 动作 |
|------|------|
| `app/static/ui-prefs.js` | **新增**（单一系统，30KB） |
| `app/static/ui-prefs.css` | **新增**（语义 token + 映射层 + 控件样式，30KB） |
| `app/static/index.html` | 改：CSS/JS 引用 → ui-prefs |
| `app/static/admin.html` | 改：CSS/JS 引用 → ui-prefs |
| `app/static/global-theme-i18n.js` | **弃用**（不再引用，保留备份） |
| `app/static/ui-preferences.js` | **弃用**（不再引用，保留备份） |
| `app/static/global-theme-i18n.css` | **并入** ui-prefs.css（React 深色映射层保留） |
| `app/static/_prefs_backup_20260801/` | 旧文件备份（已 .gitignore） |

## 四、设计取舍说明

### i18n 词条内嵌（未拆分 i18n/zh.js + en.js）
原方案拟拆分为独立词条文件，落地时**改为内嵌**，理由：
1. `window.zhidaI18n(key)` 是**同步调用**（app.js 渲染时同步取词），拆文件引入 `<script>` 加载顺序竞态
2. 单页应用减少网络请求
3. 词条量 ~150 键，内嵌文件 30KB 可接受
> 若未来词条量显著增长，可再拆（需将 `zhidaI18n` 改异步或提前加载）

### CSS 映射层保留（未完全 token 化）
`auth-login.css`（React 登录页）硬编码浅色系，全量 token 化需改 React 源码并重新 Vite 构建。本次**保留** `:root[data-theme]` 逐条映射作为**兼容层**（否则深色模式下 React 登录页错乱），同时新增语义 token 供新代码使用。完整 token 化列为后续优化项。

### React 登录卡翻译为「有界双向」而非「React 原生 i18n」
`GlassLoginCard.jsx` 等硬编码中文，无 i18n 接口。本次用**有界 TreeWalker**（仅 `#auth-react-root`）实现双向翻译，不侵入 React。彻底方案是 React 组件引入 i18n 后重新构建，列为后续优化项。

## 五、验证记录（已实测）

| 场景 | 结果 |
|------|------|
| 本地登录页控件渲染（5 按钮） | ✅ |
| 深色/浅色切换 + 持久化 | ✅ |
| 语言 zh→en 全卡翻译（tabs/输入/按钮/标题） | ✅ |
| 语言 en→zh 反向恢复 | ✅ |
| auto 跟随 OS 实时切换（CDP 模拟） | ✅ |
| 管理后台控件 + 翻译 | ✅ |
| 线上 `https://zhidajob.top/` 交互 | ✅ |
| 云端 md5 校验（4 文件全 MATCH） | ✅ |

## 六、回滚方案
若需回退：还原 `index.html` / `admin.html` 引用为旧文件（`ui-preferences.js` + `global-theme-i18n.js`），旧文件仍在 `app/static/` 与 `_prefs_backup_20260801/`。
