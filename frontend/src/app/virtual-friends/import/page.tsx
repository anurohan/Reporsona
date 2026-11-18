"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, FileUp, Loader2 } from "lucide-react";
import { ApiError, confirmConversationImport, uploadConversationPreview } from "@/lib/api";
import type { ImportPreview } from "@/lib/types";

const platforms = [
  ["auto", "Auto-detect"], ["whatsapp", "WhatsApp"], ["instagram", "Instagram"], ["telegram", "Telegram"], ["messenger", "Facebook Messenger"],
];

export default function ConversationImportPage() {
  const router = useRouter();
  const [platform, setPlatform] = useState("auto");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [selected, setSelected] = useState("");
  const [friendName, setFriendName] = useState("");
  const [friendId, setFriendId] = useState("");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function parse() {
    if (!file) return;
    setBusy(true); setError("");
    try { const result = await uploadConversationPreview(file, platform, setProgress); setPreview(result); setSelected(result.participants[0] ?? ""); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not parse export."); }
    finally { setBusy(false); }
  }

  async function confirm() {
    if (!preview || !selected || (!friendId.trim() && !friendName.trim())) return;
    setBusy(true); setError("");
    try { const result = await confirmConversationImport({ import_id: preview.import_id, target_speaker: selected, friend_id: friendId.trim() || undefined, friend_name: friendName.trim() || undefined }); router.push(`/virtual-friends/${result.friend_id}`); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not confirm import."); setBusy(false); }
  }

  return <main className="min-h-screen bg-void-950 px-5 pb-20 pt-10 text-white sm:px-8"><div className="mx-auto max-w-3xl"><Link href="/virtual-friends" className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> Virtual Friends</Link><div className="mb-8"><div className="eyebrow">Private export workflow</div><h1 className="mt-3 font-display text-4xl">Import conversations</h1><p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">Upload an authorized export, review detected participants, then choose exactly who this Virtual Friend represents.</p></div>
    <section className="glass-panel space-y-5 p-6"><div><label className="mb-2 block text-sm text-slate-300">Platform</label><select value={platform} onChange={(e) => setPlatform(e.target.value)} className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white">{platforms.map(([value, label]) => <option key={value} value={value} className="bg-void-950">{label}</option>)}</select></div><div><label className="mb-2 block text-sm text-slate-300">Export file</label><input type="file" accept=".txt,.json,.html,.htm,.zip" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPreview(null); }} className="focusable block w-full rounded-xl border border-dashed border-white/15 bg-white/[0.03] p-4 text-sm text-slate-300" /><p className="mt-2 text-xs text-slate-500">Supported: WhatsApp TXT/ZIP, Instagram JSON/HTML, Telegram JSON/HTML, Messenger JSON/HTML.</p></div><button onClick={parse} disabled={!file || busy} className="focusable inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet px-5 py-3 text-sm font-medium disabled:opacity-40"><FileUp className="h-4 w-4" /> {busy && !preview ? `Parsing ${progress}%` : "Preview export"}</button>{busy && !preview && <div className="h-1 overflow-hidden rounded bg-white/10"><div className="h-full bg-indigoGlow-400 transition-all" style={{ width: `${progress}%` }} /></div>}{error && <p role="alert" className="rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">{error}</p>}</section>
    {preview && <section className="glass-panel mt-5 space-y-5 p-6"><div className="flex items-start gap-3"><CheckCircle2 className="mt-1 h-5 w-5 text-emerald-300" /><div><h2 className="font-display text-lg">Review detected conversation</h2><p className="mt-1 text-sm text-slate-400">{preview.platform} · {preview.message_count} messages · {preview.filename}</p></div></div><div><label className="mb-2 block text-sm text-slate-300">Person represented by this Virtual Friend</label><select value={selected} onChange={(e) => setSelected(e.target.value)} className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white">{preview.participants.map((person) => <option key={person} value={person} className="bg-void-950">{person}</option>)}</select><p className="mt-2 text-xs text-slate-500">Detected participants: {preview.participants.join(", ")}</p></div><div className="grid gap-4 sm:grid-cols-2"><div><label className="mb-2 block text-sm text-slate-300">New friend name</label><input value={friendName} onChange={(e) => setFriendName(e.target.value)} placeholder={selected || "Friend name"} className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white" /></div><div><label className="mb-2 block text-sm text-slate-300">Existing friend ID <span className="text-slate-500">(optional)</span></label><input value={friendId} onChange={(e) => setFriendId(e.target.value)} placeholder="Attach to an existing friend" className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white" /></div></div><div className="rounded-xl bg-white/[0.03] p-4 text-sm text-slate-300"><p className="mb-2 text-xs uppercase tracking-wider text-slate-500">Sample</p>{preview.sample_messages.slice(0, 4).map((message, index) => <p key={index} className="mb-1"><span className="text-indigoGlow-300">{message.sender}:</span> {message.text}</p>)}</div><button onClick={confirm} disabled={busy || !selected || (!friendId.trim() && !friendName.trim())} className="focusable inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet px-5 py-3 text-sm font-medium disabled:opacity-40">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Confirm and build memory</button></section>}
  </div></main>;
}
