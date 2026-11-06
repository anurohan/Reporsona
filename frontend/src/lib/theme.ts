// Deterministic per-persona theming. Framework-agnostic: no DOM access, pure
// functions that map a seed string to a stable hue and a set of CSS custom
// properties the UI can consume via `var(--p-accent)` etc.

import type { CSSProperties } from "react";

/**
 * Derive a stable hue (0-359) from an arbitrary seed string using a simple
 * char-code rolling hash. The same seed always yields the same hue, so a
 * persona keeps its "colour identity" across pages and reloads.
 */
export function hueFromSeed(seed: string): number {
  const s = seed || "Persona";
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) % 360;
  }
  // Guard against negative/NaN just in case.
  return ((h % 360) + 360) % 360;
}

/**
 * CSS custom properties describing a persona's accent palette. Spread onto a
 * container's `style` so descendants can reference the vars.
 */
export function personaAccent(seed: string): CSSProperties {
  const h = hueFromSeed(seed);
  return {
    ["--p-hue" as any]: String(h),
    ["--p-accent" as any]: `hsl(${h} 80% 62%)`,
    ["--p-accent-soft" as any]: `hsl(${h} 80% 62% / 0.16)`,
    ["--p-accent-strong" as any]: `hsl(${h} 85% 70%)`,
    ["--p-glow" as any]: `hsl(${h} 90% 60% / 0.35)`,
  } as CSSProperties;
}

/** Text coloured with the persona accent. */
export function accentTextStyle(): CSSProperties {
  return { color: "var(--p-accent)" };
}

/** Border coloured with the (soft) persona accent. */
export function accentBorderStyle(): CSSProperties {
  return { borderColor: "var(--p-accent-soft)" };
}

/** A subtle ring/outline in the persona accent (e.g. avatars). */
export function accentRingStyle(): CSSProperties {
  return { boxShadow: "0 0 0 1px var(--p-accent-soft)" };
}
