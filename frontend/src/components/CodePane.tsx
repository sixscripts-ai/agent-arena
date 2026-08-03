type Props = {
  modelId: string;
  label: string;
  code: string;
  status: string;
  tok: string;
  color: "emerald" | "violet" | "vermillion" | "blueprint";
  artifactMeta: string;
  win?: boolean;
  winText?: string;
};

export default function CodePane({ modelId, label, code, status, tok, color, artifactMeta, win, winText }: Props) {
  const lines = code.split("\n");
  const dotColor = color === "emerald" ? "bg-emerald-500" : color === "violet" ? "bg-violet-500" : color === "vermillion" ? "bg-vermillion" : "bg-blueprint";
  const borderColor = color === "emerald" ? "border-emerald-500/30 text-emerald-700" : color === "violet" ? "border-violet-500/30 text-violet-700" : "border-ink/20";
  
  return (
    <div className="rounded-none border-[1.5px] border-ink bg-[#0A0A0A] overflow-hidden flex flex-col">
      <div className="flex items-center justify-between border-b border-white/10 bg-[#141414] px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-6 rounded-none bg-white/10 border border-white/10 grid place-items-center text-[11px] text-white">{modelId[0]?.toUpperCase()}</div>
          <div>
            <div className="text-[12px] font-medium text-white">{label}</div>
            <div className="text-[10px] mono text-zinc-500">{modelId} • {tok}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${dotColor} ${status==="running" ? "animate-pulse" : ""}`} />
          <span className="text-[10px] mono text-zinc-500 uppercase tracking-wide">{status==="running" ? "STREAMING" : status.toUpperCase()}</span>
        </div>
      </div>
      <div className="relative flex-1 flex">
        <div className="w-12 bg-[#0F0F0F] border-r border-white/10 py-3 text-right pr-3 select-none">
          {lines.slice(0,80).map((_,i)=><div key={i} className="mono text-[11px] leading-5 text-zinc-600">{i+1}</div>)}
        </div>
        <pre className="flex-1 max-h-[560px] overflow-auto p-3 mono text-[12px] leading-5 text-zinc-200 whitespace-pre-wrap break-all">
          <code>{code || "// waiting for model — real code streams here, not fake logs\n// dual pane, line numbers, win condition detection"}{status==="running" && <span className="inline-block w-2 h-3 bg-white animate-pulse ml-0.5 translate-y-0.5" />}</code>
        </pre>
      </div>
      <div className="border-t border-white/10 bg-[#111] px-3 py-2 flex items-center justify-between text-[10px] mono text-zinc-500">
        <span>{artifactMeta}</span>
        <span className={win ? "text-amber-300" : ""}>{win ? winText || "WIN CONDITION MET" : code ? "redacted + truncated (100kb cap)" : "idle"}</span>
      </div>
    </div>
  );
}
