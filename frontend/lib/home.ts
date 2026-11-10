import type {
  BrandSummary,
  CollectionSummary,
  LookbookSummary,
  ProductCard,
} from "./types";

/** Una entrada de la franja negra de portada: imagen opcional, etiqueta, título y destino. */
export type StripEntry = {
  href: string;
  kicker: string;
  title: string;
  image: string | null;
  /** Sin imagen, la miniatura es tipográfica: este texto en grande. */
  mark: string;
};

/**
 * La franja editorial bajo la portada tiene hasta tres entradas. Primero los lookbooks, que son
 * las historias; si faltan, se completa con las secciones de la tienda que sí tienen contenido.
 */
export function stripEntries({
  lookbooks,
  novedades,
  brands,
  boutique,
}: {
  lookbooks: LookbookSummary[];
  novedades: ProductCard[];
  brands: BrandSummary[];
  boutique: boolean;
}): StripEntry[] {
  const entries: StripEntry[] = lookbooks.map((lookbook) => ({
    href: `/lookbooks/${encodeURIComponent(lookbook.slug)}`,
    kicker: "Lookbook",
    title: lookbook.title,
    image: lookbook.cover_url,
    mark: lookbook.title.charAt(0),
  }));
  if (novedades.length > 0) {
    entries.push({
      href: "/novedades",
      kicker: "Novedades",
      title: "Lo último en llegar",
      image: novedades[0]?.primary_image?.url ?? null,
      mark: "N",
    });
  }
  if (brands.length > 0) {
    entries.push({
      href: "/marcas",
      kicker: "Las casas",
      title: `${brands.length} casas, una boutique`,
      image: null,
      mark: String(brands.length),
    });
  }
  if (boutique) {
    entries.push({
      href: "/la-boutique",
      kicker: "La boutique",
      title: "Conoce la boutique",
      image: null,
      mark: "11",
    });
  }
  return entries.slice(0, 3);
}

/** La imagen del cierre: la primera que exista entre lookbooks, colecciones y la portada. */
export function closingImage(
  lookbooks: LookbookSummary[],
  collections: CollectionSummary[],
  hero: string | null,
): string | null {
  return (
    lookbooks[0]?.cover_url ??
    collections.find((c) => c.cover_url)?.cover_url ??
    hero
  );
}

/** La palabra gigante de portada: el primer término del nombre del sitio. */
export function giantWord(siteName: string): string {
  return siteName.trim().split(/\s+/)[0] || siteName;
}
