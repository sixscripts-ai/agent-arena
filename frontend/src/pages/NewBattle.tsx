import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
      const fb = hostIds[0] || p[0]?.id || "host:openrouter-free";
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
      const fb = host[0]?.id || providers[0]?.id || "host:openrouter-free";
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

  if (!user) return <div className="p-8 mono text-[12px]">Login required</div>;

  return (
    <div className="max-w-[1020px] mx-auto space-y-6">
      <h1 className="display text-[28px]">NEW BATTLE // WIZARD</h1>
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 md:col-span-7 border-[1.5px] border-ink bg-paper p-5 space-y-5">
          <div>
            <div className="mono text-[10px] uppercase tracking-wide">1 • Format • {formats.length} total</div>
            <select className="mt-1 w-full h-10 border-[1.5px] border-ink px-3 text-[13px] bg-paper" value={formatId} onChange={e=>setFormatId(e.target.value)}>
              {formats.map(f=><option key={f.id} value={f.id}>{f.name} • {f.engine} • {f.roles?.filter((r:string)=>r!=="judge").length || 2} slots</option>)}
            </select>
            <p className="mono text-[10px] text-zinc-500 mt-1">Needs {need} models • roles: {roles.join(", ")} • order = role</p>
          </div>
          <div className="space-y-3">
            <div className="mono text-[10px] uppercase">2 • Models (order → role)</div>
            {selected.map((mid,i)=>(
              <div key={i} className="space-y-1">
                <label className="mono text-[10px]">Slot {i+1}: {roles[i] || `model ${i+1}`}</label>
                <select className="w-full h-10 border-[1.5px] border-ink bg-paper px-3 text-[12px]" value={mid} onChange={e=>{ const n=[...selected]; n[i]=e.target.value; setSelected(n); }}>
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
          <div className="space-y-3">
            <div className="mono text-[10px] uppercase">3 • Judge (optional)</div>
            <select className="w-full h-10 border-[1.5px] border-ink bg-paper px-3 text-[12px]" value={judgeId} onChange={e=>setJudgeId(e.target.value)}>
              <option value="">Default host judge (Kimi-K3)</option>
              {host.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
              {yours.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="mono text-[10px] uppercase">Timeout</label><input type="number" min={30} max={3600} value={timeoutSec} onChange={e=>setTimeoutSec(Number(e.target.value))} className="w-full h-10 border-[1.5px] border-ink px-3 text-[13px]" /></div>
            <div><label className="mono text-[10px] uppercase">Visibility</label><select value={visibility} onChange={e=>setVisibility(e.target.value as any)} className="w-full h-10 border-[1.5px] border-ink px-3 text-[12px] bg-paper"><option value="isolated">isolated (anti-cheat)</option><option value="open">open arena</option></select></div>
          </div>
          <label className="flex items-center gap-2 text-[12px]"><input type="checkbox" checked={save} onChange={e=>setSave(e.target.checked)} /> Save artifacts after battle</label>
          {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 mono text-[11px] text-vermillion break-all">{err}</div>}
          <button onClick={onSubmit} disabled={busy || !formatId} className="w-full h-11 bg-ink text-paper font-bold text-[13px] border-[1.5px] border-ink hover:bg-paper hover:text-ink">{busy ? "STARTING..." : "START BATTLE →"}</button>
        </div>
        <div className="col-span-12 md:col-span-5 space-y-4">
          <div className="border-[1.5px] border-ink bg-vermillion text-white p-4">
            <div className="mono text-[10px] uppercase">How slots map</div>
            <div className="mt-2 mono text-[11px] space-y-1">
              <div>roles: [{roles.map(r=>`"${r}"`).join(", ")}, "judge"]</div>
              <div>playable: [{roles.map(r=>`"${r}"`).join(", ")}] (judge skipped)</div>
              {roles.map((r,i)=><div key={r}>model_ids[{i}] → {r} = {selected[i] || "—"}</div>)}
              <div className="pt-2">len == {need} • any host: id allowed</div>
            </div>
          </div>
          <div className="border-[1.5px] border-ink bg-paper p-4">
            <div className="mono text-[10px] uppercase">Live preview will show</div>
            <ul className="mt-2 list-disc pl-4 mono text-[11px] text-zinc-600 space-y-1">
              <li>Dual code panes streaming real artifacts</li>
              <li>Line numbers + tok/s + win condition ESCAPE_OK</li>
              <li>Judge scores + Elo delta, not fake logs</li>
              <li>Minimal event log uuid deduped</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
