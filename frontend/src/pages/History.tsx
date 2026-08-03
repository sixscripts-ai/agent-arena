import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type BattleOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function History() {
  const { user, jwt, refreshJwt } = useAuth();
  const nav = useNavigate();
  const [battles, setBattles] = useState<BattleOut[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(()=>{ if (!user) nav("/login"); }, [user, nav]);

  useEffect(()=>{
    if (!jwt) return;
    (async()=>{
      try {
        const token = (await refreshJwt()) || jwt;
        const listed = await api.listBattles(token, true);
        setBattles(Array.isArray(listed) ? listed : []);
      } catch {
        try {
          const ids = JSON.parse(localStorage.getItem("arena_battle_ids") || "[]") as string[];
          const token = (await refreshJwt()) || jwt;
          const results: BattleOut[] = [];
          for (const id of ids.slice(0,20)) {
            try { results.push(await api.getBattle(token, id)); } catch {}
          }
          setBattles(results.filter(b=>b.saved));
        } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); }
      }
    })();
  }, [jwt, refreshJwt]);

  return (
    <div className="max-w-[900px] mx-auto space-y-6">
      <div className="border-b-[1.5px] border-ink pb-4">
        <h1 className="display text-[32px]">HISTORY // SAVED BATTLES</h1>
        <p className="mono text-[11px] text-zinc-500">Lab logbook — saved runs + local device IDs</p>
      </div>
      {err && <div className="border border-vermillion bg-vermillion/10 px-3 py-2 mono text-[11px] text-vermillion">{err}</div>}
      <div className="space-y-3">
        {battles.map(b=>{
          const id = (b as any).id || (b as any).$id || "";
          return (
            <div key={id} className="border-[1.5px] border-ink bg-paper p-4 flex justify-between">
              <div>
                <div className="mono text-[12px] font-bold">{id}</div>
                <div className="mono text-[11px] text-zinc-600">format: {b.format_id} • status: {b.status} • models: {(b.model_ids||[]).join(", ")}</div>
              </div>
              <Link to={`/battles/${id}`} className="h-8 px-3 grid place-items-center border-[1.5px] border-ink bg-ink text-paper mono text-[11px] hover:bg-paper hover:text-ink">OPEN →</Link>
            </div>
          );
        })}
        {!battles.length && (
          <div className="border-[1.5px] border-dashed border-ink p-8 text-center">
            <p className="mono text-[12px]">No saved battles yet.</p>
            <Link to="/battles/new" className="mt-3 inline-block border-[1.5px] border-ink px-4 py-2 mono text-[11px] font-bold hover:bg-ink hover:text-paper">CREATE BATTLE →</Link>
          </div>
        )}
      </div>
    </div>
  );
}
