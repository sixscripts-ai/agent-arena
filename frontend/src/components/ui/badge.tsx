import { cn } from "@/lib/utils";

export function Badge({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-xs font-medium text-zinc-300",
        className,
      )}
      {...props}
    />
  );
}
