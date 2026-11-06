"use client";

import { useRef, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";

interface StartButtonProps {
  onStart: () => void;
  label?: string;
  disabled?: boolean;
}

/**
 * Premium magnetic CTA. The button leans toward the cursor while hovered,
 * runs a light sweep, glows, and compresses on click.
 */
export function StartButton({
  onStart,
  label = "START REPERSONA",
  disabled = false,
}: StartButtonProps) {
  const ref = useRef<HTMLButtonElement>(null);
  const [hovered, setHovered] = useState(false);

  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, { stiffness: 220, damping: 18, mass: 0.4 });
  const y = useSpring(my, { stiffness: 220, damping: 18, mass: 0.4 });

  const onMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const relX = e.clientX - (rect.left + rect.width / 2);
    const relY = e.clientY - (rect.top + rect.height / 2);
    mx.set(relX * 0.25);
    my.set(relY * 0.35);
  };

  const reset = () => {
    mx.set(0);
    my.set(0);
    setHovered(false);
  };

  return (
    <motion.button
      ref={ref}
      type="button"
      onMouseMove={onMove}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={reset}
      onClick={onStart}
      disabled={disabled}
      whileTap={{ scale: 0.94 }}
      style={{ x, y }}
      aria-label={label}
      className="focusable group relative inline-flex items-center gap-3 overflow-hidden rounded-full border border-indigoGlow-400/40 bg-gradient-to-r from-indigoGlow-600/90 to-accent-violet/90 px-9 py-4 text-sm font-semibold tracking-[0.18em] text-white shadow-glow transition-shadow duration-300 hover:shadow-glow-lg disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span
        aria-hidden
        className={`pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/35 to-transparent transition-transform duration-700 ${
          hovered ? "translate-x-full" : ""
        }`}
      />
      <Sparkles className="h-4 w-4 shrink-0" aria-hidden />
      <span className="relative">{label}</span>
      <ArrowRight
        className="h-4 w-4 shrink-0 transition-transform duration-300 group-hover:translate-x-1"
        aria-hidden
      />
    </motion.button>
  );
}

interface SecondaryButtonProps {
  onClick: () => void;
  label: string;
  className?: string;
}

/** Smaller ghost/secondary variant, e.g. "Explore Demo". */
export function SecondaryButton({
  onClick,
  label,
  className = "",
}: SecondaryButtonProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.96 }}
      aria-label={label}
      className={`focusable inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-6 py-3 text-sm font-medium tracking-wide text-slate-200 backdrop-blur transition-colors hover:border-white/30 hover:bg-white/[0.08] ${className}`}
    >
      {label}
    </motion.button>
  );
}

export default StartButton;
