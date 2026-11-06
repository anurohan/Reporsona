"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Keyboard, X } from "lucide-react";

const SHORTCUTS: { keys: string[]; label: string }[] = [
  { keys: ["⌘", "K"], label: "Open command palette" },
  { keys: ["Ctrl", "K"], label: "Open command palette (Windows/Linux)" },
  { keys: ["?"], label: "Show this shortcuts help" },
  { keys: ["Esc"], label: "Close dialogs" },
  { keys: ["↑", "↓"], label: "Move highlight in lists" },
  { keys: ["↵"], label: "Select highlighted item" },
];

/**
 * A subtle "⌘K to search" affordance plus a `?`-triggered shortcuts modal.
 * The `?` listener ignores keypresses while typing in inputs/textareas.
 */
export default function ShortcutsHint() {
  const reduce = useReducedMotion();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        return;
      }
      const target = e.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (!typing && e.key === "?") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Keyboard shortcuts"
        className="focusable fixed bottom-16 right-4 z-40 hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-[11px] text-slate-400 backdrop-blur-md transition-colors hover:text-white sm:inline-flex"
      >
        <Keyboard className="h-3.5 w-3.5" aria-hidden />
        <span className="chip border-0 bg-transparent px-0 py-0">⌘K</span>
        to search
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-[65] flex items-center justify-center px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduce ? 0 : 0.15 }}
            role="presentation"
            onMouseDown={(e) => {
              if (e.target === e.currentTarget) setOpen(false);
            }}
          >
            <div
              className="absolute inset-0 bg-void-950/60 backdrop-blur-sm"
              aria-hidden
            />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Keyboard shortcuts"
              initial={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.97 }}
              animate={reduce ? { opacity: 1 } : { opacity: 1, scale: 1 }}
              exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.97 }}
              transition={{ duration: reduce ? 0 : 0.18 }}
              className="glass-strong relative z-10 w-full max-w-sm rounded-2xl p-5"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="flex items-center gap-2 font-display text-sm uppercase tracking-wider text-slate-200">
                  <Keyboard className="h-4 w-4 text-accent-violet" aria-hidden />
                  Keyboard shortcuts
                </h2>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Close shortcuts"
                  className="focusable rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-white"
                >
                  <X className="h-4 w-4" aria-hidden />
                </button>
              </div>
              <ul className="space-y-2.5">
                {SHORTCUTS.map((s) => (
                  <li
                    key={s.label}
                    className="flex items-center justify-between gap-4 text-sm text-slate-300"
                  >
                    <span>{s.label}</span>
                    <span className="flex shrink-0 items-center gap-1">
                      {s.keys.map((k) => (
                        <kbd
                          key={k}
                          className="rounded-md border border-white/15 bg-white/[0.06] px-2 py-0.5 font-sans text-[11px] text-slate-200"
                        >
                          {k}
                        </kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
