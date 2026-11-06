"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  ChevronDown,
  Circle,
  ExternalLink,
  MinusCircle,
} from "lucide-react";
import { getProviders, getSources } from "@/lib/api";
import type { ProviderStatus, SourceOut } from "@/lib/types";

interface SourceActivityProps {
  personaId: string;
  done: boolean;
}

// Display groups mapped to the real `SourceOut.provider` strings the backend
// emits, plus which provider-status key gates their availability.
const GROUPS: {
  id: string;
  label: string;
  providerNames: string[];
  /** Provider-status key that must be configured, or null if always-on. */
  gateKey: string | null;
}[] = [
  { id: "wikipedia", label: "Wikipedia", providerNames: ["Wikipedia"], gateKey: null },
  { id: "wikiquote", label: "Wikiquote", providerNames: ["Wikiquote"], gateKey: null },
  {
    id: "web",
    label: "Web search",
    providerNames: ["Tavily", "SerpAPI"],
    gateKey: "web_search",
  },
  { id: "youtube", label: "YouTube", providerNames: ["YouTube"], gateKey: "youtube" },
];

type GroupState = "found" | "empty" | "not_configured" | "unknown";

/**
 * "Source activity" panel. Combines the real provider configuration
 * (`GET /api/providers`) with the actually-discovered sources
 * (`GET /api/personas/{id}/sources`). Never shows fake success: unconfigured
 * optional providers render "Not configured"; configured-but-empty renders
 * "No sources". Rows with real sources expand to show their metadata.
 */
export default function SourceActivity({ personaId, done }: SourceActivityProps) {
  const [providers, setProviders] = useState<ProviderStatus[] | null>(null);
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const doneRef = useRef(done);
  doneRef.current = done;

  // Provider configuration — fetched once.
  useEffect(() => {
    let active = true;
    getProviders()
      .then((p) => active && setProviders(p))
      .catch(() => active && setProviders([]));
    return () => {
      active = false;
    };
  }, []);

  // Discovered sources — poll while building, then a final fetch on completion.
  useEffect(() => {
    if (!personaId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const rows = await getSources(personaId);
        if (active) setSources(rows);
      } catch {
        /* transient — keep last known */
      }
      if (active && !doneRef.current) timer = setTimeout(tick, 3000);
    };
    void tick();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [personaId]);

  // Re-fetch once more when the job finishes so counts are final.
  useEffect(() => {
    if (!done || !personaId) return;
    let active = true;
    getSources(personaId)
      .then((rows) => active && setSources(rows))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [done, personaId]);

  const configuredMap = useMemo(() => {
    const m = new Map<string, boolean>();
    (providers || []).forEach((p) => m.set(p.key, p.configured));
    return m;
  }, [providers]);

  const rows = useMemo(() => {
    return GROUPS.map((g) => {
      const matched = sources.filter((s) =>
        g.providerNames.some(
          (n) => (s.provider || "").toLowerCase() === n.toLowerCase()
        )
      );
      let state: GroupState;
      if (matched.length > 0) state = "found";
      else if (g.gateKey === null) state = "empty"; // always-on but nothing yet
      else if (providers === null) state = "unknown";
      else state = configuredMap.get(g.gateKey) ? "empty" : "not_configured";
      return { ...g, matched, state };
    });
  }, [sources, providers, configuredMap]);

  return (
    <div>
      <h2 className="mb-3 text-[11px] uppercase tracking-[0.24em] text-slate-400">
        Source activity
      </h2>
      <ul className="space-y-1.5">
        {rows.map((r) => {
          const expandable = r.matched.length > 0;
          const isOpen = open === r.id;
          return (
            <li
              key={r.id}
              className="overflow-hidden rounded-lg border border-white/5 bg-white/[0.02]"
            >
              <button
                type="button"
                disabled={!expandable}
                onClick={() => expandable && setOpen(isOpen ? null : r.id)}
                aria-expanded={expandable ? isOpen : undefined}
                className={`focusable flex w-full items-center gap-2.5 px-2.5 py-2 text-left ${
                  expandable ? "hover:bg-white/[0.03]" : "cursor-default"
                }`}
              >
                {r.state === "found" ? (
                  <Check className="h-3.5 w-3.5 shrink-0 text-emerald-400" aria-hidden />
                ) : r.state === "not_configured" ? (
                  <MinusCircle className="h-3.5 w-3.5 shrink-0 text-slate-600" aria-hidden />
                ) : (
                  <Circle className="h-3.5 w-3.5 shrink-0 text-slate-600" aria-hidden />
                )}
                <span
                  className={`flex-1 text-sm ${
                    r.state === "found" ? "text-slate-200" : "text-slate-400"
                  }`}
                >
                  {r.label}
                </span>
                <span
                  className={`text-[11px] ${
                    r.state === "found"
                      ? "text-emerald-300"
                      : r.state === "not_configured"
                      ? "text-slate-500"
                      : "text-slate-500"
                  }`}
                >
                  {r.state === "found"
                    ? `${r.matched.length} source${r.matched.length === 1 ? "" : "s"}`
                    : r.state === "not_configured"
                    ? "Not configured"
                    : r.state === "unknown"
                    ? "—"
                    : "No sources"}
                </span>
                {expandable && (
                  <ChevronDown
                    className={`h-3.5 w-3.5 shrink-0 text-slate-500 transition-transform ${
                      isOpen ? "rotate-180" : ""
                    }`}
                    aria-hidden
                  />
                )}
              </button>

              <AnimatePresence initial={false}>
                {isOpen && expandable && (
                  <motion.ul
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden border-t border-white/5"
                  >
                    {r.matched.map((s) => (
                      <li key={s.id}>
                        <a
                          href={s.url || undefined}
                          target="_blank"
                          rel="noreferrer"
                          className={`focusable flex items-center gap-2 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 ${
                            s.url ? "" : "pointer-events-none"
                          }`}
                        >
                          <span className="truncate">{s.title || "Untitled source"}</span>
                          {s.url && (
                            <ExternalLink className="h-3 w-3 shrink-0 opacity-60" aria-hidden />
                          )}
                        </a>
                      </li>
                    ))}
                  </motion.ul>
                )}
              </AnimatePresence>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
