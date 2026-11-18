"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { getVirtualFriend, sendVFChat } from "@/lib/api";
import type { ChatTurn, Evidence, VirtualFriendSummary } from "@/lib/types";

type ChatItem = ChatTurn & { evidence?: Evidence[]; confidence?: string };

export default function VirtualFriendChatPage() {
  const { friendId } = useParams<{ friendId: string }>();
  const [friend, setFriend] = useState<VirtualFriendSummary | null>(null);
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { getVirtualFriend(friendId).then(setFriend).catch(() => setError("Could not load this virtual friend.")); }, [friendId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;
    setInput(""); setError(""); setLoading(true);
    const next = [...messages, { role: "user", content: message } as ChatItem];
    setMessages(next);
    try {
      const response = await sendVFChat({ friend_id: friendId, message, session_id: sessionId, history: next.map(({ role, content }) => ({ role, content })) });
      setSessionId(response.session_id);
      setMessages((current) => [...current, { role: "assistant", content: response.message, evidence: response.evidence, confidence: response.confidence }]);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not send message."); }
    finally { setLoading(false); }
  }

  return <main className="min-h-screen bg-void-950 px-5 pb-20 pt-10 text-white sm:px-8">
    <div className="mx-auto max-w-3xl">
      <Link href={`/virtual-friends/${friendId}`} className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> {friend?.name ?? "Virtual Friend"}</Link>
      <div className="glass-panel flex min-h-[70vh] flex-col p-4 sm:p-6">
        <div className="border-b border-white/10 pb-4"><h1 className="font-display text-2xl">Chat with {friend?.name ?? "your virtual friend"}</h1><p className="mt-1 text-xs text-slate-400">AI simulation grounded only in uploaded conversations.</p></div>
        <div className="flex-1 space-y-4 overflow-y-auto py-5">
          {messages.length === 0 && <p className="py-20 text-center text-sm text-slate-500">Ask about something covered in the uploaded chats.</p>}
          {messages.map((m, i) => <div key={i} className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm ${m.role === "user" ? "ml-auto bg-indigoGlow-600/40" : "bg-white/[0.06]"}`}><p className="whitespace-pre-wrap leading-6">{m.content}</p>{m.role === "assistant" && <><p className="mt-2 text-[10px] uppercase tracking-wider text-slate-500">Evidence: {m.confidence ?? "INSUFFICIENT"}</p>{m.evidence?.length ? <div className="mt-2 space-y-1 text-xs text-slate-400">{m.evidence.slice(0, 3).map((e) => <p key={e.chunk_id} className="border-l border-indigoGlow-400/50 pl-2">{e.source_title}</p>)}</div> : null}</>}</div>)}
          {loading && <div className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Searching uploaded evidence…</div>}
        </div>
        {error && <p role="alert" className="mb-3 rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">{error}</p>}
        <form onSubmit={submit} className="flex gap-2 border-t border-white/10 pt-4"><input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a grounded question…" className="focusable min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white placeholder:text-slate-500" /><button disabled={loading || !input.trim()} className="focusable rounded-xl bg-indigoGlow-600 px-4 text-white disabled:opacity-40" aria-label="Send"><Send className="h-4 w-4" /></button></form>
      </div>
    </div>
  </main>;
}
