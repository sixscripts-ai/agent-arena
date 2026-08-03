"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, streamBattle, type BattleOut, type StreamEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type LogLine = { t: number; event: string; text: string };

export default function BattleLivePage() {
  const { id } = useParams<{ id: string }>();
  const { user, jwt, loading, refreshJwt } = useAuth();
  const router = useRouter();
  const [battle, setBattle] = useState<BattleOut | null>(null);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!jwt || !id) return;
    let cancelled = false;
    const ac = new AbortController();

    (async () => {
      try {
        const b = await api.getBattle(jwt, id);
        if (!cancelled) setBattle(b);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Load failed");
      }

      const token = (await refreshJwt()) || jwt;
      try {
        await streamBattle(
          id,
          token,
          (ev: StreamEvent) => {
            if (cancelled) return;
            const text =
              typeof ev.data === "string" ? ev.data : JSON.stringify(ev.data);
            setLogs((prev) =>
              [...prev, { t: Date.now(), event: ev.event, text }].slice(-500),
            );
            if (ev.event === "battle_status" || ev.event === "done") {
              const st =
                typeof ev.data === "object" && ev.data && "status" in ev.data
                  ? String((ev.data as { status: string }).status)
                  : null;
              if (st) {
                setBattle((prev) => (prev ? { ...prev, status: st } : prev));
              }
            }
          },
          ac.signal,
        );
      } catch (e) {
        if (!cancelled && !(e instanceof DOMException && e.name === "AbortError")) {
          setError(e instanceof Error ? e.message : "Stream failed");
        }
      }
    })();

    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [jwt, id, refreshJwt]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  async function cancel() {
    if (!jwt || !id) return;
    setBusy("cancel");
    try {
      await api.cancelBattle(jwt, id);
      setBattle((b) => (b ? { ...b, status: "cancelled" } : b));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
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
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading || !user) return <p className="text-zinc-500">Loading…</p>;

  const status = battle?.status || "…";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Live battle</h1>
          <p className="font-mono text-xs text-zinc-500">{id}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            className={
              status === "completed"
                ? "border-emerald-700 text-emerald-400"
                : status === "failed" || status === "cancelled"
                  ? "border-red-800 text-red-400"
                  : "border-amber-700 text-amber-300"
            }
          >
            {status}
          </Badge>
          <Button
            variant="destructive"
            size="sm"
            onClick={cancel}
            disabled={busy === "cancel" || ["completed", "failed", "cancelled"].includes(status)}
          >
            Stop
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={save}
            disabled={busy === "save" || !!battle?.saved}
          >
            {battle?.saved ? "Saved" : "Save"}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-red-400 break-all">{error}</p>}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-zinc-400">Event stream</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-[60vh] overflow-y-auto rounded-md bg-black/50 p-3 font-mono text-xs leading-relaxed">
            {logs.length === 0 && (
              <p className="text-zinc-600">Waiting for events…</p>
            )}
            {logs.map((l, i) => (
              <div key={i} className="border-b border-zinc-900/80 py-1">
                <span className="text-emerald-500/80">{l.event}</span>{" "}
                <span className="text-zinc-300 break-all">{l.text}</span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
