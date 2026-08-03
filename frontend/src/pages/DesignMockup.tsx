import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

type AccentKey = "blue" | "green" | "red";
type DensityKey = "airy" | "hybrid" | "dense";
type ThemeKey = "light" | "dark" | "system";

const STORE_KEY = "dv2_lab";

const ACCENTS: Record<AccentKey, { name: string; hex: string; note: string }> = {
  blue: { name: "Vercel Blue", hex: "#0070F3", note: "Modern dev-tool default. Trust + calm." },
  green: { name: "Supabase Green", hex: "#3ECF8E", note: "Operational / healthy. Fresh, less common." },
  red: { name: "Modern Vermillion", hex: "#FF3D00", note: "Your current red, tuned and surgical." },
};

const DENSITY: Record<DensityKey, {
  label: string;
  blurb: string;
  page: string;
  header: string;
  toolbar: string;
  stack: string;
  grid: string;
  paneHeader: string;
  paneBody: string;
  judge: string;
  title: string;
  showLog: boolean;
}> = {
  airy: {
    label: "AIRY",
    blurb: "Vercel hero — big whitespace, panes are the star",
    page: "px-6 py-10 md:px-12 md:py-14",
    header: "pb-8 md:pb-10",
    toolbar: "px-6 py-5 md:px-8 md:py-6",
    stack: "gap-6 md:gap-8",
    grid: "gap-6 md:gap-8",
    paneHeader: "px-5 py-4 md:px-6 md:py-5",
    paneBody: "text-[13px] leading-6",
    judge: "px-6 py-5 md:px-8 md:py-6",
    title: "text-[18px] md:text-[22px] tracking-[-0.02em]",
    showLog: false,
  },
  hybrid: {
    label: "HYBRID",
    blurb: "Airy chrome, dense battle grid — recommended",
    page: "px-4 py-6 md:px-8 md:py-10",
    header: "pb-5 md:pb-7",
    toolbar: "px-5 py-4",
    stack: "gap-3 md:gap-4",
    grid: "gap-2 md:gap-3",
    paneHeader: "px-3 py-2.5",
    paneBody: "text-[11px] leading-[1.55]",
    judge: "px-5 py-4",
    title: "text-[15px] md:text-[16px] tracking-[-0.01em]",
    showLog: true,
  },
  dense: {
    label: "DENSE",
    blurb: "Linear/terminal — max info per pixel",
    page: "p-3 md:p-4",
    header: "pb-3",
    toolbar: "px-3 py-2",
    stack: "gap-2",
    grid: "gap-2",
    paneHeader: "px-3 py-2",
    paneBody: "text-[11px] leading-[1.5]",
    judge: "px-3 py-3",
    title: "text-[13px]",
    showLog: true,
  },
};

const BUILDER_CODE = `import os, subprocess, sys, tempfile

class Sandbox:
    """Runs untrusted code with caps on time and memory."""

    def __init__(self, max_time=2, max_bytes=4096):
        self.max_time = max_time
        self.max_bytes = max_bytes

    def run(self, code):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "user.py")
            with open(path, "w") as f:
                f.write(code)
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", path],
                    capture_output=True, text=True,
                    timeout=self.max_time, cwd=d,
                )
            except subprocess.TimeoutExpired:
                return "timeout"
            return (proc.stdout + proc.stderr)[: self.max_bytes]

if __name__ == "__main__":
    print("SANDBOX_READY")`;

const BREAKER_CODE = `import os

# escape attempt #3 — /proc traversal outside workdir
with open("/proc/self/status") as f:
    data = f.read()

for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        with open(f"/proc/{pid}/environ", "rb") as e:
            env = e.read()
        if b"TOP_SECRET" in env:
            print("ESCAPE_OK", env)
            break
    except OSError:
        pass`;

const LOG_ROWS = [
  { phase: "build", model: "system", msg: "phase_start:build", t: "00:00" },
  { phase: "build", model: "nemotron-3-ultra:free", msg: "sandbox.py written • SANDBOX_READY", t: "00:14" },
  { phase: "break", model: "deepseek-chat", msg: "attempt 2 denied — sandbox held", t: "00:27" },
  { phase: "break", model: "deepseek-chat", msg: "ESCAPE_OK marker detected", t: "00:41" },
];

const NAV = ["ARENA", "NEW BATTLE", "KEYS", "LEADERBOARD", "HISTORY"];

const CSS = `
.dv2{--radius:8px;--radius-lg:12px;--ok:#16A34A;--ok-strong:#22C55E;--warn:#D97706;--shadow:0 1px 2px rgba(0,0,0,.05);font-family:"Geist",system-ui,sans-serif;background:var(--bg);color:var(--fg);transition:background .2s ease,color .2s ease}
.dv2[data-theme="light"]{--bg:#FFFFFF;--bg-soft:#FAFAFA;--fg:#0A0A0A;--fg-muted:#71717A;--border:#E4E4E7;--border-strong:#D4D4D8;--surface:#FFFFFF;--surface-2:#F4F4F5;--code-bg:#0A0A0A;--code-fg:#E5E5E5;--code-border:#262626;--line-no:#6B7280}
.dv2[data-theme="dark"]{--bg:#0A0A0A;--bg-soft:#111111;--fg:#FAFAFA;--fg-muted:#8A8F98;--border:#1F1F22;--border-strong:#2A2A2E;--surface:#0D0D0F;--surface-2:#161619;--code-bg:#000000;--code-fg:#DADADA;--code-border:#1F1F22;--line-no:#52525B;--shadow:0 1px 2px rgba(0,0,0,.45)}
.dv2[data-accent="blue"]{--accent:#0070F3;--accent-hover:#0061CF;--accent-fg:#FFFFFF;--link:#0070F3;--accent-soft:rgba(0,112,243,.08)}
.dv2[data-accent="blue"][data-theme="dark"]{--accent:#3291FF;--accent-hover:#4DA1FF;--link:#3291FF;--accent-soft:rgba(50,145,255,.12)}
.dv2[data-accent="green"]{--accent:#3ECF8E;--accent-hover:#2EBB7E;--accent-fg:#04281A;--link:#0F9D6E;--accent-soft:rgba(62,207,142,.10)}
.dv2[data-accent="green"][data-theme="dark"]{--accent:#4ADFA5;--accent-hover:#63E8B6;--accent-fg:#03150C;--link:#4ADFA5;--accent-soft:rgba(74,223,165,.12)}
.dv2[data-accent="red"]{--accent:#FF3D00;--accent-hover:#E63500;--accent-fg:#FFFFFF;--link:#E63500;--accent-soft:rgba(255,61,0,.08)}
.dv2[data-accent="red"][data-theme="dark"]{--accent:#FF5A33;--accent-hover:#FF7350;--accent-fg:#FFFFFF;--link:#FF5A33;--accent-soft:rgba(255,90,51,.12)}
.dv2 .card{border:1px solid var(--border);background:var(--surface);border-radius:var(--radius-lg);box-shadow:var(--shadow)}
.dv2 .btn-primary{background:var(--accent);color:var(--accent-fg);border-radius:var(--radius);font-weight:600;transition:background .15s ease}
.dv2 .btn-primary:hover{background:var(--accent-hover)}
.dv2 .btn-ghost{border:1px solid var(--border);color:var(--fg);border-radius:var(--radius);font-weight:500;transition:background .15s ease,border-color .15s ease}
.dv2 .btn-ghost:hover{background:var(--surface-2);border-color:var(--border-strong)}
.dv2 .link{color:var(--link);text-decoration:underline;text-underline-offset:2px;text-decoration-color:color-mix(in srgb,var(--link) 40%,transparent)}
.dv2 .navlink{color:var(--fg-muted);border-radius:var(--radius);transition:color .15s ease,background .15s ease}
.dv2 .navlink:hover{color:var(--fg);background:var(--surface-2)}
.dv2 .navlink.active{color:var(--fg);background:var(--surface-2)}
.dv2 a:focus-visible,.dv2 button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.dv2 ::-webkit-scrollbar{width:10px;height:10px}
.dv2 ::-webkit-scrollbar-track{background:transparent;border:none}
.dv2 ::-webkit-scrollbar-thumb{background:#333;border:2px solid var(--code-bg);border-radius:8px}
.dv2 .cursor-blink{color:var(--accent)}`;

function Seg<T extends string>({ label, value, onChange, options }: {
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; chip?: string }[];
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</span>
      <div className="flex overflow-hidden rounded-md border border-white/10">
        {options.map(o => (
          <button key={o.value} onClick={() => onChange(o.value)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] transition-colors ${value === o.value ? "bg-white text-black" : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"}`}>
            {o.chip && <span className="h-2.5 w-2.5 rounded-full border border-black/20" style={{ background: o.chip }} />}
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function LineNum({ code, px }: { code: string; px: string }) {
  return (
    <div className={`select-none pr-4 text-right ${px}`} aria-hidden>
      {code.split("\n").map((_, i) => <div key={i} className="text-[var(--line-no)]">{i + 1}</div>)}
    </div>
  );
}

export default function DesignMockup() {
  const [accent, setAccent] = useState<AccentKey>("blue");
  const [density, setDensity] = useState<DensityKey>("hybrid");
  const [theme, setTheme] = useState<ThemeKey>("system");
  const [sysDark, setSysDark] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORE_KEY);
      if (saved) {
        const s = JSON.parse(saved) as { accent?: AccentKey; density?: DensityKey; theme?: ThemeKey };
        if (s.accent && ACCENTS[s.accent]) setAccent(s.accent);
        if (s.density && DENSITY[s.density]) setDensity(s.density);
        if (s.theme) setTheme(s.theme);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({ accent, density, theme })); } catch {}
  }, [accent, density, theme]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setSysDark(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const isDark = theme === "system" ? sysDark : theme === "dark";
  const d = DENSITY[density];
  const acc = ACCENTS[accent];

  return (
    <div className="fixed inset-0 z-[200] overflow-y-auto bg-zinc-950 text-zinc-200">
      <style>{CSS}</style>

      <div className="sticky top-0 z-20 border-b border-white/10 bg-zinc-950/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-white px-2 py-0.5 text-[11px] font-bold tracking-tight text-black">DESIGN LAB</span>
            <span className="hidden text-[11px] text-zinc-500 sm:block">battle mockup v2 • {acc.name} × {DENSITY[density].label} × {isDark ? "dark" : "light"}</span>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <Seg<AccentKey> label="Accent" value={accent} onChange={setAccent}
              options={Object.entries(ACCENTS).map(([k, v]) => ({ value: k as AccentKey, label: v.name, chip: v.hex }))} />
            <Seg<DensityKey> label="Density" value={density} onChange={setDensity}
              options={(["airy", "hybrid", "dense"] as DensityKey[]).map(k => ({ value: k, label: DENSITY[k].label }))} />
            <Seg<ThemeKey> label="Theme" value={theme} onChange={setTheme}
              options={(["light", "dark", "system"] as ThemeKey[]).map(k => ({ value: k, label: k.toUpperCase() }))} />
            <Link to="/design" className="rounded-md border border-white/10 px-2.5 py-1.5 text-[11px] text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200">EXIT LAB →</Link>
          </div>
        </div>
      </div>

      <div className={`dv2 ${d.page}`} data-theme={isDark ? "dark" : "light"} data-accent={accent}>
        <div className={`mx-auto max-w-[1400px] flex flex-col ${d.stack}`}>
          <header className={`flex items-center justify-between ${d.header}`}>
            <div className="flex items-center gap-5">
              <div className="flex items-center gap-2.5">
                <div className="grid h-7 w-7 place-items-center rounded-[8px] bg-[var(--accent)] text-[13px] font-bold text-[var(--accent-fg)]">A</div>
                <span className="text-[14px] font-semibold tracking-[-0.01em]">Agent Arena</span>
              </div>
              <nav className="hidden items-center gap-1 lg:flex">
                {NAV.map(n => (
                  <a key={n} href="#mock" onClick={e => e.preventDefault()}
                    className={`navlink px-2.5 py-1.5 text-[12px] font-medium ${n === "ARENA" ? "active" : ""}`}>{n}</a>
                ))}
              </nav>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 md:flex">
                <div className="h-6 w-6 rounded-full border border-[var(--border-strong)] bg-[var(--surface-2)]" />
                <span className="text-[12px] text-[var(--fg-muted)]">emily@arena.dev</span>
              </div>
              <button className="btn-primary h-8 px-3.5 text-[12px]">New Battle →</button>
            </div>
          </header>

          <div className={`card flex flex-wrap items-center gap-3 ${d.toolbar}`}>
            <div className="flex items-center gap-3">
              <span className={`font-semibold ${d.title}`}>Code Sandbox vs Escapee</span>
              <span className="hidden rounded-md border border-[var(--border)] px-1.5 py-0.5 text-[10px] text-[var(--fg-muted)] md:block">#{d === DENSITY.dense ? "4f2a91c" : "battle 4f2a91c"}</span>
              <span className="flex items-center gap-1.5 rounded-md bg-[var(--accent-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--accent)]">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" />LIVE
              </span>
            </div>
            <div className="ml-auto flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1 text-[11px] text-[var(--ok-strong)]">BUILD <span className="text-[10px]">✓</span></span>
                <span className={`h-px w-6 ${d === DENSITY.dense ? "bg-[var(--border-strong)]" : "bg-[var(--border-strong)]"}`} />
                <span className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--accent)]">BREAK <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" /></span>
                <span className={`h-px w-6 ${d === DENSITY.dense ? "bg-[var(--border)]" : "bg-[var(--border)]"}`} />
                <span className="text-[11px] text-[var(--fg-muted)]">JUDGE</span>
              </div>
              <span className="font-mono text-[11px] text-[var(--fg-muted)]">00:41 / 10:00</span>
              <span className="rounded-md border border-[var(--border)] px-1.5 py-0.5 text-[10px] text-[var(--fg-muted)]">isolated</span>
            </div>
          </div>

          <div className={`grid grid-cols-1 lg:grid-cols-2 ${d.grid}`}>
            <section className="card flex flex-col overflow-hidden">
              <header className={`flex items-center justify-between border-b border-[var(--border)] ${d.paneHeader}`}>
                <div className="flex items-center gap-2.5">
                  <div className="grid h-6 w-6 place-items-center rounded-md border border-[var(--border-strong)] bg-[var(--surface-2)] text-[11px] font-bold">B</div>
                  <div>
                    <div className="text-[12px] font-semibold leading-tight">Builder</div>
                    <div className="font-mono text-[10px] text-[var(--fg-muted)]">nemotron-3-ultra:free • host</div>
                  </div>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-[10px] text-[var(--fg-muted)]">42 tok/s</span>
                  <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" /><span className="text-[10px] font-medium text-[var(--fg-muted)]">STREAMING</span></span>
                </div>
              </header>
              <div className="flex-1 border-b border-[var(--border)] bg-[var(--code-bg)]">
                <div className="flex p-4">
                  <LineNum code={BUILDER_CODE} px="text-[var(--pane-t)]" />
                  <pre className={`flex-1 overflow-hidden whitespace-pre-wrap break-all ${d.paneBody} font-mono text-[var(--code-fg)]`}><code>{BUILDER_CODE}<span className="cursor-blink">▌</span></code></pre>
                </div>
              </div>
              <footer className="flex items-center justify-between px-4 py-2 text-[10px] text-[var(--fg-muted)]">
                <span className="font-mono">3.2 kb • Python</span>
                <span>waiting for break phase</span>
              </footer>
            </section>

            <section className="card flex flex-col overflow-hidden">
              <header className={`flex items-center justify-between border-b border-[var(--border)] ${d.paneHeader}`}>
                <div className="flex items-center gap-2.5">
                  <div className="grid h-6 w-6 place-items-center rounded-md border border-[var(--border-strong)] bg-[var(--surface-2)] text-[11px] font-bold">B</div>
                  <div>
                    <div className="text-[12px] font-semibold leading-tight">Breaker</div>
                    <div className="font-mono text-[10px] text-[var(--fg-muted)]">deepseek-chat • your key</div>
                  </div>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-[10px] text-[var(--fg-muted)]">38 tok/s</span>
                  <span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" /><span className="text-[10px] font-medium text-[var(--fg-muted)]">STREAMING</span></span>
                </div>
              </header>
              <div className="flex-1 border-b border-[var(--border)] bg-[var(--code-bg)]">
                <div className="flex p-4">
                  <LineNum code={BREAKER_CODE} px="text-[var(--pane-t)]" />
                  <pre className={`flex-1 overflow-hidden whitespace-pre-wrap break-all ${d.paneBody} font-mono text-[var(--code-fg)]`}><code>{BREAKER_CODE}<span className="cursor-blink">▌</span></code></pre>
                </div>
              </div>
              <footer className="flex items-center justify-between px-4 py-2 text-[10px]">
                <span className="font-mono text-[var(--fg-muted)]">1.9 kb • Python</span>
                <span className="flex items-center gap-1 font-medium text-[var(--warn)]">ESCAPE_OK <span className="text-[9px]">marker</span></span>
              </footer>
            </section>
          </div>

          <div className={`card flex flex-wrap items-center gap-3 ${d.judge}`}>
            <div className="grid h-8 w-8 place-items-center rounded-full border border-[var(--border-strong)] bg-[var(--surface-2)] text-[12px] font-bold">J</div>
            <div>
              <div className="text-[12px] font-semibold">Host Judge</div>
              <div className="font-mono text-[10px] text-[var(--fg-muted)]">kimi-k3 • reasoning redacted • clamped 0-100 • retry ×3</div>
            </div>
            <div className="ml-auto flex gap-2">
              <div className={`rounded-lg border px-3 py-2 text-center ${d === DENSITY.dense ? "min-w-[84px]" : "min-w-[110px]"}`}>
                <div className="font-mono text-[9px] uppercase tracking-wider text-[var(--fg-muted)]">M1 • nemotron</div>
                <div className={`mt-1 font-semibold ${d === DENSITY.dense ? "text-[15px]" : "text-[20px]"}`}>72</div>
                <div className="font-mono text-[10px] text-[var(--fg-muted)]">−8.1 Elo</div>
              </div>
              <div className={`rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-3 py-2 text-center ${d === DENSITY.dense ? "min-w-[84px]" : "min-w-[110px]"}`}>
                <div className="font-mono text-[9px] uppercase tracking-wider text-[var(--accent)]">M2 • deepseek</div>
                <div className={`mt-1 font-semibold text-[var(--accent)] ${d === DENSITY.dense ? "text-[15px]" : "text-[20px]"}`}>89</div>
                <div className="font-mono text-[10px] text-[var(--accent)]">+12.4 Elo</div>
              </div>
            </div>
          </div>

          {d.showLog && (
            <div className="card">
              <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--fg-muted)]">Event stream</span>
                <span className="font-mono text-[10px] text-[var(--fg-muted)]">{LOG_ROWS.length} events • uuid deduped</span>
              </div>
              <div className="font-mono text-[11px]">
                {LOG_ROWS.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 border-b border-[var(--border)] px-4 py-1.5 last:border-b-0">
                    <span className="text-[var(--fg-muted)]">{r.t}</span>
                    <span className={`rounded-sm px-1.5 py-0.5 text-[9px] uppercase ${r.phase === "build" ? "bg-[var(--surface-2)] text-[var(--fg-muted)]" : "bg-[var(--accent-soft)] text-[var(--accent)]"}`}>{r.phase}</span>
                    <span className="text-[var(--fg-muted)]">{r.model}</span>
                    <span className="truncate text-[var(--fg)]">{r.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <footer className="flex items-center justify-between px-1 pb-4 text-[10px] text-[var(--fg-muted)]">
            <span>neutral-tool verdict • no WIN badges • winner = accent + Elo delta</span>
            <a href="#mock" onClick={e => e.preventDefault()} className="link">rubric →</a>
          </footer>
        </div>
      </div>
    </div>
  );
}
