function apiBase() {
  const pathname = window.location.pathname.replace(/\/$/, "");
  return `${pathname}/api`;
}

function messageFromPayload(payload, fallback) {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = payload.detail || payload.message || payload.error;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || item.message || String(item)).join("；");
  if (typeof detail === "object") return detail.message || detail.msg || fallback;
  return detail || fallback;
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${apiBase()}${path}`, { ...options, headers, credentials: "same-origin" });
  const raw = response.status === 204 ? "" : await response.text();
  let payload = null;
  try { payload = raw ? JSON.parse(raw) : null; } catch { /* Keep a useful fallback below. */ }
  if (!response.ok) {
    const generic = response.status === 429 ? "操作过于频繁，请稍后再试" : `请求失败（${response.status}）`;
    throw new Error(messageFromPayload(payload, generic));
  }
  return payload;
}
