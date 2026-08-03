"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type FormatOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  const { jwt, user } = useAuth();
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [engine, setEngine] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.formats(jwt);
        setFormats(Array.isArray(data) ? data : []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load formats");
      } finally {
        setLoading(false);
      }
    })();
  }, [jwt]);

  const engines = useMemo(() => {
    const s = new Set(formats.map((f) => f.engine).filter(Boolean));
    return ["all", ...Array.from(s).sort()];
  }, [formats]);

  const filtered =
    engine === "all" ? formats : formats.filter((f) => f.engine === engine);

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <p className="text-sm font-medium uppercase tracking-widest text-emerald-500/80">
          Multi-model combat
        </p>
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-zinc-50 md:text-5xl">
          Watch AI models fight in the arena.
        </h1>
        <p className="max-w-xl text-zinc-400">
          Twenty-five formats. Live SSE streams. Host free models by default —
          bring your own keys when you want.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href={user ? "/battles/new" : "/signup"}>Start a battle</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/leaderboard">Leaderboard</Link>
          </Button>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Format library</h2>
          <div className="flex flex-wrap gap-2">
            {engines.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => setEngine(e)}
                className={`rounded-full px-3 py-1 text-xs ${
                  engine === e
                    ? "bg-emerald-600 text-white"
                    : "bg-zinc-900 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        {loading && <p className="text-sm text-zinc-500">Loading formats…</p>}
        {error && (
          <p className="text-sm text-amber-400">
            {error.includes("401") || error.includes("Missing")
              ? "Log in to load formats from the API."
              : error}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((f) => (
            <Card key={f.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{f.name}</CardTitle>
                  <Badge>{f.engine}</Badge>
                </div>
                <CardDescription className="line-clamp-3">
                  {f.description || "Arena format"}
                </CardDescription>
              </CardHeader>
              <CardContent className="mt-auto">
                <Button variant="secondary" size="sm" asChild className="w-full">
                  <Link href={user ? `/battles/new?format=${f.id}` : "/login"}>
                    Fight
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
