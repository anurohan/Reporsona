// Maps the backend's 15-stage build pipeline onto six human-readable
// reconstruction phases used by the build screen. Pure, framework-agnostic:
// no fake data — everything is derived from real job stage keys / status.

import type { JobStage, JobStatus } from "./types";

export interface Phase {
  id: string;
  /** Full label shown in the active state. */
  label: string;
  /** Compact label for the horizontal rail. */
  short: string;
}

// Index 0..5. "Persona ready" is a terminal success state, not a rail step.
export const PHASES: Phase[] = [
  { id: "identify", label: "Identifying the person", short: "Identify" },
  { id: "discover", label: "Discovering public sources", short: "Discover" },
  { id: "understand", label: "Understanding the material", short: "Understand" },
  { id: "build", label: "Building the knowledge structure", short: "Build" },
  { id: "construct", label: "Constructing the persona", short: "Construct" },
  { id: "verify", label: "Validating evidence", short: "Verify" },
];

// Backend stage key -> phase index (1..5). Anything before the first stage
// completes is treated as phase 0 (Identify).
const STAGE_PHASE: Record<string, number> = {
  discovering_sources: 1,
  validating_sources: 1,
  collecting_data: 1,
  processing_documents: 2,
  processing_audio: 2,
  transcribing_speech: 2,
  running_ocr: 2,
  cleaning_text: 2,
  running_nlp: 2,
  generating_embeddings: 3,
  building_index: 3,
  analyzing_patterns: 4,
  constructing_persona: 4,
  validating_evidence: 5,
  persona_ready: 5,
};

export type PhaseStatus = "completed" | "active" | "future";

export interface PhaseView extends Phase {
  index: number;
  status: PhaseStatus;
}

export interface PhaseState {
  /** 0-based index of the currently active phase (0..5). */
  current: number;
  /** True when the whole build has completed. */
  done: boolean;
  /** Per-phase view models for the rail. */
  phases: PhaseView[];
  /** e.g. "Step 3 of 6" or "Complete". */
  stepLabel: string;
  /** Full label of the active phase. */
  activeLabel: string;
}

function phaseForStage(key: string | undefined): number {
  if (!key) return 0;
  return STAGE_PHASE[key] ?? 0;
}

/**
 * Derive the reconstruction phase state from real job data. Uses the furthest
 * stage that has started (processing) or completed; falls back to the raw
 * progress fraction when no stage list is present yet.
 */
export function computePhaseState(
  stages: JobStage[] | undefined,
  currentStage: string | undefined,
  progress: number,
  status: JobStatus
): PhaseState {
  const done = status === "completed";

  let reached = 0;
  if (stages && stages.length) {
    for (const s of stages) {
      if (s.status === "completed" || s.status === "processing") {
        reached = Math.max(reached, phaseForStage(s.key));
      }
    }
  }
  // The current stage may lead the completed set.
  reached = Math.max(reached, phaseForStage(currentStage));

  // Fallback: if nothing has a stage yet but progress is moving, approximate.
  if (reached === 0 && !currentStage && progress > 0) {
    reached = Math.min(5, Math.max(1, Math.round(progress * 5)));
  }

  const current = done ? 6 : Math.min(5, reached);

  const phases: PhaseView[] = PHASES.map((p, index) => {
    let s: PhaseStatus;
    if (done || index < current) s = "completed";
    else if (index === current) s = "active";
    else s = "future";
    return { ...p, index, status: s };
  });

  const stepLabel = done ? "Complete" : `Step ${current + 1} of ${PHASES.length}`;
  const activeLabel = done
    ? "Reconstruction complete"
    : PHASES[Math.min(current, PHASES.length - 1)].label;

  return { current, done, phases, stepLabel, activeLabel };
}
