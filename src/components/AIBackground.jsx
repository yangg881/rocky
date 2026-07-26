import { lazy, Suspense } from "react";
import { motion, useReducedMotion } from "framer-motion";

const FloatingParticles = lazy(() => import("./FloatingParticles"));

export default function AIBackground() {
  const reducedMotion = useReducedMotion();
  const orbit = reducedMotion ? {} : { x: [0, 28, -10, 0], y: [0, -18, 12, 0], scale: [1, 1.08, 0.98, 1] };
  return (
    <div className="ai-background" aria-hidden="true">
      <motion.div className="ai-aurora ai-aurora--one" animate={orbit} transition={{ duration: 13, repeat: Infinity, ease: "easeInOut" }} />
      <motion.div className="ai-aurora ai-aurora--two" animate={reducedMotion ? {} : { x: [0, -36, 15, 0], y: [0, 22, -12, 0] }} transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }} />
      <div className="ai-aurora ai-aurora--three" />
      <div className="ai-spatial-grid" />
      <Suspense fallback={null}><FloatingParticles /></Suspense>
    </div>
  );
}
