import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { authRoute, sanitizeInternalReturn } from "@/lib/authReturn";

export default function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const next = sanitizeInternalReturn(params.get("next"));
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try { await signup(email, password, name || email.split("@")[0]); nav(next); } catch (e) { setErr(e instanceof Error ? e.message : "Signup failed"); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-[400px]">
      <div className="card p-8">
        <div className="mb-6">
          <h1 className="text-[22px] font-semibold tracking-[-0.01em]">Create account</h1>
          <p className="mt-1 text-[13px] text-muted">Set up a profile to add keys and queue battles.</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-[12px] font-medium">Name</label>
            <input className="input" value={name} onChange={e=>setName(e.target.value)} placeholder="fighter" />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-medium">Email</label>
            <input className="input" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-medium">Password</label>
            <input className="input" type="password" minLength={8} value={password} onChange={e=>setPassword(e.target.value)} required />
          </div>
          {err && <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger break-all">{err}</div>}
          <button disabled={busy} className="btn btn-primary h-11 w-full text-[13px]">{busy ? "Creating account…" : "Sign up →"}</button>
        </form>
        <p className="mt-6 text-center text-[13px] text-muted">
          Have an account? <Link to={authRoute("login", next)} className="link">Log in</Link>
        </p>
      </div>
    </div>
  );
}
