"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { getJob, getProviders } from "@/lib/api";
import { useJobStream } from "@/lib/useJobStream";
import { computePhaseState } from "@/lib/buildPhases";
import ReconstructionRail from "@/components/build/ReconstructionRail";
import MetricsStrip from "@/components/build/MetricsStrip";
import ActivityFeed from "@/components/build/ActivityFeed";
import SourceActivity from "@/components/build/SourceActivity";
import ReadyPanel from "@/components/build/ReadyPanel";
import FailedPanel from "@/components/build/FailedPanel";
import PersonaImage from "@/components/PersonaImage";
import EthicalNotice from "@/components/EthicalNotice";
import { personaAccent } from "@/lib/theme";

const BackgroundScene = dynamic(
  () => import("@/components/three/BackgroundScene"),
  { ssr: false }
);
const ReconstructionScene = dynamic(
  () => import("@/components/three/ReconstructionScene"),
  { ssr: false }
);

export default function BuildPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = String(params.jobId || "");

  const stream = useJobStream(jobId);
  const [personaName, setPersonaName] = useState("");
  const [personaId, setPersonaId] = useState("");
  const [portraitUrl, setPortraitUrl] = useState("");
  const [providerWarnings, setProviderWarnings] = useState<string[]>([]);

  const completed = stream.status === "completed";
  const failed = stream.status === "failed";
  const jobDone = completed || failed;

  const resolvedPersonaId = stream.personaId || personaId;

  // Resolve the persona for this job, then poll it until the portrait is
  // collected (filled in mid-pipeline) or the job finishes.
  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let pid = personaId;

    const poll = async () => {
      try {
        const { getPersona } = await import("@/lib/api");
        if (!pid) {
          const job = await getJob(jobId);
          pid = job.persona_id || "";
          if (active && pid) setPersonaId(pid);
        }
        if (!pid) {
          if (active && !jobDone) timer = setTimeout(poll, 3000);
          return;
        }
        const p = await getPersona(pid);
        if (!active) return;
        if (p.name) setPersonaName(p.name);
        if (p.portrait_url) setPortraitUrl(p.portrait_url);
        if (!p.portrait_url && !jobDone) timer = setTimeout(poll, 3000);
      } catch {
        if (active && !jobDone) timer = setTimeout(poll, 3000);
      }
    };

    void poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, jobDone]);

  // Optional-provider availability, used to build honest completion warnings.
  useEffect(() => {
    let active = true;
    getProviders()
      .then((providers) => {
        if (!active) return;
        const warn: string[] = [];
        const byKey = new Map(providers.map((p) => [p.key, p]));
        const web = byKey.get("web_search");
        const yt = byKey.get("youtube");
        if (web && !web.configured) warn.push("Web search was not configured.");
        if (yt && !yt.configured) warn.push("YouTube discovery was not configured.");
        setProviderWarnings(warn);
      })
      .catch(() => setProviderWarnings([]));
    return () => {
      active = false;
    };
  }, []);

  const phase = useMemo(
    () => computePhaseState(stream.stages, stream.currentStage, stream.progress, stream.status),
    [stream.stages, stream.currentStage, stream.progress, stream.status]
  );

  const evidenceComplete = useMemo(() => {
    if (completed) return true;
    return (stream.stages || []).some(
      (s) => s.key === "validating_evidence" && s.status === "completed"
    );
  }, [stream.stages, completed]);

  const sceneCounts = useMemo(
    () => ({
      sources: Number(stream.stats?.sources ?? 0),
      documents: Number(stream.stats?.documents ?? 0),
      topics: Number(stream.stats?.topics ?? 0),
      chunks: Number(stream.stats?.chunks ?? 0),
      embeddings: Number(stream.stats?.embeddings ?? 0),
    }),
    [stream.stats]
  );

  // Completion warnings: unavailable optional providers, and the honest case
  // where no public sources were discovered at all.
  const readyWarnings = useMemo(() => {
    const w = [...providerWarnings];
    if (Number(stream.stats?.sources ?? 0) === 0) {
      w.unshift("No public sources were discovered for this persona.");
    }
    return w;
  }, [providerWarnings, stream.stats]);

  const enterPersona = () => {
    if (resolvedPersonaId) router.push(`/persona/${resolvedPersonaId}`);
  };

  const statusCaption = failed
    ? "Reconstruction paused"
    : completed
    ? "Persona ready"
    : "Reconstructing public knowledge";

  return (
    <main
      className="relative flex min-h-screen flex-col overflow-hidden px-4 py-8 sm:px-6"
      style={personaAccent(resolvedPersonaId || personaName || jobId)}
    >
      <BackgroundScene intensity="subtle" />

      <div className="relative z-10 mx-auto w-full max-w-6xl">
        {/* Header: back + phase rail */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
          <button
            type="button"
            onClick={() => router.push("/explore")}
            className="focusable inline-flex w-fit items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06]"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
            Explore
          </button>
          <div className="min-w-0 flex-1">
            <ReconstructionRail phase={phase} />
          </div>
        </div>

        {failed ? (
          <div className="mx-auto max-w-xl py-6">
            <FailedPanel
              jobId={jobId}
              error={stream.error}
              stats={stream.stats}
              onRetry={() => router.push("/explore")}
              onBack={() => router.push("/")}
            />
          </div>
        ) : (
          <>
            <div
              className={`grid gap-5 ${
                completed ? "lg:grid-cols-2" : "lg:grid-cols-3"
              }`}
            >
              {/* Reconstruction visualization */}
              <section
                className={`glass-panel relative overflow-hidden ${
                  completed ? "" : "lg:col-span-2"
                }`}
                aria-label="Persona reconstruction visualization"
              >
                <div className="relative h-[320px] w-full sm:h-[400px]">
                  <ReconstructionScene
                    phaseIndex={phase.current}
                    done={completed}
                    counts={sceneCounts}
                  />
                  {/* Center identity overlay (only while building, per spec) */}
                  {!completed && (
                    <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                      <PersonaImage
                        name={personaName || "New persona"}
                        portraitUrl={portraitUrl}
                        size={88}
                        glow
                      />
                      <p className="mt-3 font-display text-lg font-semibold text-white drop-shadow">
                        {personaName || "Identifying…"}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-300/90">{statusCaption}</p>
                    </div>
                  )}
                </div>
              </section>

              {/* Right column: running -> activity + sources; done -> ready */}
              {completed ? (
                <ReadyPanel
                  personaId={resolvedPersonaId}
                  personaName={personaName}
                  portraitUrl={portraitUrl}
                  stats={stream.stats}
                  warnings={readyWarnings}
                  onEnter={enterPersona}
                />
              ) : (
                <aside className="flex flex-col gap-5">
                  <div className="glass-panel flex h-[240px] flex-col p-4 sm:h-[260px]">
                    <ActivityFeed
                      events={stream.events}
                      connected={stream.connected}
                      done={jobDone}
                    />
                  </div>
                  <div className="glass-panel p-4">
                    {resolvedPersonaId ? (
                      <SourceActivity personaId={resolvedPersonaId} done={jobDone} />
                    ) : (
                      <p className="text-xs text-slate-500">
                        Waiting for source discovery to begin…
                      </p>
                    )}
                  </div>
                </aside>
              )}
            </div>

            {/* Metrics strip (running or done) */}
            <div className="mt-5">
              <MetricsStrip stats={stream.stats} evidenceComplete={evidenceComplete} />
            </div>

            {/* Source activity for the completed layout (kept accessible) */}
            {completed && resolvedPersonaId && (
              <div className="glass-panel mt-5 p-4">
                <SourceActivity personaId={resolvedPersonaId} done={jobDone} />
              </div>
            )}

            {!stream.connected && !jobDone && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-4 text-center text-xs text-slate-500"
              >
                Connecting to the live pipeline…
              </motion.p>
            )}
          </>
        )}

        {/* Compact ethical info bar (not a legal banner) */}
        <div className="mx-auto mt-8 max-w-3xl">
          <EthicalNotice variant="inline" />
        </div>
      </div>
    </main>
  );
}
