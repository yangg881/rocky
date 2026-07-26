import { useEffect, useMemo, useState } from "react";

const desktopOptions = {
  fullScreen: { enable: false },
  detectRetina: true,
  fpsLimit: 60,
  particles: {
    color: { value: ["#2563eb", "#7c3aed", "#6dd8ff"] },
    links: { enable: false },
    move: { enable: true, speed: 0.32, direction: "none", outModes: { default: "out" } },
    number: { value: 19, density: { enable: true, area: 1100 } },
    opacity: { value: { min: 0.12, max: 0.42 } },
    size: { value: { min: 1, max: 3 } }
  },
  interactivity: { events: { onHover: { enable: false }, onClick: { enable: false } } }
};

const mobileOptions = {
  ...desktopOptions,
  particles: { ...desktopOptions.particles, number: { value: 7, density: { enable: true, area: 900 } }, move: { ...desktopOptions.particles.move, speed: 0.18 } }
};

export default function FloatingParticles() {
  const [Particles, setParticles] = useState(null);
  const [mobile, setMobile] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 720px), (prefers-reduced-motion: reduce)");
    const update = () => setMobile(media.matches);
    update();
    media.addEventListener("change", update);
    let cancelled = false;
    const boot = async () => {
      const [{ default: ParticleCanvas, initParticlesEngine }, { loadSlim }] = await Promise.all([
        import("@tsparticles/react"),
        import("@tsparticles/slim")
      ]);
      await initParticlesEngine(async (engine) => { await loadSlim(engine); });
      if (!cancelled) setParticles(() => ParticleCanvas);
    };
    const schedule = window.requestIdleCallback ? window.requestIdleCallback(boot, { timeout: 1800 }) : window.setTimeout(boot, 420);
    return () => {
      cancelled = true;
      media.removeEventListener("change", update);
      if (window.cancelIdleCallback) window.cancelIdleCallback(schedule); else window.clearTimeout(schedule);
    };
  }, []);

  const options = useMemo(() => mobile ? mobileOptions : desktopOptions, [mobile]);
  if (!Particles) return null;
  return <Particles id="zhiday-ai-particles" className="ai-particles" options={options} aria-hidden="true" />;
}
