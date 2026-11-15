import type { ProductCard, ProductSort } from "./types";

export const PAGE_SIZE = 24;

type Params = Record<string, string | number | undefined>;

/** Arma un href omitiendo parámetros vacíos y la página 1. */
export function withParams(path: string, params: Params): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    if (key === "page" && Number(value) === 1) continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

export const SHOP_PATH = "/tienda";

export function productHref(product: Pick<ProductCard, "slug" | "brand">): string {
  const slug = encodeURIComponent(product.slug);
  return product.brand.slug
    ? `${SHOP_PATH}/marcas/${encodeURIComponent(product.brand.slug)}/${slug}`
    : `${SHOP_PATH}/piezas/${slug}`;
}

export function brandHref(slug: string): string {
  return `${SHOP_PATH}/marcas/${encodeURIComponent(slug)}`;
}

export function departmentHref(department: string, sub?: string): string {
  const base = `${SHOP_PATH}/${encodeURIComponent(department)}`;
  return sub ? `${base}/${encodeURIComponent(sub)}` : base;
}

type RawParam = string | string[] | undefined;

export function firstParam(value: RawParam): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/** Entero positivo; cualquier otra cosa es la página 1. */
export function parsePage(value: RawParam): number {
  const raw = firstParam(value);
  if (!raw || !/^\d{1,6}$/.test(raw)) return 1;
  return Math.max(1, Number(raw));
}

export function parseSort(value: RawParam): ProductSort | undefined {
  const raw = firstParam(value);
  return raw === "recent" || raw === "name" ? raw : undefined;
}

/** Los segmentos dinámicos pueden llegar codificados. */
export function decodeSlug(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
