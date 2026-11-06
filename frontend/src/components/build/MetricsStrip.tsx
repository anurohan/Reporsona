"use client";

import { motion } from "framer-motion";

interface MetricsStripProps {
  stats: Record<string, any>;
  /** Whether evidence validation has completed (drives the evidence cell). */
  evidenceComplete?: boolean;
}

// Real job-state fields, in narrative order. `evidence` is special-cased.
const FIELDS: { key: string; label: string }[] = [
  { key: "sources", label: "Sources" },
  { key: "documents", label: "Documents" },
  { key: "chunks", label: "Chunks" },
  { key: "embeddings", label: "Embeddings" },
  { key: "topics", label: "Topics" },
];

function displayValue(stats: Record<string, any>, key: string): string {
  const v = stats?.[key];
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Math.round(v).toLocaleString();
  return String(v);
}

/**
 * Compact live-metrics strip. Values come straight from the real job `stats`
 * object; missing fields render as "—" (never a fabricated number). The final
 * cell reflects evidence-validation status rather than inventing a count.
 */
export default function MetricsStrip({
  stats,
  evidenceComplete = false,
}: MetricsStripProps) {
  return (
    <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-white/10 bg-white/[0.02] sm:grid-cols-6">
      {FIELDS.map((f) => {
        const value = displayValue(stats, f.key);
        return (
          <div key={f.key} className="flex flex-col gap-0.5 bg-void-900/40 px-3 py-2.5">
            <dt className="text-[10px] uppercase tracking-wider text-slate-500">
              {f.label}
            </dt>
            <motion.dd
              key={value}
              initial={{ opacity: 0.4, y: 2 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="font-display text-base tabular-nums text-white"
            >
              {value}
            </motion.dd>
          </div>
        );
      })}
      <div className="flex flex-col gap-0.5 bg-void-900/40 px-3 py-2.5">
        <dt className="text-[10px] uppercase tracking-wider text-slate-500">
          Evidence
        </dt>
        <dd
          className={`text-sm font-medium ${
            evidenceComplete ? "text-emerald-300" : "text-slate-400"
          }`}
        >
          {evidenceComplete ? "Verified" : "Pending"}
        </dd>
      </div>
    </dl>
  );
}
