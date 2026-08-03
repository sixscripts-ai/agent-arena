"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, isHostProviderId, playableRoleCount, type FormatOut, type ProviderOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewBattlePage() {
  return (
    <Suspense fallback={<p className="text-zinc-500 p-6">Loading…</p>}>
      <NewBattleForm />
    </Suspense>
  );
}

function ModelSelect({ value, onChange, host, yours }: { value: string; onChange: (v: string) => void; host: ProviderOut[]; yours: ProviderOut[] }) {
  return (
    <select className="flex h-10 w-full rounded-[12px] border border-white/10 bg-black px-3 text-[13px]" value={value} onChange={(e) => onChange(e.target.value)}>
      {host.length > 0 && (
        <optgroup label="Host — free">
          {host.map((p) => (
            <option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>
          ))}
        </optgroup>
      )}
      {yours.length > 0 && (
        <optgroup label="Your providers">
          {yours.map((p) => (
            <option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>
          ))}
        </optgroup>
      )}
    </select>
  );
}

function NewBattleForm() {
  const { user, jwt, loading, refreshJwt } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [providers, setProviders] = useState<ProviderOut[]>([]);
  const [formatId, setFormatId] = useState(params.get("format") || "");
  const [selected, setSelected] = useState<string[]>([]);
  const [judgeId, setJudgeId] = useState<string>("");
  const [timeoutSec, setTimeoutSec] = useState(600);
  const [visibility, setVisibility] = useState<"isolated" | "open">("isolated");
  const [save, setSave] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const host = useMemo(() => providers.filter((p) => isHostProviderId(p.id)), [providers]);
  const yours = useMemo(() => providers.filter((p) => !isHostProviderId(p.id)), [providers]);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  // load formats + providers once
  useEffect(() => {
    if (!jwt) return;
    let cancelled = false;
    (async () => {
      try {
        const token = (await refreshJwt()) || jwt;
        const [f, p] = await Promise.all([api.formats(token), api.providers(token)]);
        if (cancelled) return;
        setFormats(f);
        setProviders(p);
        if (!formatId && f[0]) setFormatId(f[0].id);
        // init selected with host models
        if (selected.length===0) {
          const hostIds = p.filter(x=>isHostProviderId(x.id)).map(x=>x.id);
          const fallback = hostIds[0] || p[0]?.id || "host:openrouter-free";
          const alt = hostIds[1] || hostIds[0] || fallback;
          setSelected([fallback, alt]);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Load failed");
      }
    })();
    return ()=>{ cancelled=true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jwt]);

  const format = formats.find((f) => f.id === formatId);
  const need = format ? playableRoleCount(format) : 2;
  const roles = useMemo(()=>{
    if (!format) return ["builder","breaker"];
    const r = (format as any).roles as string[] | undefined;
    if (Array.isArray(r)) return r.filter(x=>x!=="judge");
    return ["a","b"];
  }, [format]);

  // keep selected length == need, allow ANY host:* id
  useEffect(() => {
    setSelected(prev => {
      const next = prev.slice(0, need);
      const fallback = host[0]?.id || providers[0]?.id || "host:openrouter-free";
      const alt = host[1]?.id || host[0]?.id || fallback;
      while (next.length < need) next.push(next.length===1 ? alt : fallback);
      // filter invalid ids except any host:
      const allowed = new Set([...providers.map(p=>p.id), ...host.map(p=>p.id)]);
      // allow any id that starts with host: even if not in list (for future hosts)
      return next.map(id => (allowed.has(id) || isHostProviderId(id) ? id : fallback));
    });
  }, [need, providers, host]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = (await refreshJwt()) || jwt;
    if (!token || !formatId) return;
    // validation: allow any host:* id
    const allowed = new Set(providers.map(p=>p.id));
    const invalid = selected.some(id => !allowed.has(id) && !isHostProviderId(id));
    if (invalid) {
      setError("Please choose a valid provider for every slot (host: or your own).");
      return;
    }
    setBusy(true); setError(null);
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
      router.push(`/battles/${battle.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally { setBusy(false); }
  }

  if (loading || !user) return <p className="text-zinc-500 p-6">Loading…</p>;

  return (
    <div className="mx-auto max-w-[1020px] space-y-6">
      <h1 className="text-[24px] font-semibold tracking-[-0.02em]">New Battle • Wizard</h1>
      {!yours.length && (
        <p className="rounded-[12px] border border-white/10 bg-[#0C0C0F] px-4 py-3 text-[13px] text-zinc-400">
          Using host models only. <Link href="/providers" className="text-emerald-400 hover:underline">Add your own API key</Link> to use personal models.
        </p>
      )}
      <div className="grid grid-cols-12 gap-4">
        {/* Left: form */}
        <div className="col-span-12 md:col-span-7 rounded-[16px] border border-white/10 bg-[#0C0C0F] p-5 space-y-5">
          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-zinc-500">1 • Format</div>
            <select className="flex h-10 w-full rounded-[12px] border border-white/10 bg-black px-3 text-[13px]" value={formatId} onChange={(e)=>setFormatId(e.target.value)} required>
              {formats.map(f=>(
                <option key={f.id} value={f.id}>{f.name} • {f.engine} • {f.roles?.length ? `${f.roles.filter((r:string)=>r!=="judge").length} slots` : "2 slots"}</option>
              ))}
            </select>
            <p className="text-[11px] text-zinc-500">Needs {need} models • roles: {roles.join(", ")} • order = role mapping</p>
          </div>

          <div className="space-y-3">
            <div className="text-[11px] uppercase tracking-wide text-zinc-500">2 • Models (order → role)</div>
            {selected.map((mid, i)=>(
              <div key={i} className="space-y-1">
                <Label className="text-[11px] text-zinc-400">Slot {i+1}: {roles[i] || `model ${i+1}`}</Label>
                <ModelSelect value={mid} host={host} yours={yours} onChange={(v)=>{ const n=[...selected]; n[i]=v; setSelected(n); }} />
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-zinc-500">3 • Judge (optional)</div>
            <select className="flex h-10 w-full rounded-[12px] border border-white/10 bg-black px-3 text-[13px]" value={judgeId} onChange={(e)=>setJudgeId(e.target.value)}>
              <option value="">Default host judge (Kimi-K3)</option>
              {host.length>0 && (
                <optgroup label="Host">
                  {host.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
                </optgroup>
              )}
              {yours.length>0 && (
                <optgroup label="Your providers">
                  {yours.map(p=><option key={p.id} value={p.id}>{p.name} • {p.model_name}</option>)}
                </optgroup>
              )}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-[11px] text-zinc-500">Timeout (s)</Label>
              <Input type="number" min={30} max={3600} value={timeoutSec} onChange={(e)=>setTimeoutSec(Number(e.target.value))} className="rounded-[12px] bg-black border-white/10" />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px] text-zinc-500">Visibility</Label>
              <select className="flex h-10 w-full rounded-[12px] border border-white/10 bg-black px-3 text-[13px]" value={visibility} onChange={(e)=>setVisibility(e.target.value as any)}>
                <option value="isolated">isolated (anti-cheat)</option>
                <option value="open">open arena</option>
              </select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-[13px] text-zinc-300">
            <input type="checkbox" checked={save} onChange={(e)=>setSave(e.target.checked)} />
            Save artifacts after battle
          </label>

          {error && <p className="text-[13px] text-red-300 break-all">{error}</p>}
          <Button type="button" onClick={onSubmit as any} disabled={busy || !formatId} className="w-full h-10 rounded-[12px]">{busy ? "Starting…" : "Start battle →"}</Button>
        </div>

        {/* Right: mapping explainer */}
        <div className="col-span-12 md:col-span-5 space-y-4">
          <div className="rounded-[16px] border border-emerald-500/15 bg-emerald-500/[0.04] p-5">
            <div className="text-[11px] uppercase tracking-wide text-emerald-300/80">How slots map to roles</div>
            <div className="mt-3 space-y-2 font-mono text-[11px] text-zinc-400">
              <div>format roles: [{roles.map(r=>`"${r}"`).join(", ")}, "judge"]</div>
              <div>playable: [{roles.map(r=>`"${r}"`).join(", ")}] (judge skipped)</div>
              {roles.map((r,i)=><div key={r}>model_ids[{i}] → {r} = {selected[i] || "—"}</div>)}
              <div className="pt-3 text-zinc-300">Validation: len(model_ids) == len(playable) == {need}</div>
              <div className="text-[10px] text-zinc-500">Any host: id allowed (host:openrouter-free, host:deepseek, host:groq-*, etc)</div>
            </div>
          </div>
          <div className="rounded-[16px] border border-white/10 bg-[#0C0C0F] p-5">
            <div className="text-[11px] uppercase tracking-wide text-zinc-500">Live preview will show</div>
            <ul className="mt-2 space-y-1 text-[12px] text-zinc-400 list-disc pl-4">
              <li>Dual code panes streaming real artifacts</li>
              <li>Line numbers + tok/s + win condition</li>
              <li>Judge scores + Elo delta, not fake logs</li>
              <li>Minimal event stream (uuid deduped)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
