import { safeImageSrc } from "./images";
import { departmentHref } from "./url";
import type {
  BrandSummary,
  Category,
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
      href: "/tienda?sort=recent",
      kicker: "Novedades",
      title: "Lo último en llegar",
      image: novedades[0]?.primary_image?.url ?? null,
      mark: "N",
    });
  }
  if (brands.length > 0) {
    entries.push({
      href: "/tienda/marcas",
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

export type DepartmentPanel = {
  slug: string;
  name: string;
  href: string;
  cover: string | null;
  products: ProductCard[];
  total: number;
};

/**
 * Un panel por departamento principal, en el orden del catálogo. Entra si tiene piezas o portada;
 * sin ninguna de las dos no hay nada que mostrar.
 */
export function departmentPanels(
  categories: Category[],
  samples: { category: Category; items: ProductCard[]; total: number }[],
): DepartmentPanel[] {
  const panels: DepartmentPanel[] = [];
  for (const category of categories) {
    if (category.parent_slug) continue;
    const sample = samples.find((s) => s.category.slug === category.slug);
    const products = sample?.items ?? [];
    const cover = safeImageSrc(category.cover_url);
    if (products.length === 0 && !cover) continue;
    panels.push({
      slug: category.slug,
      name: category.name,
      href: departmentHref(category.slug),
      cover,
      products,
      total: sample?.total ?? 0,
    });
  }
  return panels;
}

const WA_PREFIX = "https://wa.me/";
const IG_PATTERN = /^https:\/\/(www\.)?instagram\.com\//;

/**
 * Los enlaces del bloque de atención y del pie. Solo se aceptan `https://wa.me/` para WhatsApp e
 * `https://(www.)instagram.com/` para Instagram; cualquier otra cosa es `null`.
 */
export function attentionLinks(settings: PublicSettings): {
  whatsapp: string | null;
  boutique: string | null;
  instagram: string | null;
} {
  const wa = (url: string | null | undefined) => (url?.startsWith(WA_PREFIX) ? url : null);
  const ig = settings.instagram_url;
  return {
    whatsapp: wa(settings.attention?.whatsapp_url),
    boutique: wa(settings.attention?.boutique_whatsapp_url),
    instagram: ig && IG_PATTERN.test(ig) ? ig : null,
  };
}

/** Foto de franja (detalle o atención) lista para `HeroPicture`; `null` sin imagen válida. */
export function bandPhoto(image: string | null | undefined, mobile: string | null | undefined): HeroPhoto | null {
  const src = safeImageSrc(image);
  if (!src) return null;
  const tel = safeImageSrc(mobile);
  return { src, mobile: tel && tel !== src ? tel : null };
}
