const HOME = "/admin";
const LOGIN = "/admin/login";
const BASE = "http://panel.invalid";

/** Solo rutas internas de /admin. Cualquier otra cosa, incluidas las codificadas, vuelve al inicio. */
export function safeReturnPath(raw: string | null | undefined): string {
  if (!raw || raw.length > 2048 || !raw.startsWith("/admin")) return HOME;
  if (/[\\\u0000-\u001f\u007f]/.test(raw)) return HOME;
  let url: URL;
  let decoded: string;
  try {
    url = new URL(raw, BASE);
    decoded = decodeURIComponent(raw.split(/[?#]/)[0] ?? "");
  } catch {
    return HOME;
  }
  if (url.origin !== BASE) return HOME;
  if (decoded.includes("..") || decoded.includes("//") || decoded.includes("\\")) return HOME;
  const path = url.pathname;
  if (path !== HOME && !path.startsWith(`${HOME}/`)) return HOME;
  if (path === LOGIN || path.startsWith(`${LOGIN}/`)) return HOME;
  return `${path}${url.search}`;
}

export function loginHref(returnPath?: string | null, expired = false): string {
  const params = new URLSearchParams();
  const safe = safeReturnPath(returnPath);
  if (safe !== HOME) params.set("next", safe);
  if (expired) params.set("expirada", "1");
  const qs = params.toString();
  return qs ? `${LOGIN}?${qs}` : LOGIN;
}
