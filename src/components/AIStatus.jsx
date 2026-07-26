import { lazy, Suspense, useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Bot, CheckCircle2 } from "lucide-react";

const LottiePulse = lazy(() => import("./LottiePulse"));

const phases = ["正在分析岗位市场...", "正在提取核心技能...", "正在匹配机会画像...", "正在生成求职建议..."];

export default function AIStatus() {
  const [phase, setPhase] = useState(0);
  const reducedMotion = useReducedMotion();
  useEffect(() => {
    if (reducedMotion) return undefined;
    const timer = window.setInterval(() => setPhase((current) => (current + 1) % phases.length), 2400);
    return () => window.clearInterval(timer);
  }, [reducedMotion]);
  return (
    <motion.aside className="ai-status" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.72, duration: 0.55 }}>
      <div className="ai-status-orb">
        <Suspense fallback={null}><LottiePulse reducedMotion={reducedMotion} /></Suspense>
        <Bot size={20} strokeWidth={1.8} aria-hidden="true" />
      </div>
      <div className="ai-status-copy">
        <strong>AI职业分析助手</strong>
        <motion.p key={phase} initial={reducedMotion ? false : { opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>{phases[phase]}</motion.p>
      </div>
      <CheckCircle2 className="ai-status-check" size={16} aria-label="系统在线" />
    </motion.aside>
  );
}
