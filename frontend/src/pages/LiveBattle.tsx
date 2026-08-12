/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  Check,
  CheckCircle2,
  Clock3,
  Copy,
  Eye,
  Radio,
  Save,
  Square,
  Trophy,
  XCircle,
} from "lucide-react";
import { api, streamBattle, type BattleOut, type StreamEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import CodePane, { type PaneArtifact } from "@/components/CodePane";

type CodeArtifact = PaneArtifact & { model_id: string };

type ActivityFilter = "all" | string;

const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function timeLabel(t: number): string {
  return new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function preview(text: string): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  return normalized.length > 180 ? `${normalized.slice(0, 180)}…` : normalized;
}

function eventLabel(kind?: string): string {
  if (kind === "action_log") return "TOOL";
  if (kind === "transcript") return "OUTPUT";
  if (kind === "artifact") return "ARTIFACT";
  return (kind || "EVENT").toUpperCase();
}

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
  const [copiedId, setCopiedId] = useState(false);
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");
  const [now, setNow] = useState(Date.now());

  const sessionStartedRef = useRef(Date.now());
  const statusRef = useRef(status);
  const phaseRef = useRef(phase);

  useEffect(() => { statusRef.current = status; }, [status]);
  useEffect(() => { phaseRef.current = phase; }, [phase]);

  useEffect(() => {
    if (TERMINAL_STATES.has(status)) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  useEffect(() => {
    if (!jwt || !id) return;
    let active = true;
    (async () => {
      try {
        const token = (await refreshJwt()) || jwt;
        const b = await api.getBattle(token, id);
        if (!active) return;
        setBattle(b);
        setStatus(b.status);

        try {
          const persisted = await api.artifacts(token, id);
          if (!active || !Array.isArray(persisted) || persisted.length === 0) return;
          const base = Date.now() - persisted.length;
          setArts((current) => {
            if (current.length) return current;
            return persisted.map((item, index) => ({
              phase: item.phase,
              model_id: item.model_id,
              artifact: item.artifact,
              t: base + index,
              kind: "artifact",
            }));
          });
        } catch {
          // A live stream can still work when persisted artifacts are unavailable.
        }
      } catch (e) {
        if (active) setErr(e instanceof Error ? e.message : "Battle failed to load");
      }
    })();
    return () => { active = false; };
  }, [jwt, id, refreshJwt]);

  useEffect(() => {
    if (!jwt || !id || !user) return;
    let cancelled = false;
    const controller = new AbortController();

    const connect = async (attempt = 0): Promise<void> => {
      if (cancelled || TERMINAL_STATES.has(statusRef.current)) return;
      try {
        const token = (await refreshJwt()) || jwt;
        await streamBattle(
          id,
          token,
          (ev: StreamEvent) => {
            if (cancelled) return;
            const wrapped = ev.data as any;
            const data = wrapped?.data ?? wrapped;
            const d = data as any;

            if (ev.event === "battle_status" || ev.event === "done") {
              const nextStatus = d?.status || wrapped?.status;
              if (nextStatus) {
                statusRef.current = nextStatus;
                setStatus(nextStatus);
              }
            }

            if (ev.event === "phase_start") {
              const nextPhase = d?.phase || wrapped?.phase;
              if (nextPhase) {
                phaseRef.current = nextPhase;
                setPhase(nextPhase);
              }
            }

            if (["artifact", "transcript", "action_log"].includes(ev.event)) {
              const artifact = d?.artifact ?? wrapped?.artifact ?? d?.message ?? JSON.stringify(data);
              const modelId = d?.model_id || wrapped?.model_id || "system";
              const eventPhase = d?.phase || wrapped?.phase || phaseRef.current;
              setArts((previous) => [
                ...previous,
                {
                  phase: eventPhase,
                  model_id: modelId,
                  artifact: typeof artifact === "string" ? artifact : JSON.stringify(artifact),
                  t: Date.now(),
                  kind: ev.event,
                },
              ].slice(-300));
            }

            if (ev.event === "scores") {
              const directScores = d?.scores || wrapped?.scores;
              if (directScores) {
                setScores(directScores);
                return;
              }
              try {
                const raw = d?.artifact || wrapped?.artifact;
                const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
                if (parsed?.scores) setScores(parsed.scores);
                else if (parsed?.data?.scores) setScores(parsed.data.scores);
              } catch {}
            }
          },
          controller.signal
        );

        if (!cancelled && !TERMINAL_STATES.has(statusRef.current)) {
          await new Promise((resolve) => window.setTimeout(resolve, Math.min(1000 * 2 ** attempt, 8000)));
          await connect(Math.min(attempt + 1, 4));
        }
      } catch (e) {
        if (cancelled) return;
        if (attempt < 4) {
          await new Promise((resolve) => window.setTimeout(resolve, 1000 * 2 ** attempt));
          await connect(attempt + 1);
        } else if (!TERMINAL_STATES.has(statusRef.current)) {
          setErr(e instanceof Error ? `Live stream disconnected: ${e.message}` : "Live stream disconnected");
        }
      }
    };

    void connect();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [jwt, id, user, refreshJwt]);

  const modelIds = useMemo(() => battle?.model_ids || [], [battle?.model_ids]);

  const histories = useMemo(() => {
    const map = new Map<string, CodeArtifact[]>();
    for (const item of arts) {
      if (!map.has(item.model_id)) map.set(item.model_id, []);
      map.get(item.model_id)!.push(item);
    }
    return map;
  }, [arts]);

  const phases = useMemo(() => {
    const ordered: string[] = [];
    for (const item of arts) {
      if (item.phase && !ordered.includes(item.phase)) ordered.push(item.phase);
    }
    if (phase && !ordered.includes(phase)) ordered.push(phase);
    return ordered.length ? ordered : ["build"];
  }, [arts, phase]);

  const activity = useMemo(() => {
    const filtered = activityFilter === "all" ? arts : arts.filter((item) => item.phase === activityFilter);
    return filtered.slice(-14).reverse();
  }, [arts, activityFilter]);

  const winner = useMemo(() => {
    if (!scores || !modelIds.length) return null;
    return modelIds.reduce((best, model) => (Number(scores[model] ?? -Infinity) > Number(scores[best] ?? -Infinity) ? model : best), modelIds[0]);
  }, [scores, modelIds]);

  const startAt = arts[0]?.t || sessionStartedRef.current;
  const elapsed = formatElapsed(now - startAt);

  async function cancel() {
    if (!jwt || !id) return;
    setBusy("cancel");
    try {
      const token = (await refreshJwt()) || jwt;
      await api.cancelBattle(token, id);
      setStatus("cancelled");
      statusRef.current = "cancelled";
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
      const token = (await refreshJwt()) || jwt;
      await api.saveBattle(token, id);
      setBattle((current) => (current ? { ...current, saved: true } : current));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(null);
    }
  }

  async function copyBattleId() {
    if (!id) return;
    await navigator.clipboard.writeText(id);
    setCopiedId(true);
    window.setTimeout(() => setCopiedId(false), 1200);
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-[960px] rounded-xl border border-dashed border-border bg-surface2/50 p-10 text-center">
        <div className="mx-auto max-w-[36ch] space-y-3">
          <div className="text-[13px] font-semibold">Authentication required</div>
          <p className="text-[13px] leading-6 text-muted">This battle stream is private. Log in to continue your session.</p>
          <Link to="/login" className="btn btn-primary mx-auto mt-2 h-9 px-4 text-[12px]">Log in →</Link>
        </div>
      </div>
    );
  }

  const statusClass = status === "completed"
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
    : status === "running"
      ? "border-accent/30 bg-accent-soft text-accent"
      : status === "failed" || status === "cancelled"
        ? "border-red-500/30 bg-red-500/10 text-red-500"
        : "border-border bg-surface2 text-muted";

  return (
    <div className="mx-auto max-w-[1360px] space-y-4">
      <section className="rounded-xl border border-border bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <div className="flex flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-[10px] border border-borderStrong bg-surface2 font-mono text-[10px] font-semibold text-muted">
              {String(id).slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-[15px] font-semibold tracking-[-0.015em]">{battle?.format_id || "Battle"}</h1>
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.09em] ${statusClass}`}>
                  {status === "running" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
                  {status}
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-2 font-mono text-[9px] text-muted">
                <button type="button" onClick={copyBattleId} className="flex items-center gap-1 hover:text-foreground" title="Copy battle id">
                  {copiedId ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  {String(id).slice(0, 8)}
                </button>
                <span className="h-3 w-px bg-border" />
                <span className="flex items-center gap-1"><Eye className="h-3 w-3" />{battle?.round_visibility || "isolated"}</span>
                <span className="h-3 w-px bg-border" />
                <span className="flex items-center gap-1"><Clock3 className="h-3 w-3" />{elapsed}</span>
                <span className="h-3 w-px bg-border" />
                <span>{battle?.timeout_seconds || 600}s timeout</span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border border-border bg-surface2 px-3 py-2 font-mono text-[9px] text-muted">
              <Activity className="h-3.5 w-3.5" />
              <span>{arts.length} events</span>
              <span className="text-borderStrong">/</span>
              <span>{modelIds.length} agents</span>
            </div>
            <button
              type="button"
              onClick={save}
              disabled={busy === "save" || !!battle?.saved}
              className="btn btn-ghost h-9 px-3 text-[10px]"
            >
              <Save className="h-3.5 w-3.5" /> {battle?.saved ? "Saved" : "Save"}
            </button>
            <button
              type="button"
              onClick={cancel}
              disabled={busy === "cancel" || TERMINAL_STATES.has(status)}
              className="btn btn-danger h-9 px-3 text-[10px]"
            >
              <Square className="h-3.5 w-3.5" /> Stop
            </button>
          </div>
        </div>

        <div className="flex min-h-[48px] items-center gap-2 overflow-x-auto border-t border-border px-3 py-2">
          <span className="mr-1 shrink-0 font-mono text-[8px] uppercase tracking-[0.1em] text-muted">Timeline</span>
          {phases.map((itemPhase, index) => {
            const active = itemPhase === phase && !TERMINAL_STATES.has(status);
            const phaseIndex = phases.indexOf(phase);
            const done = TERMINAL_STATES.has(status) || index < phaseIndex;
            return (
              <button
                key={`${itemPhase}-${index}`}
                type="button"
                onClick={() => setActivityFilter(itemPhase)}
                className={`flex shrink-0 items-center gap-2 rounded-md border px-2.5 py-1.5 transition-colors ${active ? "border-accent/50 bg-accent/10 text-accent" : done ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-500" : "border-border bg-surface2 text-muted"}`}
              >
                <span className="font-mono text-[8px]">{String(index + 1).padStart(2, "0")}</span>
                <span className="font-mono text-[8px] uppercase tracking-[0.08em]">{itemPhase}</span>
                {active ? <Radio className="h-3 w-3 animate-pulse" /> : done ? <CheckCircle2 className="h-3 w-3" /> : null}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => setActivityFilter("all")}
            className={`ml-auto shrink-0 rounded-md border px-2.5 py-1.5 font-mono text-[8px] uppercase tracking-[0.08em] ${activityFilter === "all" ? "border-borderStrong bg-background text-foreground" : "border-border text-muted"}`}
          >
            all activity
          </button>
        </div>
      </section>

      {err && (
        <div className="flex items-start gap-3 rounded-lg border border-red-500/25 bg-red-500/[0.06] px-4 py-3 text-[11px] text-red-500">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="min-w-0 flex-1 break-words font-mono">{err}</span>
          <button type="button" onClick={() => setErr(null)} className="shrink-0 underline underline-offset-2">dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-12 gap-3">
        {(modelIds.length ? modelIds : ["model_a", "model_b"]).map((modelId, index) => {
          const modelHistory = histories.get(modelId) || [];
          const artifactHistory = modelHistory.filter((item) => !item.kind || item.kind === "artifact");
          const latest = artifactHistory[artifactHistory.length - 1]?.artifact || modelHistory[modelHistory.length - 1]?.artifact || "";
          return (
            <div key={modelId} className="col-span-12 lg:col-span-6">
              <CodePane
                modelId={modelId}
                label={modelId}
                role={`competitor ${index + 1}`}
                code={latest}
                history={artifactHistory}
                events={modelHistory}
                status={status}
                color={winner === modelId ? "success" : status === "running" ? "accent" : "neutral"}
                artifactMeta={`${(latest.length / 1024).toFixed(1)}kb · ${latest ? latest.split("\n").length : 0} lines`}
                win={winner === modelId && status === "completed"}
                winText="winner"
              />
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-12 gap-3">
        <section className="card col-span-12 min-h-0 overflow-hidden lg:col-span-8">
          <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
            <div>
              <div className="text-[11px] font-semibold">Battle activity</div>
              <div className="mt-0.5 font-mono text-[8px] uppercase tracking-[0.09em] text-muted">bounded execution trace · newest first</div>
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <button
                type="button"
                onClick={() => setActivityFilter("all")}
                className={`rounded-md px-2 py-1 font-mono text-[8px] uppercase ${activityFilter === "all" ? "bg-surface2 text-foreground" : "text-muted"}`}
              >
                all
              </button>
              {phases.map((itemPhase) => (
                <button
                  key={itemPhase}
                  type="button"
                  onClick={() => setActivityFilter(itemPhase)}
                  className={`rounded-md px-2 py-1 font-mono text-[8px] uppercase ${activityFilter === itemPhase ? "bg-surface2 text-foreground" : "text-muted"}`}
                >
                  {itemPhase}
                </button>
              ))}
            </div>
          </header>

          <div className="h-[230px] overflow-auto bg-code p-2">
            {activity.length ? (
              <div className="space-y-1">
                {activity.map((item, index) => {
                  const isTool = item.kind === "action_log";
                  const isArtifact = item.kind === "artifact";
                  return (
                    <div key={`${item.t}-${index}`} className="grid grid-cols-[66px_68px_90px_minmax(0,1fr)] items-start gap-2 rounded-md border border-codeBorder bg-[#0b0d0f] px-2.5 py-2 font-mono text-[9px] leading-4">
                      <span className="text-lineNo">{timeLabel(item.t)}</span>
                      <span className={isTool ? "text-amber-400" : isArtifact ? "text-accent" : "text-violet-300"}>{eventLabel(item.kind)}</span>
                      <span className="truncate text-lineNo">{item.model_id}</span>
                      <span className="min-w-0 text-codeFg/85"><span className="mr-2 uppercase text-lineNo">{item.phase}</span>{preview(item.artifact)}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <Activity className="mx-auto h-5 w-5 text-lineNo" />
                  <div className="mt-2 font-mono text-[9px] text-lineNo">Waiting for battle activity…</div>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="card col-span-12 overflow-hidden lg:col-span-4">
          <header className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <div className="text-[11px] font-semibold">Judge</div>
              <div className="mt-0.5 font-mono text-[8px] uppercase tracking-[0.09em] text-muted">verified score output only</div>
            </div>
            <Trophy className="h-4 w-4 text-muted" />
          </header>

          <div className="h-[230px] overflow-auto p-4">
            {scores && Object.keys(scores).length ? (
              <div className="space-y-3">
                {Object.entries(scores)
                  .sort(([, a], [, b]) => Number(b) - Number(a))
                  .map(([model, score], index) => (
                    <div key={model} className={`rounded-lg border p-3 ${winner === model ? "border-accent/35 bg-accent/[0.06]" : "border-border bg-surface2/40"}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[8px] text-muted">#{index + 1}</span>
                            <span className="truncate text-[11px] font-medium">{model}</span>
                          </div>
                          {winner === model && <div className="mt-1 font-mono text-[8px] uppercase tracking-[0.09em] text-accent">current winner</div>}
                        </div>
                        <div className="text-[24px] font-semibold tracking-[-0.04em]">{Number(score).toFixed(Number(score) % 1 ? 1 : 0)}</div>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="grid h-full place-items-center text-center">
                <div className="max-w-[240px]">
                  <Trophy className="mx-auto h-5 w-5 text-muted" />
                  <div className="mt-2 text-[11px] font-medium">Judge pending</div>
                  <p className="mt-1 text-[10px] leading-5 text-muted">Scores appear here only when the backend emits a real judge result. No placeholder dimensions are fabricated.</p>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
