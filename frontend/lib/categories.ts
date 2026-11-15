import type { Category, ProductSort } from "./types";
import { departmentHref, withParams } from "./url";

export const categoryHref = (slug: string) => departmentHref(slug);

export const topCategories = (categories: Category[]) =>
  categories.filter((category) => !category.parent_slug);

/** Categorías principales con piezas: las únicas que vale la pena enlazar. */
export const stockedCategories = (categories: Category[]) =>
  topCategories(categories).filter((category) => category.product_count > 0);

export const childCategories = (categories: Category[], parent: string) =>
  categories.filter((category) => category.parent_slug === parent);

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

/** «Todas las marcas» más una opción por marca; `?brand=` y el orden elegido se conservan. */
export function brandOptions(
  path: string,
  facets: { slug: string; name: string }[],
  current: string | undefined,
  sort: ProductSort | undefined,
): CatalogOption[] {
  return [
    {
      href: withParams(path, { sort }),
      label: "Todas las marcas",
      current: !current,
    },
    ...facets.map((facet) => ({
      href: withParams(path, { brand: facet.slug, sort }),
      label: facet.name,
      current: current === facet.slug,
    })),
  ];
}

/** «Todo [departamento]» más una opción por subcategoría; la subcategoría va en la ruta. */
export function subcategoryOptions(
  department: { slug: string; name: string },
  children: { slug: string; name: string }[],
  current: string | undefined,
  params: { brand?: string; sort?: ProductSort },
): CatalogOption[] {
  return [
    {
      href: withParams(departmentHref(department.slug), params),
      label: `Todo ${department.name}`,
      current: !current,
    },
    ...children.map((child) => ({
      href: withParams(departmentHref(department.slug, child.slug), params),
      label: child.name,
      current: current === child.slug,
    })),
  ];
}
