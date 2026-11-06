"use client";

import { useMemo, useRef, useState } from "react";
import { Canvas, ThreeEvent, useFrame } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { KnowledgeEdge, KnowledgeNode } from "@/lib/types";

interface KnowledgeGraph3DProps {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  reducedMotion?: boolean;
}

interface PositionedNode extends KnowledgeNode {
  position: THREE.Vector3;
  radius: number;
  color: THREE.Color;
}

const GROUP_COLORS: Record<string, string> = {
  concept: "#8b93ff",
  theme: "#5ee7f2",
  viewpoint: "#a78bfa",
  domain: "#f5c15a",
  person: "#fb7bb0",
};

function colorForGroup(group: string): THREE.Color {
  return new THREE.Color(GROUP_COLORS[group] || "#8b93ff");
}

// Distribute nodes on a Fibonacci sphere so the layout is stable & readable.
function layoutNodes(nodes: KnowledgeNode[]): PositionedNode[] {
  const n = nodes.length || 1;
  const radiusBase = 6 + Math.min(6, n * 0.12);
  const golden = Math.PI * (3 - Math.sqrt(5));
  const maxWeight = Math.max(1, ...nodes.map((x) => x.weight || 1));

  return nodes.map((node, i) => {
    const y = 1 - (i / Math.max(1, n - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * i;
    const pos = new THREE.Vector3(
      Math.cos(theta) * r,
      y,
      Math.sin(theta) * r
    ).multiplyScalar(radiusBase);
    const norm = (node.weight || 1) / maxWeight;
    return {
      ...node,
      position: pos,
      radius: 0.25 + norm * 0.55,
      color: colorForGroup(node.group),
    };
  });
}

function NodeMesh({
  node,
  selected,
  dimmed,
  onSelect,
}: {
  node: PositionedNode;
  selected: boolean;
  dimmed: boolean;
  onSelect: (id: string | null) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const ref = useRef<THREE.Mesh>(null);

  useFrame(() => {
    const m = ref.current;
    if (!m) return;
    const target = selected || hovered ? 1.35 : 1;
    m.scale.lerp(new THREE.Vector3(target, target, target), 0.18);
  });

  const emissive = selected || hovered ? 1.4 : 0.55;
  const opacity = dimmed ? 0.25 : 1;

  return (
    <group position={node.position}>
      <mesh
        ref={ref}
        onPointerOver={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          onSelect(selected ? null : node.id);
        }}
      >
        <sphereGeometry args={[node.radius, 24, 24]} />
        <meshStandardMaterial
          color={node.color}
          emissive={node.color}
          emissiveIntensity={emissive}
          transparent
          opacity={opacity}
          roughness={0.35}
          metalness={0.1}
        />
      </mesh>
      {(hovered || selected) && (
        <Html
          center
          distanceFactor={16}
          position={[0, node.radius + 0.5, 0]}
          className="pointer-events-none"
        >
          <div className="whitespace-nowrap rounded-md border border-white/15 bg-void-900/90 px-2 py-1 text-[11px] text-white backdrop-blur">
            {node.label}
          </div>
        </Html>
      )}
    </group>
  );
}

function Edges({
  positioned,
  edges,
  selectedId,
}: {
  positioned: PositionedNode[];
  edges: KnowledgeEdge[];
  selectedId: string | null;
}) {
  const byId = useMemo(() => {
    const map = new Map<string, PositionedNode>();
    positioned.forEach((p) => map.set(p.id, p));
    return map;
  }, [positioned]);

  const segments = useMemo(() => {
    return edges
      .map((edge) => {
        const a = byId.get(edge.source_node_id);
        const b = byId.get(edge.target_node_id);
        if (!a || !b) return null;
        const related =
          !selectedId ||
          edge.source_node_id === selectedId ||
          edge.target_node_id === selectedId;
        return { edge, a, b, related };
      })
      .filter(Boolean) as {
      edge: KnowledgeEdge;
      a: PositionedNode;
      b: PositionedNode;
      related: boolean;
    }[];
  }, [edges, byId, selectedId]);

  return (
    <group>
      {segments.map(({ edge, a, b, related }) => (
        // drei's <Line> avoids the intrinsic <line> (SVG) TS name clash.
        <Line
          key={edge.id}
          points={[a.position, b.position]}
          color={related ? "#8b93ff" : "#3a3f66"}
          lineWidth={related ? 1.2 : 0.6}
          transparent
          opacity={related ? 0.5 : 0.12}
        />
      ))}
    </group>
  );
}

export default function KnowledgeGraph3D({
  nodes,
  edges,
  selectedId,
  onSelect,
  reducedMotion = false,
}: KnowledgeGraph3DProps) {
  const positioned = useMemo(() => layoutNodes(nodes), [nodes]);
  const neighbors = useMemo(() => {
    if (!selectedId) return null;
    const set = new Set<string>([selectedId]);
    edges.forEach((e) => {
      if (e.source_node_id === selectedId) set.add(e.target_node_id);
      if (e.target_node_id === selectedId) set.add(e.source_node_id);
    });
    return set;
  }, [selectedId, edges]);

  return (
    <Canvas
      camera={{ position: [0, 0, 20], fov: 55 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      onPointerMissed={() => onSelect(null)}
    >
      <color attach="background" args={["#05060f"]} />
      <fog attach="fog" args={["#05060f", 22, 46]} />
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} intensity={1.2} />
      <pointLight position={[-12, -8, -6]} intensity={0.6} color="#5ee7f2" />

      <Edges positioned={positioned} edges={edges} selectedId={selectedId} />

      {positioned.map((node) => (
        <NodeMesh
          key={node.id}
          node={node}
          selected={selectedId === node.id}
          dimmed={!!neighbors && !neighbors.has(node.id)}
          onSelect={onSelect}
        />
      ))}

      <OrbitControls
        enablePan={false}
        enableDamping
        dampingFactor={0.08}
        minDistance={8}
        maxDistance={40}
        autoRotate={!reducedMotion && !selectedId}
        autoRotateSpeed={0.4}
      />
    </Canvas>
  );
}
