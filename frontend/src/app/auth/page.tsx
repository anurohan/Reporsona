"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, Loader2 } from "lucide-react";
import { ApiError, login, register, saveAuth } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const [nextPath, setNextPath] = useState("/explore");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("next");
    if (requested?.startsWith("/")) setNextPath(requested);
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = mode === "login" ? await login({ email, password }) : await register({ email, password, display_name: name });
      saveAuth(response); router.replace(nextPath);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Authentication failed."); }
    finally { setBusy(false); }
  }

  return <main className="flex min-h-screen items-center justify-center bg-void-950 px-5 text-white"><div className="glass-panel w-full max-w-md p-7"><div className="mb-7 flex items-center gap-3"><div className="rounded-xl bg-indigoGlow-600/20 p-3"><KeyRound className="h-5 w-5 text-indigoGlow-300" /></div><div><div className="eyebrow">Private archive</div><h1 className="mt-1 font-display text-2xl">{mode === "login" ? "Welcome back" : "Create your account"}</h1></div></div><form onSubmit={submit} className="space-y-4">{mode === "register" && <div><label className="mb-1.5 block text-sm text-slate-300">Display name</label><input value={name} onChange={(e) => setName(e.target.value)} className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm" /></div>}<div><label className="mb-1.5 block text-sm text-slate-300">Email</label><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm" /></div><div><label className="mb-1.5 block text-sm text-slate-300">Password</label><input type="password" required minLength={mode === "register" ? 12 : 1} value={password} onChange={(e) => setPassword(e.target.value)} className="focusable w-full rounded-xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm" />{mode === "register" && <p className="mt-1 text-xs text-slate-500">Use at least 12 characters.</p>}</div>{error && <p role="alert" className="rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">{error}</p>}<button disabled={busy} className="focusable flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigoGlow-600 to-accent-violet py-3 text-sm font-medium disabled:opacity-40">{busy && <Loader2 className="h-4 w-4 animate-spin" />}{mode === "login" ? "Sign in" : "Register"}</button></form><button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }} className="mt-5 w-full text-sm text-slate-400 hover:text-white">{mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}</button></div></main>;
}
