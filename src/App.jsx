import { motion, useReducedMotion } from "framer-motion";
import { Sparkles } from "lucide-react";
import AIBackground from "./components/AIBackground";
import AnimatedStats from "./components/AnimatedStats";
import ResumeScanner from "./components/ResumeScanner";
import AIStatus from "./components/AIStatus";
import GlassLoginCard from "./components/GlassLoginCard";

export default function App() {
  const reducedMotion = useReducedMotion();
  return (
    <div className="ai-login-shell">
      <AIBackground />
      <main className="ai-login-main">
        <section className="ai-hero" aria-labelledby="ai-login-title">
          <div className="ai-hero-copy">
            <motion.div className="ai-brand" initial={reducedMotion ? false : { opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.42 }}><span className="ai-brand-mark">职</span><span><strong>职达简历</strong><small>AI 职业操作系统</small></span></motion.div>
            <motion.div className="ai-system-signal" initial={reducedMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.14, duration: 0.45 }}><span /><Sparkles size={14} />AI 正在连接职业机会</motion.div>
            <motion.h1 id="ai-login-title" initial={reducedMotion ? false : { opacity: 0, y: 26 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.64, ease: [0.16, 1, 0.3, 1] }}>让每一份经历，<br />匹配<span className="ai-gradient-text">下一份机会。</span></motion.h1>
            <motion.p className="ai-hero-lead" initial={reducedMotion ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.33, duration: 0.54 }}>AI 深度理解你的经历与优势，实时洞察岗位市场，把简历优化、机会匹配和投递推进放进同一个职业系统。</motion.p>
            <AnimatedStats />
          </div>
          <div className="ai-hero-system">
            <ResumeScanner />
            <AIStatus />
          </div>
        </section>
        <GlassLoginCard />
      </main>
    </div>
  );
}
