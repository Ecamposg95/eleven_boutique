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
  /** Foto que trae Atlas ONE: no se edita ni se borra desde el panel. */
  read_only?: boolean;
};
export type Variant = { id: string; sku: string; size: string | null; color: string | null; available?: boolean };

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
  /** La pieza viene de Atlas ONE: nombre, marca, categoría y estado son suyos. */
  from_atlas?: boolean;
  available?: boolean;
  /** Motivo por el que una pieza de Atlas está en borrador. */
  atlas_missing?: string | null;
  hidden_on_web?: boolean;
  gender?: string | null;
  model?: string | null;
  material?: string | null;
  admin_description?: string | null;
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
  is_premium: boolean;
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
  cover_asset_id: string | null;
  cover_url: string | null;
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
  whatsapp_premium_number: string | null;
  hero_asset_id: string | null;
  hero_mobile_asset_id: string | null;
  hero_image_url: string | null;
  hero_mobile_image_url: string | null;
  hero_gallery: { asset_id: string; url: string; mobile_asset_id?: string | null; mobile_url?: string | null }[];
  hero_headline: string | null;
  hero_subhead: string | null;
  intro: string | null;
  boutique_body: string | null;
  contact_body: string | null;
  instagram_url: string | null;
  detail_asset_id: string | null;
  detail_image_url: string | null;
  detail_mobile_asset_id: string | null;
  detail_mobile_image_url: string | null;
  detail_caption: string | null;
  attention_asset_id: string | null;
  attention_image_url: string | null;
  attention_mobile_asset_id: string | null;
  attention_mobile_image_url: string | null;
  attention_headline: string | null;
  attention_subhead: string | null;
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

export type AtlasRun = {
  kind: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  counts: Record<string, number>;
  /** Solo si la corrida falló. */
  error: string | null;
  /** Aviso de una corrida buena (p. ej. la baja nocturna se omitió); no es una falla. */
  note?: string | null;
};
export type AtlasDraft = { id: string; name: string; atlas_missing: string | null };
export type AtlasStatus = {
  enabled: boolean;
  last_run: AtlasRun | null;
  last_ok_at: string | null;
  last_error?: string | null;
  drafts: AtlasDraft[];
};
export type AtlasBrandMapRow = { atlas_brand_id: string; atlas_name: string; brand_id: string | null };
export type AtlasCategoryMapRow = { atlas_department_id: string; atlas_name: string; category_id: string | null };
