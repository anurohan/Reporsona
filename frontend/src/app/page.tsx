"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown, BrainCircuit, Check, Database, Fingerprint, Layers3, LockKeyhole } from "lucide-react";
import EthicalNotice from "@/components/EthicalNotice";
import { StartButton, SecondaryButton } from "@/components/StartButton";
import AppHeader, { Reveal } from "@/components/AppHeader";

const BackgroundScene = dynamic(() => import("@/components/three/BackgroundScene"), { ssr: false });
const INIT_LINES = ["Waking the reconstruction core…", "Calibrating the evidence layer…", "Opening the archive…"];

export default function LandingPage() {
  const router = useRouter();
  const [initializing, setInitializing] = useState(false);
  const [lineIndex, setLineIndex] = useState(0);
  const beginSequence = (target: string) => {
    setInitializing(true); setLineIndex(0); let i = 0;
    const step = () => { i += 1; if (i < INIT_LINES.length) { setLineIndex(i); setTimeout(step, 550); } else setTimeout(() => router.push(target), 500); };
    setTimeout(step, 550);
  };

  return (
    <main className="relative min-h-screen overflow-hidden">
      <BackgroundScene /><div className="hero-grid pointer-events-none absolute inset-x-0 top-0 h-[760px] opacity-60" /><AppHeader />
      <AnimatePresence mode="wait">
        {initializing ? (
          <motion.div key="init" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="relative z-10 flex min-h-screen flex-col items-center justify-center text-center" role="status" aria-live="polite">
            <div className="relative mb-7 flex h-20 w-20 items-center justify-center rounded-full border border-indigoGlow-400/30 bg-indigoGlow-600/10 shadow-glow-lg"><div className="absolute inset-1 animate-spin rounded-full border border-white/10 border-t-indigoGlow-400" /><BrainCircuit className="h-7 w-7 text-indigoGlow-400" /></div>
            <AnimatePresence mode="wait"><motion.p key={lineIndex} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="font-display text-xs uppercase tracking-[.22em] text-slate-300">{INIT_LINES[lineIndex]}</motion.p></AnimatePresence><p className="mt-3 text-xs text-slate-500">Preparing your private archive</p>
          </motion.div>
        ) : (
          <>
            <section className="relative z-10 mx-auto flex min-h-[780px] max-w-7xl items-center px-6 pb-24 pt-36 sm:px-10 lg:px-16"><div className="grid w-full items-center gap-16 lg:grid-cols-[1.05fr_.95fr]">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .8, ease: [0.22,1,.36,1] }}>
                <div className="eyebrow mb-7">The intelligence archive</div><h1 className="display-title max-w-4xl text-6xl sm:text-8xl lg:text-[7.4rem]">Meet the<br /><span className="text-gradient">documented</span><br />mind.</h1>
                <p className="mt-8 max-w-xl text-base leading-8 text-slate-400 sm:text-lg">RePersona turns public writings, talks and records into a living, evidence-linked conversation. Explore a person’s ideas without pretending it is the person.</p>
                <div className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center"><StartButton label="ENTER THE ARCHIVE" onStart={() => beginSequence("/explore")} /><SecondaryButton label="See how it works ↓" onClick={() => document.getElementById("method")?.scrollIntoView({ behavior: "smooth" })} /></div>
                <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs text-slate-500">{["Evidence first", "Local-first AI", "Source-linked answers"].map((item) => <span key={item} className="inline-flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-300" />{item}</span>)}</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, scale: .94, rotate: 2 }} animate={{ opacity: 1, scale: 1, rotate: 0 }} transition={{ delay: .18, duration: 1, ease: [0.22,1,.36,1] }} className="relative mx-auto w-full max-w-[520px] lg:ml-auto"><div className="absolute -inset-10 rounded-full bg-indigoGlow-600/15 blur-3xl" /><div className="relative overflow-hidden rounded-[2rem] border border-white/15 bg-[#0a0c1c]/75 p-4 shadow-[0_30px_100px_-20px_rgba(70,65,220,.55)] backdrop-blur-2xl">
                <div className="flex items-center justify-between border-b border-white/10 px-3 pb-4"><div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_10px_rgba(110,231,183,.9)]" /><span className="text-[10px] uppercase tracking-[.2em] text-slate-500">Live reconstruction</span></div><span className="font-mono text-[10px] text-slate-600">RP / 001</span></div>
                <div className="relative flex min-h-[370px] flex-col justify-end overflow-hidden rounded-2xl px-4 pb-5 pt-10 sm:px-7"><div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_28%,rgba(139,147,255,.22),transparent_28%),radial-gradient(circle_at_50%_42%,rgba(94,231,242,.10),transparent_48%)]" /><div className="relative mx-auto mb-12 flex h-40 w-40 items-center justify-center rounded-full border border-indigoGlow-400/30 bg-[radial-gradient(circle_at_35%_25%,#b7c3ff,#5a4bff_42%,#161735_78%)] shadow-[0_0_90px_rgba(90,75,255,.55)]"><div className="absolute inset-[-20px] rounded-full border border-indigoGlow-400/20 animate-[spin_20s_linear_infinite]" /><div className="absolute inset-[-42px] rounded-full border border-accent-cyan/10 border-dashed animate-[spin_28s_linear_infinite_reverse]" /><Fingerprint className="h-14 w-14 text-white/80" strokeWidth={1} /></div><div className="relative"><div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[.18em] text-slate-500"><span>Evidence coverage</span><span className="text-emerald-300">High</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/10"><motion.div initial={{ width: 0 }} animate={{ width: "86%" }} transition={{ delay: .8, duration: 1.2 }} className="h-full rounded-full bg-gradient-to-r from-indigoGlow-600 to-accent-cyan" /></div></div><div className="relative mt-5 grid grid-cols-3 gap-2 text-center">{[["24","Sources"],["186","Passages"],["12","Themes"]].map(([value,label]) => <div key={label} className="rounded-xl border border-white/8 bg-white/[.035] px-2 py-3"><div className="font-display text-lg text-white">{value}</div><div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div></div>)}</div></div>
              </div></motion.div>
            </div></section>
            <section id="method" className="relative z-10 mx-auto max-w-7xl px-6 pb-28 sm:px-10 lg:px-16"><Reveal><div className="mb-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><div className="eyebrow mb-4">A different kind of AI</div><h2 className="display-title max-w-2xl text-4xl sm:text-5xl">Curiosity, with a paper trail.</h2></div><p className="max-w-sm text-sm leading-6 text-slate-500">Every answer is shaped by what was actually documented — and honest about what was not.</p></div></Reveal><div className="grid gap-3 md:grid-cols-3">{[{ icon: Database, n: "01", title: "Gather the record", body: "Public writings, interviews, talks and trusted references become a structured source library." }, { icon: Layers3, n: "02", title: "Map the worldview", body: "Themes, language patterns and recurring concepts reveal the shape of an individual’s thinking." }, { icon: LockKeyhole, n: "03", title: "Keep it grounded", body: "Conversations stay linked to evidence, with a clear boundary between documented and inferred." }].map(({ icon: Icon, n, title, body }, i) => <Reveal key={title} delay={i * .08}><article className="feature-card h-full"><div className="mb-10 flex items-center justify-between"><span className="number-chip">{n}</span><Icon className="h-5 w-5 text-indigoGlow-400" strokeWidth={1.5} /></div><h3 className="font-display text-xl text-white">{title}</h3><p className="mt-3 text-sm leading-6 text-slate-500">{body}</p></article></Reveal>)}</div></section>
            <section className="relative z-10 border-y border-white/8 bg-white/[.018] px-6 py-5 sm:px-10 lg:px-16"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 text-[10px] uppercase tracking-[.22em] text-slate-600"><span>Built for thoughtful exploration</span><span className="flex items-center gap-5"><span>Public sources</span><span>•</span><span>Private sessions</span><span>•</span><span>Transparent limits</span></span><ArrowDown className="hidden h-4 w-4 text-indigoGlow-400 sm:block" /></div></section>
          </>
        )}
      </AnimatePresence><EthicalNotice variant="fixed" />
    </main>
  );
}
