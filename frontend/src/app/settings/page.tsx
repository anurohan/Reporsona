"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Cpu,
  Database,
  Globe,
  Loader2,
  Server,
  Settings as SettingsIcon,
  Sparkles,
  Youtube,
  Zap,
} from "lucide-react";
import { API_BASE, ApiError, getHealth, getProviders } from "@/lib/api";
import type { ProviderStatus } from "@/lib/types";

const LS_REDUCE_MOTION = "repersona:reduce-motion";
const LS_EVIDENCE_MODE = "repersona:evidence-mode";

function readBool(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const v = window.localStorage.getItem(key);
  if (v === null) return fallback;
  return v === "true";
}

function providerIcon(key: string): React.ReactNode {
  const k = key.toLowerCase();
  if (k.includes("youtube")) return <Youtube className="h-4 w-4" aria-hidden />;
  if (k.includes("web") || k.includes("search"))
    return <Globe className="h-4 w-4" aria-hidden />;
  if (k.includes("llm") || k.includes("model"))
    return <Cpu className="h-4 w-4" aria-hidden />;
  if (k.includes("embed"))
    return <Zap className="h-4 w-4" aria-hidden />;
  if (k.includes("vector") || k.includes("store"))
    return <Database className="h-4 w-4" aria-hidden />;
  return <Sparkles className="h-4 w-4" aria-hidden />;
}

function Toggle({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-xl border border-white/5 bg-white/[0.02] p-4">
      <div className="min-w-0">
        <label htmlFor={id} className="text-sm font-medium text-white">
          {label}
        </label>
        <p className="mt-1 text-xs text-slate-400">{description}</p>
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`focusable relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors ${
          checked
            ? "border-indigoGlow-400/60 bg-indigoGlow-600/40"
            : "border-white/15 bg-white/[0.06]"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

function StatusRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/5 py-3 last:border-0">
      <span className="flex items-center gap-2 text-sm text-slate-300">
        <span className="text-accent-cyan">{icon}</span>
        {label}
      </span>
      <span className="min-w-0 truncate text-right text-sm text-white">
        {value}
      </span>
    </div>
  );
}

export default function SettingsPage() {
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[] | null>(null);

  const [reduceMotion, setReduceMotion] = useState(false);
  const [evidenceMode, setEvidenceMode] = useState(true);

  const load = () => {
    setError(null);
    setHealth(null);
    getHealth()
      .then(setHealth)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not reach the backend health endpoint."
        )
      );
    getProviders()
      .then(setProviders)
      .catch(() => setProviders([]));
  };

  useEffect(() => {
    load();
    setReduceMotion(readBool(LS_REDUCE_MOTION, false));
    setEvidenceMode(readBool(LS_EVIDENCE_MODE, true));
  }, []);

  const updateReduceMotion = (v: boolean) => {
    setReduceMotion(v);
    window.localStorage.setItem(LS_REDUCE_MOTION, String(v));
    // Reflect immediately so motion-respecting components can pick it up.
    document.documentElement.dataset.reduceMotion = v ? "true" : "false";
  };

  const updateEvidenceMode = (v: boolean) => {
    setEvidenceMode(v);
    window.localStorage.setItem(LS_EVIDENCE_MODE, String(v));
  };

  const statusOk =
    health &&
    (health.status === "ok" ||
      health.status === "healthy" ||
      health.ok === true);

  return (
    <main className="min-h-screen bg-space-gradient px-5 pb-16 pt-8">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/explore"
          className="focusable mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Explore
        </Link>

        <h1 className="flex items-center gap-2 font-display text-3xl font-bold text-white">
          <SettingsIcon className="h-6 w-6 text-accent-violet" aria-hidden />
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Backend status and local preferences for this browser.
        </p>

        {/* Backend status */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel mt-6 p-5"
          aria-label="Backend status"
        >
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-display text-sm uppercase tracking-wider text-slate-300">
              Backend
            </h2>
            {health && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-wider ${
                  statusOk
                    ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                    : "border-accent-amber/40 bg-accent-amber/10 text-amber-200"
                }`}
              >
                <CheckCircle2 className="h-3 w-3" aria-hidden />
                {statusOk ? "Online" : String(health.status ?? "unknown")}
              </span>
            )}
          </div>

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

          {!error && health === null && (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Checking backend…
            </div>
          )}

          {!error && health && (
            <div>
              <StatusRow
                icon={<Server className="h-4 w-4" aria-hidden />}
                label="API base"
                value={<code className="text-xs">{API_BASE}</code>}
              />
              <StatusRow
                icon={<Sparkles className="h-4 w-4" aria-hidden />}
                label="Demo mode"
                value={
                  health.demo_mode === undefined
                    ? "—"
                    : health.demo_mode
                    ? "On"
                    : "Off"
                }
              />
              <StatusRow
                icon={<Cpu className="h-4 w-4" aria-hidden />}
                label="LLM provider"
                value={health.llm_provider ?? "—"}
              />
              <StatusRow
                icon={<Zap className="h-4 w-4" aria-hidden />}
                label="Embedding backend"
                value={health.embedding_backend ?? "—"}
              />
              <StatusRow
                icon={<Database className="h-4 w-4" aria-hidden />}
                label="Vector store"
                value={health.vector_store ?? "—"}
              />
            </div>
          )}
        </motion.section>

        {/* Providers (§27) */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="glass-panel mt-4 p-5"
          aria-label="Configured providers"
        >
          <div className="mb-1 flex items-center justify-between">
            <h2 className="font-display text-sm uppercase tracking-wider text-slate-300">
              Providers
            </h2>
            <span className="text-[11px] text-slate-500">
              Server-side only · keys never reach the browser
            </span>
          </div>
          <p className="mb-4 text-xs text-slate-500">
            Optional API keys unlock enhanced sources. The app stays fully
            usable in local mode without them.
          </p>

          {providers === null && (
            <div className="flex items-center gap-2 py-4 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Loading provider status…
            </div>
          )}

          {providers !== null && providers.length === 0 && (
            <p className="py-3 text-sm text-slate-500">
              Provider status is unavailable right now.
            </p>
          )}

          {providers !== null && providers.length > 0 && (
            <ul className="space-y-2">
              {providers.map((p) => (
                <li
                  key={p.key}
                  className="flex items-start justify-between gap-4 rounded-xl border border-white/5 bg-white/[0.02] p-4"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-sm font-medium text-white">
                      <span className="text-accent-cyan">
                        {providerIcon(p.key)}
                      </span>
                      {p.label}
                    </div>
                    {p.detail && (
                      <p className="mt-1 text-xs text-slate-400">{p.detail}</p>
                    )}
                    {p.requires_key && !p.configured && p.docs && (
                      <a
                        href={p.docs}
                        target="_blank"
                        rel="noreferrer"
                        className="focusable mt-1 inline-block text-[11px] text-indigoGlow-300 underline decoration-dotted hover:text-indigoGlow-200"
                      >
                        Get an API key →
                      </a>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-wider ${
                        p.configured
                          ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                          : "border-white/15 bg-white/[0.04] text-slate-400"
                      }`}
                    >
                      {p.configured ? (
                        <CheckCircle2 className="h-3 w-3" aria-hidden />
                      ) : (
                        <AlertTriangle className="h-3 w-3" aria-hidden />
                      )}
                      {p.configured ? "Configured" : "Not configured"}
                    </span>
                    {p.mode && (
                      <span className="text-[11px] text-slate-500">
                        {p.mode}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </motion.section>

        {/* Preferences */}
        <section
          className="glass-panel mt-4 p-5"
          aria-label="Local preferences"
        >
          <h2 className="mb-1 font-display text-sm uppercase tracking-wider text-slate-300">
            Preferences
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            Stored in this browser only.
          </p>
          <div className="space-y-3">
            <Toggle
              id="pref-reduce-motion"
              label="Reduce motion"
              description="Minimise animations and transitions across the app."
              checked={reduceMotion}
              onChange={updateReduceMotion}
            />
            <Toggle
              id="pref-evidence-mode"
              label="Evidence mode default"
              description="Show supporting passages alongside chat answers by default."
              checked={evidenceMode}
              onChange={updateEvidenceMode}
            />
          </div>
          <p className="mt-3 text-[11px] text-slate-500">
            Reduce motion also honours your operating system&apos;s
            prefers-reduced-motion setting.
          </p>
        </section>
      </div>
    </main>
  );
}
