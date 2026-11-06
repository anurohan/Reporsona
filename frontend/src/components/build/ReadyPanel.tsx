"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  Network,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import PersonaImage from "@/components/PersonaImage";

interface ReadyPanelProps {
  personaId: string;
  personaName: string;
  portraitUrl: string;
  stats: Record<string, any>;
  /** Human-readable, real warnings (e.g. optional providers unavailable). */
  warnings: string[];
  onEnter: () => void;
}

const SUMMARY_FIELDS: { key: string; label: string }[] = [
  { key: "sources", label: "sources" },
  { key: "documents", label: "documents" },
  { key: "chunks", label: "knowledge chunks" },
  { key: "embeddings", label: "embeddings" },
  { key: "topics", label: "topics" },
];

function fmt(v: any): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Math.round(v).toLocaleString();
  return String(v);
}

/**
 * Terminal success state. Replaces the loader entirely on completion and makes
 * ENTER PERSONA the unmistakable primary action. Renders a warnings variant
 * when optional sources were unavailable, but the CTA is always enabled.
 */
export default function ReadyPanel({
  personaId,
  personaName,
  portraitUrl,
  stats,
  warnings,
  onEnter,
}: ReadyPanelProps) {
  const reduceMotion = useReducedMotion();
  const [showReadyHint, setShowReadyHint] = useState(false);
  const hasWarnings = warnings.length > 0;

  // A gentle, non-intrusive "ready" nudge — never an auto-redirect.
  useEffect(() => {
    const t = setTimeout(() => setShowReadyHint(true), 1800);
    return () => clearTimeout(t);
  }, []);

  const statusRows = [
    { icon: Network, label: "Knowledge graph", value: "Ready" },
    { icon: ShieldCheck, label: "Evidence validation", value: "Complete" },
    { icon: Sparkles, label: "Persona model", value: "Ready" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduceMotion ? 0 : 0.55, ease: "easeOut" }}
      className="glass-panel relative overflow-hidden p-6 text-center sm:p-8"
      role="status"
      aria-label={`${personaName || "Persona"} is ready`}
    >
      {/* subtle outward particles on settle */}
      {!reduceMotion && (
        <div aria-hidden className="pointer-events-none absolute inset-0">
          {[...Array(10)].map((_, i) => {
            const angle = (i / 10) * Math.PI * 2;
            return (
              <motion.span
                key={i}
                className="absolute left-1/2 top-24 h-1 w-1 rounded-full bg-accent-cyan/70"
                initial={{ opacity: 0.9, x: 0, y: 0, scale: 1 }}
                animate={{
                  opacity: 0,
                  x: Math.cos(angle) * 120,
                  y: Math.sin(angle) * 120,
                  scale: 0.4,
                }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              />
            );
          })}
        </div>
      )}

      <div className="relative mx-auto mb-4 w-fit">
        <PersonaImage name={personaName || "Persona"} portraitUrl={portraitUrl} size={96} glow />
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: reduceMotion ? 0 : 0.2, type: "spring", stiffness: 300, damping: 18 }}
          className="absolute -bottom-1 -right-1 rounded-full bg-void-950 p-0.5"
        >
          <CheckCircle2 className="h-7 w-7 text-emerald-400" aria-hidden />
        </motion.span>
      </div>

      <p className="text-[11px] uppercase tracking-[0.28em] text-accent-cyan">
        {hasWarnings ? "Persona ready with warnings" : "Persona ready"}
      </p>
      <h1 className="mt-1.5 font-display text-3xl font-semibold text-white">
        {personaName || "Persona"}
      </h1>
      <p className="mt-1.5 text-sm text-slate-400">
        Reconstruction completed successfully.
      </p>

      {/* metric summary line */}
      <p className="mx-auto mt-4 max-w-md text-sm text-slate-300">
        {SUMMARY_FIELDS.map((f, i) => (
          <span key={f.key}>
            <span className="font-medium text-white tabular-nums">{fmt(stats?.[f.key])}</span>{" "}
            <span className="text-slate-400">{f.label}</span>
            {i < SUMMARY_FIELDS.length - 1 ? <span className="text-slate-600"> · </span> : null}
          </span>
        ))}
      </p>

      {/* status rows */}
      <div className="mx-auto mt-5 max-w-sm space-y-1.5">
        {statusRows.map((row) => (
          <div
            key={row.label}
            className="flex items-center gap-2.5 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-left"
          >
            <row.icon className="h-4 w-4 shrink-0 text-indigoGlow-400" aria-hidden />
            <span className="flex-1 text-sm text-slate-300">{row.label}</span>
            <span className="text-xs font-medium text-emerald-300">{row.value}</span>
          </div>
        ))}
      </div>

      {/* warnings (real, optional-provider gaps) */}
      {hasWarnings && (
        <div className="mx-auto mt-4 max-w-sm rounded-lg border border-accent-amber/25 bg-accent-amber/5 px-3 py-2.5 text-left">
          <p className="text-xs font-medium text-amber-200">
            Some optional sources were unavailable.
          </p>
          <ul className="mt-1 space-y-0.5">
            {warnings.map((w) => (
              <li key={w} className="text-[11px] text-amber-200/80">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* primary CTA */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: reduceMotion ? 0 : 0.3, duration: 0.4 }}
        className="mt-7"
      >
        <button
          type="button"
          onClick={onEnter}
          aria-label={`Enter the ${personaName || "persona"} workspace`}
          className="focusable group relative inline-flex items-center gap-2 rounded-xl border border-indigoGlow-400/50 bg-gradient-to-r from-indigoGlow-600/80 to-indigoGlow-500/70 px-7 py-3 text-sm font-semibold text-white shadow-glow transition-all hover:from-indigoGlow-500 hover:to-accent-violet hover:shadow-glow-lg"
        >
          <span
            aria-hidden
            className="absolute inset-0 rounded-xl opacity-0 ring-2 ring-indigoGlow-400/50 transition-opacity group-hover:opacity-100"
          />
          Enter persona
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
        </button>

        {/* secondary actions */}
        <div className="mt-4 flex items-center justify-center gap-3 text-xs">
          <Link
            href={`/persona/${personaId}/sources`}
            className="focusable inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-slate-300 hover:bg-white/[0.06]"
          >
            <BookOpen className="h-3.5 w-3.5" aria-hidden />
            View sources
          </Link>
          <Link
            href={`/persona/${personaId}#timeline`}
            className="focusable inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-slate-300 hover:bg-white/[0.06]"
          >
            <CalendarClock className="h-3.5 w-3.5" aria-hidden />
            View timeline
          </Link>
        </div>

        <div className="mt-3 h-4" aria-live="polite">
          {showReadyHint && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-[11px] text-slate-500"
            >
              Your persona is ready.
            </motion.p>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
