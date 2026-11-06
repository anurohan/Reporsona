"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { animate, motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Boxes,
  Lightbulb,
  Loader2,
  MessageSquare,
  Network,
  Quote,
  Settings as SettingsIcon,
} from "lucide-react";
import { ApiError, getInsights, getPersona } from "@/lib/api";
import type {
  Insight,
  InsightClassification,
  PersonaDetail,
} from "@/lib/types";
import PersonaImage from "@/components/PersonaImage";
import EthicalNotice from "@/components/EthicalNotice";
import Timeline from "@/components/Timeline";
import Coverage from "@/components/Coverage";
import { personaAccent } from "@/lib/theme";

const BackgroundScene = dynamic(
  () => import("@/components/three/BackgroundScene"),
  { ssr: false }
);

const CLASS_STYLES: Record<InsightClassification, string> = {
  DOCUMENTED: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
  OBSERVED: "border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan",
  INFERRED: "border-accent-amber/40 bg-accent-amber/10 text-amber-200",
  UNKNOWN: "border-white/20 bg-white/5 text-slate-400",
};

function AnimatedCounter({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, {
      duration: 1,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    return () => controls.stop();
  }, [inView, value]);
  return (
    <span ref={ref} className="tabular-nums">
      {display}
    </span>
  );
}

function Section({
  title,
  icon,
  items,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
}) {
  if (!items || items.length === 0) return null;
  return (
    <section className="glass-panel p-5">
      <h2
        className="mb-3 flex items-center gap-2 border-b pb-2 font-display text-sm uppercase tracking-wider text-slate-300"
        style={{ borderColor: "var(--p-accent-soft)" }}
      >
        <span style={{ color: "var(--p-accent)" }}>{icon}</span>
        {title}
      </h2>
      <ul className="space-y-2">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2 text-sm text-slate-300">
            <span
              className="mt-1.5 h-1 w-1 shrink-0 rounded-full"
              style={{ background: "var(--p-accent)" }}
            />
            {it}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function PersonaProfilePage() {
  const params = useParams();
  const personaId = String(params.personaId || "");

  const [persona, setPersona] = useState<PersonaDetail | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([getPersona(personaId), getInsights(personaId).catch(() => [])])
      .then(([p, ins]) => {
        setPersona(p);
        setInsights(ins);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Could not load this persona."
        )
      );
  };

  useEffect(() => {
    if (personaId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="glass-panel max-w-md p-8 text-center">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-accent-rose" />
          <p className="mb-4 text-rose-100">{error}</p>
          <div className="flex justify-center gap-3">
            <button
              type="button"
              onClick={load}
              className="focusable rounded-xl border border-white/15 bg-white/[0.05] px-4 py-2 text-sm text-white hover:bg-white/10"
            >
              Retry
            </button>
            <Link
              href="/explore"
              className="focusable rounded-xl border border-white/15 px-4 py-2 text-sm text-slate-300 hover:bg-white/10"
            >
              Back to explore
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!persona) {
    return (
      <main className="mx-auto min-h-screen max-w-4xl px-6 py-16">
        <div className="glass-panel mb-6 flex items-center gap-5 p-6">
          <div className="h-28 w-28 rounded-full shimmer" />
          <div className="flex-1 space-y-3">
            <div className="h-6 w-56 rounded shimmer" />
            <div className="h-4 w-full rounded shimmer" />
            <div className="h-4 w-2/3 rounded shimmer" />
          </div>
        </div>
        <div className="flex items-center justify-center py-10 text-slate-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading persona…
        </div>
      </main>
    );
  }

  const profile = persona.profile;
  const coverage = profile?.source_coverage || {};

  return (
    <main
      className="relative min-h-screen overflow-hidden px-5 pb-28 pt-10"
      style={personaAccent(persona.id || persona.name)}
    >
      <BackgroundScene intensity="subtle" />

      {/* Persona-themed full-bleed backdrop: blurred portrait wash + accent glow. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-0">
        {persona.portrait_url && (
          <Image
            src={persona.portrait_url}
            alt=""
            fill
            referrerPolicy="no-referrer"
            loading="lazy"
            sizes="100vw"
            className="absolute inset-0 h-full w-full scale-110 object-cover opacity-[0.12] blur-3xl grayscale"
          />
        )}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% -10%, var(--p-glow), transparent 60%)",
          }}
        />
      </div>

      <div className="relative z-10 mx-auto max-w-4xl">
        <Link
          href="/explore"
          className="focusable mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Explore
        </Link>

        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel flex flex-col items-center gap-6 p-6 sm:flex-row sm:items-start"
        >
          <PersonaImage
            name={persona.name}
            portraitUrl={persona.portrait_url}
            size={128}
          />
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <h1 className="font-display text-3xl font-bold text-white">
                {persona.name}
              </h1>
              {persona.is_demo && (
                <span className="chip border-indigoGlow-400/40 text-indigoGlow-400">
                  Demo persona
                </span>
              )}
            </div>
            {persona.known_for.length > 0 && (
              <div className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
                {persona.known_for.map((k, i) => (
                  <span
                    key={i}
                    className="chip"
                    style={{
                      borderColor: "var(--p-accent-soft)",
                      background: "var(--p-accent-soft)",
                    }}
                  >
                    {k}
                  </span>
                ))}
              </div>
            )}
            {persona.summary && (
              <p className="mt-4 text-sm leading-relaxed text-slate-300">
                {persona.summary}
              </p>
            )}

            {/* Stats */}
            <div className="mt-5 flex flex-wrap justify-center gap-6 sm:justify-start">
              <div>
                <div className="font-display text-2xl text-white">
                  <AnimatedCounter value={persona.source_count} />
                </div>
                <div className="text-[11px] uppercase tracking-wider text-slate-500">
                  Sources
                </div>
              </div>
              <div>
                <div className="font-display text-2xl text-white">
                  <AnimatedCounter value={persona.topics?.length || 0} />
                </div>
                <div className="text-[11px] uppercase tracking-wider text-slate-500">
                  Topics
                </div>
              </div>
              <div>
                <div className="font-display text-2xl text-white">
                  <AnimatedCounter value={insights.length} />
                </div>
                <div className="text-[11px] uppercase tracking-wider text-slate-500">
                  Insights
                </div>
              </div>
            </div>
          </div>
        </motion.header>

        {/* Nav */}
        <nav
          className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5"
          aria-label="Persona sections"
        >
          {[
            { href: `/persona/${personaId}/chat`, label: "Chat", icon: MessageSquare },
            { href: `/persona/${personaId}/knowledge`, label: "Knowledge", icon: Network },
            { href: `/persona/${personaId}/sources`, label: "Sources", icon: BookOpen },
            { href: `/persona/${personaId}/insights`, label: "Insights", icon: Lightbulb },
            { href: `/settings`, label: "Settings", icon: SettingsIcon },
          ].map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="focusable glass-panel flex flex-col items-center gap-2 p-4 text-sm text-slate-200 transition-all hover:border-indigoGlow-400/40 hover:shadow-glow"
            >
              <Icon className="h-5 w-5 text-accent-cyan" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>

        {/* Profile sections */}
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <Section
            title="Communication style"
            icon={<Quote className="h-4 w-4" />}
            items={profile?.communication_style || []}
          />
          <Section
            title="Recurring themes"
            icon={<Boxes className="h-4 w-4" />}
            items={profile?.recurring_themes || []}
          />
          <Section
            title="Documented viewpoints"
            icon={<BookOpen className="h-4 w-4" />}
            items={profile?.documented_viewpoints || []}
          />
          <Section
            title="Frequent concepts"
            icon={<Lightbulb className="h-4 w-4" />}
            items={profile?.frequent_concepts || []}
          />
          <Section
            title="Language patterns"
            icon={<Quote className="h-4 w-4" />}
            items={profile?.language_patterns || []}
          />
          <Section
            title="Uncertainties"
            icon={<AlertTriangle className="h-4 w-4" />}
            items={profile?.uncertainties || []}
          />
        </div>

        {/* Timeline + knowledge coverage (§12 / §21) */}
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Timeline personaId={personaId} />
          <Coverage personaId={personaId} />
        </div>

        {/* Source coverage */}
        {Object.keys(coverage).length > 0 && (
          <section className="glass-panel mt-4 p-5">
            <h2 className="mb-3 font-display text-sm uppercase tracking-wider text-slate-300">
              Source coverage
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(coverage).map(([key, val]) => (
                <div key={key} className="glass rounded-xl px-3 py-2 text-center">
                  <div className="font-display text-lg text-white">
                    {typeof val === "number" ? Math.round(val) : String(val)}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">
                    {key.replace(/_/g, " ")}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Insights */}
        {insights.length > 0 && (
          <section className="glass-panel mt-4 p-5">
            <h2 className="mb-4 font-display text-sm uppercase tracking-wider text-slate-300">
              Insights
            </h2>
            <ul className="space-y-3">
              {insights.map((ins) => (
                <li
                  key={ins.id}
                  className="rounded-xl border border-white/5 bg-white/[0.02] p-4"
                >
                  <div className="mb-1 flex items-start justify-between gap-3">
                    <h3 className="text-sm font-medium text-white">
                      {ins.label}
                    </h3>
                    <span
                      className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                        CLASS_STYLES[ins.classification] || CLASS_STYLES.UNKNOWN
                      }`}
                    >
                      {ins.classification}
                    </span>
                  </div>
                  {ins.detail && (
                    <p className="text-sm text-slate-400">{ins.detail}</p>
                  )}
                  {ins.evidence_chunk_ids.length > 0 && (
                    <p className="mt-1 text-[11px] text-slate-600">
                      {ins.evidence_chunk_ids.length} supporting passage
                      {ins.evidence_chunk_ids.length === 1 ? "" : "s"}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <EthicalNotice variant="fixed" />
    </main>
  );
}
