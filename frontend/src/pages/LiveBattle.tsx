/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useRef, useState, useCallback, useLayoutEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { api, streamBattle, type BattleOut, type StreamEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import CodePane from "@/components/CodePane";

type CodeArtifact = { phase: string; model_id: string; artifact: string; t: number };

type LogFilter = "all" | "build" | "break" | "judge";

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
  const [logFilter, setLogFilter] = useState<LogFilter>("all");
  const [logAutoScroll, setLogAutoScroll] = useState(true);
  const [copiedId, setCopiedId] = useState(false);

  const logRef = useRef<HTMLDivElement>(null);

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
        await streamBattle(
          id,
          token,
          (ev: StreamEvent) => {
            if (cancelled) return;
            const data = (ev.data as any)?.data || ev.data;
            const d = data as any;
            if (ev.event === "battle_status" || ev.event === "done") {
              const st = d?.status || (ev.data as any)?.status;
              if (st) setStatus(st);
            }
            if (ev.event === "phase_start" && (d?.phase || (ev.data as any)?.phase)) {
              setPhase(d?.phase || (ev.data as any)?.phase);
            }
            if (["artifact", "transcript", "action_log"].includes(ev.event)) {
              const artifact = d?.artifact || (ev.data as any)?.artifact || JSON.stringify(data);
              const mid = d?.model_id || (ev.data as any)?.model_id || "system";
              const ph = d?.phase || (ev.data as any)?.phase || phase;
              setArts((prev) => [...prev, { phase: ph, model_id: mid, artifact, t: Date.now() }].slice(-300));
            }
            if (ev.event === "scores") {
              const sc = d?.scores || (ev.data as any)?.scores;
              if (sc) setScores(sc);
            }
          },
          ac.signal
        );
        if (!["completed", "failed", "cancelled"].includes(status)) {
          await new Promise((r) => setTimeout(r, Math.min(1000 * 2 ** attempt, 8000)));
          if (!cancelled) connect(attempt + 1);
        }
      } catch {
        if (attempt < 4 && !cancelled) {
          await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt));
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

  const onLogScroll = useCallback(() => {
    const el = logRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 64;
    setLogAutoScroll(nearBottom);
  }, []);

  useLayoutEffect(() => {
    if (!logAutoScroll || !logRef.current) return;
    logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [arts, logAutoScroll, logFilter]);

  const filteredArts = useMemo(() => {
    if (logFilter === "all") return arts;
    return arts.filter((a) => a.phase === logFilter);
  }, [arts, logFilter]);

  const modelIds = useMemo(() => battle?.model_ids || [], [battle?.model_ids]);
  const modelA = modelIds[0] || "model_a";
  const modelB = modelIds[1] || "model_b";
  const codeA = useMemo(() => arts.filter((a) => a.model_id === modelA).map((a) => a.artifact).join("\n\n"), [arts, modelA]);
  const codeB = useMemo(() => arts.filter((a) => a.model_id === modelB).map((a) => a.artifact).join("\n\n"), [arts, modelB]);

  const winner = useMemo(() => {
    if (!scores || !modelIds.length) return null;
    return modelIds.reduce((best, m) => (scores[m] > scores[best] ? m : best), modelIds[0]);
  }, [scores, modelIds]);

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
      setBattle((b) => (b ? { ...b, saved: true } : b));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(null);
    }
  }

  const statusPill =
    status === "completed"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
      : status === "running"
      ? "border-accent/30 bg-accent-soft text-accent"
      : status === "failed" || status === "cancelled"
      ? "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-300"
      : "border-border bg-surface text-muted";

  const phaseSteps = [
    { k: "build", label: "Build", blurb: "Sandbox + policy" },
    { k: "break", label: "Break", blurb: "Escape / bypass", active: phase === "break" || phase === "duel" || phase === "race" },
    { k: "judge", label: "Judge", blurb: "Rubric • 0-100", active: phase === "judge" },
  ];

  if (!user)
    return (
      <div className="mx-auto max-w-[960px] rounded-xl border border-dashed border-border bg-surface2/50 p-10 text-center">
        <div className="mx-auto max-w-[36ch] space-y-3">
          <div className="text-[13px] font-semibold">Authentication required</div>
          <p className="text-[13px] leading-6 text-muted">This battle stream is private. Log in to continue your session.</p>
          <Link to="/login" className="btn btn-primary mx-auto mt-2 h-9 px-4 text-[12px]">
            Log in →
          </Link>
        </div>
      </div>
    );

  return (
    <div className="mx-auto max-w-[1360px] space-y-4">
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-[10px] border border-borderStrong bg-surface2 font-mono text-[11px] font-bold">
            {String(id).slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-[14px] font-semibold tracking-[-0.01em]">
                {battle?.format_id || "battle"} <span className="text-muted">•</span>{" "}
                <span className="font-mono text-[13px] font-medium">{String(id).slice(0, 8)}</span>
              </h1>
              <button
                onClick={async () => {
                  if (!id) return;
                  await navigator.clipboard.writeText(id);
                  setCopiedId(true);
                  setTimeout(() => setCopiedId(false), 1200);
                }}
                className="rounded-md border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted hover:border-borderStrong hover:text-foreground"
              >
                {copiedId ? "copied" : "copy id"}
              </button>
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide ${statusPill}`}>
                {status === "running" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />}
                {status}
              </span>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-1 w-1 rounded-full bg-muted" />
                phase: {phase}
              </span>
              <span className="h-3 w-px bg-border" />
              <span>{battle?.round_visibility || "isolated"}</span>
              <span className="h-3 w-px bg-border" />
              <span>{battle?.timeout_seconds || 600}s timeout</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="rounded-full border border-border bg-surface2 px-3 py-1 font-mono text-[11px] text-muted">
            {arts.length} events • {modelIds.length} models
          </span>
          <button
            onClick={cancel}
            disabled={busy === "cancel" || ["completed", "failed", "cancelled"].includes(status)}
            className="btn btn-danger h-8 rounded-full px-3.5 text-[11px] font-semibold tracking-wide"
          >
            STOP
          </button>
          <button
            onClick={save}
            disabled={busy === "save" || !!battle?.saved}
            className="btn btn-ghost h-8 rounded-full px-3.5 text-[11px] font-medium"
          >
            {battle?.saved ? "✓ SAVED" : "SAVE"}
          </button>
        </div>
      </div>

      {err && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[12.5px] leading-6 text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
          <span className="mt-0.5 grid h-5 w-5 place-items-center rounded-full bg-red-500 text-[11px] font-bold text-white">!</span>
          <span className="break-all font-mono text-[11px]">{err}</span>
          <button onClick={() => setErr(null)} className="ml-auto text-[11px] underline underline-offset-2">
            dismiss
          </button>
        </div>
      )}

      <div className="flex items-center gap-2 overflow-x-auto rounded-full border border-border bg-surface px-2 py-1.5">
        {phaseSteps.map((p, idx) => {
          const active = (p as any).active || status === "completed" || (idx === 0 && arts.length > 0) || phase === p.k;
          const done = status === "completed" || (idx === 0 && arts.some((a) => a.phase === "build"));
          return (
            <div key={p.k} className="flex items-center gap-2">
              {idx > 0 && (
                <div className={`h-px w-10 transition-colors ${done || active ? "bg-accent" : "bg-border"}`} />
              )}
              <div
                className={`flex items-center gap-2.5 rounded-full border px-3 py-1.5 text-[11px] transition-colors ${
                  active ? "border-accent bg-accent text-accent-fg shadow-sm" : done ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "border-border bg-surface2 text-muted"
                }`}
              >
                <span className={`grid h-5 w-5 place-items-center rounded-full text-[10px] font-bold ${active ? "bg-accent-fg/20" : "bg-surface"}`}>
                  {done && !active ? "✓" : idx + 1}
                </span>
                <span className="font-medium uppercase tracking-wide">{p.label}</span>
                <span className="hidden text-[10px] opacity-70 sm:inline">{p.blurb}</span>
              </div>
            </div>
          );
        })}
        <div className="ml-auto hidden items-center gap-2 pl-2 font-mono text-[10px] text-muted sm:flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
          live • uuid deduped • retry x3
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 lg:col-span-6">
          <CodePane
            modelId={modelA}
            label={`${modelA} • builder`}
            code={codeA}
            status={status}
            color="neutral"
            artifactMeta={`${(codeA.length / 1024).toFixed(1)}kb • Python • ${codeA.split("\n").length} lines`}
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
            artifactMeta={`${(codeB.length / 1024).toFixed(1)}kb • Python • ${codeB.split("\n").length} lines`}
            win={codeB.includes("ESCAPE_OK")}
            winText="ESCAPE_OK • WIN"
          />
        </div>

        <div className="col-span-12 flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-8 w-8 place-items-center rounded-full border border-borderStrong bg-surface2 text-[12px] font-bold">J</div>
            <div>
              <div className="text-[12px] font-semibold tracking-[-0.01em]">Host Judge • rubric from format • clamped 0-100</div>
              <div className="font-mono text-[10px] text-muted">reasoning redacted • deterministic retry • no win badges</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {modelIds.map((mid, idx) => {
              const isWinner = winner === mid && !!scores;
              const score = scores?.[mid];
              return (
                <div
                  key={mid}
                  className={`min-w-[128px] rounded-xl border px-4 py-2.5 text-left transition-all ${
                    isWinner ? "border-accent bg-accent-soft shadow-[0_0_0_1px_var(--accent),0_4px_12px_var(--accent-soft)]" : "border-border bg-surface2/40"
                  }`}
                >
                  <div className="font-mono text-[9px] uppercase tracking-widest text-muted">
                    M{idx + 1} • {mid.slice(0, 14)}
                  </div>
                  <div className="mt-1 flex items-baseline gap-2">
                    <span className={`text-[22px] font-semibold tracking-[-0.02em] leading-none ${isWinner ? "text-accent" : "text-foreground"}`}>
                      {score ?? "—"}
                    </span>
                    {isWinner && <span className="rounded-full bg-accent px-1.5 py-0.5 font-mono text-[9px] font-bold text-accent-fg">WINNER</span>}
                  </div>
                  {isWinner && score !== undefined && <div className="mt-1 font-mono text-[10px] text-accent">+ scored</div>}
                </div>
              );
            })}
            {!scores && modelIds.length === 0 && (
              <div className="rounded-xl border border-dashed border-border bg-surface2/30 px-4 py-3 font-mono text-[11px] text-muted">No models yet</div>
            )}
            {!scores && modelIds.length > 0 && (
              <div className="flex items-center gap-2 rounded-xl border border-dashed border-border bg-surface2/30 px-4 py-3 font-mono text-[11px] text-muted">
                <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                Waiting for judge…
              </div>
            )}
          </div>
        </div>

        <div className="col-span-12 overflow-hidden rounded-xl border border-border bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <div className="flex h-[44px] items-center justify-between border-b border-border bg-surface2/50 px-3">
            <div className="flex items-center gap-3">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">Event stream</span>
              <div className="hidden items-center gap-1 rounded-full border border-border bg-surface p-1 sm:flex">
                {(["all", "build", "break", "judge"] as LogFilter[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => setLogFilter(f)}
                    className={`rounded-full px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-wide transition-colors ${
                      logFilter === f ? "bg-foreground text-background" : "text-muted hover:bg-surface2 hover:text-foreground"
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <span className="font-mono text-[10px] text-muted">{filteredArts.length} / {arts.length} events</span>
            </div>

            <div className="flex items-center gap-2">
              {!logAutoScroll && (
                <button
                  onClick={() => {
                    if (logRef.current) logRef.current.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
                    setLogAutoScroll(true);
                  }}
                  className="inline-flex items-center gap-1 rounded-full border border-accent bg-accent px-2.5 py-1 font-mono text-[10px] font-medium text-accent-fg"
                >
                  ↓ live
                </button>
              )}
              <span className="hidden h-4 w-px bg-border sm:inline-block" />
              <span className="font-mono text-[10px] text-muted">uuid + created_at deduped • fixed 240px</span>
            </div>
          </div>

          <div
            ref={logRef}
            onScroll={onLogScroll}
            className="scrollbar-thin relative h-[240px] overflow-auto overscroll-contain bg-code font-mono text-[11px] leading-5"
            style={{ scrollBehavior: "auto" }}
          >
            <div className="sticky top-0 z-10 flex h-6 items-center gap-2 border-b border-codeBorder bg-code/90 px-3 text-[10px] text-lineNo backdrop-blur">
              <span className="w-[56px]">time</span>
              <span className="w-[64px]">phase</span>
              <span className="w-[120px]">model</span>
              <span className="flex-1">message</span>
            </div>

            {filteredArts.length === 0 ? (
              <div className="grid h-[200px] place-items-center p-8 text-center">
                <div className="space-y-2">
                  <div className="mx-auto grid h-8 w-8 place-items-center rounded-full border border-codeBorder bg-surface2/20 text-lineNo">◌</div>
                  <div className="font-mono text-[11px] text-muted">No events yet — queueing…</div>
                  <div className="font-mono text-[10px] text-lineNo">stream opens in isolated mode • 600s timeout</div>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-codeBorder/40">
                {filteredArts.slice(-120).map((a, i) => (
                  <div key={`${a.t}-${i}`} className="flex items-center gap-2 px-3 py-1.5 hover:bg-white/[0.03]">
                    <span className="w-[56px] shrink-0 tabular-nums text-lineNo">{new Date(a.t).toLocaleTimeString()}</span>
                    <span
                      className={`inline-flex w-[64px] shrink-0 justify-center rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                        a.phase === "build"
                          ? "bg-white/10 text-white/60"
                          : a.phase === "break" || a.phase === "duel"
                          ? "bg-accent-soft text-accent"
                          : "bg-emerald-500/10 text-emerald-300"
                      }`}
                    >
                      {a.phase}
                    </span>
                    <span className="w-[120px] shrink-0 truncate text-codeFg/70">{a.model_id.slice(0, 18)}</span>
                    <span className="min-w-0 flex-1 truncate text-codeFg" title={a.artifact}>
                      {a.artifact.slice(0, 160).replace(/\n/g, " ")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex h-7 items-center justify-between border-t border-border bg-surface2/50 px-3 font-mono text-[10px] text-muted">
            <span>terminal • smooth scroll inside defined section • no page jump</span>
            <span className="hidden sm:inline">auto-scroll: {logAutoScroll ? "on" : "off • scroll to bottom to resume"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
