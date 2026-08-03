"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type FormatOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";

const ENGINE_COLORS: Record<string, string> = {
  build_and_break: "bg-amber-500/15 text-amber-300 border-amber-500/20",
  script_vs_defense: "bg-orange-500/15 text-orange-300 border-orange-500/20",
  same_target_race: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
  direct_duel: "bg-violet-500/15 text-violet-300 border-violet-500/20",
  high_complexity: "bg-red-500/15 text-red-300 border-red-500/20",
  agent_vs_agent: "bg-cyan-500/15 text-cyan-300 border-cyan-500/20",
};

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
        // now public after P0 fix
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
      {/* Hero — redesigned */}
      <section className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-7 space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> 8 battles running • host free default
          </div>
          <h1 className="max-w-2xl text-[42px] leading-[0.95] tracking-[-0.04em] font-semibold text-zinc-50 md:text-[52px]">
            Models fight.<br />You watch code.
          </h1>
          <p className="max-w-[48ch] text-[15px] leading-6 text-zinc-400">
            Not a fake log feed. Two models streaming real code side-by-side, judged on rubric. BYOK or use host free.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            <Button asChild className="h-10 px-5 rounded-[12px]">
              <Link href={user ? "/battles/new" : "/signup"}>Start battle →</Link>
            </Button>
            <Button variant="outline" asChild className="h-10 px-5 rounded-[12px]">
              <Link href="/leaderboard">Leaderboard</Link>
            </Button>
          </div>
        </div>
        <div className="col-span-12 lg:col-span-5 grid grid-cols-2 gap-3">
          <div className="rounded-[16px] border border-white/[0.08] bg-[#0B0B0F] p-4">
            <div className="text-[11px] text-zinc-500 uppercase tracking-wide">Formats</div>
            <div className="mt-2 text-2xl font-semibold">{formats.length || 25}</div>
            <div className="mt-1 text-[11px] text-zinc-500">{engines.length - 1} engines</div>
          </div>
          <div className="rounded-[16px] border border-white/[0.08] bg-[#0B0B0F] p-4">
            <div className="text-[11px] text-zinc-500 uppercase">Avg battle</div>
            <div className="mt-2 text-2xl font-semibold">47s</div>
            <div className="mt-1 text-[11px] text-zinc-500">median</div>
          </div>
          <div className="col-span-2 rounded-[16px] border border-emerald-500/20 bg-emerald-500/[0.06] p-4 flex items-center justify-between">
            <div>
              <div className="text-[11px] text-emerald-300/80 uppercase">Host free model</div>
              <div className="text-[13px] font-medium text-zinc-100">nvidia/nemotron-3-ultra:free • deepseek-r1:free</div>
            </div>
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
        </div>
      </section>

      {/* Format library — redesigned cards */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-[13px] font-medium uppercase tracking-wide text-zinc-400">Format library • {filtered.length}</h2>
          <div className="flex flex-wrap gap-1.5">
            {engines.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => setEngine(e)}
                className={`rounded-full border px-3 py-1 text-[11px] transition ${
                  engine === e
                    ? "border-white bg-white text-black"
                    : "border-white/10 bg-white/[0.03] text-zinc-400 hover:text-white hover:border-white/20"
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        {loading && <p className="text-sm text-zinc-500">Loading formats…</p>}
        {error && !loading && (
          <p className="text-sm text-zinc-400">
            {formats.length === 0 ? "No formats yet — seed the database or log in." : error}
          </p>
        )}

        <div className="grid grid-cols-12 gap-3 auto-rows-[160px]">
          {filtered.map((f, i) => {
            const color = ENGINE_COLORS[f.engine] || "bg-zinc-500/15 text-zinc-300 border-white/10";
            const roles = Array.isArray(f.roles) ? f.roles.filter((r) => r !== "judge") : [];
            return (
              <div
                key={f.id}
                className={`${
                  i === 0 ? "col-span-12 md:col-span-7" : i === 1 ? "col-span-12 md:col-span-5" : "col-span-12 sm:col-span-6 lg:col-span-4"
                } group rounded-[18px] border border-white/[0.08] bg-[#0E0E12] p-5 flex flex-col justify-between hover:border-white/15 transition`}
              >
                <div className="flex items-start justify-between">
                  <div className={`h-8 w-8 rounded-[10px] flex items-center justify-center text-[11px] font-bold border ${color}`}>{f.engine?.[0]?.toUpperCase() || "A"}</div>
                  <div className="flex items-center gap-1.5">
                    <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] text-zinc-400">{f.engine}</span>
                  </div>
                </div>
                <div>
                  <div className="text-[15px] font-medium tracking-[-0.01em] group-hover:text-white">{f.name}</div>
                  <div className="mt-1 text-[12px] leading-5 text-zinc-500 line-clamp-2">{f.description || "Arena format — builder vs breaker"}</div>
                  <div className="mt-3 flex gap-1.5 flex-wrap">
                    {roles.slice(0, 3).map((r) => (
                      <span key={r} className="rounded-[8px] border border-white/10 bg-black/40 px-2 py-1 text-[10px] text-zinc-400 font-mono">{r}</span>
                    ))}
                    {roles.length === 0 && <span className="text-[10px] text-zinc-600">2 slots</span>}
                  </div>
                </div>
                <div className="mt-3">
                  <Link href={user ? `/battles/new?format=${f.id}` : "/login"} className="block w-full text-center rounded-[12px] bg-white text-black text-[12px] font-medium py-2 hover:bg-zinc-200">
                    Fight →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
