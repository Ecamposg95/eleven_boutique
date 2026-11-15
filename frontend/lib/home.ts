import { safeImageSrc } from "./images";
import type {
  BrandSummary,
  CollectionSummary,
  LookbookSummary,
  ProductCard,
  PublicSettings,
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

/** Una foto de portada lista para pintar: `mobile` solo si es distinta de la principal. */
export type HeroPhoto = { src: string; mobile: string | null };

/**
 * Las fotos que se turnan en portada, en orden y sin repetir. Usa `hero.slides` (con versión de
 * teléfono) y, si la API es anterior, cae a la principal más la galería.
 */
export function heroPhotos(hero: PublicSettings["hero"]): HeroPhoto[] {
  const raw = hero.slides?.length
    ? hero.slides.map((slide) => ({ src: slide.image_url, mobile: slide.mobile_image_url }))
    : [hero.image_url, ...(hero.gallery ?? [])].map((src) => ({ src, mobile: null }));
  const seen = new Set<string>();
  const photos: HeroPhoto[] = [];
  for (const item of raw) {
    const src = safeImageSrc(item.src);
    if (!src || seen.has(src)) continue;
    seen.add(src);
    const mobile = safeImageSrc(item.mobile);
    photos.push({ src, mobile: mobile && mobile !== src ? mobile : null });
  }
  return photos;
}
