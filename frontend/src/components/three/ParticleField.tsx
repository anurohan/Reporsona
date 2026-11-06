"use client";

import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

export interface ParticleFieldProps {
  count?: number;
  quality?: "low" | "medium" | "high";
  reducedMotion?: boolean;
}

const QUALITY_SCALE: Record<NonNullable<ParticleFieldProps["quality"]>, number> =
  {
    low: 0.4,
    medium: 0.7,
    high: 1,
  };

/**
 * GPU-friendly drifting star/particle field. Slow rotation plus a subtle
 * mouse parallax. When reducedMotion is set it renders static points.
 */
export default function ParticleField({
  count = 2000,
  quality = "high",
  reducedMotion = false,
}: ParticleFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const { viewport } = useThree();

  const resolved = Math.max(200, Math.floor(count * QUALITY_SCALE[quality]));

  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(resolved * 3);
    const colors = new Float32Array(resolved * 3);
    const palette = [
      new THREE.Color("#8b93ff"),
      new THREE.Color("#5ee7f2"),
      new THREE.Color("#a78bfa"),
      new THREE.Color("#c7d2fe"),
    ];
    for (let i = 0; i < resolved; i++) {
      const r = 4 + Math.random() * 10;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
      const c = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    return { positions, colors };
  }, [resolved]);

  useFrame((state, delta) => {
    const pts = pointsRef.current;
    if (!pts) return;
    if (reducedMotion) return;
    pts.rotation.y += delta * 0.02;
    pts.rotation.x += delta * 0.006;
    // Gentle mouse parallax.
    const mx = (state.pointer.x * viewport.width) / 40;
    const my = (state.pointer.y * viewport.height) / 40;
    pts.position.x += (mx - pts.position.x) * 0.03;
    pts.position.y += (my - pts.position.y) * 0.03;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          count={resolved}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[colors, 3]}
          count={resolved}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.05}
        sizeAttenuation
        vertexColors
        transparent
        opacity={0.85}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
