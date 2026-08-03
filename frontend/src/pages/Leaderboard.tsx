import { useEffect, useState } from "react";
import { api, type FormatOut, type LeaderboardRow } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Leaderboard() {
  const { jwt } = useAuth();
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [formats, setFormats] = useState<FormatOut[]>([]);
  const [formatId, setFormatId] = useState("overall");
  const [err, setErr] = useState<string | null>(null);

  useEffect(()=>{ (async()=>{ try { const f = await api.formats(null); setFormats(f); } catch {} })(); }, []);

  useEffect(()=>{
    (async()=>{
      try { const data = await api.leaderboard(jwt, formatId || "overall"); setRows(Array.isArray(data) ? data : []); setErr(null); }
      catch(e){ setErr(e instanceof Error ? e.message : "Failed"); setRows([]); }
    })();
  }, [jwt, formatId]);

  return (
    <div className="space-y-6 max-w-[1000px] mx-auto">
      <div className="border-b-[1.5px] border-ink pb-4">
        <h1 className="display text-[32px]">LEADERBOARD // ELO</h1>
        <p className="mono text-[11px] text-zinc-500">Public • overall + per format • host free + BYOK</p>
      </div>
      <div className="flex gap-2">
        <select className="h-10 border-[1.5px] border-ink bg-paper px-3 text-[12px]" value={formatId} onChange={e=>setFormatId(e.target.value)}>
          <option value="overall">Overall</option>
          {formats.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
      </div>
      {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 mono text-[11px] text-vermillion">{err}</div>}
      <div className="border-[1.5px] border-ink bg-paper">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b-[1.5px] border-ink bg-ink text-paper mono text-[11px] uppercase">
              <tr><th className="px-4 py-2">#</th><th className="px-4 py-2">Model</th><th className="px-4 py-2">Format</th><th className="px-4 py-2">Elo</th><th className="px-4 py-2">Games</th></tr>
            </thead>
            <tbody className="mono text-[12px]">
              {rows.map((r,i)=>(
                <tr key={`${r.model_id}-${r.format_id}-${i}`} className="border-b border-ink/10 hover:bg-zinc-50">
                  <td className="px-4 py-2">{i+1}</td>
                  <td className="px-4 py-2 font-bold">{r.model_id}</td>
                  <td className="px-4 py-2 text-zinc-600">{r.format_id || "overall"}</td>
                  <td className="px-4 py-2 font-bold">{Math.round(r.elo)}</td>
                  <td className="px-4 py-2">{r.games_played}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={5} className="px-4 py-8 text-center text-zinc-500">No rankings yet — run a battle</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
