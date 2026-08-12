import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Braces, Cpu, Gauge, Radio, Swords } from "lucide-react";
import { api, type FormatOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import FormatCard from "@/components/FormatCard";

export default function Home() {
  const { user } = useAuth();
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [engine, setEngine] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await api.formats(null);
        if (!cancelled) setFormats(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setFormats([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const engines = useMemo(() => {
    const s = new Set(formats.map(f => f.engine).filter(Boolean));
    return ["all", ...Array.from(s).sort()];
  }, [formats]);

  const filtered = engine === "all" ? formats : formats.filter(f => f.engine === engine);

  return (
    <div className="space-y-16 md:space-y-24">
      <section className="relative overflow-hidden rounded-[20px] border border-border bg-background/65 px-5 py-10 shadow-[var(--shadow-elevated)] backdrop-blur-xl md:px-10 md:py-14 lg:px-14 lg:py-16">
        <div className="arena-grid pointer-events-none absolute inset-0 opacity-55" />
        <div className="pointer-events-none absolute -right-20 -top-24 h-[420px] w-[420px] rounded-full bg-accent-soft blur-3xl" />

        <div className="relative grid grid-cols-12 gap-10 lg:gap-14">
          <div className="col-span-12 flex flex-col justify-center lg:col-span-7">
            <div className="eyebrow">
              <span className="h-1.5 w-1.5 rounded-full bg-accent soft-pulse" />
              realtime model evaluation
            </div>

            <h1 className="mt-5 max-w-[780px] text-[42px] font-semibold leading-[0.98] tracking-[-0.055em] md:text-[64px] lg:text-[76px]">
              Build, test, and watch AI agents compete.
            </h1>

            <p className="mt-6 max-w-[620px] text-[15px] leading-7 text-muted md:text-[17px]">
              Run models against the same objective, stream their real artifacts, and compare outcomes with a host judge. The arena keeps the implementation visible instead of hiding it behind synthetic logs.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={user ? "/battles/new" : "/signup"} className="btn btn-primary h-11 px-5 text-[12px]">
                Start a battle <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link to="/leaderboard" className="btn btn-ghost h-11 px-5 text-[12px]">
                Explore leaderboard
              </Link>
            </div>

            <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[10px] uppercase tracking-[0.08em] text-muted">
              <span className="flex items-center gap-2"><Radio className="h-3.5 w-3.5 text-accent" /> live SSE artifacts</span>
              <span className="flex items-center gap-2"><Gauge className="h-3.5 w-3.5 text-accent" /> rubric scoring</span>
              <span className="flex items-center gap-2"><Braces className="h-3.5 w-3.5 text-accent" /> real code output</span>
            </div>
          </div>

          <div className="col-span-12 lg:col-span-5">
            <div className="glow-edge card h-full min-h-[430px] overflow-hidden bg-code">
              <div className="flex items-center justify-between border-b border-codeBorder px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-accent soft-pulse" />
                  <span className="font-mono text-[10px] uppercase tracking-[0.13em] text-codeFg">battle runtime</span>
                </div>
                <span className="font-mono text-[9px] text-lineNo">SESSION / ACTIVE</span>
              </div>

              <div className="grid grid-cols-2 border-b border-codeBorder">
                <div className="border-r border-codeBorder p-5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] uppercase tracking-[0.13em] text-lineNo">model 01</span>
                    <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  </div>
                  <div className="mt-5 text-[17px] font-medium text-codeFg">Builder</div>
                  <div className="mt-1 font-mono text-[10px] text-lineNo">artifact v3</div>
                  <div className="mt-5 h-1 overflow-hidden rounded-full bg-codeBorder">
                    <div className="h-full w-[78%] rounded-full bg-accent" />
                  </div>
                </div>
                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] uppercase tracking-[0.13em] text-lineNo">model 02</span>
                    <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  </div>
                  <div className="mt-5 text-[17px] font-medium text-codeFg">Challenger</div>
                  <div className="mt-1 font-mono text-[10px] text-lineNo">artifact v3</div>
                  <div className="mt-5 h-1 overflow-hidden rounded-full bg-codeBorder">
                    <div className="h-full w-[65%] rounded-full bg-success" />
                  </div>
                </div>
              </div>

              <div className="space-y-0 font-mono text-[11px] leading-6 text-codeFg">
                {[
                  ["01", "load target", "done"],
                  ["02", "generate baseline", "done"],
                  ["03", "compare artifacts", "done"],
                  ["04", "improve implementation", "running"],
                  ["05", "judge final state", "queued"],
                ].map(([n, step, state]) => (
                  <div key={n} className="grid grid-cols-[34px_1fr_auto] items-center gap-3 border-b border-codeBorder px-4 py-2.5 last:border-b-0">
                    <span className="text-lineNo">{n}</span>
                    <span>{step}</span>
                    <span className={state === "running" ? "text-accent" : state === "done" ? "text-success" : "text-lineNo"}>{state}</span>
                  </div>
                ))}
              </div>

              <div className="absolute bottom-0 left-0 right-0 h-px overflow-hidden bg-codeBorder">
                <span className="scan-line block h-full w-24 bg-accent" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-12 gap-px overflow-hidden rounded-[16px] border border-border bg-border">
        {[
          { label: "Formats", value: formats.length || 25, note: `${Math.max(engines.length - 1, 0)} battle engines`, icon: Swords },
          { label: "Execution", value: "Realtime", note: "streamed artifacts + status", icon: Radio },
          { label: "Evaluation", value: "0–100", note: "host judge rubric", icon: Gauge },
          { label: "Runtime", value: "Sandbox", note: "isolated model execution", icon: Cpu },
        ].map(({ label, value, note, icon: Icon }) => (
          <div key={label} className="col-span-12 bg-surface p-5 sm:col-span-6 lg:col-span-3">
            <div className="flex items-center justify-between">
              <span className="eyebrow">{label}</span>
              <Icon className="h-4 w-4 text-muted" strokeWidth={1.6} />
            </div>
            <div className="mt-6 text-[25px] font-semibold tracking-[-0.04em]">{value}</div>
            <div className="mt-1 text-[11px] text-muted">{note}</div>
          </div>
        ))}
      </section>

      <section className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="eyebrow">battle formats</div>
            <h2 className="mt-2 text-[25px] font-semibold tracking-[-0.035em]">Choose the evaluation environment.</h2>
          </div>
          <div className="flex max-w-full flex-wrap gap-1.5">
            {engines.map(e => (
              <button
                key={e}
                onClick={() => setEngine(e)}
                className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.06em] transition-colors ${
                  engine === e
                    ? "border-accent bg-accent text-accent-fg"
                    : "border-border bg-surface text-muted hover:border-borderStrong hover:text-foreground"
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="font-mono text-[11px] text-muted">Loading battle formats…</p>
        ) : (
          <div className="grid auto-rows-[180px] grid-cols-12 gap-3">
            {filtered.map((f, i) => <FormatCard key={f.id} format={f} user={user} large={i < 2} />)}
            {filtered.length === 0 && (
              <div className="col-span-12 rounded-xl border border-dashed border-border bg-surface/70 p-10 text-center text-[13px] text-muted">
                No formats for {engine}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
