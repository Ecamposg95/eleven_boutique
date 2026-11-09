import { cookies, headers } from "next/headers";
import { forbidden, notFound, redirect } from "next/navigation";
import { cache } from "react";
import { loginHref } from "./return-path";
import { hasRole, primaryImageUrl } from "./rules";
import { SESSION_COOKIE } from "./session";
import type { Me, ProductRef, Role } from "./types";

const API_URL = (process.env.API_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");
const TIMEOUT_MS = 15000;

type Query = Record<string, string | number | boolean | undefined>;

function buildPath(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

/** Sin caché en ningún nivel: la respuesta depende de la sesión. Solo se reenvía la cookie del panel. */
async function send(path: string): Promise<Response> {
  const session = (await cookies()).get(SESSION_COOKIE)?.value;
  return fetch(`${API_URL}/admin${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(TIMEOUT_MS),
    headers: {
      accept: "application/json",
      ...(session ? { cookie: `${SESSION_COOKIE}=${session}` } : {}),
    },
  });
}

async function toLogin(): Promise<never> {
  // proxy.ts anota la ruta pedida; `loginHref` la valida.
  const path = (await headers()).get("x-admin-path");
  redirect(loginHref(path, true));
}

/** `null` sin sesión válida. Una por petición gracias a `cache`. */
export const getMe = cache(async (): Promise<Me | null> => {
  if (!(await cookies()).has(SESSION_COOKIE)) return null;
  const res = await send("/auth/me");
  if (res.status === 401) return null;
  if (res.status === 403) forbidden();
  if (!res.ok) throw new Error(`auth/me: HTTP ${res.status}`);
  return (await res.json()) as Me;
});

/** Hay que llamarla también en cada página: los layouts no se vuelven a ejecutar al navegar. */
export async function requireMe(min: Role = "editor"): Promise<Me> {
  const me = await getMe();
  if (!me) return toLogin();
  if (!hasRole(me.role, min)) forbidden();
  return me;
}

/** 401 lleva al login, 403 a la pantalla de sin permiso, 404 a la de no encontrado. */
export async function adminGet<T>(path: string, query?: Query): Promise<T> {
  const target = buildPath(path, query);
  const res = await send(target);
  if (res.status === 401) return toLogin();
  if (res.status === 403) forbidden();
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`admin ${target}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

/** Para listas auxiliares (filtros): sin permiso el dato falta, pero la pantalla sigue. */
export async function adminGetOptional<T>(path: string, query?: Query): Promise<T | null> {
  const target = buildPath(path, query);
  const res = await send(target);
  if (res.status === 401) return toLogin();
  if (res.status === 403 || res.status === 404) return null;
  if (!res.ok) throw new Error(`admin ${target}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

const LIST_PAGE = 60;
const MAX_LIST_PAGES = 50;

/** Recorre una lista completa, esté paginada o no. `null` si el rol no la puede leer. */
export async function adminGetAll<T>(path: string): Promise<T[] | null> {
  const all: T[] = [];
  for (let page = 1; page <= MAX_LIST_PAGES; page++) {
    const batch = await adminGetOptional<{ items: T[]; total?: number }>(path, { page, page_size: LIST_PAGE });
    if (!batch) return page === 1 ? null : all;
    all.push(...batch.items);
    if (batch.total === undefined || batch.items.length === 0 || all.length >= batch.total) break;
  }
  return all;
}

type ProductDetailRef = {
  id: string;
  name: string;
  sku: string;
  brand: { name: string };
  media: { url: string; is_primary: boolean }[];
};

const PRODUCT_LOOKUP_CONCURRENCY = 6;

/**
 * El contrato solo da `product_ids` en colecciones y lookbooks, sin nombres ni un GET por lote:
 * se resuelve cada id, con tope de simultáneas. Los que ya no existen se omiten.
 */
export async function resolveProductRefs(ids: readonly string[]) {
  const found = new Map<string, ProductRef>();
  for (let i = 0; i < ids.length; i += PRODUCT_LOOKUP_CONCURRENCY) {
    const batch = ids.slice(i, i + PRODUCT_LOOKUP_CONCURRENCY);
    const rows = await Promise.all(batch.map((id) => adminGetOptional<ProductDetailRef>(`/products/${encodeURIComponent(id)}`)));
    for (const row of rows) {
      if (!row) continue;
      found.set(row.id, {
        id: row.id,
        name: row.name,
        sku: row.sku,
        brand_name: row.brand.name,
        primary_image_url: primaryImageUrl(row),
      });
    }
  }
  return ids.flatMap((id) => {
    const ref = found.get(id);
    return ref ? [ref] : [];
  });
}
