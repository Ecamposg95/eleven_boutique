import { connection } from "next/server";
import type {
  BrandDetail,
  BrandSummary,
  Category,
  CollectionDetail,
  CollectionSummary,
  ItemList,
  LookbookDetail,
  LookbookSummary,
  Paginated,
  ProductCard,
  ProductDetail,
  ProductSort,
  PublicSettings,
  SearchResults,
} from "./types";

const API_URL = (process.env.API_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");
const TIMEOUT_MS = 8000;

/** La API no respondió o respondió con error. Lo recoge app/error.tsx. */
export class ApiUnavailableError extends Error {
  constructor(path: string, cause?: unknown) {
    super(`API no disponible: ${path}`, { cause });
    this.name = "ApiUnavailableError";
  }
}

type Query = Record<string, string | number | boolean | undefined>;

function buildPath(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

// El timeout va por fuera de fetch: pasar `signal` desactiva la memoización por petición.
function withTimeout<T>(promise: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("timeout")), TIMEOUT_MS);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

/**
 * `null` en 404; lanza ApiUnavailableError si la API falla.
 * Sin caché: Next solo guarda respuestas 200, así que un 404 nunca reemplazaría a la copia
 * anterior y una pieza despublicada seguiría visible indefinidamente.
 */
async function request<T>(path: string, query?: Query, init: RequestInit = { cache: "no-store" }): Promise<T | null> {
  // Fuera del try: fuerza render en cada petición, así `next build` no toca la API.
  await connection();
  const target = buildPath(path, query);
  try {
    const res = await withTimeout(fetch(`${API_URL}${target}`, init));
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch (cause) {
    throw new ApiUnavailableError(target, cause);
  }
}

async function requestList<T>(path: string, query?: Query): Promise<T> {
  const data = await request<T>(path, query, { next: { revalidate: 30 } });
  if (data === null) throw new ApiUnavailableError(path);
  return data;
}

/** Para secciones opcionales y metadatos: `null` si la API no está disponible. */
export async function soft<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise;
  } catch (error) {
    if (error instanceof ApiUnavailableError) return null;
    throw error;
  }
}

const seg = encodeURIComponent;

export const getSettings = () => requestList<PublicSettings>("/site-settings/public");

export const getBrands = async (query?: { featured?: boolean; q?: string }): Promise<BrandSummary[]> =>
  (await requestList<ItemList<BrandSummary>>("/brands", query)).items;

export const getBrand = (slug: string) => request<BrandDetail>(`/brands/${seg(slug)}`);

export const getCategories = async (): Promise<Category[]> =>
  (await requestList<ItemList<Category>>("/categories")).items;

export type ProductQuery = {
  brand?: string;
  category?: string;
  featured?: boolean;
  sort?: ProductSort;
  page?: number;
  page_size?: number;
};

export const getProducts = (query?: ProductQuery) =>
  requestList<Paginated<ProductCard>>("/products", query);

export const getProduct = (slug: string) => request<ProductDetail>(`/products/${seg(slug)}`);

export const getNovedades = (query?: { page?: number; page_size?: number }) =>
  requestList<Paginated<ProductCard>>("/novedades", query);

export const getCollections = async (): Promise<CollectionSummary[]> =>
  (await requestList<ItemList<CollectionSummary>>("/collections")).items;

export const getCollection = (slug: string) => request<CollectionDetail>(`/collections/${seg(slug)}`);

export const getLookbooks = async (): Promise<LookbookSummary[]> =>
  (await requestList<ItemList<LookbookSummary>>("/lookbooks")).items;

export const getLookbook = (slug: string) => request<LookbookDetail>(`/lookbooks/${seg(slug)}`);

export const search = (q: string) => requestList<SearchResults>("/search", { q });

const MAX_FACET_PAGES = 10;

/**
 * Categorías con piezas de una marca. El contrato no las expone por marca, así que se
 * derivan del listado de productos, con tope de páginas para marcas muy grandes.
 */
export async function getBrandCategories(brand: string): Promise<{ slug: string; name: string }[]> {
  const found = new Map<string, string>();
  for (let page = 1; page <= MAX_FACET_PAGES; page++) {
    const batch = await getProducts({ brand, page, page_size: 60 });
    for (const product of batch.items) found.set(product.category.slug, product.category.name);
    if (batch.items.length === 0 || page * batch.page_size >= batch.total) break;
  }
  return [...found]
    .map(([slug, name]) => ({ slug, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "es"));
}
