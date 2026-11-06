"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ChevronDown,
  RotateCcw,
  Stethoscope,
  TriangleAlert,
} from "lucide-react";

interface FailedPanelProps {
  jobId: string;
  error: string;
  stats: Record<string, any>;
  onRetry: () => void;
  onBack: () => void;
}

const PARTIAL_FIELDS: { key: string; label: string }[] = [
  { key: "sources", label: "sources" },
  { key: "documents", label: "documents" },
  { key: "chunks", label: "chunks" },
];

function fmt(v: any): string {
  if (v === null || v === undefined) return "0";
  if (typeof v === "number") return Math.round(v).toLocaleString();
  return String(v);
}

/**
 * Terminal failure state. Never shows success when the job actually failed.
 * Surfaces the real backend error, how far the pipeline got, and recovery
 * actions (retry / diagnostics / back).
 */
export default function FailedPanel({
  jobId,
  error,
  stats,
  onRetry,
  onBack,
}: FailedPanelProps) {
  const [showDiag, setShowDiag] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="glass-panel border-accent-rose/30 p-6 text-center sm:p-8"
      role="alert"
    >
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-accent-rose/30 bg-accent-rose/10">
        <TriangleAlert className="h-6 w-6 text-accent-rose" aria-hidden />
      </div>

      <p className="text-[11px] uppercase tracking-[0.28em] text-accent-rose">
        Reconstruction paused
      </p>
      <h1 className="mt-1.5 font-display text-2xl font-semibold text-white">
        The build didn&apos;t finish
      </h1>

      <div className="mx-auto mt-4 max-w-md rounded-lg border border-accent-rose/20 bg-accent-rose/5 px-4 py-3 text-left">
        <p className="text-[11px] uppercase tracking-wider text-rose-300/80">Reason</p>
        <p className="mt-0.5 text-sm text-rose-100">
          {error || "The reconstruction job failed unexpectedly."}
        </p>
      </div>

      {/* how far it got */}
      <div className="mx-auto mt-4 flex max-w-md items-center justify-center gap-4 text-sm">
        {PARTIAL_FIELDS.map((f) => (
          <div key={f.key} className="flex items-baseline gap-1.5">
            <span className="font-display tabular-nums text-white">{fmt(stats?.[f.key])}</span>
            <span className="text-xs text-slate-500">{f.label}</span>
          </div>
        ))}
      </div>

      {/* actions */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
        <button
          type="button"
          onClick={onRetry}
          className="focusable inline-flex items-center gap-2 rounded-xl border border-indigoGlow-400/50 bg-indigoGlow-600/70 px-5 py-2.5 text-sm font-semibold text-white shadow-glow hover:bg-indigoGlow-500"
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          Retry
        </button>
        <button
          type="button"
          onClick={() => setShowDiag((v) => !v)}
          aria-expanded={showDiag}
          className="focusable inline-flex items-center gap-2 rounded-xl border border-white/12 bg-white/[0.04] px-5 py-2.5 text-sm text-white hover:bg-white/[0.08]"
        >
          <Stethoscope className="h-4 w-4" aria-hidden />
          View diagnostics
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform ${showDiag ? "rotate-180" : ""}`}
            aria-hidden
          />
        </button>
        <button
          type="button"
          onClick={onBack}
          className="focusable inline-flex items-center gap-2 rounded-xl border border-white/12 bg-white/[0.04] px-5 py-2.5 text-sm text-white hover:bg-white/[0.08]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Back
        </button>
      </div>

      {showDiag && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mx-auto mt-4 max-w-md overflow-hidden rounded-lg border border-white/10 bg-void-950/60 p-3 text-left"
        >
          <dl className="space-y-1 text-xs">
            <div className="flex gap-2">
              <dt className="w-24 shrink-0 text-slate-500">Job ID</dt>
              <dd className="break-all font-mono text-slate-300">{jobId || "—"}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-24 shrink-0 text-slate-500">Error</dt>
              <dd className="break-words font-mono text-rose-200">{error || "—"}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-24 shrink-0 text-slate-500">Progress</dt>
              <dd className="font-mono text-slate-300">
                {Object.keys(stats || {}).length
                  ? Object.entries(stats)
                      .filter(([, v]) => typeof v === "number")
                      .map(([k, v]) => `${k}=${v}`)
                      .join("  ")
                  : "no metrics recorded"}
              </dd>
            </div>
          </dl>
        </motion.div>
      )}
    </motion.div>
  );
}
