import type { BulkResult, MatchProposal, Role, Status } from "./types";

// Reglas del panel sin dependencias de React, para poder probarlas.

const RANK: Record<Role, number> = { editor: 1, admin: 2, superadmin: 3 };
export const hasRole = (role: Role, min: Role) => RANK[role] >= RANK[min];

export type NavItem = { href: string; label: string; min: Role };
export const ADMIN_NAV: readonly NavItem[] = [
  { href: "/admin", label: "Inicio", min: "editor" },
  { href: "/admin/productos", label: "Productos", min: "editor" },
  { href: "/admin/multimedia", label: "Multimedia", min: "editor" },
  { href: "/admin/marcas", label: "Marcas", min: "admin" },
  { href: "/admin/categorias", label: "Categorías", min: "editor" },
  { href: "/admin/colecciones", label: "Colecciones", min: "editor" },
  { href: "/admin/lookbooks", label: "Lookbooks", min: "editor" },
  { href: "/admin/importar", label: "Importar", min: "admin" },
  { href: "/admin/configuracion", label: "Configuración", min: "admin" },
  { href: "/admin/auditoria", label: "Auditoría", min: "admin" },
];
export const navFor = (role: Role) => ADMIN_NAV.filter((item) => hasRole(role, item.min));

export const STATUS_LABEL: Record<Status, string> = {
  draft: "Borrador",
  published: "Publicado",
  archived: "Archivado",
};

/** Lo que impide publicar, en las palabras de la regla del contrato. */
export function missingForPublish(product: {
  name: string;
  brand_id: string | null;
  category_id: string | null;
  media: readonly unknown[];
}): string[] {
  const missing: string[] = [];
  if (!product.name.trim()) missing.push("Falta el nombre");
  if (!product.brand_id) missing.push("Falta la marca o la clasificación «Sin marca»");
  if (!product.category_id) missing.push("Falta la categoría");
  if (product.media.length === 0) missing.push("Falta al menos una foto");
  return missing;
}

export type BulkRowInfo = { id: string; name: string; brandName: string | null };
export type BulkSummary = {
  ok: string[];
  failed: { id: string; name: string; message: string }[];
  /** Filas detenidas solo porque su marca no está publicada, por marca. */
  brandBlocked: { brand: string; ids: string[] }[];
};

export function summarizeBulk(
  results: readonly BulkResult[],
  lookup: (id: string) => BulkRowInfo | undefined,
): BulkSummary {
  const summary: BulkSummary = { ok: [], failed: [], brandBlocked: [] };
  const byBrand = new Map<string, string[]>();
  for (const result of results) {
    const row = lookup(result.id);
    if (result.ok) {
      summary.ok.push(result.id);
    } else if (result.error?.code === "brand_unpublished") {
      const brand = row?.brandName ?? "de este producto";
      byBrand.set(brand, [...(byBrand.get(brand) ?? []), result.id]);
    } else {
      summary.failed.push({
        id: result.id,
        name: row?.name ?? result.id,
        message: result.error?.message ?? "No se pudo aplicar.",
      });
    }
  }
  summary.brandBlocked = [...byBrand].map(([brand, ids]) => ({ brand, ids }));
  return summary;
}

/** Foto de los listados: la marcada como principal o, si no hay, la primera. */
export function primaryImageUrl(product: { media: readonly { url: string; is_primary: boolean }[] }): string | null {
  return (product.media.find((item) => item.is_primary) ?? product.media[0])?.url ?? null;
}

/**
 * Los 422 llegan como "body.slug: Value error, debe contener...; body.name: Field required".
 * Se separan por campo. Solo se conserva el texto propio del servidor: lo demás viene en inglés.
 */
export function parseValidationMessage(message: string): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const part of message.split("; ")) {
    const match = /^body\.([a-z_]+)(?:\.[^:]*)?: (.*)$/s.exec(part);
    if (!match) continue;
    const [, field = "", detail = ""] = match;
    const own = /^Value error, (.*)$/s.exec(detail)?.[1];
    fields[field] = own ? `${own[0]?.toUpperCase()}${own.slice(1)}.` : "Revise este campo.";
  }
  return fields;
}

export function chunk<T>(list: readonly T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size));
  return out;
}

// Decisiones de la asignación masiva.

export type Decision = {
  media_asset_id: string;
  filename: string;
  match: MatchProposal["match"];
  candidates: MatchProposal["candidates"];
  /** Producto propuesto o elegido. */
  product_id: string | null;
  /** `pending`: falta revisarla. `confirmed`: se asignará. `skipped`: se deja en la biblioteca. */
  state: "pending" | "confirmed" | "skipped";
};

export function toDecisions(proposals: readonly MatchProposal[]): Decision[] {
  return proposals.map((proposal) => ({
    media_asset_id: proposal.media_asset_id,
    filename: proposal.filename,
    match: proposal.match,
    candidates: proposal.candidates ?? [],
    product_id: proposal.product_id,
    state: "pending",
  }));
}

export function confirmAllProposed(decisions: readonly Decision[]): Decision[] {
  return decisions.map((decision) =>
    decision.state === "pending" && decision.product_id ? { ...decision, state: "confirmed" } : decision,
  );
}

/** Solo sale lo confirmado con producto: nada se asigna sin una decisión explícita. */
export function assignPayload(decisions: readonly Decision[]) {
  return decisions.flatMap((decision) =>
    decision.state === "confirmed" && decision.product_id
      ? [{ media_asset_id: decision.media_asset_id, product_id: decision.product_id }]
      : [],
  );
}

// La auditoría guarda claves internas en inglés. Una clave nueva se muestra tal cual, sin romper nada.

const AUDIT_OPERATIONS: Record<string, string> = {
  create: "Creó",
  update: "Editó",
  delete: "Eliminó",
  archive: "Archivó",
  upload: "Subió",
  login: "Inició sesión",
  logout: "Cerró sesión",
  publish: "Publicó",
  unpublish: "Despublicó",
  feature: "Destacó",
  unfeature: "Quitó destacado de",
  link_media: "Agregó foto a",
  unlink_media: "Quitó foto de",
  reorder_media: "Reordenó fotos de",
  import: "Importó",
};
const AUDIT_ENTITIES: Record<string, string> = {
  product: "producto",
  brand: "marca",
  category: "categoría",
  collection: "colección",
  lookbook: "lookbook",
  media_asset: "foto",
  site_settings: "configuración",
  admin_user: "usuario",
  import_run: "importación",
};

export function auditLabel(operation: string, entity: string): string {
  if (operation === "login" || operation === "logout") return AUDIT_OPERATIONS[operation] as string;
  return `${AUDIT_OPERATIONS[operation] ?? operation}: ${AUDIT_ENTITIES[entity] ?? entity}`;
}

/** Valor legible de un cambio. Los estados se traducen; lo demás se muestra como llegó. */
export function auditValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "vacío";
  if (value === true) return "sí";
  if (value === false) return "no";
  if (typeof value === "string" && value in STATUS_LABEL) return STATUS_LABEL[value as Status].toLowerCase();
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
