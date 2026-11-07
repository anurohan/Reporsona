"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUpRight, Command, Orbit } from "lucide-react";

interface AppHeaderProps {
  compact?: boolean;
}

export default function AppHeader({ compact = false }: AppHeaderProps) {
  return (
    <header className="app-header">
      <Link href="/" className="brand-mark focusable" aria-label="RePersona home">
        <span className="brand-mark__icon" aria-hidden>
          <Orbit className="h-4 w-4" strokeWidth={1.8} />
        </span>
        <span className="brand-mark__text">
          <span>RE</span>PERSONA
        </span>
      </Link>

      {!compact && (
        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary navigation">
          <Link className="header-link focusable" href="/explore">Explore archive</Link>
          <Link className="header-link focusable" href="/settings">System status</Link>
        </nav>
      )}

      <div className="ml-auto flex items-center gap-2">
        <span className="status-dot hidden sm:inline-flex"><i /> Local intelligence online</span>
        <button
          type="button"
          className="command-pill focusable"
          onClick={() => window.dispatchEvent(new Event("open-command-palette"))}
          aria-label="Open command palette"
        >
          <Command className="h-3.5 w-3.5" />
          <span className="hidden lg:inline">Commands</span>
          <kbd>⌘K</kbd>
        </button>
        <Link href="/explore" className="header-cta focusable">
          Open archive <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </header>
  );
}

export function Reveal({ children, delay = 0, className = "" }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.65, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
