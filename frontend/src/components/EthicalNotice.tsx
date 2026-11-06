"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { getEthicalNotice } from "@/lib/api";

const FALLBACK =
  "RePersona generates an AI simulation based on publicly available and processed historical material. It does not represent the consciousness, identity, or literal communication of the original person.";

interface EthicalNoticeProps {
  variant?: "footer" | "fixed" | "inline";
  className?: string;
}

/**
 * Subtle ethical disclosure. Pulls the canonical notice from the backend and
 * falls back to a bundled copy if the request fails.
 */
export default function EthicalNotice({
  variant = "footer",
  className = "",
}: EthicalNoticeProps) {
  const [notice, setNotice] = useState<string>(FALLBACK);

  useEffect(() => {
    let active = true;
    getEthicalNotice()
      .then((res) => {
        if (active && res?.notice) setNotice(res.notice);
      })
      .catch(() => {
        /* keep fallback */
      });
    return () => {
      active = false;
    };
  }, []);

  const base =
    "flex items-start gap-2 text-[11px] leading-relaxed text-slate-400";

  if (variant === "fixed") {
    return (
      <aside
        role="note"
        aria-label="Ethical notice"
        className={`fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-void-950/70 px-4 py-3 backdrop-blur-md ${className}`}
      >
        <div className={`mx-auto max-w-3xl ${base}`}>
          <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-amber/80" aria-hidden />
          <p>{notice}</p>
        </div>
      </aside>
    );
  }

  if (variant === "inline") {
    return (
      <div
        role="note"
        aria-label="Ethical notice"
        className={`glass-panel px-4 py-3 ${base} ${className}`}
      >
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-amber/80" aria-hidden />
        <p>{notice}</p>
      </div>
    );
  }

  return (
    <footer
      role="contentinfo"
      className={`mx-auto max-w-3xl px-4 py-6 ${className}`}
    >
      <div className={base}>
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-amber/80" aria-hidden />
        <p>{notice}</p>
      </div>
    </footer>
  );
}
