// Espejo de docs/admin-api-contract.md y, donde el contrato no fija la forma, de
// backend/app/schemas/admin.py.
// Nunca se agregan campos de precio, costo, stock ni código de barras.

export type Role = "superadmin" | "admin" | "editor";
export type Me = { id: string; email: string; role: Role };
export type Status = "draft" | "published" | "archived";

export type Dashboard = {
  products: { draft: number; published: number; archived: number; without_photo: number };
  brands: { draft: number; published: number };
  consult_clicks_30d: number;
  whatsapp_configured: boolean;
};

export type ProductMediaItem = {
  id: string;
  /** `null` en fotos anteriores a la biblioteca (datos demo). */
  media_asset_id: string | null;
  url: string;
  alt: string;
  is_primary: boolean;
  position: number;
};
export type Variant = { id: string; sku: string; size: string | null; color: string | null };

/** El listado devuelve la misma forma que el detalle. */
export type Product = {
  id: string;
  sku: string;
  name: string;
  slug: string;
  status: Status;
  is_featured: boolean;
  brand_id: string;
  category_id: string;
  brand: { id: string; name: string; slug: string; kind: "brand" | "classification"; status: Status };
  category: { id: string; name: string; slug: string };
  display_order: number;
  commercial_added_at: string | null;
  published_at: string | null;
  seo_title: string | null;
  seo_description: string | null;
  internal_notes: string | null;
  media: ProductMediaItem[];
  variants: Variant[];
  photo_refs: string[];
};

export type BulkAction = "publish" | "unpublish" | "archive" | "feature" | "unfeature";
export type ItemError = { code: string; message: string };
export type BulkResult = { id: string; ok: boolean; error: ItemError | null };

export type MediaAsset = {
  id: string;
  url: string;
  filename: string;
  alt: string;
  width: number;
  height: number;
  in_use: boolean;
  created_at: string;
};

/** Lo que devuelve bulk-match: sin marca ni foto. La búsqueda de producto sí las aporta. */
export type ProductRef = {
  id: string;
  name: string;
  sku: string;
  brand_name?: string | null;
  primary_image_url?: string | null;
};
export type MatchProposal = {
  media_asset_id: string;
  filename: string;
  product_id: string | null;
  match: "sku" | "photo_ref" | "none";
  candidates: ProductRef[];
};
export type AssignResult = { media_asset_id: string; ok: boolean; error: ItemError | null };

export type Brand = {
  id: string;
  name: string;
  slug: string;
  kind: "brand" | "classification";
  logo_asset_id: string | null;
  editorial_asset_id: string | null;
  logo_url: string | null;
  editorial_image_url: string | null;
  description: string | null;
  display_order: number;
  is_featured: boolean;
  status: Status;
  validation_status: "pending" | "approved";
  aliases: string[];
  product_count: number;
};

export type AdminCategory = {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  display_order: number;
  product_count: number;
};

export type AdminCollection = {
  id: string;
  title: string;
  slug: string;
  summary: string | null;
  cover_asset_id: string | null;
  cover_url: string | null;
  status: Status;
  display_order: number;
  product_ids: string[];
};

export type BlockText = { type: "text"; position: number; heading: string | null; body: string };
export type BlockImage = {
  type: "image";
  position: number;
  url: string;
  alt: string;
  layout: "full" | "left" | "right";
};
export type AdminBlock = BlockText | BlockImage;
export type AdminLookbook = AdminCollection & { blocks: AdminBlock[] };

export type AdminSettings = {
  whatsapp_number: string | null;
  hero_asset_id: string | null;
  hero_mobile_asset_id: string | null;
  hero_image_url: string | null;
  hero_mobile_image_url: string | null;
  hero_headline: string | null;
  hero_subhead: string | null;
  intro: string | null;
  boutique_body: string | null;
  contact_body: string | null;
};

export type ImportPreview = {
  preview_id: string;
  rows: number;
  products: number;
  variants: number;
  new_products: number;
  conflicts: number;
  new_categories: string[];
  errors: { row: number; sku: string | null; message: string }[];
  sample: { sku: string; name: string; brand: string; category: string; variants: number }[];
};
export type ImportResult = {
  import_id: string;
  created: number;
  updated: number;
  skipped: number;
  errors: number;
};

export type AuditEntry = {
  id: string;
  created_at: string;
  user_email: string | null;
  operation: string;
  entity: string;
  entity_id: string | null;
  changes: Record<string, unknown>;
};
