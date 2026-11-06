"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  BadgeCheck,
  Check,
  ChevronDown,
  Clock,
  Copy,
  ExternalLink,
  Globe,
  Info,
  Mic,
  MicOff,
  RefreshCw,
  Send,
  Sparkles,
  ShieldCheck,
  User,
  Volume2,
  VolumeX,
} from "lucide-react";
import { ApiError, sendChat } from "@/lib/api";
import type {
  ChatResponse,
  ChatTurn,
  CurrentContextItem,
  CurrentContextStatus,
  Evidence,
  ResponseMode,
  ResponseType,
  TemporalContext,
} from "@/lib/types";
import PersonaImage from "@/components/PersonaImage";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  evidence?: Evidence[];
  error?: boolean;
  // Persona-reasoner metadata (§17/§18/§22/§23)
  responseType?: ResponseType;
  mode?: string;
  temporal?: TemporalContext | null;
  worldviewConcepts?: string[];
  reasoning?: Record<string, any>;
  limitations?: string[];
  // Classification + current-context (§18/§19)
  currentContext?: CurrentContextItem[];
  currentContextStatus?: CurrentContextStatus;
  requiresCurrentContext?: boolean;
  warnings?: string[];
  knowledgeCutoff?: string;
}

// Response modes (§23) surfaced in the UI.
const MODES: {
  code: ResponseMode;
  label: string;
  hint: string;
}[] = [
  {
    code: "persona_simulation",
    label: "Persona",
    hint: "Answer in the persona's documented voice and worldview.",
  },
  {
    code: "evidence",
    label: "Evidence",
    hint: "Answer strictly from retrieved source passages.",
  },
  {
    code: "historical",
    label: "Historical",
    hint: "Answer only from what was known during their lifetime.",
  },
  {
    code: "current_context",
    label: "Current + Persona",
    hint: "Apply their worldview to present-day/after-lifetime topics (labelled simulation).",
  },
];

/**
 * Reveals text one character at a time so an answer feels like the person is
 * typing it live. Longer replies reveal a few chars per tick so they never drag.
 * Once finished it calls onDone so the parent can mark it done and never
 * re-animate on later re-renders (copy/regenerate/scroll).
 */
function TypewriterText({
  text,
  animate,
  onTick,
  onDone,
}: {
  text: string;
  animate: boolean;
  onTick?: () => void;
  onDone?: () => void;
}) {
  const [count, setCount] = useState(animate ? 0 : text.length);

  useEffect(() => {
    if (!animate) {
      setCount(text.length);
      return;
    }
    let i = 0;
    const total = text.length;
    setCount(0);
    // reveal faster for long replies so it stays snappy
    const step = total > 500 ? 4 : total > 200 ? 2 : 1;
    const timer = setInterval(() => {
      i += step;
      if (i >= total) {
        setCount(total);
        clearInterval(timer);
        onTick?.();
        onDone?.();
      } else {
        setCount(i);
        onTick?.();
      }
    }, 18);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, animate]);

  const typing = count < text.length;
  return (
    <p className="whitespace-pre-wrap">
      {text.slice(0, count)}
      {typing && (
        <span className="ml-0.5 inline-block w-[2px] animate-pulse bg-current align-middle" style={{ height: "1em" }} aria-hidden />
      )}
    </p>
  );
}

interface ChatPanelProps {
  personaId: string;
  personaName: string;
  /** External portrait URL for the assistant avatar; falls back to an orb. */
  portraitUrl?: string;
  onEvidence?: (payload: {
    evidence: Evidence[];
    coverage: ChatResponse["evidence_coverage"];
    limitations: string[];
  }) => void;
  evidenceMode: boolean;
  onToggleEvidenceMode: (v: boolean) => void;
  /** Conversation memory (§20): resume an existing session. */
  initialSessionId?: string;
  initialMessages?: {
    id: string;
    role: "user" | "assistant";
    content: string;
    evidence?: Evidence[];
  }[];
  /** Fires when the backend assigns/returns a session id, so a parent
   *  conversation list can refresh and track the active thread. */
  onSessionChange?: (sessionId: string) => void;
}

function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

type LangCode = "en" | "hi" | "hinglish";

const LANGUAGES: { code: LangCode; label: string; short: string; bcp47: string }[] = [
  { code: "en", label: "English", short: "EN", bcp47: "en-US" },
  { code: "hi", label: "हिंदी", short: "HI", bcp47: "hi-IN" },
  { code: "hinglish", label: "Hinglish", short: "HN", bcp47: "hi-IN" },
];

function bcp47For(code: LangCode): string {
  return LANGUAGES.find((l) => l.code === code)?.bcp47 ?? "en-US";
}

/** Speak text aloud via the browser's built-in speech synthesis. */
function speak(text: string, langCode: LangCode) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const want = bcp47For(langCode);
  const voices = window.speechSynthesis.getVoices();
  const match =
    voices.find((v) => v.lang === want) ||
    voices.find((v) => v.lang?.startsWith(want.split("-")[0]));
  if (match) u.voice = match;
  u.lang = want;
  u.rate = 1;
  u.pitch = 1;
  window.speechSynthesis.speak(u);
}

/**
 * Response-type label (§18): a generated answer is a SIMULATED PERSONA RESPONSE,
 * never dressed up as a real quote. A VERIFIED HISTORICAL QUOTE label is only
 * ever shown when the backend confirms a source-backed quotation.
 */
function ResponseLabel({
  responseType,
  mode,
}: {
  responseType?: ResponseType;
  mode?: string;
}) {
  const isQuote = responseType === "VERIFIED_HISTORICAL_QUOTE";
  if (isQuote) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/40 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-emerald-300">
        <BadgeCheck className="h-3 w-3" aria-hidden />
        Verified historical quote
      </span>
    );
  }
  const label =
    mode === "current_context"
      ? "Simulated persona · current context"
      : mode === "historical"
      ? "Simulated persona · historical"
      : mode === "evidence"
      ? "Evidence-backed answer"
      : "Simulated persona response";
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-accent-violet/40 bg-accent-violet/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-accent-violet">
      <Sparkles className="h-3 w-3" aria-hidden />
      {label}
    </span>
  );
}

/**
 * Historical Reality Guard banner (§17): shown when the question concerns
 * events after the persona's lifetime, so the answer is clearly framed as a
 * simulated perspective rather than something the person actually witnessed.
 */
function TemporalBanner({ temporal }: { temporal?: TemporalContext | null }) {
  if (!temporal || !temporal.needs_current_context) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-lg border border-accent-amber/30 bg-accent-amber/10 px-3 py-2 text-[11px] leading-relaxed text-amber-200">
      <Clock className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        {temporal.note ||
          "This concerns events after the person's lifetime. The answer applies their documented worldview to something they could not have known — it is a simulated perspective, not a record of what they said."}
      </span>
    </div>
  );
}

/**
 * Historical knowledge boundary chip (§17). Shows the structured, restart-durable
 * boundary (e.g. "19 Jan 1990") or an explicit "unavailable" when none is
 * documented — never a silently assumed date.
 */
function KnowledgeBoundary({
  temporal,
  knowledgeCutoff,
}: {
  temporal?: TemporalContext | null;
  knowledgeCutoff?: string;
}) {
  const display =
    temporal?.boundary_display ||
    (knowledgeCutoff ? knowledgeCutoff : "") ||
    (temporal?.cutoff_year ? String(temporal.cutoff_year) : "");
  const label = display
    ? `Historical knowledge boundary: ${display}`
    : "Historical knowledge boundary unavailable";
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-slate-400"
      title={temporal?.cutoff_reason || "No documented death date (living or unknown)."}
    >
      <ShieldCheck className="h-3 w-3" aria-hidden />
      {label}
    </span>
  );
}

/**
 * Current-context source cards (§18/§19). Rendered ONLY from live-retrieved
 * items — never from the persona's historical corpus. When retrieval is
 * unavailable/empty/errored, an honest status note is shown instead of facts.
 */
function CurrentContextCards({ message }: { message: Message }) {
  if (!message.requiresCurrentContext) return null;
  const status = message.currentContextStatus || "not_required";
  const items = message.currentContext || [];

  if (status === "ok" && items.length > 0) {
    return (
      <div className="mt-2 space-y-1.5">
        <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-sky-300">
          <Globe className="h-3.5 w-3.5" aria-hidden />
          Current context · live web sources
        </div>
        <ul className="space-y-1.5">
          {items.map((it, i) => (
            <li
              key={i}
              className="rounded-lg border border-sky-400/20 bg-sky-400/[0.06] px-2.5 py-2 text-[11px]"
            >
              <div className="flex items-start justify-between gap-2">
                <a
                  href={it.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="focusable inline-flex items-center gap-1 font-medium text-sky-200 hover:underline"
                >
                  <span className="line-clamp-1">{it.title || it.domain}</span>
                  <ExternalLink className="h-3 w-3 shrink-0" aria-hidden />
                </a>
                <span className="shrink-0 text-[10px] text-slate-500">
                  {it.publication_date || "date n/a"}
                </span>
              </div>
              {it.snippet && (
                <p className="mt-1 line-clamp-3 text-slate-300">{it.snippet}</p>
              )}
              <div className="mt-1 text-[10px] text-slate-500">
                {it.source || it.domain}
                {it.retrieved_at ? ` · retrieved ${it.retrieved_at.slice(0, 10)}` : ""}
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // No live facts — surface the honest reason, never fabricate.
  const note =
    status === "unavailable"
      ? "Current web context is unavailable because no live search provider is configured. Only a simulated worldview perspective is shown below."
      : status === "error"
      ? "The live search provider errored, so no current facts are shown (they are not fabricated)."
      : status === "empty"
      ? "The live search provider returned no current results for this question."
      : "";
  if (!note) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-lg border border-accent-amber/30 bg-accent-amber/10 px-3 py-2 text-[11px] leading-relaxed text-amber-200">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{note}</span>
    </div>
  );
}

/**
 * "Why this response?" panel (§22): a concise, user-safe reasoning trace —
 * never hidden chain-of-thought, just the evidence and signals that shaped
 * the answer.
 */
function WhyPanel({
  message,
}: {
  message: Message;
}) {
  const [open, setOpen] = useState(false);
  const r = message.reasoning || {};
  const personaEvidence: any[] = Array.isArray(r.persona_evidence)
    ? r.persona_evidence
    : [];
  const concepts = message.worldviewConcepts || r.worldview_concepts || [];
  const quoteSources: string[] = Array.isArray(r.verified_quote_sources)
    ? r.verified_quote_sources
    : [];
  const conflicts: any[] = Array.isArray(r.conflicts) ? r.conflicts : [];

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="focusable inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white"
      >
        <Info className="h-3 w-3" aria-hidden />
        Why this response?
        <ChevronDown
          className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-[11px] text-slate-300">
              {r.intent && (
                <div>
                  <span className="text-slate-500">Detected intent: </span>
                  <span className="text-slate-200">{String(r.intent)}</span>
                  {message.mode && (
                    <>
                      <span className="text-slate-500"> · mode: </span>
                      <span className="text-slate-200">{message.mode}</span>
                    </>
                  )}
                </div>
              )}

              {message.temporal?.note && (
                <div>
                  <div className="mb-1 text-slate-500">Temporal context</div>
                  <p className="text-slate-300">{message.temporal.note}</p>
                </div>
              )}

              {concepts.length > 0 && (
                <div>
                  <div className="mb-1 text-slate-500">
                    Worldview concepts applied
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {concepts.map((c: string) => (
                      <span key={c} className="chip text-[10px]">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {personaEvidence.length > 0 && (
                <div>
                  <div className="mb-1 text-slate-500">
                    Documented evidence considered
                  </div>
                  <ul className="space-y-1.5">
                    {personaEvidence.map((e, i) => (
                      <li
                        key={i}
                        className="rounded-lg border border-white/5 bg-white/[0.02] px-2 py-1.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-slate-200">
                            {e.source_title || "Source"}
                          </span>
                          <span className="shrink-0 text-[10px] text-slate-500">
                            {e.is_quote ? "quote" : e.source_type}
                            {typeof e.relevance === "number"
                              ? ` · ${Math.round(e.relevance * 100)}%`
                              : ""}
                          </span>
                        </div>
                        {e.excerpt && (
                          <p className="mt-1 line-clamp-2 text-slate-400">
                            {e.excerpt}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {quoteSources.length > 0 && (
                <div>
                  <div className="mb-1 text-slate-500">
                    Source-backed quotations
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {quoteSources.map((s, i) => (
                      <span key={i} className="chip text-[10px]">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {conflicts.length > 0 && (
                <div className="rounded-lg border border-accent-amber/30 bg-accent-amber/10 px-2 py-1.5 text-amber-200">
                  Conflicting evidence detected across sources — the answer avoids
                  stating the disputed point with certainty.
                </div>
              )}

              {message.limitations && message.limitations.length > 0 && (
                <div>
                  <div className="mb-1 text-slate-500">Limitations</div>
                  <ul className="list-disc space-y-0.5 pl-4 text-slate-400">
                    {message.limitations.map((l, i) => (
                      <li key={i}>{l}</li>
                    ))}
                  </ul>
                </div>
              )}

              {personaEvidence.length === 0 &&
                concepts.length === 0 &&
                !message.temporal?.note && (
                  <p className="text-slate-500">
                    No specific documented passages were retrieved for this
                    question; the answer reflects the persona&apos;s general
                    documented style.
                  </p>
                )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ChatPanel({
  personaId,
  personaName,
  portraitUrl,
  onEvidence,
  evidenceMode,
  onToggleEvidenceMode,
  initialSessionId,
  initialMessages,
  onSessionChange,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>(
    () => (initialMessages as Message[]) ?? []
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(
    initialSessionId
  );
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [mode, setMode] = useState<ResponseMode>("persona_simulation");
  // ids of assistant messages that should type out live (cleared once done so
  // re-renders don't replay the animation).
  const [typingIds, setTypingIds] = useState<Set<string>>(new Set());
  const [language, setLanguage] = useState<LangCode>("en");
  const [speakOn, setSpeakOn] = useState(false); // auto-read replies aloud
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState({ mic: false, tts: false });
  const recognitionRef = useRef<any>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  // Detect browser speech support once on mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    setVoiceSupported({
      mic: !!SR,
      tts: !!window.speechSynthesis,
    });
    // some browsers populate voices asynchronously
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }
    return () => {
      try {
        recognitionRef.current?.stop?.();
        window.speechSynthesis?.cancel();
      } catch {
        /* noop */
      }
    };
  }, []);

  const toggleMic = () => {
    if (typeof window === "undefined") return;
    if (listening) {
      recognitionRef.current?.stop?.();
      setListening(false);
      return;
    }
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.lang = bcp47For(language);
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (e: any) => {
      let transcript = "";
      for (let i = 0; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
      }
      setInput(transcript);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recognitionRef.current = rec;
    setListening(true);
    try {
      rec.start();
    } catch {
      setListening(false);
    }
  };

  const historyFor = (): ChatTurn[] =>
    messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.content }));

  const runSend = async (text: string, replaceId?: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const history = historyFor();
    if (!replaceId) {
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "user", content: trimmed },
      ]);
      setInput("");
    }
    setLoading(true);

    try {
      const res = await sendChat({
        persona_id: personaId,
        message: trimmed,
        session_id: sessionId,
        history,
        evidence_mode: evidenceMode,
        language,
        mode,
      });
      setSessionId(res.session_id);
      if (res.session_id && res.session_id !== sessionId) {
        onSessionChange?.(res.session_id);
      }
      const assistant: Message = {
        id: replaceId ?? uid(),
        role: "assistant",
        content: res.message,
        evidence: res.evidence,
        responseType: res.response_type,
        mode: res.mode,
        temporal: res.temporal,
        worldviewConcepts: res.worldview_concepts,
        reasoning: res.reasoning,
        limitations: res.limitations,
        currentContext: res.current_context,
        currentContextStatus: res.current_context_status,
        requiresCurrentContext: res.requires_current_context,
        warnings: res.warnings,
        knowledgeCutoff: res.knowledge_cutoff,
      };
      if (speakOn) speak(res.message, language);
      setMessages((prev) =>
        replaceId
          ? prev.map((m) => (m.id === replaceId ? assistant : m))
          : [...prev, assistant]
      );
      // mark this reply to type out live
      setTypingIds((prev) => new Set(prev).add(assistant.id));
      onEvidence?.({
        evidence: res.evidence,
        coverage: res.evidence_coverage,
        limitations: res.limitations,
      });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "The persona could not respond just now. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: msg,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void runSend(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void runSend(input);
    }
  };

  const regenerate = (assistantId: string) => {
    const idx = messages.findIndex((m) => m.id === assistantId);
    if (idx <= 0) return;
    // Find the preceding user message.
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        void runSend(messages[i].content, assistantId);
        return;
      }
    }
  };

  const copy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId((c) => (c === id ? null : c)), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <div>
          <h2 className="font-display text-sm text-white">
            You&apos;re talking with {personaName}
          </h2>
          <p className="text-[11px] text-slate-500">
            Speaking in the first person, grounded in real sources.
          </p>
        </div>
        <div className="flex items-center gap-2">
        {/* Language selector */}
        <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] p-0.5">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => setLanguage(l.code)}
              className={`focusable rounded-full px-2.5 py-1 text-[11px] transition-colors ${
                language === l.code
                  ? "bg-accent-cyan/20 text-accent-cyan"
                  : "text-slate-400 hover:text-white"
              }`}
              aria-pressed={language === l.code}
              title={`Reply in ${l.label}`}
            >
              {l.label}
            </button>
          ))}
        </div>
        {/* Speaker (auto read-aloud) toggle */}
        {voiceSupported.tts && (
          <button
            type="button"
            onClick={() => {
              const next = !speakOn;
              setSpeakOn(next);
              if (!next && typeof window !== "undefined")
                window.speechSynthesis?.cancel();
            }}
            className={`focusable flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
              speakOn
                ? "border-accent-cyan/40 bg-accent-cyan/15 text-accent-cyan"
                : "border-white/10 bg-white/[0.04] text-slate-300 hover:text-white"
            }`}
            aria-pressed={speakOn}
            title={speakOn ? "Auto read-aloud is on" : "Auto read-aloud is off"}
          >
            {speakOn ? (
              <Volume2 className="h-3.5 w-3.5" aria-hidden />
            ) : (
              <VolumeX className="h-3.5 w-3.5" aria-hidden />
            )}
            Voice
          </button>
        )}
        <label className="focusable flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300">
          <ShieldCheck
            className={`h-3.5 w-3.5 ${
              evidenceMode ? "text-accent-cyan" : "text-slate-500"
            }`}
            aria-hidden
          />
          Evidence mode
          <input
            type="checkbox"
            className="sr-only"
            checked={evidenceMode}
            onChange={(e) => onToggleEvidenceMode(e.target.checked)}
            aria-label="Toggle evidence mode"
          />
          <span
            aria-hidden
            className={`relative h-4 w-7 rounded-full transition-colors ${
              evidenceMode ? "bg-accent-cyan/70" : "bg-white/15"
            }`}
          >
            <span
              className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-transform ${
                evidenceMode ? "translate-x-3.5" : "translate-x-0.5"
              }`}
            />
          </span>
        </label>
        </div>
      </div>

      {/* Response mode selector (§23) */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-5 py-2">
        <span className="text-[10px] uppercase tracking-wider text-slate-500">
          Mode
        </span>
        <div
          className="flex flex-wrap items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] p-0.5"
          role="radiogroup"
          aria-label="Response mode"
        >
          {MODES.map((m) => (
            <button
              key={m.code}
              type="button"
              role="radio"
              aria-checked={mode === m.code}
              onClick={() => setMode(m.code)}
              title={m.hint}
              className={`focusable rounded-full px-2.5 py-1 text-[11px] transition-colors ${
                mode === m.code
                  ? "bg-accent-violet/20 text-accent-violet"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <span className="hidden text-[10px] text-slate-500 sm:inline">
          {MODES.find((m) => m.code === mode)?.hint}
        </span>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="scroll-slim flex-1 space-y-4 overflow-y-auto px-5 py-5"
      >
        {messages.length === 0 && !loading && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <p className="mb-1 font-display text-lg text-white">
              Say hello to {personaName}
            </p>
            <p className="max-w-sm text-sm text-slate-500">
              Ask anything — you&apos;ll get a reply in their own voice, drawn
              from real sources you can inspect.
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${
                m.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              {m.role === "user" ? (
                <div
                  className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigoGlow-600/70 text-white"
                  aria-hidden
                >
                  <User className="h-3.5 w-3.5" />
                </div>
              ) : (
                <div
                  className="mt-0.5 rounded-full"
                  style={{ boxShadow: "0 0 0 1.5px var(--p-accent, rgba(94,231,242,0.6))" }}
                >
                  <PersonaImage
                    name={personaName}
                    portraitUrl={portraitUrl}
                    size={28}
                    glow={false}
                  />
                </div>
              )}
              <div
                className={`group max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-indigoGlow-600/25 text-slate-100"
                    : m.error
                    ? "border border-accent-rose/30 bg-accent-rose/10 text-rose-100"
                    : "glass text-slate-200"
                }`}
                style={
                  m.role === "assistant" && !m.error
                    ? { borderLeft: "2px solid var(--p-accent-soft)" }
                    : undefined
                }
              >
                {m.role === "assistant" && !m.error && (
                  <div className="mb-1.5">
                    <ResponseLabel
                      responseType={m.responseType}
                      mode={m.mode}
                    />
                  </div>
                )}
                {m.role === "assistant" && !m.error ? (
                  <TypewriterText
                    text={m.content}
                    animate={typingIds.has(m.id)}
                    onTick={() =>
                      scrollRef.current?.scrollTo({
                        top: scrollRef.current.scrollHeight,
                      })
                    }
                    onDone={() =>
                      setTypingIds((prev) => {
                        if (!prev.has(m.id)) return prev;
                        const next = new Set(prev);
                        next.delete(m.id);
                        return next;
                      })
                    }
                  />
                ) : (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                )}
                {m.role === "assistant" && !m.error && !typingIds.has(m.id) && (
                  <>
                    <CurrentContextCards message={m} />
                    <TemporalBanner temporal={m.temporal} />
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <KnowledgeBoundary
                        temporal={m.temporal}
                        knowledgeCutoff={m.knowledgeCutoff}
                      />
                    </div>
                    <WhyPanel message={m} />
                  </>
                )}
                {m.role === "assistant" && !m.error && !typingIds.has(m.id) && (
                  <div className="mt-2 flex items-center gap-3 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      type="button"
                      onClick={() => copy(m.id, m.content)}
                      className="focusable inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white"
                      aria-label="Copy response"
                    >
                      {copiedId === m.id ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                      {copiedId === m.id ? "Copied" : "Copy"}
                    </button>
                    {voiceSupported.tts && (
                      <button
                        type="button"
                        onClick={() => speak(m.content, language)}
                        className="focusable inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white"
                        aria-label="Read aloud"
                      >
                        <Volume2 className="h-3 w-3" />
                        Listen
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => regenerate(m.id)}
                      disabled={loading}
                      className="focusable inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white disabled:opacity-40"
                      aria-label="Regenerate response"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Regenerate
                    </button>
                    {m.evidence && m.evidence.length > 0 && (
                      <span className="text-[11px] text-slate-500">
                        {m.evidence.length} source
                        {m.evidence.length === 1 ? "" : "s"}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <div className="flex gap-3">
            <div
              className="mt-0.5 rounded-full"
              style={{ boxShadow: "0 0 0 1.5px var(--p-accent, rgba(94,231,242,0.6))" }}
            >
              <PersonaImage
                name={personaName}
                portraitUrl={portraitUrl}
                size={28}
                glow={false}
              />
            </div>
            <div className="glass max-w-[60%] space-y-2 rounded-2xl px-4 py-3">
              <div className="h-2.5 w-40 rounded shimmer" />
              <div className="h-2.5 w-56 rounded shimmer" />
              <div className="h-2.5 w-32 rounded shimmer" />
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-white/10 p-3"
      >
        <div className="glass flex items-end gap-2 rounded-2xl p-2">
          <label htmlFor="chat-input" className="sr-only">
            Message {personaName}
          </label>
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={`Message ${personaName}…`}
            className="focusable max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-slate-100 placeholder:text-slate-500"
          />
          {voiceSupported.mic && (
            <button
              type="button"
              onClick={toggleMic}
              aria-label={listening ? "Stop listening" : "Speak your message"}
              title={listening ? "Listening… tap to stop" : "Speak your message"}
              className={`focusable inline-flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                listening
                  ? "animate-pulse border-accent-rose/50 bg-accent-rose/20 text-rose-200"
                  : "border-white/10 bg-white/[0.05] text-slate-300 hover:text-white"
              }`}
            >
              {listening ? (
                <MicOff className="h-4 w-4" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </button>
          )}
          <button
            type="submit"
            disabled={loading || !input.trim()}
            aria-label="Send message"
            className="focusable inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigoGlow-500 to-accent-violet text-white transition-opacity disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
