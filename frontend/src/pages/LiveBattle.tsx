import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Activity, Archive, CircleStop, Clock3, Radio, Scale, ShieldCheck, Swords } from "lucide-react";
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

  useEffect(() => {
    if (!jwt || !id) return;
    (async () => {
      try {
        const b = await api.getBattle(jwt, id);
        setBattle(b);
        setStatus(b.status);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Load failed");
      }
    })();
  }, [jwt, id]);

  useEffect(() => {
    if (!jwt || !id || !user) return;
    let cancelled = false;
    const ac = new AbortController();

    const connect = async (attempt = 0) => {
      if (cancelled) return;
      try {
        const token = (await refreshJwt()) || jwt;
        await streamBattle(id, token, (ev: StreamEvent) => {
          if (cancelled) return;
          const data = ev.data as any;
          const d = data?.data || data;

          if (ev.event === "battle_status" || ev.event === "done") {
            const st = d?.status || data?.status;
            if (st) setStatus(st);
          }
          if (ev.event === "phase_start" && (d?.phase || data?.phase)) {
            setPhase(d?.phase || data?.phase);
          }
          if (["artifact", "transcript", "action_log"].includes(ev.event)) {
            const artifact = d?.artifact || data?.artifact || JSON.stringify(data);
            const mid = d?.model_id || data?.model_id || "system";
            const ph = d?.phase || data?.phase || phase;
            setArts(prev => [...prev, { phase: ph, model_id: mid, artifact, t: Date.now() }].slice(-200));
          }
          if (ev.event === "scores") {
            const sc = d?.scores || data?.scores;
            if (sc) setScores(sc);
          }
        }, ac.signal);

        if (!["completed", "failed", "cancelled"].includes(status)) {
          await new Promise(r => setTimeout(r, Math.min(1000 * 2 ** attempt, 8000)));
          if (!cancelled) connect(attempt + 1);
        }
      } catch {
        if (attempt < 4 && !cancelled) {
          await new Promise(r => setTimeout(r, 1000 * 2 ** attempt));
          connect(attempt + 1);
        }
      }
    };

    connect();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [jwt, id, user, refreshJwt, status, phase]);

  const modelIds = battle?.model_ids || [];
  const modelA = modelIds[0] || "model_a";
  const modelB = modelIds[1] || "model_b";

  const historyA = useMemo(() => arts.filter(a => a.model_id === modelA), [arts, modelA]);
  const historyB = useMemo(() => arts.filter(a => a.model_id === modelB), [arts, modelB]);
  const codeA = historyA.at(-1)?.artifact || "";
  const codeB = historyB.at(-1)?.artifact || "";

  const winner = useMemo(() => {
    if (!scores || !modelIds.length) return null;
    return modelIds.reduce((best, m) => ((scores[m] ?? -Infinity) > (scores[best] ?? -Infinity) ? m : best), modelIds[0]);
  }, [scores, modelIds]);

  const activity = useMemo(() => [...arts].slice(-10).reverse(), [arts]);

  async function cancel() {
    if (!jwt || !id) return;
    setBusy("cancel");
    try {
      await api.cancelBattle(jwt, id);
      setStatus("cancelled");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    if (!jwt || !id) return;
    setBusy("save");
    try {
      await api.saveBattle(jwt, id);
      setBattle(b => b ? { ...b, saved: true } : b);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(null);
    }
  }

  const statusPill = status === "completed"
    ? "border-success/30 bg-success/10 text-success"
    : status === "running"
      ? "border-accent/30 bg-accent-soft text-accent"
      : status === "failed" || status === "cancelled"
        ? "border-danger/30 bg-danger/10 text-danger"
        : "border-border text-muted";

  if (!user) {
    return <div className="p-8 text-[13px] text-muted">Login required — <Link to="/login" className="link">log in</Link></div>;
  }

  return (
    <div className="space-y-4">
      <section className="card overflow-hidden">
        <div className="arena-grid relative flex flex-wrap items-center justify-between gap-4 px-5 py-4 md:px-6">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent-soft/40 to-transparent opacity-40" />
          <div className="relative flex min-w-0 items-center gap-3.5">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-accent/30 bg-accent-soft text-accent">
              <Swords className="h-5 w-5" strokeWidth={1.7} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow">live battle monitor</div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <h1 className="truncate text-[15px] font-semibold tracking-[-0.02em]">{battle?.format_id || "battle"} / {String(id).slice(0, 8)}</h1>
                <span className={`rounded-full border px-2 py-0.5 font-mono text-[8px] font-semibold uppercase tracking-[0.1em] ${statusPill}`}>
                  {status === "running" && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-accent soft-pulse" />}
                  {status}
                </span>
              </div>
              <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.08em] text-muted">
                phase {phase} / {battle?.round_visibility || "isolated"} visibility / {battle?.timeout_seconds || 600}s timeout
              </div>
            </div>
          </div>

          <div className="relative flex flex-wrap items-center gap-2">
            <span className="tag"><Activity className="h-3 w-3" /> {arts.length} artifacts</span>
            <button
              onClick={cancel}
              disabled={busy === "cancel" || ["completed", "failed", "cancelled"].includes(status)}
              className="btn btn-danger h-8 px-3 text-[10px]"
            >
              <CircleStop className="h-3.5 w-3.5" /> Stop
            </button>
            <button
              onClick={save}
              disabled={busy === "save" || !!battle?.saved}
              className="btn btn-ghost h-8 px-3 text-[10px]"
            >
              <Archive className="h-3.5 w-3.5" /> {battle?.saved ? "Saved" : "Save"}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 border-t border-border bg-bg-soft/70">
          {[
            { label: "Execute", sub: "model runtime", active: status === "running" && phase !== "judge", done: ["completed"].includes(status) || phase === "judge" },
            { label: "Observe", sub: "artifact stream", active: status === "running", done: status === "completed" },
            { label: "Evaluate", sub: "host judge", active: phase === "judge", done: status === "completed" },
          ].map((step, index) => (
            <div key={step.label} className={`relative border-r border-border px-4 py-3 last:border-r-0 ${step.active ? "bg-accent-soft" : ""}`}>
              <div className="flex items-center gap-2">
                <span className={`grid h-5 w-5 place-items-center rounded-full border font-mono text-[8px] ${step.done ? "border-success/40 bg-success/10 text-success" : step.active ? "border-accent/40 bg-accent-soft text-accent" : "border-border text-muted"}`}>{index + 1}</span>
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.06em]">{step.label}</div>
                  <div className="mt-0.5 hidden font-mono text-[8px] text-muted sm:block">{step.sub}</div>
                </div>
              </div>
              {step.active && <span className="absolute inset-x-0 bottom-0 h-px bg-accent" />}
            </div>
          ))}
        </div>
      </section>

      {err && <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-[11px] text-danger break-all">{err}</div>}

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 lg:col-span-6">
          <CodePane
            modelId={modelA}
            label={`${modelA} / competitor 01`}
            code={codeA}
            history={historyA}
            status={status}
            color="accent"
            artifactMeta={`${(codeA.length / 1024).toFixed(1)}kb / ${historyA.length} version${historyA.length === 1 ? "" : "s"}`}
            win={codeA.includes("ESCAPE_OK")}
            winText="win condition met"
          />
        </div>

        <div className="col-span-12 lg:col-span-6">
          <CodePane
            modelId={modelB}
            label={`${modelB} / competitor 02`}
            code={codeB}
            history={historyB}
            status={status}
            color="success"
            artifactMeta={`${(codeB.length / 1024).toFixed(1)}kb / ${historyB.length} version${historyB.length === 1 ? "" : "s"}`}
            win={codeB.includes("ESCAPE_OK")}
            winText="win condition met"
          />
        </div>

        <div className="col-span-12 card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface2 text-muted">
                <Scale className="h-4 w-4" strokeWidth={1.7} />
              </div>
              <div>
                <div className="text-[12px] font-semibold">Host judge</div>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.06em] text-muted">rubric / redacted reasoning / 0–100</div>
              </div>
            </div>
            <span className="tag"><ShieldCheck className="h-3 w-3" /> Kimi-K3</span>
          </div>

          <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2">
            {modelIds.map((mid, idx) => (
              <div key={mid} className={`relative bg-surface px-5 py-4 ${winner === mid && scores ? "bg-accent-soft" : ""}`}>
                {winner === mid && scores && <span className="absolute inset-x-0 top-0 h-px bg-accent" />}
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted">competitor {String(idx + 1).padStart(2, "0")}</div>
                    <div className="mt-1 truncate text-[11px] font-medium">{mid}</div>
                  </div>
                  <div className={`text-[28px] font-semibold tracking-[-0.04em] ${winner === mid && scores ? "text-accent" : ""}`}>{scores?.[mid] ?? "—"}</div>
                </div>
                <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface2">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${winner === mid && scores ? "bg-accent" : "bg-muted"}`}
                    style={{ width: `${Math.max(0, Math.min(100, scores?.[mid] ?? 0))}%` }}
                  />
                </div>
              </div>
            ))}
            {!modelIds.length && <div className="bg-surface p-5 text-[11px] text-muted">Waiting for participants…</div>}
          </div>
        </div>

        <div className="col-span-12 card h-[184px] overflow-hidden">
          <div className="flex h-11 items-center justify-between border-b border-border px-4">
            <div className="flex items-center gap-2">
              <Radio className="h-3.5 w-3.5 text-accent" />
              <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">battle activity</span>
            </div>
            <span className="font-mono text-[9px] text-muted">latest 10 / {arts.length} total</span>
          </div>

          <div className="h-[140px] overflow-auto">
            {activity.map((a, i) => (
              <div key={`${a.t}-${i}`} className="grid grid-cols-[82px_110px_1fr] items-center gap-3 border-b border-border px-4 py-2 last:border-b-0">
                <span className="flex items-center gap-1.5 font-mono text-[8px] text-muted">
                  <Clock3 className="h-3 w-3" />
                  {new Date(a.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
                <span className="truncate font-mono text-[8px] uppercase tracking-[0.06em] text-muted">{a.phase} / {a.model_id}</span>
                <span className="truncate font-mono text-[9px] text-foreground/80">{a.artifact.replace(/\n/g, " ").slice(0, 180)}</span>
              </div>
            ))}
            {activity.length === 0 && (
              <div className="grid h-full place-items-center font-mono text-[10px] text-muted">No runtime activity yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
