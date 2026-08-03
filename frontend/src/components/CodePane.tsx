import { useMemo, useState } from "react";

type Props = {
  modelId: string;
  label: string;
  code: string;
  status: string;
  tok?: string;
  color?: "accent" | "neutral" | "success" | "danger";
  artifactMeta: string;
  win?: boolean;
  winText?: string;
};

const DOT: Record<string, string> = {
  accent: "bg-accent",
  neutral: "bg-zinc-400",
  success: "bg-success",
  danger: "bg-danger",
};

type Parsed = {
  files?: Record<string, string>;
  chosen_skills?: string[];
  theory?: string;
  outcome?: string;
  steps?: number;
};

function tryParse(code: string): Parsed | null {
  try {
    const j = JSON.parse(code);
    if (j && typeof j === "object" && (j.files || j.chosen_skills || j.theory)) return j as Parsed;
    // also handle nested artifact that is files JSON string inside wrapped artifact
    if (typeof j === "string") {
      const inner = JSON.parse(j);
      if (inner && typeof inner === "object" && inner.files) return inner as Parsed;
    }
  } catch {}
  // try to find last JSON object in code (for joined artifacts)
  try {
    const matches = [...code.matchAll(/\{[\s\S]*?"files"\s*:\s*\{[\s\S]*?\}\s*[\s\S]*?\}/g)];
    if (matches.length) {
      const last = matches[matches.length - 1][0];
      const j = JSON.parse(last);
      if (j.files) return j as Parsed;
    }
  } catch {}
  return null;
}

export default function CodePane({ modelId, label, code, status, tok, color = "neutral", artifactMeta, win, winText }: Props) {
  const dot = DOT[color] || DOT.neutral;
  const parsed = useMemo(() => tryParse(code), [code]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const files = parsed?.files || null;
  const fileList = useMemo(() => (files ? Object.keys(files).sort() : []), [files]);
  const activeFile = selectedFile || (fileList[0] || null);
  const activeContent = activeFile && files ? files[activeFile] : null;
  const displayCode = activeContent || code;
  const lines = displayCode.split("\n");
  const isStructured = !!files;

  return (
    <div className="card flex flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <div className="grid h-6 w-6 place-items-center rounded-md border border-borderStrong bg-surface2 text-[11px] font-bold">
            {modelId[0]?.toUpperCase()}
          </div>
          <div>
            <div className="text-[12px] font-semibold leading-tight">{label}</div>
            <div className="font-mono text-[10px] text-muted">{modelId}{tok ? ` • ${tok}` : ""}</div>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          {tok && <span className="font-mono text-[10px] text-muted">{tok}</span>}
          <span className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${dot} ${status === "running" ? "animate-pulse" : ""}`} />
            <span className="text-[10px] font-medium text-muted">{status === "running" ? "STREAMING" : status.toUpperCase()}</span>
          </span>
        </div>
      </header>

      {/* Skill chips + theory for competitive draft */}
      {parsed && (parsed.chosen_skills?.length || parsed.theory) && (
        <div className="border-b border-border bg-surface2/40 px-3 py-2 space-y-2">
          {parsed.chosen_skills && parsed.chosen_skills.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-[9px] uppercase tracking-widest text-muted">Skills to beat opponent: </span>
              {parsed.chosen_skills.map((s) => (
                <span key={s} className="rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 font-mono text-[10px] text-accent">
                  {s}
                </span>
              ))}
              {parsed.outcome && (
                <span className={`ml-1 rounded-full px-2 py-0.5 text-[9px] font-bold ${parsed.outcome.includes("PASS") ? "bg-success text-white" : parsed.outcome.includes("FAIL") ? "bg-danger text-white" : "bg-surface2 text-muted"}`}>
                  {parsed.outcome}
                </span>
              )}
              {parsed.steps !== undefined && <span className="font-mono text-[10px] text-muted">• {parsed.steps} steps</span>}
            </div>
          )}
          {parsed.theory && (
            <div className="rounded-md border border-border bg-code px-2.5 py-1.5 font-mono text-[11px] leading-4 text-codeFg/80">
              <span className="text-[9px] uppercase tracking-widest text-muted">THEORY: </span>{parsed.theory.slice(0, 400)}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-1 bg-code min-h-[320px]">
        {/* File tree for structured artifacts */}
        {isStructured ? (
          <>
            <div className="w-[140px] shrink-0 border-r border-codeBorder bg-code/50 p-2">
              <div className="font-mono text-[9px] uppercase tracking-widest text-lineNo mb-1.5">work/</div>
              <div className="space-y-0.5">
                {fileList.map((f) => (
                  <button
                    key={f}
                    onClick={() => setSelectedFile(f)}
                    className={`block w-full truncate rounded px-1.5 py-0.5 text-left font-mono text-[11px] ${activeFile === f ? "bg-accent text-accent-fg" : "text-codeFg/70 hover:bg-white/[0.06] hover:text-codeFg"}`}
                  >
                    {f.endsWith("solution.py") ? "● " : f.endsWith("THEORY.md") ? "▲ " : f.endsWith(".py") ? "· " : "  "}
                    {f}
                  </button>
                ))}
              </div>
              <div className="mt-3 font-mono text-[9px] text-lineNo">{fileList.length} files • {artifactMeta}</div>
            </div>
            <div className="flex flex-1">
              <div className="w-12 shrink-0 select-none border-r border-codeBorder py-3 pr-3 text-right">
                {lines.slice(0, 120).map((_, i) => (
                  <div key={i} className="font-mono text-[11px] leading-5 text-lineNo">{i + 1}</div>
                ))}
              </div>
              <pre className="max-h-[560px] flex-1 overflow-auto p-3 font-mono text-[12px] leading-5 text-codeFg whitespace-pre-wrap break-all">
                <code>
                  {displayCode || "// waiting for real code — not fake logs\n// streams token-by-token via sandbox"}
                  {status === "running" && <span className="ml-0.5 inline-block h-3 w-2 translate-y-0.5 animate-pulse bg-white" />}
                </code>
              </pre>
            </div>
          </>
        ) : (
          <>
            <div className="w-12 shrink-0 select-none border-r border-codeBorder py-3 pr-3 text-right">
              {lines.slice(0, 80).map((_, i) => (
                <div key={i} className="font-mono text-[11px] leading-5 text-lineNo">{i + 1}</div>
              ))}
            </div>
            <pre className="max-h-[560px] flex-1 overflow-auto p-3 font-mono text-[12px] leading-5 text-codeFg whitespace-pre-wrap break-all">
              <code>
                {code || "// waiting for real code — not fake logs\n// streams token-by-token via sandbox"}
                {status === "running" && <span className="ml-0.5 inline-block h-3 w-2 translate-y-0.5 animate-pulse bg-white" />}
              </code>
            </pre>
          </>
        )}
      </div>

      <footer className="flex items-center justify-between border-t border-border px-4 py-2 text-[10px]">
        <span className="font-mono text-muted">{isStructured ? `${fileList.length} files • ${activeFile || "no file"} • ${lines.length} lines • ${artifactMeta}` : artifactMeta}</span>
        <span className={win ? "font-medium text-warn" : "font-mono text-muted"}>
          {win ? winText || "WIN CONDITION MET" : isStructured ? (parsed?.outcome || "structured") : code ? "redacted + truncated" : "idle"}
        </span>
      </footer>
    </div>
  );
}
