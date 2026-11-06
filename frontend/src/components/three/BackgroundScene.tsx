"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import ParticleField from "./ParticleField";

function usePrefersReducedMotion(): boolean {
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

function useIsMobile(): boolean {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const check = () => setMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);
  return mobile;
}

function FloatingRings({ reducedMotion }: { reducedMotion: boolean }) {
  const group = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (reducedMotion || !group.current) return;
    group.current.rotation.z += delta * 0.05;
    group.current.rotation.x += delta * 0.01;
  });
  const rings = useMemo(
    () => [
      { r: 5.2, color: "#5a4bff", opacity: 0.18 },
      { r: 6.8, color: "#5ee7f2", opacity: 0.12 },
      { r: 8.4, color: "#a78bfa", opacity: 0.08 },
    ],
    []
  );
  return (
    <group ref={group} position={[0, 0, -2]}>
      {rings.map((ring, i) => (
        <mesh key={i} rotation={[Math.PI / 2.2, i * 0.3, 0]}>
          <torusGeometry args={[ring.r, 0.012, 16, 120]} />
          <meshBasicMaterial
            color={ring.color}
            transparent
            opacity={ring.opacity}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  );
}

export interface BackgroundSceneProps {
  className?: string;
  intensity?: "subtle" | "normal";
}

/**
 * Full-bleed ambient 3D background: drifting particle field, soft fog and
 * slow floating rings. Reduces particle count on mobile and honours
 * prefers-reduced-motion (renders a static field).
 */
export default function BackgroundScene({
  className = "",
  intensity = "normal",
}: BackgroundSceneProps) {
  const reducedMotion = usePrefersReducedMotion();
  const isMobile = useIsMobile();

  const baseCount = intensity === "subtle" ? 1200 : 2000;
  const count = isMobile ? Math.floor(baseCount * 0.45) : baseCount;
  const quality: "low" | "medium" | "high" = isMobile ? "low" : "high";

  return (
    <div
      className={`pointer-events-none absolute inset-0 -z-10 ${className}`}
      aria-hidden="true"
    >
      <Canvas
        camera={{ position: [0, 0, 12], fov: 60 }}
        dpr={isMobile ? [1, 1.5] : [1, 2]}
        gl={{ antialias: !isMobile, alpha: true, powerPreference: "high-performance" }}
      >
        <fog attach="fog" args={["#05060f", 10, 24]} />
        <ambientLight intensity={0.4} />
        <ParticleField
          count={count}
          quality={quality}
          reducedMotion={reducedMotion}
        />
        <FloatingRings reducedMotion={reducedMotion} />
      </Canvas>
    </div>
  );
}
