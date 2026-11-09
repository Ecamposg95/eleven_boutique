/** Lista de hostnames desde env, sin espacios ni vacíos. */
export function parseImageHosts(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((host) => host.trim())
    .filter(Boolean);
}

/** `null` si next/image no puede renderizar el valor: rutas relativas o esquemas raros. */
export function safeImageSrc(src: string | null | undefined): string | null {
  if (!src) return null;
  if (src.startsWith("//")) return null;
  if (src.startsWith("/") || /^https?:\/\//i.test(src)) return src;
  return null;
}

/**
 * SVG y hosts fuera de la lista no pasan por el optimizador.
 * Así no hace falta dangerouslyAllowSVG y un host sin declarar no rompe la página.
 */
export function bypassOptimizer(src: string, allowedHosts: readonly string[]): boolean {
  const [path = ""] = src.split(/[?#]/);
  if (path.toLowerCase().endsWith(".svg")) return true;
  if (src.startsWith("/")) return false;
  try {
    const url = new URL(src);
    return url.protocol !== "https:" || !allowedHosts.includes(url.hostname);
  } catch {
    return true;
  }
}
