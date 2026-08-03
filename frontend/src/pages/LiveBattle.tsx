import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, streamBattle, type BattleOut, type StreamEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import CodePane from "@/components/CodePane";

type CodeArtifact = { phase: string; model_id: string; artifact: string; t: number };

export default function LiveBattle() {
  const { id } = useParams<{ id: string }>();
  const { user, jwt, refreshJwt } = useAuth();
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

  const winner = useMemo(()=>{
    if (!scores || !modelIds.length) return null;
    return modelIds.reduce((best, m)=> (scores[m] > scores[best] ? m : best), modelIds[0]);
  }, [scores, modelIds]);

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

  const statusPill = status === "completed" ? "border-success/30 bg-success/10 text-success"
    : status === "running" ? "border-accent/30 bg-accent-soft text-accent"
    : status === "failed" || status === "cancelled" ? "border-danger/30 bg-danger/10 text-danger"
    : "border-border text-muted";

  if (!user) return <div className="p-8 text-[13px] text-muted">Login required — <Link to="/login" className="link">log in</Link></div>;

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 place-items-center rounded-lg border border-borderStrong bg-surface2 text-[12px] font-bold">{String(id).slice(0,1).toUpperCase()}</div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-semibold tracking-[-0.01em]">{battle?.format_id || "battle"} • {String(id).slice(0,8)}</span>
              <span className={`rounded-md border px-2 py-0.5 text-[10px] font-medium uppercase ${statusPill}`}>
                {status === "running" && <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />}
                {status.toUpperCase()}
              </span>
            </div>
            <div className="mt-0.5 font-mono text-[11px] text-muted">phase: {phase} • {battle?.round_visibility || "isolated"} • {battle?.timeout_seconds || 600}s</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-border px-3 py-1.5 font-mono text-[11px] text-muted">{arts.length} artifacts</span>
          <button onClick={cancel} disabled={busy==="cancel" || ["completed","failed","cancelled"].includes(status)} className="btn btn-danger h-8 px-3 text-[11px]">STOP</button>
          <button onClick={save} disabled={busy==="save" || !!battle?.saved} className="btn btn-ghost h-8 px-3 text-[11px]">{battle?.saved ? "SAVED" : "SAVE"}</button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {[
          {k:"build", label:"Build", done: arts.some(a=>a.phase==="build")},
          {k:"break", label:"Break / Escape", active: phase==="break"||phase==="duel"||phase==="race", done: status==="completed"},
          {k:"judge", label:"Judge", active: phase==="judge", done: status==="completed"},
        ].map((p,idx)=>(
          <div key={p.k} className="flex items-center gap-2">
            {idx>0 && <div className={`h-px w-8 ${p.done||p.active ? "bg-accent" : "bg-border"}`} />}
            <div className={`rounded-md border px-3 py-1 text-[11px] font-medium uppercase ${p.active ? "border-accent bg-accent text-accent-fg" : p.done ? "border-success/40 bg-success/10 text-success" : "border-border text-muted"}`}>{p.label}</div>
          </div>
        ))}
      </div>

      {err && <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger break-all">{err}</div>}

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 lg:col-span-6">
          <CodePane
            modelId={modelA}
            label={`${modelA} • builder`}
            code={codeA}
            status={status}
            color="neutral"
            artifactMeta={`${(codeA.length/1024).toFixed(1)}kb • Python`}
            win={codeA.includes("ESCAPE_OK")}
            winText="WIN CONDITION MET"
          />
        </div>
        <div className="col-span-12 lg:col-span-6">
          <CodePane
            modelId={modelB}
            label={`${modelB} • breaker`}
            code={codeB}
            status={status}
            color="neutral"
            artifactMeta={`${(codeB.length/1024).toFixed(1)}kb • Python`}
            win={codeB.includes("ESCAPE_OK")}
            winText="WIN CONDITION MET"
          />
        </div>

        <div className="col-span-12 card flex flex-wrap items-center gap-4 p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-8 w-8 place-items-center rounded-full border border-borderStrong bg-surface2 text-[12px] font-bold">J</div>
            <div>
              <div className="text-[12px] font-semibold">Host Judge • Kimi-K3 • rubric from format</div>
              <div className="font-mono text-[10px] text-muted">reasoning redacted • clamped 0-100 • retry x3</div>
            </div>
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            {modelIds.map((mid,idx)=>(
              <div key={mid} className={`rounded-lg border px-4 py-2 text-center min-w-[100px] ${winner===mid && scores ? "border-accent bg-accent-soft" : "border-border"}`}>
                <div className="font-mono text-[9px] uppercase tracking-wider text-muted">M{idx+1} • {mid.slice(0,12)}</div>
                <div className={`mt-1 text-[20px] font-semibold ${winner===mid && scores ? "text-accent" : ""}`}>{scores?.[mid] ?? "—"}</div>
                {winner===mid && scores && <div className="font-mono text-[10px] text-accent">winner</div>}
              </div>
            ))}
            {!scores && <div className="rounded-lg border border-dashed border-border px-4 py-2 font-mono text-[11px] text-muted">Waiting for judge…</div>}
          </div>
        </div>

        <div className="col-span-12 card overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-4 py-2">
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted">Event stream • uuid + created_at deduped</span>
            <span className="font-mono text-[10px] text-muted">{arts.length} events</span>
          </div>
          <div className="max-h-[160px] overflow-auto px-4 py-2 font-mono text-[11px] leading-5 text-muted">
            {arts.slice(-20).map((a,i)=><div key={i} className="truncate">[{a.phase}] {a.model_id} → {a.artifact.slice(0,120).replace(/\n/g," ")}...</div>)}
            {arts.length===0 && <div>No events yet — queueing…</div>}
            <div ref={bottomRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
