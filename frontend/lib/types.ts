// Espejo exacto de docs/api-contract.md.

export type Media = {
  url: string;
  alt: string;
  is_primary: boolean;
  position: number;
};

export type BrandSummary = {
  slug: string;
  name: string;
  logo_url: string | null;
  is_featured: boolean;
  aliases: string[];
  product_count: number;
};
export type BrandDetail = BrandSummary & {
  description: string | null;
  editorial_image_url: string | null;
};

/** `product_count`: piezas visibles; la principal suma las de sus hijas. */
export type Category = {
  slug: string;
  name: string;
  parent_slug: string | null;
  product_count: number;
};

export type ProductCard = {
  slug: string;
  name: string;
  brand: { slug: string | null; name: string | null }; // null si es "Sin marca"
  category: { slug: string; name: string };
  primary_image: Media | null;
  secondary_image: Media | null;
};
export type ProductDetail = ProductCard & {
  gallery: Media[];
  consult_url: string | null; // wa.me listo; null si no hay número configurado
  seo_title: string | null;
  seo_description: string | null;
  published_at: string | null;
};

export type CollectionSummary = {
  slug: string;
  title: string;
  summary: string | null;
  cover_url: string | null;
  product_count: number;
};
export type CollectionDetail = CollectionSummary & { products: ProductCard[] };

export type LookbookSummary = {
  slug: string;
  title: string;
  summary: string | null;
  cover_url: string | null;
};
export type LookbookBlock =
  | { type: "text"; position: number; heading: string | null; body: string }
  | {
      type: "image";
      position: number;
      url: string;
      alt: string;
      layout: "full" | "left" | "right";
    };
export type LookbookDetail = LookbookSummary & {
  blocks: LookbookBlock[];
  products: ProductCard[];
};

export type PublicSettings = {
  demo_mode: boolean;
  whatsapp_enabled: boolean; // nunca se expone el número por separado
  site_name: string;
  hero: {
    image_url: string | null;
    mobile_image_url?: string | null; // Dirección de arte para teléfono; si falta, se recorta image_url.
    headline: string | null;
    subhead: string | null;
    gallery?: string[]; // Fotos extra que se turnan después de image_url. Opcional: APIs anteriores no lo envían.
  };
  intro: string | null;
  boutique: { body: string | null };
  contact: { body: string | null };
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type ItemList<T> = { items: T[] };
export type SearchResults = { brands: BrandSummary[]; products: ProductCard[] };
export type ApiErrorBody = { error: { code: string; message: string } };
export type ConsultEvent = { type: "whatsapp_click"; product_slug: string };

export type ProductSort = "recent" | "name" | "display";
