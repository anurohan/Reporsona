"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Compass,
  Home,
  Loader2,
  PlusCircle,
  Search,
  User,
} from "lucide-react";
import { listPersonas } from "@/lib/api";
import type { PersonaSummary } from "@/lib/types";

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: React.ReactNode;
  run: () => void;
}

/**
 * Global command palette. Opens on Cmd/Ctrl+K, closes on Esc.
 * Fuzzy/substring search over quick navigation + all personas.
 */
export default function CommandPalette() {
  const router = useRouter();
  const reduce = useReducedMotion();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [personas, setPersonas] = useState<PersonaSummary[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setActive(0);
  }, []);

  // Global open shortcut.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // On open: remember focus, fetch personas, focus input.
  useEffect(() => {
    if (!open) return;
    restoreFocusRef.current = document.activeElement as HTMLElement | null;
    // Focus after paint.
    const raf = requestAnimationFrame(() => inputRef.current?.focus());

    if (personas === null && !loading) {
      setLoading(true);
      setLoadError(null);
      listPersonas()
        .then((data) => setPersonas(data))
        .catch(() =>
          setLoadError("Could not load personas. Navigation still works.")
        )
        .finally(() => setLoading(false));
    }
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Restore focus on close.
  useEffect(() => {
    if (open) return;
    restoreFocusRef.current?.focus?.();
  }, [open]);

  const navigate = useCallback(
    (href: string) => {
      close();
      router.push(href);
    },
    [close, router]
  );

  const commands = useMemo<Command[]>(() => {
    const base: Command[] = [
      {
        id: "nav-home",
        label: "Home",
        hint: "Landing",
        icon: <Home className="h-4 w-4" aria-hidden />,
        run: () => navigate("/"),
      },
      {
        id: "nav-explore",
        label: "Explore",
        hint: "Browse personas",
        icon: <Compass className="h-4 w-4" aria-hidden />,
        run: () => navigate("/explore"),
      },
      {
        id: "action-create",
        label: "Create new persona",
        hint: "Start a build",
        icon: <PlusCircle className="h-4 w-4" aria-hidden />,
        run: () => navigate("/explore"),
      },
    ];

    const personaCmds: Command[] = (personas || []).map((p) => ({
      id: `persona-${p.id}`,
      label: p.name,
      hint:
        p.status === "ready"
          ? p.known_for?.[0] || "Persona"
          : `${p.status}…`,
      icon: <User className="h-4 w-4" aria-hidden />,
      run: () => navigate(`/persona/${p.id}`),
    }));

    return [...base, ...personaCmds];
  }, [personas, navigate]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => {
      const hay = `${c.label} ${c.hint ?? ""}`.toLowerCase();
      // substring match, plus a loose subsequence (fuzzy) fallback
      if (hay.includes(q)) return true;
      let qi = 0;
      for (let i = 0; i < hay.length && qi < q.length; i++) {
        if (hay[i] === q[qi]) qi++;
      }
      return qi === q.length;
    });
  }, [commands, query]);

  // Keep highlight in range as results change.
  useEffect(() => {
    setActive((a) => (results.length === 0 ? 0 : Math.min(a, results.length - 1)));
  }, [results.length]);

  // Scroll active item into view.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(
      `[data-index="${active}"]`
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (results.length ? (a + 1) % results.length : 0));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) =>
        results.length ? (a - 1 + results.length) % results.length : 0
      );
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      results[active]?.run();
      return;
    }
    if (e.key === "Tab") {
      // Simple focus trap: keep focus on the input.
      e.preventDefault();
      inputRef.current?.focus();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-start justify-center px-4 pt-[12vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0 : 0.15 }}
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) close();
          }}
        >
          <div
            className="absolute inset-0 bg-void-950/60 backdrop-blur-sm"
            aria-hidden
          />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={reduce ? { opacity: 0 } : { opacity: 0, y: -12, scale: 0.98 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: reduce ? 0 : 0.18, ease: "easeOut" }}
            onKeyDown={onKeyDown}
            className="glass-strong relative z-10 w-full max-w-xl overflow-hidden rounded-2xl shadow-[0_20px_80px_-20px_rgba(0,0,0,0.8)]"
          >
            <div className="flex items-center gap-3 border-b border-white/10 px-4">
              <Search className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
              <label htmlFor="command-input" className="sr-only">
                Search commands and personas
              </label>
              <input
                id="command-input"
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(0);
                }}
                placeholder="Search personas, or jump to a page…"
                autoComplete="off"
                spellCheck={false}
                aria-controls="command-results"
                aria-activedescendant={
                  results[active] ? `cmd-${results[active].id}` : undefined
                }
                className="w-full bg-transparent py-4 text-sm text-white outline-none placeholder:text-slate-500"
              />
              {loading && (
                <Loader2
                  className="h-4 w-4 shrink-0 animate-spin text-slate-500"
                  aria-hidden
                />
              )}
            </div>

            <ul
              ref={listRef}
              id="command-results"
              role="listbox"
              aria-label="Results"
              className="scroll-slim max-h-80 overflow-y-auto p-2"
            >
              {loadError && (
                <li className="px-3 py-2 text-xs text-accent-amber">
                  {loadError}
                </li>
              )}
              {results.length === 0 ? (
                <li className="px-3 py-8 text-center text-sm text-slate-500">
                  No matches for “{query}”.
                </li>
              ) : (
                results.map((c, i) => {
                  const selected = i === active;
                  return (
                    <li key={c.id} role="presentation">
                      <button
                        type="button"
                        id={`cmd-${c.id}`}
                        data-index={i}
                        role="option"
                        aria-selected={selected}
                        onMouseMove={() => setActive(i)}
                        onClick={() => c.run()}
                        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                          selected
                            ? "bg-indigoGlow-600/20 text-white"
                            : "text-slate-300 hover:bg-white/[0.05]"
                        }`}
                      >
                        <span
                          className={
                            selected ? "text-accent-cyan" : "text-slate-500"
                          }
                        >
                          {c.icon}
                        </span>
                        <span className="min-w-0 flex-1 truncate">
                          {c.label}
                        </span>
                        {c.hint && (
                          <span className="shrink-0 text-[11px] text-slate-500">
                            {c.hint}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })
              )}
            </ul>

            <div className="flex items-center justify-between border-t border-white/10 px-4 py-2 text-[11px] text-slate-500">
              <span>↑↓ to navigate · ↵ to select · esc to close</span>
              <span className="chip">⌘K</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
