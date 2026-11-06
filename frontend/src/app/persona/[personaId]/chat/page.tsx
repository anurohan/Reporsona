"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Check,
  MessageSquarePlus,
  Network,
  PanelRightClose,
  PanelRightOpen,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import {
  ApiError,
  deleteConversation,
  getConversation,
  getPersona,
  listConversations,
  renameConversation,
} from "@/lib/api";
import type {
  ChatResponse,
  Conversation,
  Evidence,
  PersonaDetail,
} from "@/lib/types";
import ChatPanel from "@/components/ChatPanel";
import EvidencePanel from "@/components/EvidencePanel";
import PersonaImage from "@/components/PersonaImage";
import { personaAccent } from "@/lib/theme";

interface InitialMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  evidence?: Evidence[];
}

export default function PersonaChatPage() {
  const params = useParams();
  const personaId = String(params.personaId || "");

  const [persona, setPersona] = useState<PersonaDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [coverage, setCoverage] =
    useState<ChatResponse["evidence_coverage"] | null>(null);
  const [limitations, setLimitations] = useState<string[]>([]);
  const [hasAsked, setHasAsked] = useState(false);
  const [evidenceMode, setEvidenceMode] = useState(true);
  const [showEvidence, setShowEvidence] = useState(true);

  // Conversation memory (§20)
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(
    undefined
  );
  const [initialMessages, setInitialMessages] = useState<InitialMessage[]>([]);
  // Remount key so switching/starting a conversation resets ChatPanel state.
  const [chatKey, setChatKey] = useState(0);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameText, setRenameText] = useState("");

  const load = () => {
    setError(null);
    getPersona(personaId)
      .then(setPersona)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Could not load this persona."
        )
      );
  };

  const loadConversations = useCallback(() => {
    if (!personaId) return;
    listConversations(personaId)
      .then(setConversations)
      .catch(() => setConversations([]));
  }, [personaId]);

  useEffect(() => {
    if (personaId) {
      load();
      loadConversations();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  // Start a fresh conversation: clear state and remount the chat panel.
  const startNewConversation = () => {
    setActiveSessionId(undefined);
    setInitialMessages([]);
    setEvidence([]);
    setCoverage(null);
    setLimitations([]);
    setHasAsked(false);
    setChatKey((k) => k + 1);
  };

  // Resume a stored conversation by loading its messages into a remounted panel.
  const openConversation = async (sessionId: string) => {
    if (sessionId === activeSessionId) return;
    try {
      const detail = await getConversation(sessionId);
      const msgs: InitialMessage[] = detail.messages.map((m) => ({
        id: m.id,
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
        evidence: Array.isArray(m.evidence)
          ? (m.evidence as Evidence[])
          : undefined,
      }));
      setInitialMessages(msgs);
      setActiveSessionId(sessionId);
      // Reflect the last assistant turn's evidence in the side panel.
      const lastAssistant = [...detail.messages]
        .reverse()
        .find((m) => m.role === "assistant");
      setEvidence(
        lastAssistant && Array.isArray(lastAssistant.evidence)
          ? (lastAssistant.evidence as Evidence[])
          : []
      );
      setHasAsked(detail.messages.length > 0);
      setChatKey((k) => k + 1);
    } catch {
      /* leave current conversation intact on failure */
    }
  };

  const handleSessionChange = (sessionId: string) => {
    setActiveSessionId(sessionId);
    loadConversations();
  };

  const submitRename = async (sessionId: string) => {
    const title = renameText.trim();
    setRenamingId(null);
    if (!title) return;
    try {
      await renameConversation(sessionId, title);
      loadConversations();
    } catch {
      /* ignore */
    }
  };

  const removeConversation = async (sessionId: string) => {
    try {
      await deleteConversation(sessionId);
      setConversations((prev) => prev.filter((c) => c.id !== sessionId));
      if (sessionId === activeSessionId) startNewConversation();
    } catch {
      /* ignore */
    }
  };

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="glass-panel max-w-md p-8 text-center">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-accent-rose" />
          <p className="mb-4 text-rose-100">{error}</p>
          <button
            type="button"
            onClick={load}
            className="focusable rounded-xl border border-white/15 bg-white/[0.05] px-4 py-2 text-sm text-white hover:bg-white/10"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main
      className="flex h-screen flex-col overflow-hidden bg-space-gradient"
      style={personaAccent(persona?.id || personaId)}
    >
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <Link
          href={`/persona/${personaId}`}
          className="focusable inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          <span className="hidden sm:inline">Profile</span>
        </Link>
        <div className="flex items-center gap-2 text-sm text-slate-300">
          {persona && (
            <>
              <PersonaImage
                name={persona.name}
                portraitUrl={persona.portrait_url}
                size={28}
                glow={false}
              />
              <span className="font-display text-white">{persona.name}</span>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={() => setShowEvidence((v) => !v)}
          className="focusable inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/10 lg:hidden"
          aria-label={showEvidence ? "Hide evidence panel" : "Show evidence panel"}
        >
          {showEvidence ? (
            <PanelRightClose className="h-4 w-4" />
          ) : (
            <PanelRightOpen className="h-4 w-4" />
          )}
          Evidence
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* LEFT: identity + topics + nav */}
        <aside className="hidden w-64 shrink-0 flex-col border-r border-white/10 p-5 lg:flex">
          {persona ? (
            <>
              <div className="flex flex-col items-center text-center">
                <PersonaImage
                  name={persona.name}
                  portraitUrl={persona.portrait_url}
                  size={80}
                />
                <h2 className="mt-3 font-display text-lg text-white">
                  {persona.name}
                </h2>
                {persona.is_demo && (
                  <span className="chip mt-1 text-[10px]">Demo</span>
                )}
                {persona.summary && (
                  <p className="mt-2 line-clamp-4 text-xs text-slate-400">
                    {persona.summary}
                  </p>
                )}
              </div>

              {persona.topics && persona.topics.length > 0 && (
                <div className="mt-6">
                  <h3 className="mb-2 text-[11px] uppercase tracking-wider text-slate-500">
                    Topics
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {persona.topics.slice(0, 12).map((t) => (
                      <span key={t.id} className="chip text-[11px]">
                        {t.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Conversations (§20) */}
              <div className="mt-6 min-h-0 flex-1">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-[11px] uppercase tracking-wider text-slate-500">
                    Conversations
                  </h3>
                  <button
                    type="button"
                    onClick={startNewConversation}
                    className="focusable inline-flex items-center gap-1 rounded-lg border border-white/10 px-2 py-1 text-[11px] text-slate-300 hover:bg-white/10"
                    title="Start a new conversation"
                  >
                    <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden />
                    New
                  </button>
                </div>
                {conversations.length === 0 ? (
                  <p className="text-[11px] text-slate-600">
                    No saved conversations yet.
                  </p>
                ) : (
                  <ul className="scroll-slim max-h-56 space-y-1 overflow-y-auto pr-1">
                    {conversations.map((c) => {
                      const active = c.id === activeSessionId;
                      const renaming = renamingId === c.id;
                      return (
                        <li key={c.id}>
                          {renaming ? (
                            <div className="flex items-center gap-1">
                              <input
                                autoFocus
                                value={renameText}
                                onChange={(e) => setRenameText(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") submitRename(c.id);
                                  if (e.key === "Escape") setRenamingId(null);
                                }}
                                className="focusable min-w-0 flex-1 rounded-md border border-white/15 bg-white/[0.05] px-2 py-1 text-[11px] text-white"
                              />
                              <button
                                type="button"
                                onClick={() => submitRename(c.id)}
                                className="focusable rounded-md p-1 text-emerald-300 hover:bg-white/10"
                                aria-label="Save name"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setRenamingId(null)}
                                className="focusable rounded-md p-1 text-slate-400 hover:bg-white/10"
                                aria-label="Cancel rename"
                              >
                                <X className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ) : (
                            <div
                              className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 text-left transition-colors ${
                                active
                                  ? "bg-white/[0.08] text-white"
                                  : "text-slate-300 hover:bg-white/[0.05]"
                              }`}
                            >
                              <button
                                type="button"
                                onClick={() => openConversation(c.id)}
                                className="focusable min-w-0 flex-1 truncate text-left text-[12px]"
                                title={c.title}
                              >
                                {c.title || "Untitled conversation"}
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  setRenamingId(c.id);
                                  setRenameText(c.title || "");
                                }}
                                className="focusable rounded-md p-1 text-slate-500 opacity-0 hover:text-white group-hover:opacity-100"
                                aria-label="Rename conversation"
                              >
                                <Pencil className="h-3 w-3" />
                              </button>
                              <button
                                type="button"
                                onClick={() => removeConversation(c.id)}
                                className="focusable rounded-md p-1 text-slate-500 opacity-0 hover:text-rose-300 group-hover:opacity-100"
                                aria-label="Delete conversation"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <nav className="mt-auto space-y-1 pt-6" aria-label="Persona navigation">
                <Link
                  href={`/persona/${personaId}/knowledge`}
                  className="focusable flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.06]"
                >
                  <Network className="h-4 w-4 text-accent-cyan" aria-hidden />
                  Knowledge graph
                </Link>
                <Link
                  href={`/persona/${personaId}/sources`}
                  className="focusable flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.06]"
                >
                  <BookOpen className="h-4 w-4 text-accent-cyan" aria-hidden />
                  Sources
                </Link>
              </nav>
            </>
          ) : (
            <div className="space-y-3">
              <div className="mx-auto h-20 w-20 rounded-full shimmer" />
              <div className="h-4 w-full rounded shimmer" />
              <div className="h-4 w-2/3 rounded shimmer" />
            </div>
          )}
        </aside>

        {/* CENTER: chat */}
        <section className="flex min-w-0 flex-1 flex-col">
          {persona ? (
            <ChatPanel
              key={chatKey}
              personaId={personaId}
              personaName={persona.name}
              portraitUrl={persona.portrait_url}
              evidenceMode={evidenceMode}
              onToggleEvidenceMode={setEvidenceMode}
              initialSessionId={activeSessionId}
              initialMessages={initialMessages}
              onSessionChange={handleSessionChange}
              onEvidence={({ evidence, coverage, limitations }) => {
                setEvidence(evidence);
                setCoverage(coverage);
                setLimitations(limitations);
                setHasAsked(true);
              }}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center text-slate-500">
              Loading conversation…
            </div>
          )}
        </section>

        {/* RIGHT: evidence */}
        <aside
          className={`w-full max-w-sm shrink-0 border-l border-white/10 bg-void-950/40 lg:block ${
            showEvidence ? "block" : "hidden"
          } ${showEvidence ? "fixed inset-y-0 right-0 z-20 lg:static" : ""}`}
        >
          <EvidencePanel
            evidence={evidence}
            coverage={coverage}
            limitations={limitations}
            hasAsked={hasAsked}
          />
        </aside>
      </div>
    </main>
  );
}
