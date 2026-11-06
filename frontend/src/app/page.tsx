"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import EthicalNotice from "@/components/EthicalNotice";
import { StartButton, SecondaryButton } from "@/components/StartButton";

// 3D background must be client-only.
const BackgroundScene = dynamic(
  () => import("@/components/three/BackgroundScene"),
  { ssr: false }
);

const INIT_LINES = [
  "Initializing reconstruction core…",
  "Calibrating evidence engine…",
  "Opening the archive…",
];

export default function LandingPage() {
  const router = useRouter();
  const [initializing, setInitializing] = useState(false);
  const [lineIndex, setLineIndex] = useState(0);

  const beginSequence = (target: string) => {
    setInitializing(true);
    setLineIndex(0);
    let i = 0;
    const step = () => {
      i += 1;
      if (i < INIT_LINES.length) {
        setLineIndex(i);
        setTimeout(step, 550);
      } else {
        setTimeout(() => router.push(target), 500);
      }
    };
    setTimeout(step, 550);
  };

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      <BackgroundScene />

      <AnimatePresence mode="wait">
        {initializing ? (
          <motion.div
            key="init"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="relative z-10 flex flex-col items-center text-center"
            role="status"
            aria-live="polite"
          >
            <div className="mb-6 h-14 w-14 animate-spin rounded-full border-2 border-white/10 border-t-indigoGlow-400" />
            <AnimatePresence mode="wait">
              <motion.p
                key={lineIndex}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="font-display text-sm tracking-[0.2em] text-slate-300"
              >
                {INIT_LINES[lineIndex]}
              </motion.p>
            </AnimatePresence>
          </motion.div>
        ) : (
          <motion.div
            key="hero"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative z-10 flex max-w-3xl flex-col items-center text-center"
          >
            <span className="mb-6 chip animate-pulseGlow">
              AI-Powered Personality Reconstruction
            </span>
            <h1 className="font-display text-6xl font-bold tracking-tight text-gradient sm:text-8xl">
              REPERSONA
            </h1>
            <p className="mt-5 text-xl text-slate-200 sm:text-2xl">
              Explore the documented mind of history.
            </p>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-400 sm:text-base">
              RePersona reconstructs a person from their public writings, talks
              and recordings, then lets you converse with the result — every
              answer traced back to the source it came from.
            </p>

            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
              <StartButton onStart={() => beginSequence("/explore")} />
              <SecondaryButton
                label="Explore Demo"
                onClick={() => beginSequence("/explore?demo=1")}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <EthicalNotice variant="fixed" />
    </main>
  );
}
