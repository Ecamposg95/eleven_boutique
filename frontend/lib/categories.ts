import type { Category, ProductCard, ProductSort } from "./types";
import { withParams } from "./url";

/** Ficha del carrusel de portada: una categoría con la foto de una de sus piezas. */
export type CategoryTile = {
  href: string;
  label: string;
  image: string | null;
  count: number;
};

export const categoryHref = (slug: string) =>
  `/categorias/${encodeURIComponent(slug)}`;

export const topCategories = (categories: Category[]) =>
  categories.filter((category) => !category.parent_slug);

/** Categorías principales con piezas: las únicas que vale la pena enlazar. */
export const stockedCategories = (categories: Category[]) =>
  topCategories(categories).filter((category) => category.product_count > 0);

export const childCategories = (categories: Category[], parent: string) =>
  categories.filter((category) => category.parent_slug === parent);

/**
 * Novedades primero y luego cada categoría principal con piezas, en el orden del catálogo.
 * Las categorías sin piezas se omiten: una ficha vacía no lleva a ningún lado.
 * Cada ficha usa la primera foto que no se haya usado ya, para que no se repitan.
 */
export function categoryTiles(
  newest: ProductCard[],
  samples: { category: Category; total: number; items: ProductCard[] }[],
): CategoryTile[] {
  const used = new Set<string>();
  const pick = (items: ProductCard[]) => {
    const urls = items
      .map((item) => item.primary_image?.url)
      .filter((url): url is string => Boolean(url));
    const url =
      urls.find((candidate) => !used.has(candidate)) ?? urls[0] ?? null;
    if (url) used.add(url);
    return url;
  };
  const tiles: CategoryTile[] = [];
  if (newest.length > 0) {
    tiles.push({
      href: "/novedades",
      label: "Novedades",
      image: pick(newest),
      count: newest.length,
    });
  }
  for (const { category, total, items } of samples) {
    if (total <= 0) continue;
    tiles.push({
      href: categoryHref(category.slug),
      label: category.name,
      image: pick(items),
      count: total,
    });
  }
  return tiles;
}

export type CatalogOption = { href: string; label: string; current: boolean };

const SORTS = [
  { value: undefined, label: "Selección" },
  { value: "recent", label: "Recientes" },
  { value: "name", label: "Nombre" },
] as const;

/** Opciones de orden de un listado, conservando el resto de parámetros (sin la página). */
export function sortOptions(
  path: string,
  params: Record<string, string | undefined>,
  sort: ProductSort | undefined,
): CatalogOption[] {
  return SORTS.map((item) => ({
    href: withParams(path, { ...params, sort: item.value }),
    label: item.label,
    current: sort === item.value,
  }));
}

/** «Todas» más una opción por categoría; el orden elegido se conserva. */
export function filterOptions(
  path: string,
  items: { slug: string; name: string }[],
  current: string | undefined,
  sort: ProductSort | undefined,
): CatalogOption[] {
  return [
    { href: withParams(path, { sort }), label: "Todas", current: !current },
    ...items.map((item) => ({
      href: withParams(path, { category: item.slug, sort }),
      label: item.name,
      current: current === item.slug,
    })),
  ];
}
