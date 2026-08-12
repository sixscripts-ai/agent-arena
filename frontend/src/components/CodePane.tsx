import { useMemo, useState } from "react";
import { Braces, CheckCircle2, Clock3, Layers3, Radio } from "lucide-react";

export type PaneArtifact = {
  phase: string;
  artifact: string;
  t: number;
};

type Props = {
  modelId: string;
  label: string;
  code: string;
  status: string;
  tok?: string;
  color?: "accent" | "neutral" | "success" | "danger";
  artifactMeta: string;
  history?: PaneArtifact[];
  win?: boolean;
  winText?: string;
};

const DOT: Record<string, string> = {
  accent: "bg-accent",
  neutral: "bg-zinc-400",
  success: "bg-success",
  danger: "bg-danger",
};

export default function CodePane({
  modelId,
  label,
  code,
  status,
  tok,
  color = "neutral",
  artifactMeta,
  history = [],
  win,
  winText,
}: Props) {
  const [view, setView] = useState<"artifact" | "versions">("artifact");
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const dot = DOT[color] || DOT.neutral;

  const versions = useMemo<PaneArtifact[]>(() => {
    if (history.length) return history;
    if (!code) return [];
    return [{ phase: "current", artifact: code, t: 0 }];
  }, [history, code]);

  const activeIndex = selectedIndex !== null && versions[selectedIndex] ? selectedIndex : Math.max(versions.length - 1, 0);
  const selected = versions[activeIndex];
  const selectedCode = selected?.artifact || code || "";
  const lines = selectedCode.split("\n");
  const isLatest = !versions.length || activeIndex === versions.length - 1;

  const chooseVersion = (index: number) => {
    setSelectedIndex(index);
    setView("artifact");
  };

  const showLatest = () => setSelectedIndex(null);

  return (
    <div className="card flex h-[560px] min-h-0 flex-col overflow-hidden bg-surface">
      <header className="flex min-h-[64px] items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-borderStrong bg-surface2 font-mono text-[11px] font-semibold text-foreground">
            {modelId[0]?.toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="truncate text-[12px] font-semibold tracking-[-0.01em]">{label}</div>
            <div className="mt-0.5 truncate font-mono text-[9px] uppercase tracking-[0.08em] text-muted">
              {modelId}{tok ? ` / ${tok}` : ""}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden items-center gap-1.5 rounded-full border border-border bg-background/70 px-2 py-1 sm:flex">
            <span className={`h-1.5 w-1.5 rounded-full ${dot} ${status === "running" ? "soft-pulse" : ""}`} />
            <span className="font-mono text-[8px] uppercase tracking-[0.1em] text-muted">{status === "running" ? "live" : status}</span>
          </span>
        </div>
      </header>

      <div className="flex min-h-[42px] items-center justify-between border-b border-border bg-bg-soft/70 px-3">
        <div className="flex h-full items-center gap-1">
          <button
            onClick={() => setView("artifact")}
            className={`flex h-8 items-center gap-1.5 rounded-md px-2.5 font-mono text-[9px] uppercase tracking-[0.08em] transition-colors ${view === "artifact" ? "bg-surface2 text-foreground" : "text-muted hover:text-foreground"}`}
          >
            <Braces className="h-3.5 w-3.5" /> artifact
          </button>
          <button
            onClick={() => setView("versions")}
            className={`flex h-8 items-center gap-1.5 rounded-md px-2.5 font-mono text-[9px] uppercase tracking-[0.08em] transition-colors ${view === "versions" ? "bg-surface2 text-foreground" : "text-muted hover:text-foreground"}`}
          >
            <Layers3 className="h-3.5 w-3.5" /> versions {versions.length ? `(${versions.length})` : ""}
          </button>
        </div>

        {!isLatest && versions.length > 0 && (
          <button onClick={showLatest} className="font-mono text-[9px] uppercase tracking-[0.08em] text-accent hover:underline">
            latest
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 bg-code">
        {view === "artifact" ? (
          <div className="flex h-full min-h-0">
            <div className="w-12 shrink-0 select-none border-r border-codeBorder bg-code py-3 pr-3 text-right">
              {lines.map((_, i) => (
                <div key={i} className="font-mono text-[10px] leading-5 text-lineNo">{i + 1}</div>
              ))}
            </div>
            <pre className="h-full min-w-0 flex-1 overflow-auto p-3 font-mono text-[11px] leading-5 text-codeFg whitespace-pre-wrap break-words">
              <code>{selectedCode || "// Waiting for the first artifact…"}</code>
            </pre>
          </div>
        ) : (
          <div className="h-full overflow-auto p-3">
            {versions.length ? (
              <div className="space-y-2">
                {[...versions].reverse().map((item, reverseIndex) => {
                  const index = versions.length - 1 - reverseIndex;
                  const latest = index === versions.length - 1;
                  return (
                    <button
                      key={`${item.t}-${index}`}
                      onClick={() => chooseVersion(index)}
                      className="group flex w-full items-start gap-3 rounded-lg border border-codeBorder bg-[#0c0f11] p-3 text-left transition-colors hover:border-borderStrong hover:bg-[#101417]"
                    >
                      <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${latest ? "bg-accent" : "bg-lineNo"}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-codeFg">v{index + 1} / {item.phase || "artifact"}</span>
                          <span className="flex items-center gap-1 font-mono text-[9px] text-lineNo">
                            <Clock3 className="h-3 w-3" />
                            {item.t ? new Date(item.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "current"}
                          </span>
                        </div>
                        <p className="mt-2 line-clamp-2 font-mono text-[10px] leading-5 text-lineNo">
                          {item.artifact.replace(/\s+/g, " ").slice(0, 180) || "empty artifact"}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="grid h-full place-items-center">
                <div className="text-center">
                  <Layers3 className="mx-auto h-5 w-5 text-lineNo" />
                  <div className="mt-2 font-mono text-[10px] text-lineNo">No artifact versions yet.</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <footer className="flex min-h-[44px] items-center justify-between gap-3 border-t border-border bg-surface px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <span className="truncate font-mono text-[9px] text-muted">{artifactMeta}</span>
          {versions.length > 0 && (
            <span className="hidden items-center gap-1 font-mono text-[9px] text-muted sm:flex">
              <Layers3 className="h-3 w-3" /> v{activeIndex + 1}/{versions.length}
            </span>
          )}
        </div>
        <span className={`flex shrink-0 items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.06em] ${win ? "text-warn" : status === "running" ? "text-accent" : "text-muted"}`}>
          {win ? <CheckCircle2 className="h-3.5 w-3.5" /> : status === "running" ? <Radio className="h-3.5 w-3.5" /> : null}
          {win ? winText || "win condition" : status === "running" ? "receiving" : isLatest ? "latest artifact" : "historical artifact"}
        </span>
      </footer>
    </div>
  );
}
