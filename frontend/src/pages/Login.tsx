import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const next = params.get("next") || "/";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try { await login(email, password); nav(next); } catch (e) { setErr(e instanceof Error ? e.message : "Login failed"); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-[420px] border-[1.5px] border-ink bg-paper p-8 shadow-brutal">
      <div className="border-b-[1.5px] border-ink pb-4 mb-6">
        <h1 className="display text-[28px]">LOG IN</h1>
        <p className="mono text-[11px] text-zinc-500 mt-1">LAB LOG // AUTH REQUIRED FOR BATTLES</p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="mono text-[11px] uppercase tracking-wide">Email</label>
          <input className="mt-1 w-full h-11 border-[1.5px] border-ink bg-paper px-3 text-[13px] focus:outline-none focus:shadow-brutal-sm" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="mono text-[11px] uppercase">Password</label>
          <input className="mt-1 w-full h-11 border-[1.5px] border-ink bg-paper px-3 text-[13px]" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
        </div>
        {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 text-[12px] text-vermillion">{err}</div>}
        <button disabled={busy} className="w-full h-11 bg-ink text-paper font-bold text-[13px] border-[1.5px] border-ink hover:bg-white hover:text-ink disabled:opacity-50">{busy ? "SIGNING IN..." : "LOG IN →"}</button>
      </form>
      <p className="mt-6 text-center mono text-[11px]">NO ACCOUNT? <Link to="/signup" className="underline decoration-2">SIGN UP</Link></p>
    </div>
  );
}
