import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, streamBattle, type BattleOut, type StreamEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type CodeArtifact = { phase: string; model_id: string; artifact: string; t: number };

export default function LiveBattle() {
  const { id } = useParams<{ id: string }>();
  const { user, jwt, refreshJwt } = useAuth();
  const nav = useNavigate();
  const [battle, setBattle] = useState<BattleOut | null>(null);
  const [arts, setArts] = useState<CodeArtifact[]>([]);
  const [scores, setScores] = useState<Record<string, number> | null>(null);
  const [status, setStatus] = useState("queued");
  const [phase, setPhase] = useState("build");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(()=>{
    if (!jwt || !id) return;
    (async()=>{
      try { const b = await api.getBattle(jwt, id); setBattle(b); setStatus(b.status); } catch(e){ setErr(e instanceof Error ? e.message : "Load failed"); }
    })();
  }, [jwt, id]);

  useEffect(()=>{
    if (!jwt || !id || !user) return;
    let cancelled=false;
    const ac = new AbortController();
    const connect = async (attempt=0)=>{
      if (cancelled) return;
      try {
        const token = (await refreshJwt()) || jwt;
        await streamBattle(id, token, (ev: StreamEvent)=>{
          if (cancelled) return;
          const data = ev.data as any;
          const d = data?.data || data;
          if (ev.event==="battle_status" || ev.event==="done") {
            const st = d?.status || data?.status;
            if (st) setStatus(st);
          }
          if (ev.event==="phase_start" && (d?.phase || data?.phase)) setPhase(d?.phase || data?.phase);
          if (["artifact","transcript","action_log"].includes(ev.event)) {
            const artifact = d?.artifact || data?.artifact || JSON.stringify(data);
            const mid = d?.model_id || data?.model_id || "system";
            const ph = d?.phase || data?.phase || phase;
            setArts(prev=>[...prev, {phase: ph, model_id: mid, artifact, t: Date.now()}].slice(-200));
          }
          if (ev.event==="scores") {
            const sc = d?.scores || data?.scores;
            if (sc) setScores(sc);
          }
        }, ac.signal);
        if (!["completed","failed","cancelled"].includes(status)) {
          await new Promise(r=>setTimeout(r, Math.min(1000*2**attempt, 8000)));
          if (!cancelled) connect(attempt+1);
        }
      } catch {
        if (attempt<4 && !cancelled) { await new Promise(r=>setTimeout(r, 1000*2**attempt)); connect(attempt+1); }
      }
    };
    connect();
    return ()=>{ cancelled=true; ac.abort(); };
  }, [jwt, id, user, refreshJwt, status, phase]);

  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); }, [arts]);

  const modelIds = battle?.model_ids || [];
  const modelA = modelIds[0] || "model_a";
  const modelB = modelIds[1] || "model_b";
  const codeA = useMemo(()=> arts.filter(a=>a.model_id===modelA).map(a=>a.artifact).join("\n\n"), [arts, modelA]);
  const codeB = useMemo(()=> arts.filter(a=>a.model_id===modelB).map(a=>a.artifact).join("\n\n"), [arts, modelB]);

  async function cancel() {
    if (!jwt || !id) return;
    setBusy("cancel");
    try { await api.cancelBattle(jwt, id); setStatus("cancelled"); } catch(e){ setErr(e instanceof Error ? e.message : "Cancel failed"); } finally { setBusy(null); }
  }
  async function save() {
    if (!jwt || !id) return;
    setBusy("save");
    try { await api.saveBattle(jwt, id); setBattle(b=> b? {...b, saved:true}:b); } catch(e){ setErr(e instanceof Error ? e.message : "Save failed"); } finally { setBusy(null); }
  }

  if (!user) return <div className="p-8 mono text-[12px]">Login required</div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-[1.5px] border-ink bg-paper px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 bg-ink text-paper grid place-items-center font-bold text-[12px]">W</div>
          <div>
            <div className="flex items-center gap-2"><span className="text-[14px] font-bold">{battle?.format_id || "battle"} • {String(id).slice(0,8)}</span><span className={`border px-2 py-0.5 text-[10px] mono uppercase ${status==="completed" ? "border-success bg-success/10 text-success" : status==="running" ? "border-amber-500 bg-amber-500/10 text-amber-700" : "border-ink/20 text-zinc-500"}`}>{status.toUpperCase()}</span></div>
            <div className="mono text-[11px] text-zinc-500">phase: {phase} • {battle?.round_visibility || "isolated"} • {battle?.timeout_seconds || 600}s</div>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="border border-ink px-3 py-1.5 mono text-[11px]">{arts.length} artifacts</div>
          <button onClick={cancel} disabled={busy==="cancel" || ["completed","failed","cancelled"].includes(status)} className="h-8 px-3 border-[1.5px] border-ink bg-vermillion text-white mono text-[11px] disabled:opacity-50">STOP</button>
          <button onClick={save} disabled={busy==="save" || !!battle?.saved} className="h-8 px-3 border-[1.5px] border-ink bg-ink text-paper mono text-[11px] disabled:opacity-50">{battle?.saved ? "SAVED" : "SAVE"}</button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {[
          {k:"build", label:"Build", done: arts.some(a=>a.phase==="build")},
          {k:"break", label:"Break / Escape", active: phase==="break"||phase==="duel"||phase==="race", done: status==="completed"},
          {k:"judge", label:"Judge", active: phase==="judge", done: status==="completed"},
        ].map((p,idx)=>(
          <div key={p.k} className="flex items-center gap-2">
            {idx>0 && <div className={`h-px w-8 ${p.done||p.active ? "bg-ink" : "bg-ink/20"}`} />}
            <div className={`border-[1.5px] px-3 py-1 mono text-[11px] uppercase ${p.active ? "bg-ink text-paper border-ink" : p.done ? "bg-success/10 border-success text-success" : "bg-paper border-ink/20 text-zinc-500"}`}>{p.label}</div>
          </div>
        ))}
      </div>

      {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 mono text-[12px] text-vermillion break-all">{err}</div>}

      <div className="grid grid-cols-12 gap-3">
        {[
          {id: modelA, label: `${modelA} • builder`, code: codeA, color: "ink"},
          {id: modelB, label: `${modelB} • breaker`, code: codeB, color: "blueprint"},
        ].map(m=>(
          <div key={m.id} className="col-span-12 lg:col-span-6 border-[1.5px] border-ink bg-[#0A0A0A] flex flex-col">
            <div className="flex items-center justify-between border-b border-white/10 bg-[#141414] px-4 py-2.5">
              <div className="flex items-center gap-2">
                <div className="h-6 w-6 bg-white/10 border border-white/10 grid place-items-center text-[11px] text-white">{m.id[0]?.toUpperCase()}</div>
                <div><div className="text-[12px] font-bold text-white">{m.label}</div><div className="mono text-[10px] text-zinc-500">{m.id} • 42 tok/s</div></div>
              </div>
              <div className="flex items-center gap-2"><span className="h-2 w-2 bg-white animate-pulse" /><span className="mono text-[10px] text-zinc-500">{status.toUpperCase()}</span></div>
            </div>
            <div className="relative flex-1 flex">
              <div className="w-12 bg-[#0F0F0F] border-r border-white/10 py-3 text-right pr-3 select-none">
                {m.code.split("\n").slice(0,80).map((_,i)=><div key={i} className="mono text-[11px] leading-5 text-zinc-600">{i+1}</div>)}
              </div>
              <pre className="flex-1 max-h-[560px] overflow-auto p-3 mono text-[12px] leading-5 text-zinc-200 whitespace-pre-wrap break-all"><code>{m.code || "// waiting for real code — not fake logs\n// streams token-by-token from /internal/model via sandbox"}{status==="running" && <span className="inline-block w-2 h-3 bg-white animate-pulse ml-0.5" />}</code></pre>
            </div>
            <div className="border-t border-white/10 bg-[#111] px-3 py-2 flex justify-between mono text-[10px] text-zinc-500">
              <span>{(m.code.length/1024).toFixed(1)}kb • Python</span>
              <span className={m.code.includes("ESCAPE_OK") ? "text-amber-300" : ""}>{m.code.includes("ESCAPE_OK") ? "WIN CONDITION MET" : m.code ? "redacted + truncated" : "idle"}</span>
            </div>
          </div>
        ))}
        <div className="col-span-12 border-[1.5px] border-ink bg-paper p-4 flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 bg-ink text-paper grid place-items-center font-bold text-[12px]">J</div>
            <div><div className="text-[12px] font-bold">Host Judge • Kimi-K3 • rubric from format</div><div className="mono text-[11px] text-zinc-500">reasoning redacted • clamped 0-100 • retry x3</div></div>
          </div>
          <div className="ml-auto flex gap-2">
            {modelIds.map((mid,idx)=>(
              <div key={mid} className="border-[1.5px] border-ink bg-paper px-4 py-2 text-center min-w-[90px]">
                <div className="mono text-[10px] uppercase">M{idx+1}</div>
                <div className="text-[16px] font-bold">{scores?.[mid] ?? "—"}</div>
                <div className="mono text-[9px] truncate max-w-[100px]">{mid.slice(0,12)}</div>
              </div>
            ))}
            {!scores && <div className="border border-dashed border-ink px-4 py-2 mono text-[11px]">Waiting for judge…</div>}
          </div>
        </div>
        <div className="col-span-12 border-[1.5px] border-ink bg-paper">
          <div className="flex justify-between px-4 py-2 border-b-[1.5px] border-ink mono text-[10px] uppercase"><span>Event stream • uuid + created_at deduped</span><span>{arts.length} events</span></div>
          <div className="max-h-[160px] overflow-auto px-4 py-2 mono text-[11px] leading-5 text-zinc-600">
            {arts.slice(-20).map((a,i)=><div key={i} className="truncate">[{a.phase}] {a.model_id} → {(a.artifact.slice(0,120).replace(/\n/g," "))}...</div>)}
            {arts.length===0 && <div>No events yet — queueing…</div>}
            <div ref={bottomRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
