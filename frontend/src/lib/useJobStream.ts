"use client";

import { useEffect, useRef, useState } from "react";
import { getJob, jobStreamUrl } from "./api";
import type {
  Job,
  JobActivityEvent,
  JobStage,
  JobStreamEvent,
  JobStatus,
} from "./types";

const NAMED_EVENTS = [
  "SNAPSHOT",
  "JOB_STARTED",
  "SOURCE_DISCOVERY",
  "SOURCE_VALIDATION",
  "DOCUMENT_PROCESSING",
  "AUDIO_PROCESSING",
  "TRANSCRIPTION",
  "OCR_PROCESSING",
  "NLP_ANALYSIS",
  "EMBEDDING",
  "VECTOR_INDEXING",
  "PERSONALITY_ANALYSIS",
  "PERSONA_BUILDING",
  "EVIDENCE_VALIDATION",
  "COMPLETED",
  "FAILED",
  "PING",
] as const;

export interface JobStreamState {
  status: JobStatus;
  progress: number;
  currentStage: string;
  stages: JobStage[];
  stats: Record<string, any>;
  error: string;
  personaId: string;
  connected: boolean;
  /** Real-time activity log derived from SSE frames + stat deltas. */
  events: JobActivityEvent[];
}

const INITIAL: JobStreamState = {
  status: "pending",
  progress: 0,
  currentStage: "",
  stages: [],
  stats: {},
  error: "",
  personaId: "",
  connected: false,
  events: [],
};

const MAX_EVENTS = 60;
let activitySeq = 0;

const STAGE_MILESTONES: Record<string, { label: string; detail: string }> = {
  building_index: { label: "KNOWLEDGE INDEX BUILT", detail: "Vector store ready" },
  constructing_persona: { label: "PERSONA CONSTRUCTED", detail: "Core model assembled" },
  validating_evidence: { label: "EVIDENCE VALIDATED", detail: "Claims checked against sources" },
};

// Stat fields we surface as activity, in a sensible narrative order.
const STAT_ACTIVITY: {
  key: string;
  kind: JobActivityEvent["kind"];
  label: string;
  noun: string;
}[] = [
  { key: "sources", kind: "source", label: "SOURCE DISCOVERED", noun: "sources" },
  { key: "documents", kind: "document", label: "DOCUMENT PROCESSED", noun: "documents" },
  { key: "transcripts", kind: "document", label: "SPEECH TRANSCRIBED", noun: "transcripts" },
  { key: "chunks", kind: "chunk", label: "KNOWLEDGE CHUNKS", noun: "chunks" },
  { key: "embeddings", kind: "embedding", label: "EMBEDDINGS GENERATED", noun: "embeddings" },
  { key: "topics", kind: "topic", label: "TOPIC EXTRACTED", noun: "topics" },
];

/**
 * Derive real activity-feed entries from the transition between the previous
 * state and an incoming SSE frame. Only reports things the backend actually
 * reported (stat increases, milestone stage completions). Never invents data.
 */
function deriveActivity(
  prev: JobStreamState,
  data: JobStreamEvent,
  nextStats: Record<string, any>
): JobActivityEvent[] {
  const out: JobActivityEvent[] = [];
  const now = Date.now();

  // Stat deltas (a metric moved up -> the pipeline produced something).
  for (const f of STAT_ACTIVITY) {
    const before = Number(prev.stats?.[f.key] ?? 0);
    const after = Number(nextStats?.[f.key] ?? 0);
    if (after > before) {
      out.push({
        id: `a${activitySeq++}`,
        kind: f.kind,
        label: f.label,
        detail: `${after} ${f.noun}`,
        ts: now,
      });
    }
  }

  // Milestone stage completions.
  if (data.status === "completed" && data.stage && STAGE_MILESTONES[data.stage]) {
    const m = STAGE_MILESTONES[data.stage];
    out.push({
      id: `a${activitySeq++}`,
      kind: data.stage === "validating_evidence" ? "evidence" : "milestone",
      label: m.label,
      detail: m.detail,
      ts: now,
    });
  }

  return out;
}

/**
 * Subscribes to `/api/jobs/{jobId}/stream` via EventSource.
 * Handles every named backend event plus the `message` fallback and PING
 * keep-alives. Falls back to a one-shot GET /jobs/{id} if the stream never
 * connects, and cleans up on unmount.
 */
export function useJobStream(jobId: string | null | undefined): JobStreamState {
  const [state, setState] = useState<JobStreamState>(INITIAL);
  const doneRef = useRef(false);

  useEffect(() => {
    if (!jobId) return;
    doneRef.current = false;
    setState(INITIAL);

    let es: EventSource | null = null;
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const applyEvent = (data: JobStreamEvent) => {
      setState((prev) => {
        const mergedStats = data.stats
          ? { ...prev.stats, ...data.stats }
          : prev.stats;
        const next: JobStreamState = {
          ...prev,
          connected: true,
          progress:
            typeof data.progress === "number" ? data.progress : prev.progress,
          currentStage: data.stage || prev.currentStage,
          stages: data.stages && data.stages.length ? data.stages : prev.stages,
          stats: mergedStats,
        };
        if (data.status) next.status = data.status;
        if (data.error) next.error = data.error;
        if (data.persona_id) next.personaId = data.persona_id;

        if (data.event === "COMPLETED") {
          next.status = "completed";
          next.progress = 1;
        } else if (data.event === "FAILED") {
          next.status = "failed";
        }

        const derived = deriveActivity(prev, data, mergedStats);
        if (derived.length) {
          next.events = [...prev.events, ...derived].slice(-MAX_EVENTS);
        }
        return next;
      });

      if (data.event === "COMPLETED" || data.event === "FAILED") {
        doneRef.current = true;
        es?.close();
      }
    };

    const handle = (raw: MessageEvent) => {
      if (!raw?.data) return;
      try {
        const data = JSON.parse(raw.data) as JobStreamEvent;
        if (data.event === "PING") {
          setState((prev) => ({ ...prev, connected: true }));
          return;
        }
        applyEvent(data);
      } catch {
        /* ignore malformed frame */
      }
    };

    const applyJob = (job: Job) => {
      setState((prev) => {
        const mergedStats = { ...prev.stats, ...(job.stats || {}) };
        // Reuse the same delta logic; synthesize a frame from the polled job so
        // the activity feed still populates when SSE is unavailable.
        const derived = deriveActivity(
          prev,
          {
            event: "SNAPSHOT",
            job_id: job.id,
            stage: job.current_stage,
            status: job.status,
            progress: job.progress,
          } as JobStreamEvent,
          mergedStats
        );
        return {
          ...prev,
          status: job.status,
          progress: job.progress,
          currentStage: job.current_stage,
          stages: job.stages?.length ? job.stages : prev.stages,
          stats: mergedStats,
          error: job.error || prev.error,
          personaId: job.persona_id || prev.personaId,
          events: derived.length
            ? [...prev.events, ...derived].slice(-MAX_EVENTS)
            : prev.events,
        };
      });
      if (job.status === "completed" || job.status === "failed") {
        doneRef.current = true;
      }
    };

    // Polling fallback if EventSource is unavailable or never connects.
    const startPolling = () => {
      if (pollTimer) return;
      const tick = async () => {
        if (doneRef.current) {
          if (pollTimer) clearInterval(pollTimer);
          return;
        }
        try {
          applyJob(await getJob(jobId));
        } catch {
          /* keep trying */
        }
      };
      void tick();
      pollTimer = setInterval(tick, 2000);
    };

    if (typeof window !== "undefined" && "EventSource" in window) {
      try {
        es = new EventSource(jobStreamUrl(jobId));
        es.onmessage = handle; // generic 'message' fallback
        NAMED_EVENTS.forEach((name) =>
          es!.addEventListener(name, handle as EventListener)
        );
        es.onerror = () => {
          // If the stream closed before completion, fall back to polling.
          if (!doneRef.current) startPolling();
        };
        // Safety net: if nothing arrives promptly, start polling too.
        fallbackTimer = setTimeout(() => {
          setState((prev) => {
            if (!prev.connected) startPolling();
            return prev;
          });
        }, 4000);
      } catch {
        startPolling();
      }
    } else {
      startPolling();
    }

    return () => {
      doneRef.current = true;
      if (fallbackTimer) clearTimeout(fallbackTimer);
      if (pollTimer) clearInterval(pollTimer);
      if (es) {
        NAMED_EVENTS.forEach((name) =>
          es!.removeEventListener(name, handle as EventListener)
        );
        es.close();
      }
    };
  }, [jobId]);

  return state;
}
