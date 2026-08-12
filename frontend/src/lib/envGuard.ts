const DEFAULT_MODAL_URL = "https://sixscripts--agent-arena-backend-fastapi-app.modal.run";

/**
 * Normalize VITE_MODAL_URL before the app uses it.
 *
 * Vercel users sometimes paste `VITE_MODAL_URL=https://...` into the VALUE
 * field instead of pasting only the URL. This helper tolerates that mistake
 * and rejects non-http(s) values so API requests do not silently become
 * malformed relative URLs.
 */
export function normalizedModalUrl(raw: unknown): string {
  const value = String(raw ?? "")
    .trim()
    .replace(/^VITE_MODAL_URL\s*=\s*/i, "")
    .replace(/^['"]|['"]$/g, "")
    .replace(/\/+$/, "");

  if (/^https?:\/\//i.test(value)) return value;
  return DEFAULT_MODAL_URL;
}

export const MODAL_URL = normalizedModalUrl(import.meta.env.VITE_MODAL_URL);
