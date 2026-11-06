"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  Circle,
  Loader2,
} from "lucide-react";
import type { JobStage } from "@/lib/types";

interface PipelineStagesProps {
  stages: JobStage[];
  progress: number;
  stats?: Record<string, any>;
  currentStage?: string;
}

// The canonical 15-stage pipeline, used as a scaffold before the first
// SNAPSHOT arrives so we never show an empty list.
const DEFAULT_STAGES: JobStage[] = [
  { key: "SOURCE_DISCOVERY", label: "Source discovery", status: "pending", detail: "" },
  { key: "SOURCE_VALIDATION", label: "Source validation", status: "pending", detail: "" },
  { key: "DOCUMENT_PROCESSING", label: "Document processing", status: "pending", detail: "" },
  { key: "AUDIO_PROCESSING", label: "Audio processing", status: "pending", detail: "" },
  { key: "TRANSCRIPTION", label: "Transcription", status: "pending", detail: "" },
  { key: "OCR_PROCESSING", label: "OCR processing", status: "pending", detail: "" },
  { key: "NLP_ANALYSIS", label: "NLP analysis", status: "pending", detail: "" },
  { key: "EMBEDDING", label: "Embedding", status: "pending", detail: "" },
  { key: "VECTOR_INDEXING", label: "Vector indexing", status: "pending", detail: "" },
  { key: "PERSONALITY_ANALYSIS", label: "Personality analysis", status: "pending", detail: "" },
  { key: "PERSONA_BUILDING", label: "Persona building", status: "pending", detail: "" },
  { key: "EVIDENCE_VALIDATION", label: "Evidence validation", status: "pending", detail: "" },
];

const STAT_FIELDS: { key: string; label: string; suffix?: string }[] = [
  { key: "sources", label: "Sources" },
  { key: "documents", label: "Documents" },
  { key: "audio_seconds", label: "Audio", suffix: "s" },
  { key: "transcripts", label: "Transcripts" },
  { key: "ocr_pages", label: "OCR pages" },
  { key: "chunks", label: "Chunks" },
  { key: "embeddings", label: "Embeddings" },
  { key: "topics", label: "Topics" },
];

function StageIcon({ status }: { status: string }) {
  if (status === "completed")
    return <Check className="h-4 w-4 text-accent-cyan" aria-hidden />;
  if (status === "processing")
    return (
      <Loader2 className="h-4 w-4 animate-spin text-indigoGlow-400" aria-hidden />
    );
  if (status === "failed")
    return <AlertTriangle className="h-4 w-4 text-accent-rose" aria-hidden />;
  return <Circle className="h-4 w-4 text-slate-600" aria-hidden />;
}

function formatStatValue(key: string, value: any): string {
  if (value === null || value === undefined) return "0";
  if (key === "audio_seconds" && typeof value === "number") {
    return value >= 60 ? `${Math.round(value / 60)}m` : `${Math.round(value)}`;
  }
  if (typeof value === "number") return Math.round(value).toLocaleString();
  return String(value);
}

export default function PipelineStages({
  stages,
  progress,
  stats = {},
  currentStage,
}: PipelineStagesProps) {
  const list = stages && stages.length ? stages : DEFAULT_STAGES;
  const pct = Math.round(Math.min(1, Math.max(0, progress)) * 100);
  const embedder = stats?.embedder as string | undefined;

  return (
    <div className="w-full">
      {/* Progress header */}
      <div className="mb-5">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-xs uppercase tracking-[0.2em] text-slate-400">
            Reconstruction progress
          </span>
          <span
            className="font-display text-2xl tabular-nums text-white"
            aria-live="polite"
          >
            {pct}%
          </span>
        </div>
        <div
          className="h-2 overflow-hidden rounded-full bg-white/10"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-indigoGlow-500 to-accent-cyan"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ ease: "easeOut", duration: 0.5 }}
          />
        </div>
      </div>

      {/* Live stats */}
      <div className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {STAT_FIELDS.map((f) => (
          <div
            key={f.key}
            className="glass rounded-xl px-3 py-2 text-center"
          >
            <div className="font-display text-lg tabular-nums text-white">
              {formatStatValue(f.key, stats?.[f.key])}
              {f.suffix && stats?.[f.key] ? f.suffix : ""}
            </div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              {f.label}
            </div>
          </div>
        ))}
      </div>

      {embedder && (
        <p className="mb-4 text-center text-[11px] text-slate-500">
          Embedder: <span className="text-slate-300">{embedder}</span>
        </p>
      )}

      {/* Stage list */}
      <ol className="space-y-1.5" aria-label="Pipeline stages">
        {list.map((stage) => {
          const active =
            stage.status === "processing" || stage.key === currentStage;
          return (
            <li
              key={stage.key}
              className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
                active
                  ? "border-indigoGlow-400/40 bg-indigoGlow-600/10"
                  : "border-white/5 bg-white/[0.02]"
              }`}
            >
              <StageIcon status={stage.status} />
              <div className="min-w-0 flex-1">
                <div
                  className={`text-sm ${
                    stage.status === "completed"
                      ? "text-slate-300"
                      : active
                      ? "text-white"
                      : "text-slate-400"
                  }`}
                >
                  {stage.label}
                </div>
                {stage.detail && (
                  <div className="truncate text-xs text-slate-500">
                    {stage.detail}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
