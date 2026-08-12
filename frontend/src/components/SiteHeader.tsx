import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useEffect, useState } from "react";
import { History, KeyRound, Menu, Plus, Swords, Trophy, X } from "lucide-react";

const LINKS = [
  { href: "/", label: "Arena", icon: Swords },
  { href: "/battles/new", label: "New battle", icon: Plus },
  { href: "/providers", label: "Keys", icon: KeyRound },
  { href: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { href: "/history", label: "History", icon: History },
];

export default function SiteHeader() {
  const { user, logout, init } = useAuth();
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const loc = useLocation();

  useEffect(() => { init(); }, [init]);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 md:px-8">
        <div className="flex min-w-0 items-center gap-7">
          <Link to="/" className="group flex shrink-0 items-center gap-2.5">
            <div className="relative grid h-8 w-8 place-items-center overflow-hidden rounded-[9px] border border-accent/40 bg-accent-soft text-accent shadow-[0_0_28px_var(--accent-soft)]">
              <Swords className="h-4 w-4" strokeWidth={1.9} />
              <span className="scan-line absolute inset-y-0 w-4 bg-gradient-to-r from-transparent via-white/25 to-transparent" />
            </div>
            <div className="leading-none">
              <div className="text-[13px] font-semibold tracking-[-0.02em]">Agent Arena</div>
              <div className="mt-1 font-mono text-[8px] uppercase tracking-[0.18em] text-muted">model runtime</div>
            </div>
          </Link>

          <div className="hidden h-5 w-px bg-border lg:block" />

          <nav className="hidden items-center gap-1 lg:flex">
            {LINKS.map(l => {
              const active = loc.pathname === l.href || (l.href !== "/" && loc.pathname.startsWith(l.href));
              const Icon = l.icon;
              return (
                <Link key={l.href} to={l.href} className={`navlink ${active ? "active" : ""}`}>
                  <Icon className="h-3.5 w-3.5" strokeWidth={1.8} />
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="hidden items-center gap-2 rounded-full border border-border bg-surface px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] text-muted md:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-success soft-pulse" />
            runtime online
          </span>

          {user ? (
            <>
              <span className="hidden max-w-[180px] truncate text-[11px] text-muted xl:block">{user.email || user.name || user.$id.slice(0, 8)}</span>
              <button
                onClick={async () => { await logout(); nav("/"); }}
                className="btn btn-ghost h-8 px-3 text-[11px]"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="navlink">Log in</Link>
              <Link to="/signup" className="btn btn-primary h-8 px-4 text-[11px]">Start building</Link>
            </>
          )}

          <button
            onClick={() => setOpen(!open)}
            aria-label={open ? "Close menu" : "Open menu"}
            className="grid h-8 w-8 place-items-center rounded-md border border-border bg-surface text-muted lg:hidden"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border bg-background/95 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="mx-auto max-w-[1440px] space-y-1">
            {LINKS.map(l => {
              const Icon = l.icon;
              return (
                <Link
                  key={l.href}
                  to={l.href}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-[12px] text-muted hover:bg-surface2 hover:text-foreground"
                >
                  <Icon className="h-4 w-4" strokeWidth={1.8} />
                  {l.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
