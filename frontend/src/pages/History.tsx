import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, type BattleOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { authRoute, currentInternalReturn } from "@/lib/authReturn";

export default function History() {
  const { user, jwt, refreshJwt } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [battles, setBattles] = useState<BattleOut[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(()=>{ if (!user) nav(authRoute("login", currentInternalReturn(loc)), { replace: true }); }, [user, nav, loc]);

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
      <div>
        <h1 className="text-[22px] font-semibold tracking-[-0.01em]">History</h1>
        <p className="mt-1 text-[13px] text-muted">Saved battles — plus runs from this device.</p>
      </div>
      {err && <div className="rounded-md border border-danger bg-danger/10 px-3 py-2 text-[12px] text-danger">{err}</div>}
      <div className="space-y-3">
        {battles.map(b=>{
          const id = (b as any).id || (b as any).$id || "";
          const statusColor = b.status === "completed" ? "text-success" : b.status === "failed" || b.status === "cancelled" ? "text-danger" : "text-warn";
          return (
            <div key={id} className="card p-4 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="font-mono text-[12px] font-semibold">{id}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-muted">
                  format: {b.format_id} • <span className={statusColor}>{b.status}</span> • {(b.model_ids||[]).join(", ")}
                </div>
              </div>
              <Link to={`/battles/${id}`} className="btn btn-ghost h-8 px-3 text-[12px] shrink-0">Open →</Link>
            </div>
          );
        })}
        {!battles.length && (
          <div className="card p-10 text-center">
            <p className="text-[13px] text-muted">No saved battles yet.</p>
            <Link to="/battles/new" className="btn btn-primary mt-4 h-10 px-5 text-[12px]">Create battle →</Link>
          </div>
        )}
      </div>
    </div>
  );
}
