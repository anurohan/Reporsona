"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import { useReducedMotion } from "framer-motion";
import * as THREE from "three";

export interface ReconstructionSceneProps {
  /** 0..5 active phase index (see buildPhases). */
  phaseIndex: number;
  done: boolean;
  counts: {
    sources?: number;
    documents?: number;
    topics?: number;
    chunks?: number;
    embeddings?: number;
  };
  reducedMotion?: boolean;
}

interface SatCfg {
  id: string;
  label: string;
  color: string;
  /** Phase index at which this node becomes active. */
  activeAt: number;
  /** Optional real-count key; presence (>0) also activates the node. */
  countKey?: keyof ReconstructionSceneProps["counts"];
}

// The reconstruction metaphor: sources / documents / ideas / topics / events /
// evidence orbit a central persona core. Activation is tied to the REAL phase
// the pipeline has reached (and real counts where available) — never random.
const SATELLITES: SatCfg[] = [
  { id: "sources", label: "Sources", color: "#5ee7f2", activeAt: 1, countKey: "sources" },
  { id: "documents", label: "Documents", color: "#8b93ff", activeAt: 2, countKey: "documents" },
  { id: "events", label: "Events", color: "#f5c15a", activeAt: 2 },
  { id: "ideas", label: "Ideas", color: "#a78bfa", activeAt: 4 },
  { id: "topics", label: "Topics", color: "#fb7bb0", activeAt: 4, countKey: "topics" },
  { id: "evidence", label: "Evidence", color: "#6ee7a8", activeAt: 5 },
];

const RADIUS = 3.4;

function isActive(
  cfg: SatCfg,
  phaseIndex: number,
  done: boolean,
  counts: ReconstructionSceneProps["counts"]
): boolean {
  if (done) return true;
  if (phaseIndex >= cfg.activeAt) return true;
  if (cfg.countKey && Number(counts[cfg.countKey] ?? 0) > 0) return true;
  return false;
}

function Satellite({
  position,
  color,
  label,
  active,
}: {
  position: THREE.Vector3;
  color: string;
  label: string;
  active: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshStandardMaterial>(null);

  useFrame(() => {
    const m = ref.current;
    if (!m) return;
    const target = active ? 1 : 0.55;
    m.scale.lerp(new THREE.Vector3(target, target, target), 0.12);
    if (matRef.current) {
      const targetE = active ? 1.5 : 0.25;
      matRef.current.emissiveIntensity +=
        (targetE - matRef.current.emissiveIntensity) * 0.1;
      const targetO = active ? 1 : 0.4;
      matRef.current.opacity += (targetO - matRef.current.opacity) * 0.1;
    }
  });

  return (
    <group position={position}>
      <mesh ref={ref}>
        <sphereGeometry args={[0.32, 24, 24]} />
        <meshStandardMaterial
          ref={matRef}
          color={color}
          emissive={color}
          emissiveIntensity={0.25}
          transparent
          opacity={0.4}
          roughness={0.35}
          metalness={0.1}
        />
      </mesh>
      {active && (
        <Html center distanceFactor={12} position={[0, 0.62, 0]} className="pointer-events-none">
          <div className="whitespace-nowrap rounded border border-white/10 bg-void-900/80 px-1.5 py-0.5 text-[10px] text-slate-200 backdrop-blur">
            {label}
          </div>
        </Html>
      )}
    </group>
  );
}

function Core({
  active,
  done,
  reducedMotion,
}: {
  active: boolean;
  done: boolean;
  reducedMotion: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshStandardMaterial>(null);
  useFrame((state) => {
    const m = ref.current;
    if (!m) return;
    if (!reducedMotion) {
      const pulse = done ? 1.05 : active ? 1 + Math.sin(state.clock.elapsedTime * 2) * 0.04 : 1;
      m.scale.setScalar(pulse);
    }
    if (matRef.current) {
      const targetE = done ? 2.2 : active ? 1.6 : 0.6;
      matRef.current.emissiveIntensity +=
        (targetE - matRef.current.emissiveIntensity) * 0.08;
    }
  });
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.95, 40, 40]} />
      <meshStandardMaterial
        ref={matRef}
        color="#6b6bff"
        emissive="#8b93ff"
        emissiveIntensity={0.6}
        roughness={0.25}
        metalness={0.2}
      />
    </mesh>
  );
}

function EvidenceRing({ active }: { active: boolean }) {
  const matRef = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(() => {
    if (matRef.current) {
      const target = active ? 0.55 : 0.12;
      matRef.current.opacity += (target - matRef.current.opacity) * 0.08;
    }
  });
  return (
    <mesh rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[RADIUS + 0.9, 0.02, 16, 120]} />
      <meshBasicMaterial
        ref={matRef}
        color="#6ee7a8"
        transparent
        opacity={0.12}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

function Rig({ phaseIndex, done, counts, reducedMotion }: ReconstructionSceneProps) {
  const group = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (reducedMotion || !group.current) return;
    // Rotation settles (slows) once the build completes.
    group.current.rotation.y += delta * (done ? 0.05 : 0.16);
  });

  const nodes = useMemo(
    () =>
      SATELLITES.map((cfg, i) => {
        const angle = (i / SATELLITES.length) * Math.PI * 2;
        const position = new THREE.Vector3(
          Math.cos(angle) * RADIUS,
          Math.sin(angle) * RADIUS,
          0
        );
        return { cfg, position };
      }),
    []
  );

  const coreActive = done || phaseIndex >= 4;
  const evidenceActive = done || phaseIndex >= 5;

  return (
    <group ref={group}>
      <EvidenceRing active={evidenceActive} />
      {nodes.map(({ cfg, position }) => {
        const active = isActive(cfg, phaseIndex, done, counts);
        return (
          <group key={cfg.id}>
            <Line
              points={[new THREE.Vector3(0, 0, 0), position]}
              color={active ? cfg.color : "#3a3f66"}
              lineWidth={active ? 1.1 : 0.5}
              transparent
              opacity={active ? 0.5 : 0.14}
            />
            <Satellite
              position={position}
              color={cfg.color}
              label={cfg.label}
              active={active}
            />
          </group>
        );
      })}
      <Core active={coreActive} done={done} reducedMotion={!!reducedMotion} />
    </group>
  );
}

/**
 * Lightweight R3F reconstruction visualization. A persona core surrounded by
 * source/document/idea/topic/event/evidence nodes that light up as the real
 * build pipeline advances. No fake graph data — activation maps to the actual
 * phase and stat counts. Honours reduced-motion (no rotation / pulsing).
 */
export default function ReconstructionScene(props: ReconstructionSceneProps) {
  const prefersReduced = useReducedMotion();
  const reducedMotion = props.reducedMotion ?? !!prefersReduced;
  return (
    <Canvas
      camera={{ position: [0, 0, 10.5], fov: 52 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
    >
      <fog attach="fog" args={["#05060f", 12, 26]} />
      <ambientLight intensity={0.55} />
      <pointLight position={[8, 8, 8]} intensity={1.1} />
      <pointLight position={[-10, -6, -4]} intensity={0.5} color="#5ee7f2" />
      <Rig {...props} reducedMotion={reducedMotion} />
    </Canvas>
  );
}
