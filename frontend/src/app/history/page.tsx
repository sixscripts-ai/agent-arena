"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type BattleOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HistoryPage() {
  const { user, jwt, loading } = useAuth();
  const router = useRouter();
  const [battles, setBattles] = useState<BattleOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!jwt) return;
    (async () => {
      try {
        const listed = await api.listBattles(jwt, true);
        setBattles(Array.isArray(listed) ? listed : []);
      } catch {
        // Fallback: localStorage IDs from this device
        try {
          const ids = JSON.parse(localStorage.getItem("arena_battle_ids") || "[]") as string[];
          const results: BattleOut[] = [];
          for (const id of ids.slice(0, 20)) {
            try {
              results.push(await api.getBattle(jwt, id));
            } catch {
              /* skip */
            }
          }
          setBattles(results.filter((b) => b.saved));
        } catch (e) {
          setError(e instanceof Error ? e.message : "Failed");
        }
      }
    })();
  }, [jwt]);

  if (loading || !user) return <p className="text-zinc-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">History</h1>
      <p className="text-sm text-zinc-400">Saved battles and deep links from this device.</p>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="space-y-3">
        {battles.map((b) => {
          const id = b.id || (b as { $id?: string }).$id || "";
          return (
            <Card key={id}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="font-mono text-sm">{id}</CardTitle>
                <Badge>{b.status}</Badge>
              </CardHeader>
              <CardContent className="text-sm text-zinc-400">
                <div>format: {b.format_id}</div>
                <div>models: {(b.model_ids || []).join(", ")}</div>
                <Link
                  href={`/battles/${id}`}
                  className="mt-2 inline-block text-emerald-400 hover:underline"
                >
                  Open →
                </Link>
              </CardContent>
            </Card>
          );
        })}
        {!battles.length && (
          <p className="text-sm text-zinc-500">No saved battles yet.</p>
        )}
      </div>
    </div>
  );
}
