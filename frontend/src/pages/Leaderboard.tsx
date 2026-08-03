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
      <div>
        <h1 className="text-[22px] font-semibold tracking-[-0.01em]">Leaderboard</h1>
        <p className="mt-1 text-[13px] text-muted">Elo rankings across formats — host free + BYOK models.</p>
      </div>
      <div className="flex gap-2">
        <select className="select w-auto" value={formatId} onChange={e=>setFormatId(e.target.value)}>
          <option value="overall">Overall</option>
          {formats.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
      </div>
      {err && <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger">{err}</div>}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-border bg-soft text-[11px] font-semibold text-muted uppercase tracking-wide">
              <tr><th className="px-4 py-2.5">#</th><th className="px-4 py-2.5">Model</th><th className="px-4 py-2.5">Format</th><th className="px-4 py-2.5">Elo</th><th className="px-4 py-2.5">Games</th></tr>
            </thead>
            <tbody className="text-[13px]">
              {rows.map((r,i)=>(
                <tr key={`${r.model_id}-${r.format_id}-${i}`} className="border-b border-border last:border-b-0 hover:bg-soft/60">
                  <td className="px-4 py-2.5 font-mono text-[12px] text-muted">{i+1}</td>
                  <td className="px-4 py-2.5 font-semibold">{r.model_id}</td>
                  <td className="px-4 py-2.5 text-muted">{r.format_id || "overall"}</td>
                  <td className="px-4 py-2.5 font-semibold">{Math.round(r.elo)}</td>
                  <td className="px-4 py-2.5 text-muted">{r.games_played}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={5} className="px-4 py-10 text-center text-[13px] text-muted">No rankings yet — run a battle</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
