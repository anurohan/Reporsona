"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  FileText,
  Globe,
  Layers,
  ShieldCheck,
  Sparkles,
  Tag,
} from "lucide-react";
import type { JobActivityEvent, ActivityKind } from "@/lib/types";

interface ActivityFeedProps {
  events: JobActivityEvent[];
  connected: boolean;
  /** True once the job has reached a terminal state. */
  done?: boolean;
}

const ICONS: Record<ActivityKind, typeof Activity> = {
  stage: Activity,
  source: Globe,
  document: FileText,
  chunk: Layers,
  embedding: Sparkles,
  topic: Tag,
  evidence: ShieldCheck,
  milestone: Sparkles,
};

const TINTS: Record<ActivityKind, string> = {
  stage: "text-slate-300",
  source: "text-accent-cyan",
  document: "text-indigoGlow-400",
  chunk: "text-accent-violet",
  embedding: "text-accent-violet",
  topic: "text-accent-amber",
  evidence: "text-emerald-300",
  milestone: "text-indigoGlow-400",
};

/**
 * Live reconstruction activity feed. Shows only real backend-derived events
 * (newest first). When nothing has happened yet it shows a quiet waiting state
 * rather than fabricating activity.
 */
export default function ActivityFeed({
  events,
  connected,
  done = false,
}: ActivityFeedProps) {
  const ordered = [...events].reverse();

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
          Live activity
        </h2>
        <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              done
                ? "bg-emerald-400"
                : connected
                ? "animate-pulse bg-accent-cyan"
                : "bg-slate-600"
            }`}
            aria-hidden
          />
          {done ? "Finished" : connected ? "Streaming" : "Connecting"}
        </span>
      </div>

      <div
        className="scroll-slim flex-1 space-y-1.5 overflow-y-auto pr-1"
        role="log"
        aria-live="polite"
        aria-label="Reconstruction activity"
      >
        {ordered.length === 0 ? (
          <p className="py-6 text-center text-xs text-slate-500">
            {connected
              ? "Waiting for the pipeline to report activity…"
              : "Connecting to the live pipeline…"}
          </p>
        ) : (
          <AnimatePresence initial={false}>
            {ordered.map((e) => {
              const Icon = ICONS[e.kind] ?? Activity;
              return (
                <motion.div
                  key={e.id}
                  layout
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.28, ease: "easeOut" }}
                  className="flex items-start gap-2.5 rounded-lg border border-white/5 bg-white/[0.02] px-2.5 py-2"
                >
                  <Icon
                    className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${TINTS[e.kind] ?? "text-slate-300"}`}
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-300">
                      {e.label}
                    </div>
                    <div className="truncate text-xs text-slate-500">{e.detail}</div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
