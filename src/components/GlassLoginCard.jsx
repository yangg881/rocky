import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Smartphone, UserRound } from "lucide-react";
import { apiRequest } from "../lib/api";

const initialValues = {
  username: "", password: "", phone: "", code: "", confirmPassword: "", resetPassword: "", resetConfirmPassword: ""
};

const modeCopy = {
  login: { title: "欢迎回来", description: "继续让 AI 为你的职业机会持续工作" },
  register: { title: "创建你的职业入口", description: "完成手机号验证后，即可建立专属求职系统" },
  reset: { title: "重设登录密码", description: "验证绑定手机号后，安全设置新密码" }
};

function PasswordField({ id, value, onChange, placeholder, autoComplete = "current-password" }) {
  const [visible, setVisible] = useState(false);
  return <div className="ai-input-wrap"><LockKeyhole size={17} aria-hidden="true" /><input id={id} value={value} onChange={(event) => onChange(event.target.value)} type={visible ? "text" : "password"} autoComplete={autoComplete} placeholder={placeholder} required minLength={8} /><button type="button" className="ai-eye" onClick={() => setVisible((state) => !state)} aria-label={visible ? "隐藏密码" : "显示密码"}>{visible ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>;
}

function Field({ icon: Icon, id, value, onChange, placeholder, type = "text", inputMode, autoComplete, required = true }) {
  return <div className="ai-input-wrap"><Icon size={17} aria-hidden="true" /><input id={id} value={value} onChange={(event) => onChange(event.target.value)} type={type} inputMode={inputMode} autoComplete={autoComplete} placeholder={placeholder} required={required} /></div>;
}

export default function GlassLoginCard() {
  const [mode, setMode] = useState("login");
  const [loginMethod, setLoginMethod] = useState("password");
  const [values, setValues] = useState(initialValues);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("error");
  const [pending, setPending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [release, setRelease] = useState(null);
  const reducedMotion = useReducedMotion();
  const copy = modeCopy[mode];

  useEffect(() => {
    apiRequest("/app/version?platform=android&version_code=0").then(setRelease).catch(() => setRelease(null));
  }, []);

  useEffect(() => {
    if (!cooldown) return undefined;
    const timer = window.setInterval(() => setCooldown((seconds) => Math.max(0, seconds - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  const update = (key) => (value) => setValues((current) => ({ ...current, [key]: value }));
  const phoneScene = useMemo(() => mode === "register" ? "register" : mode === "reset" ? "reset_password" : "login", [mode]);
  // The /app/version download_url is HTTP+IP (best for the Android in-app updater,
  // which carriers RST over HTTPS). But a browser on an HTTPS page blocks an HTTP
  // download as mixed content, so on HTTPS pick a same-protocol URL instead.
  const appDownloadUrl = useMemo(() => {
    const onHttps = typeof window !== "undefined" && window.location.protocol === "https:";
    const urls = release?.download_urls || [];
    if (onHttps) {
      const https = urls.find((u) => typeof u === "string" && u.startsWith("https://"));
      if (https) return https;
    }
    return release?.download_url || urls[0] || "download/android-full.apk";
  }, [release]);
  const showMessage = (text, type = "error") => { setMessage(text); setMessageType(type); };
  const changeMode = (next) => { setMode(next); setMessage(""); setLoginMethod("password"); };

  const sendCode = async () => {
    const phone = values.phone.trim();
    if (!/^1\d{10}$/.test(phone)) { showMessage("请先输入正确的 11 位手机号"); return; }
    setPending(true);
    try {
      await apiRequest("/auth/sms-code", { method: "POST", body: JSON.stringify({ phone, scene: phoneScene }) });
      setCooldown(60); showMessage("验证码已发送，请注意查收", "success");
    } catch (error) { showMessage(error.message); } finally { setPending(false); }
  };

  const finishAuth = (data) => {
    if (data?.user?.role === "admin") { showMessage("管理员请从后台入口登录"); return; }
    showMessage("验证成功，正在进入你的职业工作台…", "success");
    window.setTimeout(() => window.location.reload(), 360);
  };

  const submit = async (event) => {
    event.preventDefault();
    setMessage(""); setPending(true);
    try {
      if (mode === "login") {
        const payload = loginMethod === "password"
          ? { username: values.username.trim(), password: values.password }
          : { phone: values.phone.trim(), code: values.code.trim() };
        const endpoint = loginMethod === "password" ? "/auth/login" : "/auth/sms-login";
        finishAuth(await apiRequest(endpoint, { method: "POST", body: JSON.stringify(payload) }));
      } else if (mode === "register") {
        if (values.password !== values.confirmPassword) throw new Error("两次输入的密码不一致");
        finishAuth(await apiRequest("/auth/register", { method: "POST", body: JSON.stringify({ username: values.username.trim(), phone: values.phone.trim(), code: values.code.trim(), password: values.password, confirm_password: values.confirmPassword }) }));
      } else {
        if (values.resetPassword !== values.resetConfirmPassword) throw new Error("两次输入的新密码不一致");
        await apiRequest("/auth/reset-password", { method: "POST", body: JSON.stringify({ phone: values.phone.trim(), code: values.code.trim(), new_password: values.resetPassword }) });
        showMessage("密码已更新，请使用新密码登录", "success");
        window.setTimeout(() => changeMode("login"), 720);
      }
    } catch (error) { showMessage(error.message); } finally { setPending(false); }
  };

  return (
    <motion.section className="ai-glass-login" initial={reducedMotion ? false : { opacity: 0, x: 28, scale: 0.98 }} animate={{ opacity: 1, x: 0, scale: 1 }} transition={{ duration: 0.62, delay: 0.16, ease: [0.16, 1, 0.3, 1] }} aria-label="账号登录与注册">
      <div className="ai-moving-border" aria-hidden="true" />
      <div className="ai-glass-login-inner">
        {mode !== "reset" && <div className="ai-auth-tabs" role="tablist" aria-label="登录或注册"><button className={mode === "login" ? "active" : ""} onClick={() => changeMode("login")} type="button" role="tab" aria-selected={mode === "login"}>登录</button><button className={mode === "register" ? "active" : ""} onClick={() => changeMode("register")} type="button" role="tab" aria-selected={mode === "register"}>注册</button></div>}
        <AnimatePresence mode="wait"><motion.form key={`${mode}-${loginMethod}`} className="ai-auth-form" onSubmit={submit} initial={reducedMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.22 }}>
          <div className="ai-form-heading"><h2>{copy.title}</h2><p>{copy.description}</p></div>
          {mode === "login" && <div className="ai-login-methods" role="tablist"><button type="button" className={loginMethod === "password" ? "active" : ""} onClick={() => setLoginMethod("password")}>账号密码</button><button type="button" className={loginMethod === "sms" ? "active" : ""} onClick={() => setLoginMethod("sms")}>手机验证码</button></div>}
          {mode === "login" && loginMethod === "password" && <><label htmlFor="ai-login-username">用户名</label><Field icon={UserRound} id="ai-login-username" value={values.username} onChange={update("username")} placeholder="请输入用户名" autoComplete="username" /><label htmlFor="ai-login-password">密码</label><PasswordField id="ai-login-password" value={values.password} onChange={update("password")} placeholder="请输入密码" /></>}
          {(mode === "register" || mode === "login" && loginMethod === "sms" || mode === "reset") && <><label htmlFor="ai-auth-phone">手机号</label><div className="ai-code-row"><Field icon={Smartphone} id="ai-auth-phone" value={values.phone} onChange={update("phone")} placeholder="请输入手机号" inputMode="tel" autoComplete="tel" /><button type="button" onClick={sendCode} disabled={pending || cooldown > 0}>{cooldown ? `${cooldown}s 后重发` : "发送验证码"}</button></div><label htmlFor="ai-auth-code">短信验证码</label><Field icon={Mail} id="ai-auth-code" value={values.code} onChange={update("code")} placeholder="请输入验证码" inputMode="numeric" autoComplete="one-time-code" /></>}
          {mode === "register" && <><label htmlFor="ai-register-username">用户名</label><Field icon={UserRound} id="ai-register-username" value={values.username} onChange={update("username")} placeholder="3 至 40 个字符" autoComplete="username" /><label htmlFor="ai-register-password">设置密码</label><PasswordField id="ai-register-password" value={values.password} onChange={update("password")} placeholder="至少 8 位密码" autoComplete="new-password" /><label htmlFor="ai-register-confirm">确认密码</label><PasswordField id="ai-register-confirm" value={values.confirmPassword} onChange={update("confirmPassword")} placeholder="再次输入密码" autoComplete="new-password" /></>}
          {mode === "reset" && <><label htmlFor="ai-reset-password">新密码</label><PasswordField id="ai-reset-password" value={values.resetPassword} onChange={update("resetPassword")} placeholder="至少 8 位密码" autoComplete="new-password" /><label htmlFor="ai-reset-confirm">确认新密码</label><PasswordField id="ai-reset-confirm" value={values.resetConfirmPassword} onChange={update("resetConfirmPassword")} placeholder="再次输入新密码" autoComplete="new-password" /></>}
          {mode === "login" && loginMethod === "password" && <div className="ai-remember-row"><label className="ai-checkbox"><input type="checkbox" /> <span>记住我</span></label><button type="button" onClick={() => changeMode("reset")}>忘记密码？</button></div>}
          <motion.button className="ai-submit" type="submit" disabled={pending} whileHover={reducedMotion ? undefined : { y: -3 }} whileTap={{ scale: 0.97 }}>{pending ? "正在验证…" : mode === "register" ? "创建职业入口" : mode === "reset" ? "保存新密码" : "进入工作台"}<ArrowRight size={18} /></motion.button>
          {mode === "login" && <p className="ai-switch-copy">还没有账号？<button type="button" onClick={() => changeMode("register")}>立即注册</button></p>}
          {mode === "reset" && <p className="ai-switch-copy"><button type="button" onClick={() => changeMode("login")}>返回登录</button></p>}
          <p className={`ai-form-message ${messageType === "success" ? "is-success" : ""}`} aria-live="polite">{message}</p>
        </motion.form></AnimatePresence>
        <a className="ai-app-download" href={appDownloadUrl} download><span><Smartphone size={18} /><b>Android App 完整安装包</b><small>{release?.latest_version_name ? `v${release.latest_version_name}` : "最新版本"}</small></span><em>下载</em></a>
      </div>
    </motion.section>
  );
}
