import { Link } from "react-router-dom";
import type { FormatOut } from "@/lib/api";

const ENGINE_COLORS: Record<string, string> = {
  build_and_break: "bg-amber-500 text-black",
  script_vs_defense: "bg-orange-500 text-black",
  same_target_race: "bg-emerald-500 text-black",
  direct_duel: "bg-violet-500 text-white",
  high_complexity: "bg-red-600 text-white",
  agent_vs_agent: "bg-cyan-400 text-black",
};

export default function FormatCard({ format, user, large }: { format: FormatOut; user: any; large?: boolean }) {
  const color = ENGINE_COLORS[format.engine] || "bg-zinc-900 text-white";
  const roles = Array.isArray(format.roles) ? format.roles.filter(r=>r!=="judge") : [];
  return (
    <div className={`${large ? "col-span-12 md:col-span-7" : "col-span-12 sm:col-span-6 lg:col-span-4"} group border-[1.5px] border-ink bg-paper p-5 flex flex-col justify-between hover:shadow-brutal transition-shadow`}>
      <div className="flex items-start justify-between">
        <div className={`h-8 w-8 grid place-items-center text-[11px] font-bold border-[1.5px] border-ink ${color}`}>{format.engine?.[0]?.toUpperCase() || "A"}</div>
        <div className="flex gap-1.5">
          <span className="border border-ink px-2 py-0.5 text-[10px] mono">{format.engine}</span>
        </div>
      </div>
      <div className="mt-4">
        <div className="display text-[22px] leading-none tracking-tight">{format.name}</div>
        <div className="mt-2 text-[12px] leading-5 text-zinc-600 line-clamp-2">{format.description || "Arena format — builder vs breaker, real code execution"}</div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {roles.slice(0,3).map(r=><span key={r} className="border border-ink/20 bg-zinc-100 px-2 py-0.5 text-[10px] mono">{r}</span>)}
        </div>
      </div>
      <Link to={user ? `/battles/new?format=${format.id}` : "/login"} className="mt-4 block w-full text-center border-[1.5px] border-ink py-2 text-[12px] font-bold hover:bg-ink hover:text-paper transition-colors">
        FIGHT →
      </Link>
    </div>
  );
}
