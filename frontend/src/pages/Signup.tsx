import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try { await signup(email, password, name || email.split("@")[0]); nav("/"); } catch (e) { setErr(e instanceof Error ? e.message : "Signup failed"); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-[420px] border-[1.5px] border-ink bg-paper p-8 shadow-brutal">
      <div className="border-b-[1.5px] border-ink pb-4 mb-6">
        <h1 className="display text-[28px]">CREATE ACCOUNT</h1>
        <p className="mono text-[11px] text-zinc-500">LAB ACCESS // 8+ CHARS PASSWORD</p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <div><label className="mono text-[11px] uppercase">Name</label><input className="mt-1 w-full h-11 border-[1.5px] border-ink px-3 text-[13px]" value={name} onChange={e=>setName(e.target.value)} placeholder="fighter" /></div>
        <div><label className="mono text-[11px] uppercase">Email</label><input className="mt-1 w-full h-11 border-[1.5px] border-ink px-3 text-[13px]" type="email" value={email} onChange={e=>setEmail(e.target.value)} required /></div>
        <div><label className="mono text-[11px] uppercase">Password</label><input className="mt-1 w-full h-11 border-[1.5px] border-ink px-3 text-[13px]" type="password" minLength={8} value={password} onChange={e=>setPassword(e.target.value)} required /></div>
        {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 text-[12px] text-vermillion">{err}</div>}
        <button disabled={busy} className="w-full h-11 bg-ink text-paper font-bold text-[13px] border-[1.5px] border-ink hover:bg-white hover:text-ink">{busy ? "CREATING..." : "SIGN UP →"}</button>
      </form>
      <p className="mt-6 text-center mono text-[11px]">HAVE ACCOUNT? <Link to="/login" className="underline decoration-2">LOG IN</Link></p>
    </div>
  );
}
