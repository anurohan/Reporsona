"use client";

import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

interface PersonaImageProps {
  name: string;
  /** External portrait URL (e.g. Wikimedia). May be "" / undefined. */
  portraitUrl?: string;
  /** Alias for `portraitUrl`. */
  src?: string;
  size?: number;
  className?: string;
  glow?: boolean;
}

// Deterministic hue from the name so the same persona always gets the same orb.
function hueFromName(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) % 360;
  }
  return h;
}

/**
 * Blur-to-sharp portrait reveal. When no portrait URL is present (or the image
 * fails to load), renders an abstract animated "identity orb" seeded from the
 * persona's name. Respects prefers-reduced-motion (shows a static image/orb).
 */
export default function PersonaImage({
  name,
  portraitUrl,
  src,
  size = 128,
  className = "",
  glow = true,
}: PersonaImageProps) {
  const url = (portraitUrl || src || "").trim();
  const [loaded, setLoaded] = useState(false);
  const [errored, setErrored] = useState(false);
  const reduceMotion = useReducedMotion();

  const hue = useMemo(() => hueFromName(name || "Persona"), [name]);
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";
  const showOrb = !url || errored;

  const orbGradient = `radial-gradient(circle at 30% 25%, hsl(${hue} 90% 68%), hsl(${
    (hue + 40) % 360
  } 80% 45%) 45%, hsl(${(hue + 300) % 360} 70% 22%) 100%)`;

  // When motion is reduced, treat the image as already-revealed so we never
  // start blurred/scaled and never animate.
  const revealed = loaded || reduceMotion;

  return (
    <div
      className={`relative shrink-0 ${className}`}
      style={{ width: size, height: size }}
    >
      {glow && (
        <div
          aria-hidden
          className="absolute inset-0 rounded-full blur-2xl"
          style={{
            background: `radial-gradient(circle, hsl(${hue} 90% 60% / 0.45), transparent 70%)`,
          }}
        />
      )}

      {showOrb ? (
        <motion.div
          initial={reduceMotion ? false : { scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.7, ease: "easeOut" }}
          role="img"
          aria-label={`${name} identity orb`}
          className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-full border border-white/15 shadow-glow"
          style={{ background: orbGradient }}
        >
          <div
            aria-hidden
            className="absolute inset-0 animate-floaty opacity-60 mix-blend-screen"
            style={{
              background: `conic-gradient(from 0deg, transparent, hsl(${
                (hue + 180) % 360
              } 90% 70% / 0.5), transparent 60%)`,
            }}
          />
          <span
            className="relative font-display text-white/90"
            style={{ fontSize: size * 0.4 }}
          >
            {initial}
          </span>
        </motion.div>
      ) : (
        <>
          {!revealed && (
            <div className="absolute inset-0 rounded-full shimmer" aria-hidden />
          )}
          {/* External (Wikimedia) URL — must be a plain <img>, not next/image. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt={`Portrait of ${name}`}
            referrerPolicy="no-referrer"
            loading="lazy"
            onLoad={() => setLoaded(true)}
            onError={() => setErrored(true)}
            className={`relative h-full w-full rounded-full border border-white/15 object-cover shadow-glow ${
              reduceMotion ? "" : "transition-all duration-700"
            } ${
              revealed
                ? "scale-100 blur-0 opacity-100"
                : "scale-105 blur-lg opacity-0"
            }`}
          />
        </>
      )}
    </div>
  );
}
