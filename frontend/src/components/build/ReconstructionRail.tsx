"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { PhaseState } from "@/lib/buildPhases";

interface ReconstructionRailProps {
  phase: PhaseState;
}

/**
 * Compact horizontal reconstruction rail. Each phase renders as a labelled
 * node: completed = check, active = animated pulse, future = muted. On
 * completion every node becomes checked. Purely presentational — driven by the
 * real phase state derived from job stages.
 */
export default function ReconstructionRail({ phase }: ReconstructionRailProps) {
  return (
    <div className="w-full">
      <div className="mb-3 flex items-baseline justify-between">
        <span className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
          Reconstruction
        </span>
        <span
          className="text-[11px] font-medium tabular-nums text-slate-300"
          aria-live="polite"
        >
          {phase.stepLabel}
        </span>
      </div>

      <ol
        className="flex items-center gap-1.5"
        aria-label="Reconstruction phases"
      >
        {phase.phases.map((p, i) => {
          const isCompleted = p.status === "completed";
          const isActive = p.status === "active";
          return (
            <li key={p.id} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              {/* connector + node */}
              <div className="relative flex w-full items-center">
                {i > 0 && (
                  <span
                    aria-hidden
                    className={`h-px flex-1 transition-colors duration-500 ${
                      isCompleted || isActive ? "bg-indigoGlow-400/50" : "bg-white/10"
                    }`}
                  />
                )}
                <span
                  className={`relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold transition-colors duration-500 ${
                    isCompleted
                      ? "border-accent-cyan/60 bg-accent-cyan/15 text-accent-cyan"
                      : isActive
                      ? "border-indigoGlow-400/70 bg-indigoGlow-500/20 text-white"
                      : "border-white/10 bg-white/[0.03] text-slate-500"
                  }`}
                  aria-current={isActive ? "step" : undefined}
                >
                  {isActive && (
                    <motion.span
                      aria-hidden
                      className="absolute inset-0 rounded-full ring-2 ring-indigoGlow-400/40"
                      animate={{ opacity: [0.2, 0.7, 0.2], scale: [1, 1.25, 1] }}
                      transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                    />
                  )}
                  {isCompleted ? (
                    <Check className="h-3.5 w-3.5" aria-hidden />
                  ) : (
                    <span className="relative">{i + 1}</span>
                  )}
                </span>
                {i < phase.phases.length - 1 && (
                  <span
                    aria-hidden
                    className={`h-px flex-1 transition-colors duration-500 ${
                      isCompleted ? "bg-indigoGlow-400/50" : "bg-white/10"
                    }`}
                  />
                )}
              </div>
              <span
                className={`w-full truncate text-center text-[10px] tracking-wide transition-colors ${
                  isActive
                    ? "text-white"
                    : isCompleted
                    ? "text-slate-400"
                    : "text-slate-600"
                }`}
                title={p.label}
              >
                {p.short}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
