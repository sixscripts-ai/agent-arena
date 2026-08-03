import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/", label: "ARENA" },
  { href: "/battles/new", label: "NEW BATTLE" },
  { href: "/providers", label: "KEYS" },
  { href: "/leaderboard", label: "LEADERBOARD" },
  { href: "/history", label: "HISTORY" },
];

export default function SiteHeader() {
  const { user, logout, init } = useAuth();
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const loc = useLocation();

  useEffect(() => { init(); }, [init]);

  return (
    <header className="sticky top-0 z-50 border-b-[1.5px] border-ink bg-paper">
      <div className="mx-auto flex h-[60px] max-w-[1360px] items-center justify-between px-6">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="h-8 w-8 bg-ink text-paper grid place-items-center font-bold text-[13px]">A</div>
            <span className="text-[16px] font-bold tracking-[-0.02em]">AGENT ARENA</span>
            <span className="hidden md:inline ml-2 border border-ink px-2 py-0.5 text-[9px] tracking-widest">LAB LOG // 001</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {LINKS.map(l => {
              const active = loc.pathname === l.href || (l.href !== "/" && loc.pathname.startsWith(l.href));
              return (
                <Link key={l.href} to={l.href}
                  className={`px-3 py-1.5 text-[12px] tracking-wide border ${active ? "bg-ink text-paper border-ink" : "border-transparent text-zinc-600 hover:text-ink hover:border-ink"}`}>
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          {user ? (
            <>
              <span className="hidden sm:block text-[11px] mono text-zinc-500">{user.email || user.name || user.$id.slice(0,8)}</span>
              <button onClick={async()=>{ await logout(); nav("/"); }} className="h-8 px-3 border-[1.5px] border-ink bg-paper text-[11px] hover:bg-ink hover:text-paper">LOG OUT</button>
            </>
          ) : (
            <>
              <Link to="/login" className="h-8 px-3 grid place-items-center border-[1.5px] border-transparent text-[11px] hover:border-ink">LOG IN</Link>
              <Link to="/signup" className="h-8 px-4 grid place-items-center bg-ink text-paper text-[11px] font-bold hover:bg-zinc-800">SIGN UP</Link>
            </>
          )}
          <button onClick={()=>setOpen(!open)} className="md:hidden h-8 w-8 grid place-items-center border-[1.5px] border-ink">☰</button>
        </div>
      </div>
      {open && (
        <div className="md:hidden border-t-[1.5px] border-ink bg-paper px-6 py-4 space-y-2">
          {LINKS.map(l=>(
            <Link key={l.href} to={l.href} onClick={()=>setOpen(false)} className="block py-2 text-[13px] border-b border-ink/10">{l.label}</Link>
          ))}
        </div>
      )}
    </header>
  );
}
