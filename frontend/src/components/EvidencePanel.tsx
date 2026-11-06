"use client";

import {
  BookOpen,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Info,
  Mic,
  Video,
} from "lucide-react";
import type {
  Evidence,
  EvidenceCoverage,
  SourceType,
} from "@/lib/types";

interface EvidencePanelProps {
  evidence: Evidence[];
  coverage: EvidenceCoverage | null;
  limitations: string[];
  hasAsked: boolean;
}

function typeIcon(type: SourceType) {
  const cls = "h-3.5 w-3.5";
  switch (type) {
    case "video":
      return <Video className={cls} aria-hidden />;
    case "audio":
      return <Mic className={cls} aria-hidden />;
    case "article":
      return <BookOpen className={cls} aria-hidden />;
    case "image":
      return <ImageIcon className={cls} aria-hidden />;
    default:
      return <FileText className={cls} aria-hidden />;
  }
}

const COVERAGE_STYLES: Record<EvidenceCoverage, string> = {
  HIGH: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
  MEDIUM: "border-accent-amber/40 bg-accent-amber/10 text-amber-200",
  LOW: "border-accent-rose/40 bg-accent-rose/10 text-rose-200",
};

function formatTimestamp(seconds?: number | null): string | null {
  if (seconds === null || seconds === undefined) return null;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function EvidencePanel({
  evidence,
  coverage,
  limitations,
  hasAsked,
}: EvidencePanelProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <h2 className="font-display text-sm text-white">Evidence</h2>
        {coverage && (
          <span
            className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide ${COVERAGE_STYLES[coverage]}`}
          >
            {coverage} coverage
          </span>
        )}
      </div>

      <div className="scroll-slim flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {!hasAsked && (
          <div className="flex h-full flex-col items-center justify-center px-2 text-center">
            <Info className="mb-2 h-5 w-5 text-slate-600" aria-hidden />
            <p className="text-sm text-slate-500">
              Citations appear here after you ask a question. Each answer is
              backed by the sources it drew from.
            </p>
          </div>
        )}

        {hasAsked && evidence.length === 0 && (
          <div className="glass-panel px-4 py-4 text-sm text-slate-400">
            No direct source passages were matched for the last answer. Treat
            it as low-confidence.
          </div>
        )}

        {evidence.map((ev, i) => {
          const ts = formatTimestamp(ev.timestamp);
          const relevance = Math.round(
            Math.min(1, Math.max(0, ev.relevance)) * 100
          );
          return (
            <article
              key={ev.chunk_id || i}
              className="glass-panel overflow-hidden p-4"
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2 text-slate-300">
                  <span className="text-accent-violet">
                    {typeIcon(ev.source_type)}
                  </span>
                  <span className="truncate text-sm font-medium text-white">
                    {ev.source_title || "Untitled source"}
                  </span>
                </div>
                {ev.url && (
                  <a
                    href={ev.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="focusable shrink-0 text-slate-400 hover:text-white"
                    aria-label={`Open source: ${ev.source_title}`}
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>

              <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                <span className="uppercase tracking-wider">
                  {ev.source_type}
                </span>
                {ev.publication_date && <span>· {ev.publication_date}</span>}
                {ts && <span>· {ts}</span>}
                {ev.page != null && <span>· p.{ev.page}</span>}
              </div>

              <p className="mb-3 text-sm leading-relaxed text-slate-300">
                “{ev.text}”
              </p>

              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigoGlow-500 to-accent-cyan"
                    style={{ width: `${relevance}%` }}
                  />
                </div>
                <span className="text-[11px] tabular-nums text-slate-500">
                  {relevance}%
                </span>
              </div>
            </article>
          );
        })}

        {limitations.length > 0 && (
          <div className="glass-panel border-accent-amber/20 p-4">
            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent-amber/90">
              <Info className="h-3.5 w-3.5" aria-hidden />
              Limitations
            </h3>
            <ul className="list-disc space-y-1 pl-4 text-xs text-slate-400">
              {limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
