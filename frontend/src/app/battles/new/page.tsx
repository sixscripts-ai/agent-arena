"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  api,
  playableRoleCount,
  type FormatOut,
  type ProviderOut,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const HOST_FREE = "host:openrouter-free";

export default function NewBattlePage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">Loading…</p>}>
      <NewBattleForm />
    </Suspense>
  );
}

function NewBattleForm() {
  const { user, jwt, loading } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [providers, setProviders] = useState<ProviderOut[]>([]);
  const [formatId, setFormatId] = useState(params.get("format") || "");
  const [selected, setSelected] = useState<string[]>([HOST_FREE, HOST_FREE]);
  const [timeoutSec, setTimeoutSec] = useState(600);
  const [visibility, setVisibility] = useState<"isolated" | "open">("isolated");
  const [save, setSave] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!jwt) return;
    (async () => {
      try {
        const [f, p] = await Promise.all([api.formats(jwt), api.providers(jwt)]);
        setFormats(f);
        setProviders(p);
        if (!formatId && f[0]) setFormatId(f[0].id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Load failed");
      }
    })();
  }, [jwt, formatId]);

  const format = formats.find((f) => f.id === formatId);
  const need = format ? playableRoleCount(format) : 2;

  useEffect(() => {
    setSelected((prev) => {
      const next = prev.slice(0, need);
      while (next.length < need) next.push(HOST_FREE);
      return next;
    });
  }, [need]);

  const modelOptions = useMemo(() => {
    return providers.map((p) => ({ id: p.id, label: `${p.name} (${p.model_name})` }));
  }, [providers]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!jwt || !formatId) return;
    setBusy(true);
    setError(null);
    try {
      const battle = await api.createBattle(jwt, {
        format_id: formatId,
        model_ids: selected,
        arena_size: selected.length,
        timeout_seconds: timeoutSec,
        round_visibility: visibility,
        save,
      });
      try {
        const key = "arena_battle_ids";
        const prev = JSON.parse(localStorage.getItem(key) || "[]") as string[];
        localStorage.setItem(key, JSON.stringify([battle.id, ...prev].slice(0, 50)));
      } catch {
        /* ignore */
      }
      router.push(`/battles/${battle.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading || !user) return <p className="text-zinc-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">Create battle</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label>Format</Label>
              <select
                className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm"
                value={formatId}
                onChange={(e) => setFormatId(e.target.value)}
                required
              >
                {formats.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} · {f.engine}
                  </option>
                ))}
              </select>
              <p className="text-xs text-zinc-500">Needs {need} models (non-judge roles)</p>
            </div>

            {selected.map((mid, i) => (
              <div key={i} className="space-y-1">
                <Label>Model slot {i + 1}</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm"
                  value={mid}
                  onChange={(e) => {
                    const next = [...selected];
                    next[i] = e.target.value;
                    setSelected(next);
                  }}
                >
                  {modelOptions.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            ))}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Timeout (s)</Label>
                <Input
                  type="number"
                  min={30}
                  max={3600}
                  value={timeoutSec}
                  onChange={(e) => setTimeoutSec(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1">
                <Label>Visibility</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 text-sm"
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as "isolated" | "open")}
                >
                  <option value="isolated">isolated (anti-cheat)</option>
                  <option value="open">open arena</option>
                </select>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={save}
                onChange={(e) => setSave(e.target.checked)}
              />
              Save artifacts after battle
            </label>

            {error && <p className="text-sm text-red-400 break-all">{error}</p>}
            <Button type="submit" className="w-full" disabled={busy || !formatId}>
              {busy ? "Starting…" : "Start battle"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
