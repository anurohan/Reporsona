"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Brain, Loader2, Trash2 } from "lucide-react";
import { deleteVFMemory, getVirtualFriend, listVFMemories } from "@/lib/api";
import type { VFMemory, VirtualFriendSummary } from "@/lib/types";

export default function VirtualFriendMemoryPage() {
  const { friendId } = useParams<{ friendId: string }>();
  const [friend, setFriend] = useState<VirtualFriendSummary | null>(null);
  const [memories, setMemories] = useState<VFMemory[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([getVirtualFriend(friendId), listVFMemories(friendId)]).then(([f, m]) => { setFriend(f); setMemories(m); }).catch(() => setError("Could not load memories.")); }, [friendId]);
  async function remove(id: string) { await deleteVFMemory(friendId, id); setMemories((current) => current?.filter((m) => m.id !== id) ?? current); }
  return <main className="min-h-screen bg-void-950 px-5 pb-20 pt-10 text-white sm:px-8"><div className="mx-auto max-w-3xl"><Link href={`/virtual-friends/${friendId}`} className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> {friend?.name ?? "Virtual Friend"}</Link><div className="mb-6"><div className="eyebrow">Evidence-backed profile</div><h1 className="mt-2 font-display text-3xl">Memory</h1><p className="mt-2 text-sm text-slate-400">Observed patterns are labeled separately from documented statements and inferences.</p></div>{error && <p role="alert" className="text-rose-200">{error}</p>}{memories === null && <Loader2 className="animate-spin text-slate-500" />}{memories?.length === 0 && <div className="glass-panel p-8 text-center text-sm text-slate-500">No extracted memories yet. Upload more conversation history.</div>}<div className="space-y-3">{memories?.map((m) => <article key={m.id} className="glass-panel flex gap-4 p-5"><Brain className="mt-1 h-5 w-5 shrink-0 text-accent-cyan" /><div className="min-w-0 flex-1"><div className="flex flex-wrap gap-2"><h2 className="font-medium">{m.label}</h2><span className="chip px-2 py-0.5 text-[10px]">{m.classification}</span></div><p className="mt-2 text-sm leading-6 text-slate-300">{m.detail}</p>{m.evidence_chunk_ids.length > 0 && <p className="mt-2 text-xs text-slate-500">{m.evidence_chunk_ids.length} supporting evidence chunk(s)</p>}</div><button onClick={() => remove(m.id)} className="focusable h-fit rounded-lg border border-white/10 p-2 text-slate-500 hover:border-rose-400/40 hover:text-rose-300" aria-label="Delete memory"><Trash2 className="h-4 w-4" /></button></article>)}</div></div></main>;
}
