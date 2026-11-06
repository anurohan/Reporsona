"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Clock,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Info,
  Loader2,
  Lock,
  Mic,
  Plus,
  Search,
  Unlock,
  UploadCloud,
  Video,
} from "lucide-react";
import { addTextSource, ApiError, getSources, uploadSourceFile } from "@/lib/api";
import type { SourceOut, SourceType } from "@/lib/types";
import { useToast } from "@/components/ui/Toast";

const UPLOAD_ACCEPT =
  ".txt,.md,.pdf,.png,.jpg,.jpeg,.mp3,.wav,.m4a,.mp4";

const TEXT_TYPES: { value: string; label: string }[] = [
  { value: "article", label: "Article" },
  { value: "document", label: "Document" },
  { value: "transcript", label: "Transcript" },
  { value: "note", label: "Note" },
];

type Tab = {
  key: "all" | SourceType;
  label: string;
};

const TABS: Tab[] = [
  { key: "all", label: "All" },
  { key: "video", label: "Videos" },
  { key: "audio", label: "Audio" },
  { key: "article", label: "Articles" },
  { key: "document", label: "Documents" },
  { key: "image", label: "Images" },
];

function typeIcon(type: SourceType) {
  const cls = "h-4 w-4";
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

function formatDuration(seconds: number): string | null {
  if (!seconds) return null;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function StatusPill({ status }: { status: string }) {
  if (!status) return null;
  const map: Record<string, string> = {
    completed: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
    processing: "border-indigoGlow-400/40 bg-indigoGlow-600/10 text-indigoGlow-400",
    pending: "border-white/15 bg-white/5 text-slate-400",
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

function AddSourcePanel({
  personaId,
  onAdded,
}: {
  personaId: string;
  onAdded: () => void;
}) {
  const { toast } = useToast();
  const [mode, setMode] = useState<"text" | "file">("text");

  // Paste-text state
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [sourceType, setSourceType] = useState<string>("article");

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [fileTitle, setFileTitle] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [submitting, setSubmitting] = useState(false);

  const reportResult = (
    extraction: string,
    chunks: number,
    note?: string
  ) => {
    toast({
      variant: "success",
      title: "Source added",
      description: `${chunks} chunk${chunks === 1 ? "" : "s"} added via ${extraction}.${
        note ? ` ${note}` : ""
      }`,
    });
  };

  const reportError = (err: unknown, fallback: string) => {
    toast({
      variant: "error",
      title: "Could not add source",
      description: err instanceof ApiError ? err.message : fallback,
    });
  };

  const submitText = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || submitting) return;
    setSubmitting(true);
    try {
      const res = await addTextSource(personaId, {
        title: title.trim() || undefined,
        text,
        source_type: sourceType,
      });
      reportResult(res.extraction, res.chunks_added, res.note);
      setTitle("");
      setText("");
      onAdded();
    } catch (err) {
      reportError(err, "The text could not be ingested. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || submitting) return;
    setSubmitting(true);
    try {
      const res = await uploadSourceFile(
        personaId,
        file,
        fileTitle.trim() || undefined
      );
      reportResult(res.extraction, res.chunks_added, res.note);
      setFile(null);
      setFileTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      onAdded();
    } catch (err) {
      reportError(
        err,
        "The file could not be processed. It may be an unsupported type or too large."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.section
      id="add-source-panel"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      className="glass-panel mt-5 overflow-hidden p-5"
      aria-label="Add a source"
    >
      {/* Mode tabs */}
      <div
        className="mb-4 inline-flex rounded-xl border border-white/10 bg-white/[0.03] p-1"
        role="tablist"
        aria-label="Add source method"
      >
        {(
          [
            { key: "text", label: "Paste text" },
            { key: "file", label: "Upload file" },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={mode === t.key}
            onClick={() => setMode(t.key)}
            className={`focusable rounded-lg px-4 py-1.5 text-sm transition-colors ${
              mode === t.key
                ? "bg-indigoGlow-600/25 text-white"
                : "text-slate-300 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {mode === "text" ? (
        <form onSubmit={submitText} className="space-y-3">
          <div>
            <label
              htmlFor="add-text-title"
              className="mb-1 block text-xs uppercase tracking-wider text-slate-400"
            >
              Title
            </label>
            <input
              id="add-text-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Optional title for this source"
              className="focusable w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500"
            />
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1">
              <label
                htmlFor="add-text-type"
                className="mb-1 block text-xs uppercase tracking-wider text-slate-400"
              >
                Source type
              </label>
              <select
                id="add-text-type"
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="focusable w-full rounded-xl border border-white/10 bg-void-900 px-3 py-2.5 text-sm text-white"
              >
                {TEXT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label
              htmlFor="add-text-body"
              className="mb-1 block text-xs uppercase tracking-wider text-slate-400"
            >
              Text
            </label>
            <textarea
              id="add-text-body"
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
              rows={6}
              placeholder="Paste the passage, transcript, or article text here…"
              className="focusable scroll-slim w-full resize-y rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500"
            />
          </div>
          <button
            type="submit"
            disabled={!text.trim() || submitting}
            className="focusable inline-flex items-center gap-2 rounded-xl border border-indigoGlow-400/40 bg-indigoGlow-600/20 px-4 py-2 text-sm text-white transition-colors hover:bg-indigoGlow-600/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Plus className="h-4 w-4" aria-hidden />
            )}
            Add text source
          </button>
        </form>
      ) : (
        <form onSubmit={submitFile} className="space-y-3">
          <div>
            <label
              htmlFor="add-file-title"
              className="mb-1 block text-xs uppercase tracking-wider text-slate-400"
            >
              Title
            </label>
            <input
              id="add-file-title"
              value={fileTitle}
              onChange={(e) => setFileTitle(e.target.value)}
              placeholder="Optional — defaults to the file name"
              className="focusable w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-white placeholder:text-slate-500"
            />
          </div>
          <div>
            <label
              htmlFor="add-file-input"
              className="mb-1 block text-xs uppercase tracking-wider text-slate-400"
            >
              File
            </label>
            <input
              id="add-file-input"
              ref={fileInputRef}
              type="file"
              accept={UPLOAD_ACCEPT}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="focusable block w-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-indigoGlow-600/25 file:px-3 file:py-1.5 file:text-sm file:text-white hover:file:bg-indigoGlow-600/35"
            />
            {file && (
              <p className="mt-1 text-xs text-slate-500">
                Selected: {file.name}
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={!file || submitting}
            className="focusable inline-flex items-center gap-2 rounded-xl border border-indigoGlow-400/40 bg-indigoGlow-600/20 px-4 py-2 text-sm text-white transition-colors hover:bg-indigoGlow-600/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <UploadCloud className="h-4 w-4" aria-hidden />
            )}
            Upload &amp; process
          </button>
        </form>
      )}

      <p className="mt-4 flex items-start gap-2 text-[11px] leading-relaxed text-slate-500">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-amber/80" aria-hidden />
        Plain text and Markdown are always supported. PDF, image (OCR), and
        audio/video (transcription) require optional backend dependencies — if
        they&apos;re missing, the upload returns a clear message explaining
        what to install.
      </p>
    </motion.section>
  );
}

export default function SourcesPage() {
  const params = useParams();
  const personaId = String(params.personaId || "");

  const [sources, setSources] = useState<SourceOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab["key"]>("all");
  const [query, setQuery] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const load = () => {
    setError(null);
    setSources(null);
    getSources(personaId, tab === "all" ? undefined : tab)
      .then(setSources)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Could not load sources."
        )
      );
  };

  // Silent refresh that keeps the current list visible (used after adding).
  const refresh = () => {
    getSources(personaId, tab === "all" ? undefined : tab)
      .then(setSources)
      .catch(() => {
        /* keep existing list; a toast already reported the add result */
      });
  };

  useEffect(() => {
    if (personaId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId, tab]);

  const filtered = useMemo(() => {
    if (!sources) return [];
    const q = query.trim().toLowerCase();
    if (!q) return sources;
    return sources.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.author.toLowerCase().includes(q) ||
        s.provider.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q)
    );
  }, [sources, query]);

  return (
    <main className="min-h-screen bg-space-gradient px-5 pb-16 pt-8">
      <div className="mx-auto max-w-4xl">
        <Link
          href={`/persona/${personaId}`}
          className="focusable mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Profile
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl font-bold text-white">
              Sources
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              The material this persona was reconstructed from.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowAdd((v) => !v)}
            aria-expanded={showAdd}
            aria-controls="add-source-panel"
            className="focusable inline-flex items-center gap-2 rounded-xl border border-indigoGlow-400/40 bg-indigoGlow-600/15 px-4 py-2 text-sm text-white transition-colors hover:bg-indigoGlow-600/25"
          >
            <Plus className="h-4 w-4" aria-hidden />
            Add source
          </button>
        </div>

        {showAdd && (
          <AddSourcePanel
            personaId={personaId}
            onAdded={() => {
              refresh();
            }}
          />
        )}

        {/* Tabs */}
        <div
          className="mt-6 flex flex-wrap gap-2"
          role="tablist"
          aria-label="Source type"
        >
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`focusable rounded-full border px-4 py-1.5 text-sm transition-colors ${
                tab === t.key
                  ? "border-indigoGlow-400/60 bg-indigoGlow-600/15 text-white"
                  : "border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.07]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Filter */}
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3">
          <Search className="h-4 w-4 shrink-0 text-slate-500" aria-hidden />
          <label htmlFor="source-filter" className="sr-only">
            Filter sources
          </label>
          <input
            id="source-filter"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by title, author or provider…"
            className="focusable w-full bg-transparent py-2.5 text-sm text-white placeholder:text-slate-500"
          />
        </div>

        {/* States */}
        {error && (
          <div className="glass-panel mt-6 flex items-center justify-between px-4 py-3 text-sm text-rose-200">
            <span className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> {error}
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

        {!error && sources === null && (
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="glass-panel h-32 p-4">
                <div className="h-full w-full rounded-lg shimmer" />
              </div>
            ))}
          </div>
        )}

        {!error && sources && filtered.length === 0 && (
          <div className="glass-panel mt-6 px-4 py-10 text-center text-sm text-slate-400">
            {query
              ? "No sources match your filter."
              : "No sources of this type were found for this persona."}
          </div>
        )}

        {/* Grid */}
        {!error && filtered.length > 0 && (
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {filtered.map((s, i) => {
              const duration = formatDuration(s.duration_seconds);
              return (
                <motion.article
                  key={s.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i * 0.03, 0.3) }}
                  className="glass-panel flex flex-col p-4"
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2 text-accent-violet">
                      {typeIcon(s.source_type)}
                      <span className="truncate text-sm font-medium text-white">
                        {s.title || "Untitled"}
                      </span>
                    </div>
                    {s.url && (
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="focusable shrink-0 text-slate-400 hover:text-white"
                        aria-label={`Open source: ${s.title}`}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </div>

                  {s.description && (
                    <p className="mb-3 line-clamp-2 text-xs text-slate-400">
                      {s.description}
                    </p>
                  )}

                  <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                    <span className="uppercase tracking-wider">
                      {s.source_type}
                    </span>
                    {s.author && <span>· {s.author}</span>}
                    {s.publication_date && <span>· {s.publication_date}</span>}
                    {s.provider && <span>· {s.provider}</span>}
                    {duration && (
                      <span className="inline-flex items-center gap-1">
                        · <Clock className="h-3 w-3" /> {duration}
                      </span>
                    )}
                  </div>

                  <div className="mt-2 flex items-center gap-2">
                    <StatusPill status={s.processing_status} />
                    {s.access_type && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-slate-500">
                        {s.access_type.toLowerCase().includes("open") ? (
                          <Unlock className="h-3 w-3" />
                        ) : (
                          <Lock className="h-3 w-3" />
                        )}
                        {s.access_type}
                      </span>
                    )}
                  </div>
                </motion.article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
