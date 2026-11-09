import type { BrandSummary } from "./types";

/** Cuánto permanece cada casa en la portada antes de pasar a la siguiente. */
export const HOUSE_MS = 5000;

/**
 * Las casas estrella son las destacadas, en el orden que fija el panel. El resto son todas las
 * demás publicadas, para los créditos de "También en la boutique".
 */
export function splitShowroom(all: BrandSummary[], featured: BrandSummary[]) {
  const starSlugs = new Set(featured.map((brand) => brand.slug));
  return { stars: featured, rest: all.filter((brand) => !starSlugs.has(brand.slug)) };
}

export function nextHouse(index: number, total: number): number {
  return total > 0 ? (index + 1) % total : 0;
}
