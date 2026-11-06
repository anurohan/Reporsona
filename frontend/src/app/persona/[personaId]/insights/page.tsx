"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Lightbulb,
  MessageSquare,
  Network,
  Sparkles,
  User,
} from "lucide-react";
import { ApiError, getInsights, getPersona } from "@/lib/api";
import type {
  Insight,
  InsightClassification,
  PersonaDetail,
} from "@/lib/types";

const CLASS_STYLES: Record<InsightClassification, string> = {
  DOCUMENTED: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
  OBSERVED: "border-sky-400/40 bg-sky-400/10 text-sky-300",
  INFERRED: "border-accent-amber/40 bg-accent-amber/10 text-amber-200",
  UNKNOWN: "border-slate-400/30 bg-slate-400/10 text-slate-300",
};

export default function InsightsPage() {
  const params = useParams();
  const personaId = String(params.personaId || "");

  const [persona, setPersona] = useState<PersonaDetail | null>(null);
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    setInsights(null);
    Promise.all([getPersona(personaId), getInsights(personaId)])
      .then(([p, ins]) => {
        setPersona(p);
        setInsights(ins);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not load insights for this persona."
        )
      );
  };

  useEffect(() => {
    if (personaId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  const nav = [
    { href: `/persona/${personaId}/chat`, label: "Chat", icon: MessageSquare },
    { href: `/persona/${personaId}/knowledge`, label: "Knowledge", icon: Network },
    { href: `/persona/${personaId}/sources`, label: "Sources", icon: BookOpen },
    { href: `/persona/${personaId}/insights`, label: "Insights", icon: Lightbulb },
    { href: `/persona/${personaId}`, label: "Profile", icon: User },
  ];

  return (
    <main className="min-h-screen bg-space-gradient px-5 pb-16 pt-8">
      <div className="mx-auto max-w-4xl">
        <Link
          href={`/persona/${personaId}`}
          className="focusable mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Profile
        </Link>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 font-display text-3xl font-bold text-white">
              <Sparkles className="h-6 w-6 text-accent-violet" aria-hidden />
              Insights
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              {persona
                ? `What the sources reveal about ${persona.name}, each labelled by how it's grounded.`
                : "What the sources reveal, each labelled by how it's grounded."}
            </p>
          </div>
        </div>

        {/* Nav */}
        <nav
          className="mt-5 flex flex-wrap gap-2"
          aria-label="Persona sections"
        >
          {nav.map(({ href, label, icon: Icon }) => {
            const isCurrent = label === "Insights";
            return (
              <Link
                key={href}
                href={href}
                aria-current={isCurrent ? "page" : undefined}
                className={`focusable inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm transition-colors ${
                  isCurrent
                    ? "border-indigoGlow-400/60 bg-indigoGlow-600/15 text-white"
                    : "border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.07]"
                }`}
              >
                <Icon className="h-4 w-4 text-accent-cyan" aria-hidden />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Legend */}
        <div className="mt-5 flex flex-wrap gap-2">
          {(
            [
              "DOCUMENTED",
              "OBSERVED",
              "INFERRED",
              "UNKNOWN",
            ] as InsightClassification[]
          ).map((c) => (
            <span
              key={c}
              className={`rounded-full border px-2.5 py-0.5 text-[10px] uppercase tracking-wider ${CLASS_STYLES[c]}`}
            >
              {c}
            </span>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="glass-panel mt-6 flex items-center justify-between px-4 py-3 text-sm text-rose-200">
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

        {/* Loading skeletons */}
        {!error && insights === null && (
          <div className="mt-6 grid gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="glass-panel p-5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="h-4 w-1/3 rounded shimmer" />
                  <div className="h-4 w-20 rounded-full shimmer" />
                </div>
                <div className="mb-2 h-3 w-full rounded shimmer" />
                <div className="h-3 w-2/3 rounded shimmer" />
              </div>
            ))}
          </div>
        )}

        {/* Empty */}
        {!error && insights && insights.length === 0 && (
          <div className="glass-panel mt-6 px-4 py-12 text-center">
            <Lightbulb
              className="mx-auto mb-3 h-8 w-8 text-slate-500"
              aria-hidden
            />
            <p className="text-sm text-slate-400">
              No insights have been derived for this persona yet. Add more
              sources to give the model material to work from.
            </p>
            <Link
              href={`/persona/${personaId}/sources`}
              className="focusable mt-4 inline-block rounded-xl border border-white/15 bg-white/[0.05] px-4 py-2 text-sm text-white hover:bg-white/10"
            >
              Add sources
            </Link>
          </div>
        )}

        {/* Insight cards */}
        {!error && insights && insights.length > 0 && (
          <div className="mt-6 grid gap-3">
            {insights.map((ins, i) => {
              const count = ins.evidence_chunk_ids?.length || 0;
              return (
                <motion.article
                  key={ins.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.03, 0.3) }}
                  className="glass-panel p-5"
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <h2 className="text-sm font-medium text-white">
                      {ins.label}
                    </h2>
                    <span
                      className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                        CLASS_STYLES[ins.classification] || CLASS_STYLES.UNKNOWN
                      }`}
                    >
                      {ins.classification}
                    </span>
                  </div>
                  {ins.detail && (
                    <p className="text-sm leading-relaxed text-slate-300">
                      {ins.detail}
                    </p>
                  )}
                  <p className="mt-3 text-[11px] text-slate-500">
                    {count} supporting passage{count === 1 ? "" : "s"}
                  </p>
                </motion.article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
