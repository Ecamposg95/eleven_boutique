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

const CLOUDINARY_UPLOAD = /^https:\/\/res\.cloudinary\.com\/[^/]+\/image\/upload\//;

/** Foto alojada en Cloudinary (las de Atlas ONE): Cloudinary la redimensiona, no el servidor de la tienda. */
export function isCloudinary(src: string): boolean {
  return CLOUDINARY_UPLOAD.test(src);
}

/**
 * Loader de next/image para Cloudinary: pide el ancho exacto que usa el navegador, en el formato
 * más ligero que acepte (AVIF/WebP) y con calidad automática. La original nunca viaja al visitante
 * y el servidor de la tienda no gasta CPU en optimizar.
 */
export function cloudinaryLoader({ src, width, quality }: { src: string; width: number; quality?: number }): string {
  const q = quality ? `q_${quality}` : "q_auto";
  return src.replace(/\/image\/upload\//, `/image/upload/f_auto,${q},c_limit,w_${width}/`);
}
