"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ArrowLeft, Loader2, Network, X } from "lucide-react";
import { ApiError, getKnowledgeGraph } from "@/lib/api";
import type { KnowledgeGraph } from "@/lib/types";

const KnowledgeGraph3D = dynamic(
  () => import("@/components/three/KnowledgeGraph3D"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Rendering graph…
      </div>
    ),
  }
);

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

export default function KnowledgePage() {
  const params = useParams();
  const personaId = String(params.personaId || "");
  const reducedMotion = usePrefersReducedMotion();

  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = () => {
    setError(null);
    getKnowledgeGraph(personaId)
      .then(setGraph)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not load the knowledge graph."
        )
      );
  };

  useEffect(() => {
    if (personaId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personaId]);

  const selectedNode = useMemo(
    () => graph?.nodes.find((n) => n.id === selectedId) || null,
    [graph, selectedId]
  );

  const relatedNodes = useMemo(() => {
    if (!graph || !selectedId) return [];
    const ids = new Set<string>();
    graph.edges.forEach((e) => {
      if (e.source_node_id === selectedId) ids.add(e.target_node_id);
      if (e.target_node_id === selectedId) ids.add(e.source_node_id);
    });
    return graph.nodes.filter((n) => ids.has(n.id));
  }, [graph, selectedId]);

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-void-950">
      {/* Top bar */}
      <div className="absolute left-0 right-0 top-0 z-20 flex items-center justify-between px-4 py-3">
        <Link
          href={`/persona/${personaId}`}
          className="focusable inline-flex items-center gap-2 rounded-lg border border-white/10 bg-void-900/60 px-3 py-1.5 text-sm text-slate-300 backdrop-blur hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Profile
        </Link>
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-void-900/60 px-3 py-1.5 text-sm text-slate-300 backdrop-blur">
          <Network className="h-4 w-4 text-accent-cyan" aria-hidden />
          Knowledge graph
        </div>
      </div>

      {error && (
        <div className="flex h-full items-center justify-center px-6">
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
        </div>
      )}

      {!error && !graph && (
        <div className="flex h-full items-center justify-center text-slate-500">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading knowledge…
        </div>
      )}

      {!error && graph && graph.nodes.length === 0 && (
        <div className="flex h-full items-center justify-center px-6">
          <div className="glass-panel max-w-md p-8 text-center text-slate-400">
            <Network className="mx-auto mb-3 h-8 w-8 text-slate-600" />
            No knowledge graph is available for this persona yet.
          </div>
        </div>
      )}

      {!error && graph && graph.nodes.length > 0 && (
        <div className="h-full w-full">
          <KnowledgeGraph3D
            nodes={graph.nodes}
            edges={graph.edges}
            selectedId={selectedId}
            onSelect={setSelectedId}
            reducedMotion={reducedMotion}
          />
        </div>
      )}

      {/* Legend */}
      {graph && graph.nodes.length > 0 && !selectedNode && (
        <div className="pointer-events-none absolute bottom-4 left-4 z-10 rounded-lg border border-white/10 bg-void-900/60 px-3 py-2 text-[11px] text-slate-400 backdrop-blur">
          Drag to rotate · scroll to zoom · click a node for detail
        </div>
      )}

      {/* Detail drawer */}
      <AnimatePresence>
        {selectedNode && (
          <motion.aside
            key={selectedNode.id}
            initial={{ x: 340, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 340, opacity: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            className="absolute inset-y-0 right-0 z-30 w-full max-w-sm border-l border-white/10 bg-void-950/85 p-6 backdrop-blur-xl"
            aria-label={`Details for ${selectedNode.label}`}
          >
            <div className="mb-4 flex items-start justify-between">
              <span className="chip text-[10px] uppercase tracking-wider">
                {selectedNode.group}
              </span>
              <button
                type="button"
                onClick={() => setSelectedId(null)}
                className="focusable rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-white"
                aria-label="Close detail"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <h2 className="font-display text-2xl text-white">
              {selectedNode.label}
            </h2>
            <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
              <span>Weight</span>
              <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigoGlow-500 to-accent-cyan"
                  style={{
                    width: `${Math.min(100, (selectedNode.weight || 1) * 20)}%`,
                  }}
                />
              </div>
              <span className="tabular-nums">
                {selectedNode.weight.toFixed(1)}
              </span>
            </div>

            {selectedNode.description && (
              <p className="mt-4 text-sm leading-relaxed text-slate-300">
                {selectedNode.description}
              </p>
            )}

            {relatedNodes.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-2 text-[11px] uppercase tracking-wider text-slate-500">
                  Related ({relatedNodes.length})
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {relatedNodes.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => setSelectedId(n.id)}
                      className="focusable chip transition-colors hover:border-indigoGlow-400/50 hover:text-white"
                    >
                      {n.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </motion.aside>
        )}
      </AnimatePresence>
    </main>
  );
}
