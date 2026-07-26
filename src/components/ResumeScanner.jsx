import { motion, useReducedMotion } from "framer-motion";
import CountUp from "react-countup";
import { Check, FileText, Sparkles } from "lucide-react";

const skills = ["产品管理", "AI应用", "数据分析"];

function MatchGauge() {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="ai-match-gauge" aria-label="匹配度 96%，高度匹配">
      <svg viewBox="0 0 112 112" role="img" aria-hidden="true">
        <defs><linearGradient id="ai-match-gradient" x1="0" x2="1"><stop stopColor="#2563eb" /><stop offset="1" stopColor="#8b5cf6" /></linearGradient></defs>
        <circle className="ai-gauge-track" cx="56" cy="56" r={radius} />
        <motion.circle className="ai-gauge-progress" cx="56" cy="56" r={radius} stroke="url(#ai-match-gradient)" strokeDasharray={circumference} initial={{ strokeDashoffset: circumference }} animate={{ strokeDashoffset: circumference * 0.04 }} transition={{ duration: 1.55, delay: 0.55, ease: "easeOut" }} />
      </svg>
      <div><strong><CountUp end={96} duration={1.55} delay={0.45} />%</strong><span>高度匹配</span></div>
    </div>
  );
}

export default function ResumeScanner() {
  const reducedMotion = useReducedMotion();
  return (
    <div className="ai-scanner-wrap">
      <motion.article
        className="ai-resume-card"
        initial={reducedMotion ? false : { opacity: 0, y: 24, rotate: -2 }}
        animate={reducedMotion ? { opacity: 1 } : { opacity: 1, y: [0, -9, 0], rotate: [-1.1, 0.3, -1.1] }}
        transition={reducedMotion ? { duration: 0.35 } : { opacity: { duration: 0.6 }, y: { duration: 5.8, repeat: Infinity, ease: "easeInOut" }, rotate: { duration: 5.8, repeat: Infinity, ease: "easeInOut" } }}
      >
        <div className="ai-resume-reflection" />
        <header className="ai-resume-header"><span><FileText size={17} fill="currentColor" /> PDF</span><strong>我的简历.pdf</strong><i /></header>
        <div className="ai-resume-person"><div className="ai-resume-avatar" /><div><b /><b /><b /></div></div>
        <div className="ai-resume-lines"><i /><i /><i /><i /><i /></div>
        <div className="ai-scan-line" />
        <div className="ai-skill-list">
          {skills.map((skill, index) => <motion.span key={skill} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 + index * 0.16 }}><Check size={11} />{skill}</motion.span>)}
        </div>
        <MatchGauge />
      </motion.article>
      <motion.div className="ai-scanner-spark" animate={reducedMotion ? {} : { scale: [0.8, 1.15, 0.8], opacity: [0.4, 1, 0.4] }} transition={{ duration: 2.2, repeat: Infinity }}><Sparkles size={18} /></motion.div>
      <div className="ai-scanner-floor" />
    </div>
  );
}
