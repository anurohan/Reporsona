"use client";

import dynamic from "next/dynamic";
import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Loader2,
  Search,
  Sparkles,
  Trash2,
  Users,
  Wand2,
  X,
} from "lucide-react";
import {
  ApiError,
  createPersona,
  deletePersona,
  listPersonas,
  resolveIdentity,
} from "@/lib/api";
import type { IdentityCandidate, PersonaSummary, Resolution } from "@/lib/types";
import PersonaImage from "@/components/PersonaImage";
import EthicalNotice from "@/components/EthicalNotice";

const BackgroundScene = dynamic(
  () => import("@/components/three/BackgroundScene"),
  { ssr: false }
);

const SUGGESTIONS = [
  "Osho",
  "Albert Einstein",
  "Leonardo da Vinci",
  "William Shakespeare",
  "Steve Jobs",
];

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
    building: "border-indigoGlow-400/40 bg-indigoGlow-600/10 text-indigoGlow-400",
    pending: "border-white/15 bg-white/5 text-slate-300",
    failed: "border-accent-rose/40 bg-accent-rose/10 text-rose-200",
  };
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${
        map[status] || map.pending
      }`}
    >
      {status}
    </span>
  );
}

function ExploreInner() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [personas, setPersonas] = useState<PersonaSummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Identity resolution (§8)
  const [resolving, setResolving] = useState(false);
  const [resolution, setResolution] = useState<Resolution | null>(null);

  const loadPersonas = () => {
    setListError(null);
    listPersonas()
      .then(setPersonas)
      .catch((err) =>
        setListError(
          err instanceof ApiError
            ? err.message
            : "Could not load existing personas."
        )
      );
  };

  useEffect(() => {
    loadPersonas();
  }, []);

  const startCreate = async (personaName: string, demo: boolean) => {
    const trimmed = personaName.trim();
    if (!trimmed || creating) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await createPersona({ name: trimmed, demo });
      router.push(`/persona/build/${res.job.id}`);
    } catch (err) {
      setCreateError(
        err instanceof ApiError
          ? err.message
          : "Could not start reconstruction. Please try again."
      );
      setCreating(false);
    }
  };

  // Identity resolution (§8): disambiguate a name before deep ingestion.
  const runResolve = async (personaName: string) => {
    const trimmed = personaName.trim();
    if (!trimmed || resolving || creating) return;
    setResolving(true);
    setCreateError(null);
    setResolution(null);
    try {
      const res = await resolveIdentity({ name: trimmed, limit: 5 });
      if (res.candidates.length <= 1) {
        // Unambiguous (or no candidates): proceed straight to the build using
        // the resolved name when available, else the raw query.
        await startCreate(res.candidates[0]?.name || trimmed, false);
        return;
      }
      setResolution(res);
    } catch (err) {
      // Resolution is a convenience layer — if it fails, fall back to a direct
      // build rather than blocking the user.
      await startCreate(trimmed, false);
    } finally {
      setResolving(false);
    }
  };

  const chooseCandidate = (c: IdentityCandidate) => {
    setResolution(null);
    startCreate(c.name, false);
  };

  const openPersona = (p: PersonaSummary) => {
    if (p.status === "ready") {
      router.push(`/persona/${p.id}`);
    }
  };

  const removePersona = async (id: string) => {
    setDeletingId(id);
    setListError(null);
    try {
      await deletePersona(id);
      setPersonas((prev) => (prev ? prev.filter((p) => p.id !== id) : prev));
      setConfirmId(null);
    } catch (err) {
      setListError(
        err instanceof ApiError ? err.message : "Could not delete this persona."
      );
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden px-6 pb-28 pt-16">
      <BackgroundScene intensity="subtle" />

      <div className="relative z-10 mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <h1 className="font-display text-3xl font-bold text-white sm:text-4xl">
            Who would you like to explore?
          </h1>
          <p className="mt-3 text-sm text-slate-400">
            Name any documented person. RePersona will gather and process public
            material, or use a bundled demo corpus.
          </p>
        </motion.div>

        {/* Search + actions */}
        <div className="glass-panel mx-auto mt-8 max-w-2xl p-4">
          <label htmlFor="persona-name" className="sr-only">
            Persona name
          </label>
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3">
            <Search className="h-4 w-4 shrink-0 text-slate-500" aria-hidden />
            <input
              id="persona-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runResolve(name);
              }}
              placeholder="e.g. Osho, Albert Einstein…"
              className="focusable w-full bg-transparent py-3 text-base text-white placeholder:text-slate-500"
            />
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setName(s);
                  setSelected(s);
                }}
                className={`focusable chip transition-colors hover:border-indigoGlow-400/50 hover:text-white ${
                  selected === s
                    ? "border-indigoGlow-400/60 bg-indigoGlow-600/15 text-white"
                    : ""
                }`}
                aria-pressed={selected === s}
              >
                {s}
              </button>
            ))}
          </div>

          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={() => runResolve(name)}
              disabled={creating || resolving || !name.trim()}
              className="focusable inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-slate-200 transition-colors hover:bg-white/[0.1] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {resolving ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Search className="h-4 w-4" aria-hidden />
              )}
              Search
            </button>
            <button
              type="button"
              onClick={() => startCreate(name, false)}
              disabled={creating || resolving || !name.trim()}
              className="focusable inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet px-4 py-3 text-sm font-medium text-white shadow-glow transition-shadow hover:shadow-glow-lg disabled:cursor-not-allowed disabled:opacity-40"
            >
              {creating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Wand2 className="h-4 w-4" aria-hidden />
              )}
              Create Persona
            </button>
            <button
              type="button"
              onClick={() => startCreate(name || "Osho", true)}
              disabled={creating || resolving}
              className="focusable inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-indigoGlow-400/40 bg-indigoGlow-600/10 px-4 py-3 text-sm text-indigoGlow-400 transition-colors hover:bg-indigoGlow-600/20 disabled:opacity-40"
            >
              <Sparkles className="h-4 w-4" aria-hidden />
              Use Demo Persona
            </button>
          </div>

          {createError && (
            <p
              role="alert"
              className="mt-3 rounded-lg border border-accent-rose/30 bg-accent-rose/10 px-3 py-2 text-sm text-rose-200"
            >
              {createError}
            </p>
          )}
        </div>

        {/* Existing personas */}
        <section className="mt-12">
          <h2 className="mb-4 font-display text-sm uppercase tracking-[0.2em] text-slate-400">
            Existing personas
          </h2>

          {listError && (
            <div className="glass-panel flex items-center justify-between px-4 py-3 text-sm text-rose-200">
              <span>{listError}</span>
              <button
                type="button"
                onClick={loadPersonas}
                className="focusable rounded-lg border border-white/15 px-3 py-1 text-slate-200 hover:bg-white/10"
              >
                Retry
              </button>
            </div>
          )}

          {!listError && personas === null && (
            <div className="grid gap-3 sm:grid-cols-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="glass-panel h-24 p-4">
                  <div className="h-full w-full rounded-lg shimmer" />
                </div>
              ))}
            </div>
          )}

          {!listError && personas && personas.length === 0 && (
            <div className="glass-panel px-4 py-8 text-center text-sm text-slate-400">
              No personas yet. Create your first one above.
            </div>
          )}

          {personas && personas.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {personas.map((p) => {
                const ready = p.status === "ready";
                const confirming = confirmId === p.id;
                const deleting = deletingId === p.id;
                return (
                  <div
                    key={p.id}
                    className={`group glass-panel relative flex items-center gap-4 p-4 transition-all ${
                      ready
                        ? "hover:border-indigoGlow-400/40 hover:shadow-glow"
                        : "opacity-70"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => openPersona(p)}
                      disabled={!ready}
                      className={`focusable flex min-w-0 flex-1 items-center gap-4 text-left ${
                        ready ? "" : "cursor-default"
                      }`}
                      aria-label={`${p.name} — ${p.status}`}
                    >
                      <PersonaImage
                        name={p.name}
                        portraitUrl={p.portrait_url}
                        size={56}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-display text-base text-white">
                            {p.name}
                          </span>
                          <StatusBadge status={p.status} />
                          {p.is_demo && (
                            <span className="chip px-2 py-0 text-[10px]">
                              Demo
                            </span>
                          )}
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs text-slate-400">
                          {p.summary || p.known_for.join(", ") || "Persona"}
                        </p>
                      </div>
                      {ready && (
                        <ArrowRight
                          className="h-4 w-4 shrink-0 text-slate-500 transition-transform group-hover:translate-x-1 group-hover:text-white"
                          aria-hidden
                        />
                      )}
                    </button>

                    {/* Delete control */}
                    {confirming ? (
                      <div className="flex shrink-0 items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => removePersona(p.id)}
                          disabled={deleting}
                          className="focusable inline-flex items-center gap-1 rounded-lg border border-accent-rose/40 bg-accent-rose/15 px-2.5 py-1.5 text-xs text-rose-200 hover:bg-accent-rose/25 disabled:opacity-50"
                        >
                          {deleting ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                          ) : (
                            <Trash2 className="h-3.5 w-3.5" aria-hidden />
                          )}
                          Delete
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmId(null)}
                          disabled={deleting}
                          className="focusable rounded-lg border border-white/15 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/10 disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmId(p.id)}
                        className="focusable shrink-0 rounded-lg border border-white/10 p-2 text-slate-500 opacity-0 transition-all hover:border-accent-rose/40 hover:text-rose-300 group-hover:opacity-100"
                        aria-label={`Delete ${p.name}`}
                        title="Delete persona"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      <EthicalNotice variant="fixed" />

      {/* Identity resolution overlay (§8) */}
      {resolution && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-space-900/70 px-4 py-10 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Select a person"
          onClick={() => setResolution(null)}
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className="glass-panel relative w-full max-w-2xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setResolution(null)}
              className="focusable absolute right-4 top-4 rounded-lg border border-white/10 p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
              aria-label="Close"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>

            <h2 className="flex items-center gap-2 font-display text-xl font-bold text-white">
              <Users className="h-5 w-5 text-accent-violet" aria-hidden />
              Who are you looking for?
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {resolution.note ||
                `Several public figures match “${resolution.query}”. Pick the right one before we gather sources.`}
            </p>

            <ul className="mt-5 space-y-2">
              {resolution.candidates.map((c, i) => (
                <li key={`${c.name}-${i}`}>
                  <button
                    type="button"
                    onClick={() => chooseCandidate(c)}
                    disabled={creating}
                    className="focusable group flex w-full items-center gap-4 rounded-xl border border-white/8 bg-white/[0.02] p-3 text-left transition-all hover:border-indigoGlow-400/40 hover:bg-white/[0.05] disabled:opacity-50"
                  >
                    <PersonaImage
                      name={c.name}
                      portraitUrl={c.portrait_url}
                      size={48}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-display text-base text-white">
                          {c.name}
                        </span>
                        {(c.birth_year || c.death_year) && (
                          <span className="text-[11px] text-slate-500">
                            {c.birth_year ?? "?"}
                            {c.death_year ? `–${c.death_year}` : ""}
                          </span>
                        )}
                      </div>
                      {c.description && (
                        <p className="text-xs font-medium text-indigoGlow-300">
                          {c.description}
                        </p>
                      )}
                      {c.summary && (
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-400">
                          {c.summary}
                        </p>
                      )}
                    </div>
                    <ArrowRight
                      className="h-4 w-4 shrink-0 text-slate-500 transition-transform group-hover:translate-x-1 group-hover:text-white"
                      aria-hidden
                    />
                  </button>
                </li>
              ))}
            </ul>

            <div className="mt-5 flex items-center justify-between border-t border-white/5 pt-4">
              <p className="text-[11px] text-slate-500">
                None of these? Use the exact name and create directly.
              </p>
              <button
                type="button"
                onClick={() => {
                  setResolution(null);
                  startCreate(resolution.query, false);
                }}
                disabled={creating}
                className="focusable inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/10 disabled:opacity-50"
              >
                <Wand2 className="h-3.5 w-3.5" aria-hidden />
                Create “{resolution.query}”
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </main>
  );
}

export default function ExplorePage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-indigoGlow-400" />
        </main>
      }
    >
      <ExploreInner />
    </Suspense>
  );
}
