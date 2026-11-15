import { AdminApiError, api } from "./client";
import { plural } from "./format";
import type {
  AdminCategory,
  AtlasBrandMapRow,
  AtlasCategoryMapRow,
  AtlasStatus,
  Product,
} from "./types";

// Lógica de la pantalla Atlas ONE y de las piezas de solo lectura, sin React, para poder probarla.

export const SYNC_RUNNING_MESSAGE = "Ya hay una sincronización en curso.";

/** Conteos de una corrida en español. Los ceros no se dicen. */
export function describeCounts(counts: Record<string, number>): string[] {
  const n = (key: string) => counts[key] ?? 0;
  const out: string[] = [];
  if (n("creadas")) out.push(plural(n("creadas"), "creada", "creadas"));
  if (n("actualizadas")) out.push(plural(n("actualizadas"), "actualizada", "actualizadas"));
  if (n("bajas")) out.push(plural(n("bajas"), "archivada", "archivadas"));
  if (n("borradores")) out.push(plural(n("borradores"), "borrador", "borradores"));
  if (n("disponibilidad")) out.push(`${n("disponibilidad")} con disponibilidad actualizada`);
  if (n("eventos_enviados")) out.push(plural(n("eventos_enviados"), "evento enviado", "eventos enviados"));
  if (n("eventos_pendientes")) out.push(plural(n("eventos_pendientes"), "evento en espera", "eventos en espera"));
  if (n("archivado_omitido")) out.push("Archivado omitido");
  return out;
}

/** Pide la sincronización. Un 409 no es una excepción para la pantalla: es un mensaje. */
export async function startSync(post: () => Promise<unknown> = () => api("/atlas/sync", { method: "POST", json: {} })) {
  try {
    await post();
    return { started: true, message: null as string | null };
  } catch (cause) {
    if (cause instanceof AdminApiError && cause.status === 409) {
      const message = cause.code === "sync_running" && !cause.message ? SYNC_RUNNING_MESSAGE : cause.message;
      return { started: false, message };
    }
    return { started: false, message: cause instanceof Error ? cause.message : "Ocurrió un error inesperado." };
  }
}

/** La corrida pedida terminó: hay una corrida más nueva que la que se veía y ya cerró. */
export function runFinished(status: AtlasStatus, before: string | null): boolean {
  const run = status.last_run;
  return Boolean(run && run.started_at !== before && run.finished_at);
}

/** Consulta el estado cada `intervalMs` hasta que la corrida termine; `null` si se acaba el tiempo. */
export async function pollSync({
  fetchStatus,
  before,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  now = Date.now,
  intervalMs = 3000,
  maxMs = 120000,
  signal,
}: {
  fetchStatus: () => Promise<AtlasStatus>;
  before: string | null;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
  intervalMs?: number;
  maxMs?: number;
  /** Al abortar (p. ej. al salir de la pantalla) no se vuelve a consultar. */
  signal?: AbortSignal;
}): Promise<AtlasStatus | null> {
  const deadline = now() + maxMs;
  while (now() < deadline) {
    if (signal?.aborted) return null;
    const status = await fetchStatus();
    if (signal?.aborted) return null;
    if (runFinished(status, before)) return status;
    await sleep(intervalMs);
  }
  return null;
}

export const POLL_ERROR_MESSAGE = "No se pudo consultar el estado; la sincronización puede seguir en curso.";

/** Mapas: primero lo que falta ligar, luego por nombre de Atlas (es). */
export function unlinkedFirst<T extends { atlas_name: string }>(rows: readonly T[], linked: (row: T) => string | null): T[] {
  return [...rows].sort((a, b) => {
    const gap = Number(linked(a) !== null) - Number(linked(b) !== null);
    return gap || a.atlas_name.localeCompare(b.atlas_name, "es");
  });
}

const STATUS_BULK = new Set(["publish", "unpublish", "archive"]);

/** Publicar, despublicar y archivar los decide Atlas ONE: esas piezas no se mandan al servidor. */
export function splitAtlasBulk(
  action: string,
  ids: readonly string[],
  isAtlas: (id: string) => boolean,
): { send: string[]; skipped: number } {
  if (!STATUS_BULK.has(action)) return { send: [...ids], skipped: 0 };
  const send = ids.filter((id) => !isAtlas(id));
  return { send, skipped: ids.length - send.length };
}

export const atlasSkippedMessage = (count: number) =>
  count === 1 ? "1 pieza viene de Atlas ONE y no se cambió" : `${plural(count, "pieza", "piezas")} vienen de Atlas ONE y no se cambiaron`;
export const fetchAtlasStatus = () => api<AtlasStatus>("/atlas/status");

export const saveBrandMap = (atlas_brand_id: string, brand_id: string | null) =>
  api<AtlasBrandMapRow>("/atlas/brand-map", { method: "PATCH", json: { atlas_brand_id, brand_id } });

export const saveCategoryMap = (atlas_department_id: string, category_id: string | null) =>
  api<AtlasCategoryMapRow>("/atlas/category-map", { method: "PATCH", json: { atlas_department_id, category_id } });

/** Rutas «Padre › Hijo» para elegir categoría en los mapas. */
export function categoryPaths(list: readonly Pick<AdminCategory, "id" | "name" | "parent_id">[]): { id: string; name: string }[] {
  const byId = new Map(list.map((item) => [item.id, item]));
  const path = (item: Pick<AdminCategory, "name" | "parent_id">, depth = 0): string => {
    const parent = item.parent_id && depth < 8 ? byId.get(item.parent_id) : undefined;
    return parent ? `${path(parent, depth + 1)} › ${item.name}` : item.name;
  };
  return list.map((item) => ({ id: item.id, name: path(item) }));
}

// Piezas de Atlas ONE: estos campos son suyos y el servidor los rechaza (422 atlas_owned) si cambian.
export const ATLAS_OWNED_FIELDS = ["name", "slug", "brand_id", "category_id"] as const;
export type AtlasOwnedField = (typeof ATLAS_OWNED_FIELDS)[number];

export const isAtlasLocked = (product: Pick<Product, "from_atlas">, field: string): boolean =>
  Boolean(product.from_atlas) && (ATLAS_OWNED_FIELDS as readonly string[]).includes(field);

/** Cuerpo del PATCH: en una pieza de Atlas no viaja lo que es de Atlas. */
export function editorialPayload<T extends Record<string, unknown>>(product: Pick<Product, "from_atlas">, values: T): Partial<T> {
  if (!product.from_atlas) return values;
  return Object.fromEntries(Object.entries(values).filter(([key]) => !isAtlasLocked(product, key))) as Partial<T>;
}
