"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  Brain,
  FileText,
  Loader2,
  MessageSquare,
  RefreshCw,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import {
  ApiError,
  addTextTranscript,
  deleteTranscript,
  getVirtualFriend,
  listTranscripts,
  reprocessTranscript,
  selectSpeaker,
  uploadTranscript,
} from "@/lib/api";
import type { VirtualFriendSummary, VFTranscript, TranscriptUploadResult } from "@/lib/types";
import AppHeader from "@/components/AppHeader";

const BackgroundScene = dynamic(
  () => import("@/components/three/BackgroundScene"),
  { ssr: false }
);

function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
    processing: "border-yellow-400/40 bg-yellow-400/10 text-yellow-200",
    building: "border-indigoGlow-400/40 bg-indigoGlow-600/10 text-indigoGlow-400",
    failed: "border-accent-rose/40 bg-accent-rose/10 text-rose-200",
  };
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${
        map[status] ?? map.ready
      }`}
    >
      {status}
    </span>
  );
}

// UploadModal ----------------------------------------------------------------
function UploadModal({
  friendId,
  onClose,
  onDone,
}: {
  friendId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [targetSpeaker, setTargetSpeaker] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscriptUploadResult | null>(null);
  const [speakerPicking, setSpeakerPicking] = useState(false);
  const [pickingLoading, setPickingLoading] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || uploading) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadTranscript(friendId, file, targetSpeaker || undefined);
      setResult(res);
      // If multiple speakers and no target chosen, prompt selection
      if (res.speakers.length > 1 && !res.target_speaker) {
        setSpeakerPicking(true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleSelectSpeaker = async (speaker: string) => {
    if (!result || pickingLoading) return;
    setPickingLoading(true);
    setError(null);
    try {
      await selectSpeaker(friendId, result.transcript_id, speaker);
      setSpeakerPicking(false);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not select speaker.");
    } finally {
      setPickingLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="glass-panel w-full max-w-lg p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-white">Upload Transcript</h2>
          <button
            type="button"
            onClick={onClose}
            className="focusable rounded-lg border border-white/10 p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {!result ? (
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-300">
                Chat export file <span className="text-accent-rose">*</span>
              </label>
              <div
                className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-white/20 bg-white/[0.02] p-6 text-center transition hover:border-indigoGlow-400/40 hover:bg-indigoGlow-600/[0.04]"
                onClick={() => fileRef.current?.click()}
              >
                <Upload className="h-8 w-8 text-slate-500" />
                <div>
                  <p className="text-sm text-slate-300">
                    {file ? file.name : "Click to select a file"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Accepts .txt, .json, .csv
                  </p>
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".txt,.json,.csv"
                  className="sr-only"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </div>
            </div>

            <div>
              <label htmlFor="target-speaker" className="mb-1.5 block text-xs font-medium text-slate-300">
                Target speaker{" "}
                <span className="text-slate-500">(optional)</span>
              </label>
              <input
                id="target-speaker"
                value={targetSpeaker}
                onChange={(e) => setTargetSpeaker(e.target.value)}
                placeholder="Leave blank to auto-detect most frequent speaker"
                className="focusable w-full rounded-xl border border-white/10 bg-white/[0.045] px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-indigoGlow-400/50"
              />
            </div>

            {error && (
              <p role="alert" className="rounded-lg border border-accent-rose/30 bg-accent-rose/10 px-3 py-2 text-sm text-rose-200">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="focusable flex-1 rounded-xl border border-white/10 bg-white/[0.05] py-2.5 text-sm text-slate-200 hover:bg-white/10"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!file || uploading}
                className="focusable flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {uploading ? "Uploading…" : "Upload"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            {/* Upload result */}
            <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4 text-sm">
              <p className="font-medium text-emerald-300">Upload successful</p>
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-slate-400">
                <span>Format</span><span className="text-slate-200">{result.format}</span>
                <span>Messages</span><span className="text-slate-200">{result.message_count}</span>
                <span>Chunks added</span><span className="text-slate-200">{result.chunks_added}</span>
                <span>Target speaker</span>
                <span className="text-slate-200">{result.target_speaker || "auto"}</span>
              </div>
              {result.speakers.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-slate-500">Detected speakers:</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {result.speakers.map((s) => (
                      <span key={s} className="chip text-[11px]">{s}</span>
                    ))}
                  </div>
                </div>
              )}
              {result.parse_errors?.length > 0 && (
                <div className="mt-2 text-xs text-amber-300">
                  {result.parse_errors.length} parse warning(s)
                </div>
              )}
            </div>

            {/* Speaker picker if needed */}
            {speakerPicking && result.speakers.length > 1 && (
              <div>
                <p className="mb-2 text-sm text-slate-300">
                  Multiple speakers detected. Select the target person:
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.speakers.map((s) => (
                    <button
                      key={s}
                      type="button"
                      disabled={pickingLoading}
                      onClick={() => handleSelectSpeaker(s)}
                      className="focusable rounded-lg border border-indigoGlow-400/40 bg-indigoGlow-600/10 px-3 py-1.5 text-sm text-indigoGlow-400 hover:bg-indigoGlow-600/20 disabled:opacity-50"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <p role="alert" className="rounded-lg border border-accent-rose/30 bg-accent-rose/10 px-3 py-2 text-sm text-rose-200">
                {error}
              </p>
            )}

            {!speakerPicking && (
              <button
                type="button"
                onClick={() => { onDone(); onClose(); }}
                className="focusable w-full rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet py-2.5 text-sm font-medium text-white"
              >
                Done
              </button>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
}

// TextModal ------------------------------------------------------------------
function TextModal({
  friendId,
  onClose,
  onDone,
}: {
  friendId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [targetSpeaker, setTargetSpeaker] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscriptUploadResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await addTextTranscript(friendId, {
        text: text.trim(),
        title: title.trim() || undefined,
        target_speaker: targetSpeaker.trim() || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add transcript.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="glass-panel w-full max-w-lg p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-white">Paste Chat Text</h2>
          <button type="button" onClick={onClose} className="focusable rounded-lg border border-white/10 p-1.5 text-slate-400 hover:bg-white/10 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="text-title" className="mb-1.5 block text-xs font-medium text-slate-300">
                Title <span className="text-slate-500">(optional)</span>
              </label>
              <input
                id="text-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. WhatsApp June 2023"
                className="focusable w-full rounded-xl border border-white/10 bg-white/[0.045] px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-indigoGlow-400/50"
              />
            </div>
            <div>
              <label htmlFor="text-body" className="mb-1.5 block text-xs font-medium text-slate-300">
                Chat text <span className="text-accent-rose">*</span>
              </label>
              <textarea
                id="text-body"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste your chat export here…"
                rows={8}
                required
                className="focusable w-full resize-none rounded-xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-indigoGlow-400/50"
              />
            </div>
            <div>
              <label htmlFor="text-speaker" className="mb-1.5 block text-xs font-medium text-slate-300">
                Target speaker <span className="text-slate-500">(optional)</span>
              </label>
              <input
                id="text-speaker"
                value={targetSpeaker}
                onChange={(e) => setTargetSpeaker(e.target.value)}
                placeholder="Leave blank to auto-detect"
                className="focusable w-full rounded-xl border border-white/10 bg-white/[0.045] px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-indigoGlow-400/50"
              />
            </div>

            {error && (
              <p role="alert" className="rounded-lg border border-accent-rose/30 bg-accent-rose/10 px-3 py-2 text-sm text-rose-200">{error}</p>
            )}

            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="focusable flex-1 rounded-xl border border-white/10 bg-white/[0.05] py-2.5 text-sm text-slate-200 hover:bg-white/10">Cancel</button>
              <button
                type="submit"
                disabled={!text.trim() || submitting}
                className="focusable flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                {submitting ? "Adding…" : "Add Transcript"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4 text-sm">
              <p className="font-medium text-emerald-300">Transcript added</p>
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-slate-400">
                <span>Format</span><span className="text-slate-200">{result.format}</span>
                <span>Messages</span><span className="text-slate-200">{result.message_count}</span>
                <span>Chunks added</span><span className="text-slate-200">{result.chunks_added}</span>
              </div>
            </div>
            <button type="button" onClick={() => { onDone(); onClose(); }} className="focusable w-full rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet py-2.5 text-sm font-medium text-white">Done</button>
          </div>
        )}
      </motion.div>
    </div>
  );
}

// Main page ------------------------------------------------------------------
export default function VirtualFriendProfilePage() {
  const params = useParams();
  const friendId = String(params.friendId ?? "");

  const [friend, setFriend] = useState<VirtualFriendSummary | null>(null);
  const [transcripts, setTranscripts] = useState<VFTranscript[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [showText, setShowText] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([
      getVirtualFriend(friendId),
      listTranscripts(friendId).catch(() => [] as VFTranscript[]),
    ])
      .then(([f, t]) => {
        setFriend(f);
        setTranscripts(t);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Could not load friend.")
      );
  };

  useEffect(() => {
    if (friendId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [friendId]);

  const handleDeleteTranscript = async (id: string) => {
    setDeletingId(id);
    try {
      await deleteTranscript(friendId, id);
      setTranscripts((prev) => prev?.filter((t) => t.id !== id) ?? prev);
      setConfirmId(null);
    } catch (err) {
      /* surface error inline */
    } finally {
      setDeletingId(null);
    }
  };

  const handleReprocessTranscript = async (id: string) => {
    try {
      await reprocessTranscript(friendId, id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reprocess transcript.");
    }
  };

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="glass-panel max-w-md p-8 text-center">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-accent-rose" />
          <p className="mb-4 text-rose-100">{error}</p>
          <div className="flex justify-center gap-3">
            <button type="button" onClick={load} className="focusable rounded-xl border border-white/15 bg-white/[0.05] px-4 py-2 text-sm text-white hover:bg-white/10">
              Retry
            </button>
            <Link href="/virtual-friends" className="focusable rounded-xl border border-white/15 px-4 py-2 text-sm text-slate-300 hover:bg-white/10">
              Back
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!friend) {
    return (
      <main className="relative min-h-screen overflow-hidden px-5 pb-28 pt-28 sm:px-8">
        <AppHeader compact />
        <div className="mx-auto max-w-4xl">
          <div className="glass-panel flex items-center gap-5 p-6">
            <div className="h-20 w-20 rounded-full shimmer" />
            <div className="flex-1 space-y-3">
              <div className="h-6 w-48 rounded shimmer" />
              <div className="h-4 w-full rounded shimmer" />
            </div>
          </div>
          <div className="mt-6 flex justify-center text-slate-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading…
          </div>
        </div>
      </main>
    );
  }

  const personality = friend.personality || {};
  const commStyles: string[] = Array.isArray(personality.communication_style)
    ? personality.communication_style
    : [];
  const themes: string[] = Array.isArray(personality.recurring_themes)
    ? personality.recurring_themes
    : [];
  const preferences: string[] = Array.isArray(personality.preferences)
    ? personality.preferences
    : [];
  const langPatterns: string[] = Array.isArray(personality.language_patterns)
    ? personality.language_patterns
    : [];

  return (
    <main className="relative min-h-screen overflow-hidden px-5 pb-28 pt-10 sm:px-8">
      <BackgroundScene intensity="subtle" />
      <AppHeader compact />

      <div className="relative z-10 mx-auto max-w-4xl pt-16">
        <Link
          href="/virtual-friends"
          className="focusable mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Virtual Friends
        </Link>

        {/* Header card */}
        <motion.header
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel flex flex-col items-center gap-6 p-6 sm:flex-row sm:items-start"
        >
          <div
            className="flex h-24 w-24 shrink-0 items-center justify-center rounded-full text-3xl font-bold text-white shadow-lg"
            style={{ backgroundColor: friend.avatar_color || "#6366f1" }}
          >
            {getInitials(friend.name)}
          </div>
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <h1 className="font-display text-3xl font-bold text-white">{friend.name}</h1>
              <StatusBadge status={friend.status} />
            </div>
            {friend.description && (
              <p className="mt-2 text-sm leading-relaxed text-slate-300">{friend.description}</p>
            )}
            <div className="mt-4 flex flex-wrap justify-center gap-6 sm:justify-start">
              {[
                { label: "Messages", value: friend.total_messages },
                { label: "Transcripts", value: friend.total_transcripts },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div className="font-display text-2xl text-white">{value}</div>
                  <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.header>

        {/* Nav tabs */}
        <nav className="mt-5 grid grid-cols-3 gap-3" aria-label="Friend sections">
          {[
            { href: `/virtual-friends/${friendId}/chat`, label: "Chat", icon: MessageSquare },
            { href: `/virtual-friends/${friendId}/memory`, label: "Memory", icon: Brain },
            { href: `/virtual-friends/${friendId}`, label: "Transcripts", icon: FileText },
          ].map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="focusable glass-panel flex flex-col items-center gap-2 p-4 text-sm text-slate-200 transition-all hover:border-indigoGlow-400/40 hover:shadow-glow"
            >
              <Icon className="h-5 w-5 text-accent-cyan" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>

        {/* Personality */}
        {(commStyles.length > 0 || themes.length > 0 || preferences.length > 0 || langPatterns.length > 0) && (
          <section className="mt-6 grid gap-4 md:grid-cols-2">
            {commStyles.length > 0 && (
              <div className="glass-panel p-5">
                <h2 className="mb-3 font-display text-sm uppercase tracking-wider text-slate-300">Communication Style</h2>
                <div className="flex flex-wrap gap-2">
                  {commStyles.map((s, i) => (
                    <span key={i} className="chip">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {themes.length > 0 && (
              <div className="glass-panel p-5">
                <h2 className="mb-3 font-display text-sm uppercase tracking-wider text-slate-300">Recurring Themes</h2>
                <div className="flex flex-wrap gap-2">
                  {themes.map((t, i) => (
                    <span key={i} className="chip">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {preferences.length > 0 && (
              <div className="glass-panel p-5">
                <h2 className="mb-3 font-display text-sm uppercase tracking-wider text-slate-300">Preferences</h2>
                <div className="flex flex-wrap gap-2">
                  {preferences.map((p, i) => (
                    <span key={i} className="chip">{p}</span>
                  ))}
                </div>
              </div>
            )}
            {langPatterns.length > 0 && (
              <div className="glass-panel p-5">
                <h2 className="mb-3 font-display text-sm uppercase tracking-wider text-slate-300">Language Patterns</h2>
                <ul className="space-y-1.5">
                  {langPatterns.map((p, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-300">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-indigoGlow-400" />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {/* Transcripts section */}
        <section className="mt-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="font-display text-lg text-white">Transcripts</h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowText(true)}
                className="focusable inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-slate-200 hover:bg-white/10"
              >
                <FileText className="h-4 w-4" aria-hidden />
                Paste text
              </button>
              <button
                type="button"
                onClick={() => setShowUpload(true)}
                className="focusable inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet px-3 py-2 text-sm font-medium text-white"
              >
                <Upload className="h-4 w-4" aria-hidden />
                Upload file
              </button>
            </div>
          </div>

          {transcripts === null && (
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3 text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading transcripts…
              </div>
            </div>
          )}

          {transcripts && transcripts.length === 0 && (
            <div className="glass-panel flex flex-col items-center gap-3 px-6 py-10 text-center">
              <FileText className="h-10 w-10 text-slate-600" />
              <p className="text-sm text-slate-400">
                Upload a chat export to get started.
              </p>
              <button
                type="button"
                onClick={() => setShowUpload(true)}
                className="focusable inline-flex items-center gap-2 rounded-xl border border-indigoGlow-400/40 bg-indigoGlow-600/10 px-4 py-2 text-sm text-indigoGlow-400"
              >
                <Upload className="h-4 w-4" /> Upload transcript
              </button>
            </div>
          )}

          {transcripts && transcripts.length > 0 && (
            <div className="space-y-3">
              {transcripts.map((t) => {
                const confirming = confirmId === t.id;
                const deleting = deletingId === t.id;
                return (
                  <div key={t.id} className="glass-panel flex items-start justify-between gap-4 p-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="truncate font-medium text-white text-sm">{t.filename}</span>
                        <span className="chip px-2 py-0.5 text-[10px]">{t.format}</span>
                        {t.target_speaker && (
                          <span className="chip border-indigoGlow-400/30 px-2 py-0.5 text-[10px] text-indigoGlow-400">
                            {t.target_speaker}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                        <span>{t.message_count} messages</span>
                        {t.speakers?.length > 0 && (
                          <span>Speakers: {t.speakers.join(", ")}</span>
                        )}
                        <span>{new Date(t.created_at).toLocaleDateString()}</span>
                      </div>
                      {t.parse_errors?.length > 0 && (
                        <p className="mt-1 text-xs text-amber-300">
                          ⚠ {t.parse_errors.length} parse warning(s)
                        </p>
                      )}
                    </div>

                    {confirming ? (
                      <div className="flex shrink-0 items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleDeleteTranscript(t.id)}
                          disabled={deleting}
                          className="focusable inline-flex items-center gap-1 rounded-lg border border-accent-rose/40 bg-accent-rose/15 px-2.5 py-1.5 text-xs text-rose-200 hover:bg-accent-rose/25 disabled:opacity-50"
                        >
                          {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                          Delete
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmId(null)}
                          className="focusable rounded-lg border border-white/15 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/10"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex shrink-0 gap-2">
                        <button type="button" onClick={() => handleReprocessTranscript(t.id)} className="focusable rounded-lg border border-white/10 px-2 py-1.5 text-xs text-slate-400 hover:bg-white/10 hover:text-white">Reprocess</button>
                        <button type="button" onClick={() => setConfirmId(t.id)} className="focusable rounded-lg border border-white/10 p-2 text-slate-500 hover:border-accent-rose/40 hover:text-rose-300" aria-label="Delete transcript"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Reload button */}
          {transcripts !== null && (
            <button
              type="button"
              onClick={load}
              className="focusable mt-3 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:bg-white/10 hover:text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          )}
        </section>
      </div>

      <AnimatePresence>
        {showUpload && (
          <UploadModal
            friendId={friendId}
            onClose={() => setShowUpload(false)}
            onDone={() => { load(); setShowUpload(false); }}
          />
        )}
        {showText && (
          <TextModal
            friendId={friendId}
            onClose={() => setShowText(false)}
            onDone={() => { load(); setShowText(false); }}
          />
        )}
      </AnimatePresence>
    </main>
  );
}
