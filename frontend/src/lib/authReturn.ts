export type AuthPage = "login" | "signup";

export function sanitizeInternalReturn(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  try {
    const parsed = new URL(value, "https://agent-arena.local");
    if (parsed.origin !== "https://agent-arena.local") return "/";
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "/";
  }
}

export function currentInternalReturn(location: Pick<Location, "pathname" | "search" | "hash">): string {
  return sanitizeInternalReturn(`${location.pathname}${location.search}${location.hash}`);
}

export function authRoute(page: AuthPage, next?: string | null): string {
  const target = sanitizeInternalReturn(next);
  return target === "/" ? `/${page}` : `/${page}?next=${encodeURIComponent(target)}`;
}
