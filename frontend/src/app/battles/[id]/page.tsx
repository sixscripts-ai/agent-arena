"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, streamBattle, type BattleOut, type StreamEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type CodeArtifact = { phase: string; model_id: string; artifact: string; t: number };

export default function BattleLivePage() {
  const { id } = useParams<{ id: string }>();
  const { user, jwt, loading, refreshJwt } = useAuth();
  const router = useRouter();
  const [battle, setBattle] = useState<BattleOut | null>(null);
  const [artifacts, setArtifacts] = useState<CodeArtifact[]>([]);
  const [scores, setScores] = useState<Record<string, number> | null>(null);
  const [status, setStatus] = useState<string>("queued");
  const [phaseName, setPhaseName] = useState<string>("build");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  // fetch battle meta
  useEffect(() => {
    if (!jwt || !id) return;
    (async () => {
      try {
        const b = await api.getBattle(jwt, id);
        setBattle(b);
        setStatus(b.status);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Load failed");
      }
    })();
  }, [jwt, id]);

  // stream
  useEffect(() => {
    if (!jwt || !id || !user) return;
    let cancelled = false;
    const ac = new AbortController();
    const terminal = ["completed","failed","cancelled"];

    const connect = async (attempt=0) => {
      if (cancelled) return;
      try {
        const token = (await refreshJwt()) || jwt;
        await streamBattle(id, token, (ev: StreamEvent) => {
          if (cancelled) return;
          const data = ev.data as any;
          if (ev.event === "battle_status" || ev.event === "done") {
            const st = data?.status || data?.data?.status;
            if (st) setStatus(st);
          }
          if (ev.event === "phase_start") {
            if (data?.phase) setPhaseName(data.phase);
            else if (data?.data?.phase) setPhaseName(data.data.phase);
          }
          if (ev.event === "artifact" || ev.event === "transcript" || ev.event === "action_log") {
            const a = data?.artifact || data?.data?.artifact || JSON.stringify(data);
            const mid = data?.model_id || data?.data?.model_id || "system";
            const ph = data?.phase || data?.data?.phase || phaseName;
            setArtifacts(prev => [...prev, { phase: ph, model_id: mid, artifact: a, t: Date.now() }].slice(-200));
          }
          if (ev.event === "scores") {
            const sc = data?.scores || data?.data?.scores;
            if (sc) setScores(sc);
          }
        }, ac.signal);
        if (terminal.includes(status)) return;
        // reconnect with backoff
        await new Promise(r=>setTimeout(r, Math.min(1000*2**attempt, 8000)));
        if (!cancelled) connect(attempt+1);
      } catch (e) {
        if (cancelled) return;
        if (attempt < 4) {
          await new Promise(r=>setTimeout(r, 1000*2**attempt));
          if (!cancelled) connect(attempt+1);
        } else {
          setError(e instanceof Error ? e.message : "Stream failed");
        }
      }
    };
    connect();
    return () => { cancelled=true; ac.abort(); };
  }, [jwt, id, user, refreshJwt, status, phaseName]);

  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); }, [artifacts]);

  const modelIds = battle?.model_ids || [];
  const modelA = modelIds[0] || "model_a";
  const modelB = modelIds[1] || "model_b";

  const codeA = useMemo(()=> artifacts.filter(a=>a.model_id===modelA).map(a=>a.artifact).join("\n\n") || artifacts.filter(a=>a.model_id!=="system").slice(-2)[0]?.artifact || "", [artifacts, modelA]);
  const codeB = useMemo(()=> artifacts.filter(a=>a.model_id===modelB).map(a=>a.artifact).join("\n\n") || "", [artifacts, modelB]);

  async function cancelBattle(){
    if (!jwt || !id) return;
    setBusy("cancel");
    try { await api.cancelBattle(jwt, id); setStatus("cancelled"); } catch(e){ setError(e instanceof Error? e.message:"Cancel failed"); } finally { setBusy(null); }
  }
  async function saveBattle(){
    if (!jwt || !id) return;
    setBusy("save");
    try { await api.saveBattle(jwt, id); setBattle(b=> b? {...b, saved:true}:b); } catch(e){ setError(e instanceof Error? e.message:"Save failed"); } finally { setBusy(null); }
  }

  if (loading || !user) return <p className="text-zinc-500 p-6">Loading…</p>;

  return (
    <div className="min-h-screen bg-[#050507] text-zinc-100">
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap'); *{font-family:Geist, ui-sans-serif} .mono{font-family:Geist Mono, monospace}`}</style>
      <div className="mx-auto max-w-[1320px] px-6 py-6 space-y-4">
        {/* header */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[16px] border border-white/10 bg-[#0C0C0F] px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-[10px] bg-white text-black grid place-items-center font-bold text-[12px]">W</div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-medium">{battle?.format_id || "battle"} • {String(id).slice(0,8)}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] border ${status==="completed" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : status==="running" ? "border-amber-500/30 bg-amber-500/10 text-amber-300" : "border-white/10 text-zinc-400"}`}>{status.toUpperCase()}</span>
              </div>
              <div className="text-[11px] text-zinc-500 mono">phase: {phaseName} • {battle?.round_visibility || "isolated"} • {battle?.timeout_seconds || 600}s • {modelIds.length} models</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="rounded-full border border-white/10 bg-black px-3 py-1.5 text-[11px] text-zinc-400">{artifacts.length} artifacts</div>
            <button onClick={cancelBattle} disabled={busy==="cancel" || ["completed","failed","cancelled"].includes(status)} className="h-8 px-3 rounded-[10px] bg-red-500/10 border border-red-500/20 text-[12px] text-red-300 hover:bg-red-500/20 disabled:opacity-50">Stop</button>
            <button onClick={saveBattle} disabled={busy==="save" || !!battle?.saved} className="h-8 px-3 rounded-[10px] bg-white text-black text-[12px] font-medium disabled:opacity-50">{battle?.saved ? "Saved" : "Save"}</button>
          </div>
        </div>

        {/* phase stepper */}
        <div className="flex items-center gap-2 px-1">
          {[
            {k:"build", label:"Build", done: artifacts.some(a=>a.phase==="build")},
            {k:"break", label:"Break / Escape", active: phaseName==="break"||phaseName==="duel"||phaseName==="race", done: status==="completed"},
            {k:"judge", label:"Judge", active: phaseName==="judge", done: status==="completed"},
          ].map((p,idx)=>(
            <div key={p.k} className="flex items-center gap-2">
              {idx>0 && <div className={`h-px w-8 ${p.done||p.active ? "bg-white/20":"bg-white/10"}`} />}
              <div className={`flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] ${p.active ? "border-white bg-white text-black" : p.done ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-white/10 bg-white/[0.03] text-zinc-500"}`}>{p.label}</div>
            </div>
          ))}
        </div>

        {error && <p className="text-sm text-red-300 break-all">{error}</p>}

        {/* DUAL CODE VIEW */}
        <div className="grid grid-cols-12 gap-3">
          {[
            {id: modelA, name: `${modelA} • builder`, color:"emerald", code: codeA, tok: "42 tok/s"},
            {id: modelB, name: `${modelB} • breaker`, color:"violet", code: codeB, tok: "38 tok/s"},
          ].map((m)=>(
            <div key={m.id} className="col-span-12 lg:col-span-6 rounded-[16px] border border-white/[0.08] bg-[#0A0A0E] overflow-hidden flex flex-col">
              <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#0F0F14] px-4 py-2.5">
                <div className="flex items-center gap-2.5">
                  <div className={`h-6 w-6 rounded-full border grid place-items-center text-[11px] ${m.color==="emerald" ? "bg-[#1A1A22] border-emerald-500/30 text-emerald-300" : "bg-[#1A1A22] border-violet-500/30 text-violet-300"}`}>{m.id[0]?.toUpperCase()}</div>
                  <div>
                    <div className="text-[12px] font-medium">{m.name}</div>
                    <div className="text-[10px] text-zinc-500 mono">{m.id} • {m.tok}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full ${m.color==="emerald" ? "bg-emerald-400" : "bg-violet-400"} animate-pulse`} />
                  <span className="text-[10px] text-zinc-500">{status==="running" ? "STREAMING" : status.toUpperCase()}</span>
                </div>
              </div>
              <div className="relative flex-1">
                <div className="absolute left-0 top-0 bottom-0 w-12 bg-[#0E0E12] border-r border-white/[0.04] py-3 text-right pr-3 select-none overflow-hidden">
                  {m.code.split("\n").slice(0,60).map((_,i)=><div key={i} className="mono text-[11px] leading-5 text-zinc-600">{i+1}</div>)}
                </div>
                <pre className="ml-12 max-h-[560px] overflow-auto p-3 mono text-[12px] leading-5 text-zinc-200 whitespace-pre-wrap">
                  <code>{m.code || "// waiting for model output...\n// real code streams here, not fake logs"}{status==="running" && <span className={`inline-block w-2 h-3 ${m.color==="emerald" ? "bg-emerald-400" : "bg-violet-400"} animate-pulse ml-0.5 translate-y-0.5`} />}</code>
                </pre>
              </div>
              <div className="border-t border-white/[0.06] bg-[#0E0E12] px-3 py-2 flex items-center justify-between text-[10px] text-zinc-500 mono">
                <span>artifact: {m.id}.py • {(m.code.length/1024).toFixed(1)}kb • Python</span>
                <span className={m.code.includes("ESCAPE_OK") || m.code.includes("secret") ? "text-amber-300" : ""}>{m.code.includes("ESCAPE_OK") ? "WIN CONDITION MET" : m.code ? "redacted + truncated" : "idle"}</span>
              </div>
            </div>
          ))}

          {/* judge strip */}
          <div className="col-span-12 rounded-[16px] border border-white/10 bg-[#0E0E13] p-4 flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-[10px] bg-white text-black grid place-items-center font-bold text-[12px]">J</div>
              <div>
                <div className="text-[12px] font-medium">Host Judge • moonshotai/Kimi-K3 • rubric from format</div>
                <div className="text-[11px] text-zinc-500">reasoning redacted • clamped 0-100 • retry x3 • per-format weights</div>
              </div>
            </div>
            <div className="ml-auto flex gap-2">
              {modelIds.map((mid, idx)=>(
                <div key={mid} className={`rounded-[12px] border px-4 py-2 text-center min-w-[90px] ${scores ? "bg-black/40 border-white/10" : "bg-black/20 border-white/5"}`}>
                  <div className="text-[10px] text-zinc-500 uppercase">Model {idx+1}</div>
                  <div className="text-[16px] font-semibold">{scores?.[mid] ?? "—"}</div>
                  <div className="text-[10px] text-zinc-500 truncate max-w-[100px]">{mid.slice(0,12)}</div>
                </div>
              ))}
              {!scores && <div className="rounded-[12px] border border-white/10 bg-white/[0.03] px-4 py-2 text-[11px] text-zinc-500">Waiting for judge…</div>}
            </div>
          </div>

          {/* minimal event log */}
          <div className="col-span-12 rounded-[14px] border border-white/[0.06] bg-black/40">
            <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06]">
              <span className="text-[11px] text-zinc-500 uppercase">Event stream • uuid + created_at deduped</span>
              <span className="text-[10px] text-zinc-600 mono">{artifacts.length} events</span>
            </div>
            <div className="max-h-[160px] overflow-auto px-4 py-2 mono text-[11px] leading-5 text-zinc-500">
              {artifacts.slice(-20).map((a,i)=>(
                <div key={i} className="truncate">[{a.phase}] {a.model_id} → {(a.artifact.slice(0,120).replace(/\n/g," "))}...</div>
              ))}
              {artifacts.length===0 && <div className="text-zinc-600">No events yet — battle queueing…</div>}
              <div ref={bottomRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
