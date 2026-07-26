import Lottie from "lottie-react";
import pulseAnimation from "./aiPulse.json";

export default function LottiePulse({ reducedMotion }) {
  return <Lottie animationData={pulseAnimation} loop={!reducedMotion} autoplay={!reducedMotion} aria-hidden="true" />;
}
