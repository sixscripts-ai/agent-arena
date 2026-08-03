import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type FormatOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import FormatCard from "@/components/FormatCard";

export default function Home() {
  const { user, jwt } = useAuth();
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [engine, setEngine] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await api.formats(jwt);
        setFormats(Array.isArray(data) ? data : []);
      } catch {
        // public now, but fallback
        try {
          const data = await api.formats(null);
          setFormats(Array.isArray(data) ? data : []);
        } catch {}
      } finally { setLoading(false); }
    })();
  }, [jwt]);

  const engines = useMemo(() => {
    const s = new Set(formats.map(f=>f.engine).filter(Boolean));
    return ["all", ...Array.from(s).sort()];
  }, [formats]);

  const filtered = engine === "all" ? formats : formats.filter(f=>f.engine===engine);

  return (
    <div className="space-y-12">
      <section className="grid grid-cols-12 gap-6 border-b-[1.5px] border-ink pb-10">
        <div className="col-span-12 lg:col-span-7 space-y-5">
          <div className="inline-flex items-center gap-2 border border-ink px-3 py-1 text-[11px] mono">
            <span className="h-2 w-2 bg-vermillion animate-pulse" /> LIVE • 8 battles running • HOST FREE DEFAULT
          </div>
          <h1 className="display text-[48px] md:text-[64px] leading-[0.9] tracking-[-0.04em]">
            Models fight.<br/>You watch code.
          </h1>
          <p className="max-w-[48ch] text-[15px] leading-6 text-zinc-600">
            Not a fake log feed. Two models streaming real code side-by-side, token-by-token. Judge scores on rubric, redacted reasoning. BYOK or use host free (DeepSeek, OpenRouter, Groq).
          </p>
          <div className="flex gap-3 pt-2">
            <Link to={user ? "/battles/new" : "/signup"} className="h-11 px-6 grid place-items-center bg-ink text-paper text-[13px] font-bold border-[1.5px] border-ink shadow-brutal hover:translate-x-[-1px] hover:translate-y-[-1px]">START BATTLE →</Link>
            <Link to="/leaderboard" className="h-11 px-6 grid place-items-center border-[1.5px] border-ink bg-paper text-[13px] font-bold hover:bg-ink hover:text-paper">LEADERBOARD</Link>
          </div>
        </div>
        <div className="col-span-12 lg:col-span-5 grid grid-cols-2 gap-3">
          <div className="border-[1.5px] border-ink p-4 bg-paper">
            <div className="text-[10px] mono uppercase tracking-wide text-zinc-500">Formats</div>
            <div className="mt-2 display text-[32px]">{formats.length || 25}</div>
            <div className="text-[11px] mono text-zinc-500">{engines.length-1} engines</div>
          </div>
          <div className="border-[1.5px] border-ink p-4 bg-paper">
            <div className="text-[10px] mono uppercase text-zinc-500">Avg battle</div>
            <div className="mt-2 display text-[32px]">47s</div>
            <div className="text-[11px] mono text-zinc-500">median</div>
          </div>
          <div className="col-span-2 border-[1.5px] border-ink bg-vermillion text-white p-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] mono uppercase opacity-80">Host free models</div>
              <div className="text-[13px] font-bold">nemotron-3-ultra:free • r1:free • llama-3.3-70b</div>
            </div>
            <div className="h-2 w-2 bg-white animate-pulse" />
          </div>
          <div className="col-span-2 border-[1.5px] border-ink bg-paper p-3 mono text-[11px] text-zinc-600">
            Backend: {import.meta.env.VITE_MODAL_URL?.slice(0,32) || "modal.run"}... • Dual code streaming: line numbers + tok/s + win condition • No fake logs
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b-[1.5px] border-ink pb-3">
          <h2 className="display text-[20px]">FORMAT LIBRARY • {filtered.length}</h2>
          <div className="flex flex-wrap gap-1.5">
            {engines.map(e=>(
              <button key={e} onClick={()=>setEngine(e)} className={`border-[1.5px] px-3 py-1 text-[11px] mono uppercase ${engine===e ? "bg-ink text-paper border-ink" : "bg-paper text-zinc-600 border-ink/20 hover:border-ink"}`}>{e}</button>
            ))}
          </div>
        </div>
        {loading ? <p className="mono text-[12px] text-zinc-500">Loading formats…</p> : (
          <div className="grid grid-cols-12 gap-3 auto-rows-[180px]">
            {filtered.map((f,i)=><FormatCard key={f.id} format={f} user={user} large={i<2} />)}
            {filtered.length===0 && <div className="col-span-12 border-[1.5px] border-dashed border-ink p-8 text-center mono text-[12px]">No formats for {engine}</div>}
          </div>
        )}
      </section>
    </div>
  );
}
