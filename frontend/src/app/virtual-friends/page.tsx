"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Heart,
  Loader2,
  MessageSquare,
  Plus,
  Trash2,
  X,
  FileText,
} from "lucide-react";
import {
  ApiError,
  createVirtualFriend,
  deleteVirtualFriend,
  listVirtualFriends,
} from "@/lib/api";
import type { VirtualFriendSummary } from "@/lib/types";
import AppHeader from "@/components/AppHeader";

const BackgroundScene = dynamic(
  () => import("@/components/three/BackgroundScene"),
  { ssr: false }
);

const PRESET_COLORS = [
  "#6366f1",
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
];

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

function FriendCard({
  friend,
  onDelete,
  onClick,
}: {
  friend: VirtualFriendSummary;
  onDelete: (id: string) => Promise<void>;
  onClick: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(friend.id);
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="group glass-panel relative flex flex-col gap-4 p-5 transition-all hover:border-indigoGlow-400/30 hover:shadow-glow"
    >
      <button
        type="button"
        onClick={onClick}
        className="focusable flex items-center gap-4 text-left"
        aria-label={`Open ${friend.name}`}
      >
        {/* Avatar */}
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white shadow-lg"
          style={{ backgroundColor: friend.avatar_color || "#6366f1" }}
        >
          {getInitials(friend.name)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate font-display text-base text-white">
              {friend.name}
            </span>
            <StatusBadge status={friend.status} />
          </div>
          {friend.description && (
            <p className="mt-1 line-clamp-2 text-xs text-slate-400">
              {friend.description}
            </p>
          )}
          <div className="mt-2 flex items-center gap-4 text-[11px] text-slate-500">
            <span className="flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5" aria-hidden />
              {friend.total_messages} messages
            </span>
            <span className="flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" aria-hidden />
              {friend.total_transcripts} transcripts
            </span>
          </div>
        </div>
      </button>

      {/* Delete control */}
      <div className="absolute right-4 top-4 flex shrink-0 items-center gap-1.5">
        {confirming ? (
          <>
            <button
              type="button"
              onClick={handleDelete}
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
              onClick={() => setConfirming(false)}
              disabled={deleting}
              className="focusable rounded-lg border border-white/15 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/10 disabled:opacity-50"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="focusable rounded-lg border border-white/10 p-2 text-slate-500 opacity-0 transition-all hover:border-accent-rose/40 hover:text-rose-300 group-hover:opacity-100"
            aria-label={`Delete ${friend.name}`}
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        )}
      </div>
    </motion.div>
  );
}

function CreateModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (friend: VirtualFriendSummary) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(PRESET_COLORS[0]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || creating) return;
    setCreating(true);
    setError(null);
    try {
      const friend = await createVirtualFriend({
        name: name.trim(),
        description: description.trim() || undefined,
        avatar_color: color,
      });
      onCreate(friend);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not create virtual friend. Please try again."
      );
      setCreating(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Create virtual friend"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 8, scale: 0.97 }}
        transition={{ duration: 0.2 }}
        className="glass-panel w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-white">
            New Virtual Friend
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="focusable rounded-lg border border-white/10 p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="vf-name" className="mb-1.5 block text-xs font-medium text-slate-300">
              Name <span className="text-accent-rose">*</span>
            </label>
            <input
              id="vf-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Alex, Mom, Best Friend…"
              required
              className="focusable w-full rounded-xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-indigoGlow-400/50 focus:bg-indigoGlow-600/[.06]"
            />
          </div>

          <div>
            <label htmlFor="vf-desc" className="mb-1.5 block text-xs font-medium text-slate-300">
              Description <span className="text-slate-500">(optional)</span>
            </label>
            <textarea
              id="vf-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this person briefly…"
              rows={3}
              className="focusable w-full resize-none rounded-xl border border-white/10 bg-white/[0.045] px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-indigoGlow-400/50 focus:bg-indigoGlow-600/[.06]"
            />
          </div>

          <div>
            <span className="mb-2 block text-xs font-medium text-slate-300">
              Avatar color
            </span>
            <div className="flex gap-2.5">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`focusable h-8 w-8 rounded-full transition-transform hover:scale-110 ${
                    color === c ? "ring-2 ring-white ring-offset-2 ring-offset-void-950" : ""
                  }`}
                  style={{ backgroundColor: c }}
                  aria-label={`Color ${c}`}
                  aria-pressed={color === c}
                />
              ))}
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-lg border border-accent-rose/30 bg-accent-rose/10 px-3 py-2 text-sm text-rose-200"
            >
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="focusable flex-1 rounded-xl border border-white/10 bg-white/[0.05] py-2.5 text-sm text-slate-200 hover:bg-white/10"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || !name.trim()}
              className="focusable flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet py-2.5 text-sm font-medium text-white shadow-glow transition-all hover:-translate-y-0.5 hover:shadow-glow-lg disabled:cursor-not-allowed disabled:opacity-40"
            >
              {creating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Heart className="h-4 w-4" aria-hidden />
              )}
              Create
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

export default function VirtualFriendsPage() {
  const router = useRouter();
  const [friends, setFriends] = useState<VirtualFriendSummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = () => {
    setListError(null);
    listVirtualFriends()
      .then(setFriends)
      .catch((err) =>
        setListError(
          err instanceof ApiError ? err.message : "Could not load virtual friends."
        )
      );
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    await deleteVirtualFriend(id);
    setFriends((prev) => (prev ? prev.filter((f) => f.id !== id) : prev));
  };

  const handleCreated = (friend: VirtualFriendSummary) => {
    setShowCreate(false);
    router.push(`/virtual-friends/${friend.id}`);
  };

  return (
    <main className="relative min-h-screen overflow-hidden px-5 pb-28 pt-28 sm:px-8">
      <BackgroundScene intensity="subtle" />
      <AppHeader compact />

      <div className="relative z-10 mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <div className="eyebrow">AI Companions</div>
            <h1 className="display-title mt-3 text-4xl sm:text-5xl">Virtual Friends</h1>
            <p className="mt-3 max-w-xl text-sm leading-7 text-slate-400">
              Create AI companions from your conversation history. Upload chat exports
              and have meaningful conversations based on real memories.
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Link href="/virtual-friends/import" className="focusable inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/[0.05] px-4 py-3 text-sm text-slate-200 hover:bg-white/10"><FileText className="h-4 w-4" /> Import export</Link>
            <button type="button" onClick={() => setShowCreate(true)} className="focusable inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet px-5 py-3 text-sm font-medium text-white shadow-glow transition-all hover:-translate-y-0.5 hover:shadow-glow-lg"><Plus className="h-4 w-4" aria-hidden /> Create Virtual Friend</button>
          </div>
        </motion.div>

        {/* Error */}
        {listError && (
          <div className="glass-panel mt-8 flex items-center justify-between px-4 py-3 text-sm text-rose-200">
            <span className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
              {listError}
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

        {/* Loading */}
        {!listError && friends === null && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="glass-panel h-32 p-5">
                <div className="flex items-center gap-4">
                  <div className="h-14 w-14 rounded-full shimmer" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 rounded shimmer" />
                    <div className="h-3 w-full rounded shimmer" />
                    <div className="h-3 w-24 rounded shimmer" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!listError && friends && friends.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-panel mt-8 flex flex-col items-center gap-4 px-8 py-16 text-center"
          >
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-indigoGlow-400/20 bg-indigoGlow-600/10">
              <Heart className="h-10 w-10 text-indigoGlow-400" />
            </div>
            <div>
              <h2 className="font-display text-xl text-white">
                No virtual friends yet
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                Create your first virtual friend and upload a chat export to get started.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="focusable mt-2 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet px-5 py-2.5 text-sm font-medium text-white shadow-glow"
            >
              <Plus className="h-4 w-4" aria-hidden />
              Create Virtual Friend
            </button>
          </motion.div>
        )}

        {/* Grid */}
        {friends && friends.length > 0 && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {friends.map((f) => (
              <FriendCard
                key={f.id}
                friend={f}
                onDelete={handleDelete}
                onClick={() => router.push(`/virtual-friends/${f.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      <AnimatePresence>
        {showCreate && (
          <CreateModal onClose={() => setShowCreate(false)} onCreate={handleCreated} />
        )}
      </AnimatePresence>
    </main>
  );
}
