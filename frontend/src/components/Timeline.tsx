"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  AlertTriangle,
  Award,
  BookOpen,
  CalendarClock,
  Flag,
  Skull,
  Sparkles,
} from "lucide-react";
import { ApiError, getTimeline } from "@/lib/api";
import type { TimelineEvent } from "@/lib/types";

/** Documented timeline (§12): birth/death + dated source-derived events, with
 *  category filtering and confidence (documented vs inferred) metadata. */

function categoryIcon(category: string) {
  const cls = "h-4 w-4";
  switch (category) {
    case "birth":
      return <Flag className={cls} aria-hidden />;
    case "death":
      return <Skull className={cls} aria-hidden />;
    case "work":
      return <BookOpen className={cls} aria-hidden />;
    case "event":
      return <Award className={cls} aria-hidden />;
    default:
      return <Sparkles className={cls} aria-hidden />;
  }
}

function labelFor(category: string): string {
  return category ? category.charAt(0).toUpperCase() + category.slice(1) : "Event";
}

export default function Timeline({ personaId }: { personaId: string }) {
  const reduce = useReducedMotion();

  const [events, setEvents] = useState<TimelineEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const load = () => {
    setError(null);
    setEvents(null);
    getTimeline(personaId)
      .then(setEvents)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not load the documented timeline."
        )
      );
  };

  useEffect(() => {
    if (personaId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  const categories = useMemo(() => {
    if (!events) return [];
    return Array.from(new Set(events.map((e) => e.category).filter(Boolean)));
  }, [events]);

  const shown = useMemo(() => {
    if (!events) return [];
    return filter === "all"
      ? events
      : events.filter((e) => e.category === filter);
  }, [events, filter]);

  return (
    <section className="glass-panel p-5" aria-label="Documented timeline">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 font-display text-sm uppercase tracking-wider text-slate-300">
          <CalendarClock className="h-4 w-4 text-accent-violet" aria-hidden />
          Timeline
        </h2>
        {categories.length > 1 && (
          <div
            className="flex flex-wrap items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] p-0.5"
            role="radiogroup"
            aria-label="Filter timeline by category"
          >
            {["all", ...categories].map((c) => (
              <button
                key={c}
                type="button"
                role="radio"
                aria-checked={filter === c}
                onClick={() => setFilter(c)}
                className={`focusable rounded-full px-2.5 py-1 text-[11px] capitalize transition-colors ${
                  filter === c
                    ? "bg-accent-violet/20 text-accent-violet"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        )}
      </div>

      <p className="mb-4 text-[11px] text-slate-500">
        Derived from the persona&apos;s documented lifespan and dated sources.
        Events marked <em>inferred</em> are estimated from source dates.
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

      {!error && events === null && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-4">
              <div className="h-3 w-3 shrink-0 rounded-full shimmer" />
              <div className="h-10 flex-1 rounded-lg shimmer" />
            </div>
          ))}
        </div>
      )}

      {!error && events && shown.length === 0 && (
        <p className="rounded-xl border border-white/5 bg-white/[0.02] px-4 py-8 text-center text-sm text-slate-400">
          No dated events are available for this persona yet.
        </p>
      )}

      {!error && shown.length > 0 && (
        <ol className="relative ml-2 border-l border-white/10 pl-6">
          {shown.map((e, i) => (
            <motion.li
              key={`${e.date}-${i}`}
              initial={reduce ? { opacity: 0 } : { opacity: 0, x: -8 }}
              whileInView={reduce ? { opacity: 1 } : { opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ delay: Math.min(i * 0.04, 0.3) }}
              className="relative mb-4 last:mb-0"
            >
              <span
                className="absolute -left-[1.65rem] top-1.5 h-3 w-3 rounded-full border-2 border-void-950 bg-indigoGlow-400"
                aria-hidden
              />
              <div className="rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
                <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-accent-cyan">
                  {e.year ?? e.date}
                  <span
                    className={`rounded-full border px-1.5 py-0 text-[9px] normal-case tracking-normal ${
                      e.confidence === "documented"
                        ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                        : "border-white/15 bg-white/[0.04] text-slate-400"
                    }`}
                  >
                    {e.confidence || "documented"}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-accent-violet" title={labelFor(e.category)}>
                    {categoryIcon(e.category)}
                  </span>
                  <span className="text-sm text-white">{e.title}</span>
                </div>
                {e.description && (
                  <p className="mt-1 text-xs text-slate-400">{e.description}</p>
                )}
                {e.source_title && (
                  <p className="mt-1 text-[11px] text-slate-500">
                    Source: {e.source_title}
                  </p>
                )}
              </div>
            </motion.li>
          ))}
        </ol>
      )}
    </section>
  );
}
