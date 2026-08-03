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

export default function CodePane({ modelId, label, code, status, tok, color = "neutral", artifactMeta, win, winText }: Props) {
  const lines = code.split("\n");
  const dot = DOT[color] || DOT.neutral;

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
      <div className="flex flex-1 bg-code">
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
      </div>
      <footer className="flex items-center justify-between border-t border-border px-4 py-2 text-[10px]">
        <span className="font-mono text-muted">{artifactMeta}</span>
        <span className={win ? "font-medium text-warn" : "font-mono text-muted"}>
          {win ? winText || "WIN CONDITION MET" : code ? "redacted + truncated" : "idle"}
        </span>
      </footer>
    </div>
  );
}
