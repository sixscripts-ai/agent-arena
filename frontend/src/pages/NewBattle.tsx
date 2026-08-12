import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, isHostProviderId, playableRoleCount, type FormatOut, type ProviderOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function NewBattle() {
  const { user, jwt, refreshJwt } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [providers, setProviders] = useState<ProviderOut[]>([]);
  const [formatId, setFormatId] = useState(params.get("format") || "");
  const [selected, setSelected] = useState<string[]>([]);
  const [judgeId, setJudgeId] = useState("");
  const [timeoutSec, setTimeoutSec] = useState(600);
  const [visibility, setVisibility] = useState<"isolated" | "open">("isolated");
  const [save, setSave] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const host = useMemo(()=>providers.filter(p=>isHostProviderId(p.id)), [providers]);
  const yours = useMemo(()=>providers.filter(p=>!isHostProviderId(p.id)), [providers]);

  useEffect(()=>{
    if (!jwt) return;
    (async()=>{
      const token = (await refreshJwt()) || jwt;
      const [f,p] = await Promise.all([api.formats(token), api.providers(token)]);
      setFormats(f);
      setProviders(p);
      if (!formatId && f[0]) setFormatId(f[0].id);
      const hostIds = p.filter(x=>isHostProviderId(x.id)).map(x=>x.id);
      const fb = hostIds[0] || p[0]?.id || "host:manus-1.6-lite";
      const alt = hostIds[1] || hostIds[0] || fb;
      if (selected.length===0) setSelected([fb, alt]);
    })();
  }, [jwt]);

  const format = formats.find(f=>f.id===formatId);
  const need = format ? playableRoleCount(format) : 2;
  const roles = useMemo(()=>{
    if (!format) return ["builder","breaker"];
    const r = (format as any).roles as string[] | undefined;
    if (Array.isArray(r)) return r.filter(x=>x!=="judge");
    return ["a","b"];
  }, [format]);

  useEffect(()=>{
    setSelected(prev=>{
      const next = prev.slice(0, need);
      const fb = host[0]?.id || providers[0]?.id || "host:manus-1.6-lite";
      const alt = host[1]?.id || host[0]?.id || fb;
      while (next.length < need) next.push(next.length===1 ? alt : fb);
      const allowed = new Set(providers.map(p=>p.id));
      return next.map(id=> (allowed.has(id) || isHostProviderId(id) ? id : fb));
    });
  }, [need, providers, host]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const token = (await refreshJwt()) || jwt;
    if (!token) return;
    const allowed = new Set(providers.map(p=>p.id));
    const invalid = selected.some(id=> !allowed.has(id) && !isHostProviderId(id));
    if (invalid) { setErr("Invalid provider — choose any host: or your own"); return; }
    setBusy(true); setErr(null);
    try {
      const battle = await api.createBattle(token, {
        format_id: formatId,
        model_ids: selected,
        arena_size: selected.length,
        timeout_seconds: timeoutSec,
        round_visibility: visibility,
        save,
        judge_provider_id: judgeId || null,
      });
      try {
        const key="arena_battle_ids";
        const prev=JSON.parse(localStorage.getItem(key)||"[]") as string[];
        localStorage.setItem(key, JSON.stringify([battle.id, ...prev].slice(0,50)));
      } catch {}
      nav(`/battles/${battle.id}`);
    } catch (er) { setErr(er instanceof Error ? er.message : "Create failed"); } finally { setBusy(false); }
  }

  if (!user) return <div className="p-8 text-[13px] text-muted">Login required — <Link to="/login" className="link">log in</Link></div>;

  const Step = ({ n, title }: { n: number; title: string }) => (
    <div className="flex items-center gap-2 text-[13px] font-semibold tracking-[-0.01em]">
      <span className="grid h-5 w-5 place-items-center rounded-full bg-accent text-[10px] font-semibold text-accent-fg">{n}</span>
      {title}
    </div>
  );

  return (
    <div className="max-w-[1020px] mx-auto space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-[-0.01em]">New battle</h1>
        <p className="mt-1 text-[13px] text-muted">Pick a format, assign models to roles, and hit start.</p>
      </div>
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 md:col-span-7 card p-6 space-y-6">
          <div className="space-y-2">
            <Step n={1} title={`Format — ${formats.length} total`} />
            <select className="select" value={formatId} onChange={e=>setFormatId(e.target.value)}>
              {formats.map(f=><option key={f.id} value={f.id}>{f.name} • {f.engine} • {f.roles?.filter((r:string)=>r!=="judge").length || 2} slots</option>)}
            </select>
            <p className="text-[12px] text-muted">Needs {need} models • roles: {roles.join(", ")} • order = role</p>
          </div>

          <div className="space-y-3">
            <Step n={2} title="Models — order maps to role" />
            {selected.map((mid,i)=>(
              <div key={i} className="space-y-1.5">
                <label className="text-[12px] font-medium">Slot {i+1}: {roles[i] || `model ${i+1}`}</label>
                <select className="select" value={mid} onChange={e=>{ const n=[...selected]; n[i]=e.target.value; setSelected(n); }}>
                  <optgroup label="Host — free">
                    {host.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
                  </optgroup>
                  <optgroup label="Your">
                    {yours.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
                  </optgroup>
                </select>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <Step n={3} title="Judge (optional)" />
            <select className="select" value={judgeId} onChange={e=>setJudgeId(e.target.value)}>
              <option value="">Default host judge (Kimi-K3)</option>
              {host.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
              {yours.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Timeout</label>
              <input type="number" min={30} max={3600} value={timeoutSec} onChange={e=>setTimeoutSec(Number(e.target.value))} className="input" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium">Visibility</label>
              <select value={visibility} onChange={e=>setVisibility(e.target.value as any)} className="select">
                <option value="isolated">isolated (anti-cheat)</option>
                <option value="open">open arena</option>
              </select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-[13px]">
            <input type="checkbox" checked={save} onChange={e=>setSave(e.target.checked)} className="h-4 w-4 rounded border-borderStrong accent-accent" />
            Save artifacts after battle
          </label>

          {err && <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger break-all">{err}</div>}

          <button onClick={onSubmit} disabled={busy || !formatId} className="btn btn-primary h-11 w-full text-[13px]">
            {busy ? "Starting…" : "Start battle →"}
          </button>
        </div>

        <div className="col-span-12 md:col-span-5 space-y-4">
          <div className="card p-5">
            <div className="text-[13px] font-semibold">How slots map</div>
            <div className="mt-3 rounded-lg bg-soft border border-border p-3 font-mono text-[11px] leading-5 text-muted">
              <div>roles: [{roles.map(r=>`"${r}"`).join(", ")}, "judge"]</div>
              <div>playable: [{roles.map(r=>`"${r}"`).join(", ")}] (judge skipped)</div>
              {roles.map((r,i)=><div key={r}>model_ids[{i}] → {r} = <span className="text-foreground">{selected[i] || "—"}</span></div>)}
              <div className="pt-2">len == {need} • any host: id allowed</div>
            </div>
          </div>
          <div className="card p-5">
            <div className="text-[13px] font-semibold">Live preview will show</div>
            <ul className="mt-2 space-y-1.5 text-[13px] leading-5 text-muted">
              <li>• Dual code panes streaming real artifacts</li>
              <li>• Line numbers + tok/s + win condition ESCAPE_OK</li>
              <li>• Judge scores + Elo delta, not fake logs</li>
              <li>• Minimal event log, uuid deduped</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
