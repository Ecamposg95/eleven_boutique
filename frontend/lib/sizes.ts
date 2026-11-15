import type { ProductVariant } from "./types";

// Secuencia común de tallas de ropa; S=Ch y L=G comparten rango.
const LETTER_RANK: Record<string, number> = {
  xxs: 0, xs: 1, ch: 2, s: 2, m: 3, g: 4, l: 4, xl: 5, xxl: 6, xxxl: 7,
};

function rank(size: string): [number, number] {
  const key = size.trim().toLowerCase();
  if (key in LETTER_RANK) return [0, LETTER_RANK[key]!];
  const n = Number(key.replace(",", "."));
  if (key !== "" && Number.isFinite(n)) return [1, n];
  return [2, 0];
}

/** Ordena tallas: letras por secuencia común, numéricas ascendentes, desconocidas al final en su orden. */
export function sortSizes(sizes: string[]): string[] {
  return sizes
    .map((size, index) => ({ size, index, r: rank(size) }))
    .sort((a, b) => a.r[0] - b.r[0] || a.r[1] - b.r[1] || a.index - b.index)
    .map((entry) => entry.size);
}

/** Una talla por entrada; agotada solo si todas sus variantes (colores) lo están. */
export function sizesOf(variants: ProductVariant[]): { size: string; available: boolean }[] {
  const byLower = new Map<string, { size: string; available: boolean }>();
  for (const v of variants) {
    if (!v.size) continue;
    const key = v.size.trim().toLowerCase();
    const found = byLower.get(key);
    if (found) found.available = found.available || v.available;
    else byLower.set(key, { size: v.size, available: v.available });
  }
  const entries = [...byLower.values()];
  const order = sortSizes(entries.map((e) => e.size));
  return order.map((size) => entries.find((e) => e.size === size)!);
}
