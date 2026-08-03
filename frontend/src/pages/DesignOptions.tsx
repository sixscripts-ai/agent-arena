import { useState } from "react";
import { Link } from "react-router-dom";

type Theme = "terminal" | "swiss" | "paper" | "void";

const THEMES: Record<Theme, {
  name: string;
  vibe: string;
  colors: { bg: string; fg: string; accent: string; accent2: string; border: string };
  fonts: { display: string; body: string; mono: string };
  refs: { label: string; url: string }[];
  desc: string;
}> = {
  terminal: {
    name: "TERMINAL // CRT",
    vibe: "Hacker lab, green phosphor, 1980s security research terminal, noisy and alive",
    colors: { bg: "#080A0A", fg: "#E0E0D0", accent: "#00FF88", accent2: "#FFB800", border: "#1A2A1A" },
    fonts: { display: "Geist Mono", body: "Geist Mono", mono: "Geist Mono" },
    refs: [
      { label: "Linear App — dark data dense", url: "https://linear.app" },
      { label: "Vercel Dashboard — terminal minimal", url: "https://vercel.com/dashboards" },
      { label: "Puter.com — retro terminal OS", url: "https://puter.com" },
    ],
    desc: "All mono, high contrast, scanlines, blinking cursors. Code panes are real terminals with green glow. Live = real. No rounded corners anywhere. Feels like you're SSH'd into the arena."
  },
  swiss: {
    name: "SWISS GRID",
    vibe: "International Typographic Style, Helvetica, red/black, asymmetric grid, like a research poster",
    colors: { bg: "#FFFFFF", fg: "#000000", accent: "#FF0000", accent2: "#0000FF", border: "#000000" },
    fonts: { display: "Helvetica Now, Inter", body: "Inter", mono: "JetBrains Mono" },
    refs: [
      { label: "Swiss Design — grid systems", url: "https://www.brutalistwebsites.com/" },
      { label: "Stripe Docs — swiss + code", url: "https://stripe.com/docs" },
      { label: "Figma — tool UI done right", url: "https://www.figma.com" },
    ],
    desc: "12-col grid visible, thick black rules, red dots for live, blue for info. Huge Helvetica 64px headlines, 11px labels. Cards are just black borders, no shadow. Feels like a lab manual printed in 1972."
  },
  paper: {
    name: "PAPER LAB NOTEBOOK",
    vibe: "Off-white lab book, hand-stamped, ink bleed, like a security researcher notebook scanned",
    colors: { bg: "#FDFCF8", fg: "#1A1A18", accent: "#FF4D00", accent2: "#0A0A0A", border: "#1A1A18" },
    fonts: { display: "Newsreader, Instrument Serif", body: "Geist", mono: "Geist Mono" },
    refs: [
      { label: "Excalidraw — paper + hand drawn", url: "https://excalidraw.com" },
      { label: "Linear - light mode with grit", url: "https://linear.app/now" },
      { label: "Obsidian Publish — paper knowledge", url: "https://publish.obsidian.md" },
    ],
    desc: "Paper texture, ink stamps for status, hand-drawn underline for active battles. Code panes are off-black with paper gutters. Feels tactile, not digital. The current attempt tried this but went too beige and too many shadows — this version is sharper, 0px radius, 2px borders."
  },
  void: {
    name: "VOID // ARENA",
    vibe: "Fighting game / esports scoreboard, void black, neon score, minimal but violent, like Street Fighter VS",
    colors: { bg: "#000000", fg: "#FFFFFF", accent: "#FFFF00", accent2: "#FF00FF", border: "#2A2A2A" },
    fonts: { display: "Sora, Space Grotesk", body: "Inter", mono: "JetBrains Mono" },
    refs: [
      { label: "Kaggle Competitions — arena", url: "https://www.kaggle.com/competitions" },
      { label: "HuggingFace Spaces — model arena", url: "https://huggingface.co/spaces" },
      { label: "Vercel Arena — edgy dark", url: "https://vercel.com/templates" },
    ],
    desc: "Pure black void, neon yellow for live, magenta for breaker, score in 72px yellow. Code panes have no chrome, just glowing cursor. Judge is a big VS screen. Feels like watching two AIs box."
  },
};

function MiniHome({ theme }: { theme: Theme }) {
  const t = THEMES[theme];
  return (
    <div style={{ background: t.colors.bg, color: t.colors.fg, border: `1.5px solid ${t.colors.border}`, fontFamily: t.fonts.body }} className="p-4 h-[220px] overflow-hidden flex flex-col gap-3">
      <div className="flex justify-between text-[10px] uppercase tracking-widest opacity-60">
        <span style={{ fontFamily: t.fonts.mono }}>ARENA 001 // {theme}</span>
        <span style={{ background: t.colors.accent, color: t.colors.bg, padding: "2px 6px" }}>LIVE 8</span>
      </div>
      <div style={{ fontFamily: t.fonts.display, fontSize: 28, lineHeight: 0.9, letterSpacing: "-0.03em", fontWeight: 600 }}>
        Models<br/>fight.
      </div>
      <div className="grid grid-cols-3 gap-2 mt-auto">
        {[1,2,3].map(i=>(
          <div key={i} style={{ border: `1px solid ${t.colors.border}`, background: i===1 ? t.colors.fg : "transparent", color: i===1 ? t.colors.bg : t.colors.fg, padding: "8px", fontSize: 10 }}>
            <div style={{ fontFamily: t.fonts.mono, fontSize: 9, opacity: 0.6 }}>FORMAT {i}</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>WAF vs Bypasser</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniBattle({ theme }: { theme: Theme }) {
  const t = THEMES[theme];
  return (
    <div style={{ background: t.colors.bg, color: t.colors.fg, border: `1.5px solid ${t.colors.border}` }} className="p-3 h-[220px] flex flex-col gap-2">
      <div className="flex justify-between text-[9px] mono uppercase tracking-wide opacity-60">
        <span>build → break → judge</span>
        <span style={{ color: t.colors.accent }}>● LIVE STREAMING</span>
      </div>
      <div className="grid grid-cols-2 gap-2 flex-1 min-h-0">
        <div style={{ background: theme==="paper" ? "#0A0A0A" : "#111", color: "#EEE", border: `1px solid ${t.colors.border}`, fontFamily: t.fonts.mono, fontSize: 9, padding: 8 }} className="overflow-hidden">
          <div style={{ opacity: 0.5, marginBottom: 6 }}>builder • grok-3 • 42 tok/s</div>
          <div>def is_xss(p):<br/>&nbsp;&nbsp;return "&lt;script" in p.lower()</div>
          <div style={{ marginTop: 8, color: t.colors.accent }}>▌</div>
        </div>
        <div style={{ background: theme==="paper" ? "#0A0A0A" : "#111", color: "#EEE", border: `1px solid ${t.colors.border}`, fontFamily: t.fonts.mono, fontSize: 9, padding: 8 }} className="overflow-hidden">
          <div style={{ opacity: 0.5, marginBottom: 6 }}>breaker • deepseek • 38 tok/s</div>
          <div>&lt;Svg OnLoad=alert(1)&gt;<br/>// bypass via SVG</div>
          <div style={{ marginTop: 8, color: theme==="void" ? t.colors.accent2 : t.colors.accent }}>WIN: ESCAPE_OK</div>
        </div>
      </div>
      <div className="flex gap-2">
        <div style={{ border: `1px solid ${t.colors.border}`, padding: "4px 8px", fontSize: 10, flex: 1, textAlign: "center" }}>Builder 72</div>
        <div style={{ background: t.colors.fg, color: t.colors.bg, padding: "4px 8px", fontSize: 10, flex: 1, textAlign: "center", fontWeight: 700 }}>Breaker 89 WIN</div>
      </div>
    </div>
  );
}

export default function DesignOptions() {
  const [active, setActive] = useState<Theme>("terminal");

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#FAF6F0]">
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&family=Sora:wght@500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;1,6..72,400&display=swap');`}</style>
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur">
        <div className="mx-auto max-w-[1440px] px-6 h-[60px] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 bg-white text-black grid place-items-center font-bold text-[12px]">A</div>
            <span className="font-bold tracking-tight">AGENT ARENA</span>
            <span className="text-[10px] opacity-50 border border-white/20 px-2 py-0.5 ml-2">DESIGN OPTIONS // PICK ONE</span>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/design/battle" className="text-[11px] bg-white text-black border border-white px-3 py-1.5 hover:bg-black hover:text-white">BATTLE MOCKUP →</Link>
            <Link to="/" className="text-[11px] border border-white/20 px-3 py-1.5 hover:bg-white hover:text-black">← BACK TO ARENA</Link>
          </div>        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-6 py-8 space-y-10">
        <div className="space-y-3">
          <h1 className="text-[40px] leading-[0.9] tracking-[-0.04em] font-semibold">Pick a direction.<br/>Not the old shit.</h1>
          <p className="max-w-[60ch] text-[14px] leading-6 text-white/60">The last attempt was brutalist lab logbook but too soft, too much beige, too many shadows. Here are 4 completely different, production-grade directions — each avoids AI slop (no purple gradients, no glassmorphism, no 32px rounded everything). Click to preview live.</p>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {(Object.keys(THEMES) as Theme[]).map(key=>{
            const th = THEMES[key];
            const sel = active===key;
            return (
              <button key={key} onClick={()=>setActive(key)} className={`col-span-12 md:col-span-6 lg:col-span-3 text-left group border-[1.5px] p-0 overflow-hidden transition-all ${sel ? "border-white bg-white/[0.06] -translate-y-1 shadow-[8px_8px_0px_0px_white]" : "border-white/10 bg-white/[0.02] hover:border-white/30"}`}>
                <div className="p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="text-[13px] font-bold tracking-wide">{th.name}</div>
                      <div className="text-[11px] leading-4 opacity-60 max-w-[24ch]">{th.vibe}</div>
                    </div>
                    <div className={`h-5 w-5 rounded-full grid place-items-center text-[10px] border ${sel ? "bg-white text-black border-white" : "border-white/20"}`}>{sel ? "●" : ""}</div>
                  </div>
                  <div className="flex gap-1.5">
                    {Object.values(th.colors).slice(0,4).map((c,i)=><div key={i} style={{ background: c }} className="h-5 w-8 border border-white/10" />)}
                  </div>
                  <p className="text-[11px] leading-4 opacity-70 line-clamp-3">{th.desc}</p>
                  <div className="pt-2 border-t border-white/10 space-y-1">
                    {th.refs.map(r=>(
                      <a key={r.url} href={r.url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()} className="block text-[10px] underline decoration-white/20 hover:decoration-white underline-offset-2 opacity-60 hover:opacity-100 truncate">↗ {r.label}</a>
                    ))}
                  </div>
                </div>
                <div className="border-t border-white/10">
                  <MiniHome theme={key} />
                  <MiniBattle theme={key} />
                </div>
              </button>
            );
          })}
        </div>

        <div className="border-[1.5px] border-white bg-[#0F0F0F] p-6 grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-5 space-y-4">
            <div className="text-[11px] uppercase tracking-widest opacity-50">Active preview • {THEMES[active].name}</div>
            <h2 className="text-[28px] leading-none tracking-tight font-semibold" style={{ fontFamily: THEMES[active].fonts.display }}>{THEMES[active].name}</h2>
            <p className="text-[13px] leading-5 opacity-70" style={{ fontFamily: THEMES[active].fonts.body }}>{THEMES[active].desc}</p>
            <div className="space-y-2 pt-4 border-t border-white/10">
              <div className="text-[10px] uppercase opacity-40">Fonts</div>
              <div className="text-[12px] space-y-1">
                <div>Display: {THEMES[active].fonts.display}</div>
                <div>Body: {THEMES[active].fonts.body}</div>
                <div>Mono: {THEMES[active].fonts.mono}</div>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              {Object.entries(THEMES[active].colors).map(([k,v])=>(
                <div key={k} className="space-y-1">
                  <div style={{ background: v }} className="h-8 w-12 border border-white/10" />
                  <div className="text-[9px] uppercase opacity-50">{k}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="col-span-12 lg:col-span-7 space-y-3">
            <div className="rounded-none border border-white/10 overflow-hidden">
              <div className="bg-black/50 px-3 py-2 flex justify-between text-[10px] uppercase tracking-wide opacity-60">
                <span>Live battle — dual real code streaming (the CORE ask)</span>
                <span>● streaming</span>
              </div>
              <MiniBattle theme={active} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <MiniHome theme={active} />
              <div style={{ background: THEMES[active].colors.bg, color: THEMES[active].colors.fg, border: `1.5px solid ${THEMES[active].colors.border}` }} className="p-4 h-[220px] flex flex-col">
                <div className="text-[10px] uppercase opacity-50">Judge strip</div>
                <div className="mt-auto flex gap-2">
                  <div style={{ border: `1px solid ${THEMES[active].colors.border}`, padding: 12, flex: 1, textAlign: "center" }}>
                    <div className="text-[10px] opacity-50">BUILDER</div>
                    <div className="text-[20px] font-bold">72</div>
                  </div>
                  <div style={{ background: THEMES[active].colors.fg, color: THEMES[active].colors.bg, padding: 12, flex: 1, textAlign: "center" }}>
                    <div className="text-[10px] opacity-70">BREAKER</div>
                    <div className="text-[20px] font-bold">89 WIN +0.8 Elo</div>
                  </div>
                </div>
              </div>
            </div>
            <button onClick={()=>{
              // @ts-ignore
              window._chosenTheme = active;
              alert(`Chosen: ${THEMES[active].name}\n\nI will now rebuild the entire app in this style, wiping the old shitty design. Confirm to proceed?`);
            }} className="w-full h-11 bg-white text-black font-bold text-[13px] border border-white hover:bg-black hover:text-white">APPLY THIS DIRECTION → REBUILD ENTIRE APP</button>
            <p className="text-[10px] opacity-40">References above are real sites that nail this aesthetic (Linear, Vercel, Kaggle, etc). No AI slop: no purple gradients on white, no glassmorphism as default, no 32px+ rounded cards, no side-stripe borders.</p>
          </div>
        </div>

        <div className="border border-white/10 bg-white/[0.02] p-4 text-[11px] leading-5 opacity-60 space-y-2">
          <div className="font-bold uppercase">Why last design failed — honest audit</div>
          <ul className="list-disc pl-4 space-y-1">
            <li>Beige #FAF6F0 band is AI default of 2026 — warm-neutral reads as "cream/sand slop" regardless of name (per impeccable skill)</li>
            <li>Too many shadows: `box-shadow: 4px 4px 0px 0px #0A0A0A` on every card + border 1.5px = noisy, not brutalist</li>
            <li>Identical card grids: same-sized cards with icon+heading+text repeated 25x — AI tell</li>
            <li>No hierarchy: everything border-black, no asymmetry, no overlap, no diagonal flow</li>
            <li>Fix: pick ONE saturated color to carry 30-60% of surface (committed), not tinted neutrals + one accent ≤10% everywhere</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
