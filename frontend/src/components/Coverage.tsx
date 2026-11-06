"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, Gauge, Search, Sparkles } from "lucide-react";
import { ApiError, getCoverage } from "@/lib/api";
import type { Coverage as CoverageData } from "@/lib/types";

/** Knowledge coverage estimates (§21): per-facet coverage bars plus suggested
 *  searches that would fill the biggest documented gaps. These are estimates
 *  derived from the ingested corpus, not a claim of completeness. */

function barColor(score: number): string {
  if (score >= 66) return "bg-emerald-400";
  if (score >= 33) return "bg-accent-amber";
  return "bg-accent-rose";
}

export default function Coverage({ personaId }: { personaId: string }) {
  const reduce = useReducedMotion();

  const [data, setData] = useState<CoverageData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setData(null);
    getCoverage(personaId)
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not estimate knowledge coverage."
        )
      );
  };

  useEffect(() => {
    if (personaId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  return (
    <section className="glass-panel p-5" aria-label="Knowledge coverage estimates">
      <h2 className="mb-1 flex items-center gap-2 font-display text-sm uppercase tracking-wider text-slate-300">
        <Gauge className="h-4 w-4 text-accent-cyan" aria-hidden />
        Knowledge coverage
      </h2>
      <p className="mb-4 text-[11px] text-slate-500">
        Estimated from the ingested corpus. These are coverage estimates, not a
        measure of completeness — low areas indicate documented gaps.
      </p>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-accent-rose/30 bg-accent-rose/5 px-4 py-3 text-sm text-rose-200">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" aria-hidden /> {error}
          </span>
          <button
            type="button"
            onClick={load}
            className="focusable rounded-lg border border-white/15 px-3 py-1 text-slate-200 hover:bg-white/10"
          >
            Retry
          </button>
        </div>
      )}

      {!error && data === null && (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-6 w-full rounded-lg shimmer" />
          ))}
        </div>
      )}

      {!error && data && (
        <>
          <div className="mb-4 flex flex-wrap gap-4 text-[11px] text-slate-400">
            <span>
              <strong className="text-white">{data.source_count}</strong> sources
            </span>
            <span>
              <strong className="text-white">{data.chunk_count}</strong> passages
            </span>
          </div>

          <ul className="space-y-3">
            {data.facets.map((f, i) => {
              const score = Math.max(0, Math.min(100, Math.round(f.coverage)));
              return (
                <li key={f.facet}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-slate-300">{f.facet}</span>
                    <span className="tabular-nums text-slate-500">{score}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                    <motion.div
                      className={`h-full rounded-full ${barColor(score)}`}
                      initial={reduce ? { width: `${score}%` } : { width: 0 }}
                      whileInView={{ width: `${score}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: Math.min(i * 0.05, 0.3) }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>

          {data.note && (
            <p className="mt-4 flex items-start gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-[11px] text-slate-400">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-violet" aria-hidden />
              {data.note}
            </p>
          )}

          {data.suggested_searches && data.suggested_searches.length > 0 && (
            <div className="mt-4">
              <h3 className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-wider text-slate-500">
                <Search className="h-3.5 w-3.5" aria-hidden />
                Suggested searches to fill gaps
              </h3>
              <div className="flex flex-wrap gap-2">
                {data.suggested_searches.map((s, i) => (
                  <span
                    key={i}
                    className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-slate-300"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
