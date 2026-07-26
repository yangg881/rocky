import { motion, useReducedMotion } from "framer-motion";
import CountUp from "react-countup";
import { BadgeCheck, Clock3, Radar } from "lucide-react";

const stats = [
  { value: 98, suffix: "%", label: "岗位关键词覆盖", icon: BadgeCheck },
  { value: 10, suffix: "分钟", label: "AI简历优化", icon: Clock3 },
  { value: 3500, suffix: "+", label: "实时岗位匹配", icon: Radar }
];

export default function AnimatedStats() {
  const reducedMotion = useReducedMotion();
  return (
    <div className="ai-stats" aria-label="职达简历系统能力">
      {stats.map(({ value, suffix, label, icon: Icon }, index) => (
        <motion.article
          className="ai-stat"
          key={label}
          initial={reducedMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 + index * 0.09, duration: 0.5 }}
          whileHover={reducedMotion ? undefined : { y: -4 }}
        >
          <Icon size={15} strokeWidth={1.8} aria-hidden="true" />
          <strong><CountUp end={value} duration={1.55} separator="," />{suffix}</strong>
          <span>{label}</span>
        </motion.article>
      ))}
    </div>
  );
}
