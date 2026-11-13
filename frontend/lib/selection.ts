/**
 * «Mi selección»: piezas guardadas en este navegador para consultarlas juntas por WhatsApp.
 * No hay carrito ni cuenta; vive en localStorage y se sincroniza entre pestañas.
 */
export type SelectedPiece = {
  slug: string;
  name: string;
  brand: string | null;
  href: string;
  image: { url: string; alt: string } | null;
};

/** Mismo tope que la API (POST /selection/consult). */
export const SELECTION_LIMIT = 24;
export const STORAGE_KEY = "eleven:seleccion:v1";

const isText = (value: unknown): value is string => typeof value === "string" && value.length > 0;

function toPiece(raw: unknown): SelectedPiece | null {
  if (!raw || typeof raw !== "object") return null;
  const item = raw as Record<string, unknown>;
  if (!isText(item.slug) || !isText(item.name) || !isText(item.href) || !item.href.startsWith("/")) return null;
  const image = item.image as Record<string, unknown> | null | undefined;
  return {
    slug: item.slug,
    name: item.name,
    brand: isText(item.brand) ? item.brand : null,
    href: item.href,
    image: image && isText(image.url) ? { url: image.url, alt: typeof image.alt === "string" ? image.alt : "" } : null,
  };
}

/** Lectura tolerante: cualquier dato dañado o ajeno se descarta sin romper la página. */
export function parseSelection(raw: string | null): SelectedPiece[] {
  if (!raw) return [];
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(data)) return [];
  const seen = new Set<string>();
  const pieces: SelectedPiece[] = [];
  for (const entry of data) {
    const piece = toPiece(entry);
    if (!piece || seen.has(piece.slug)) continue;
    seen.add(piece.slug);
    pieces.push(piece);
    if (pieces.length === SELECTION_LIMIT) break;
  }
  return pieces;
}

export const hasPiece = (pieces: SelectedPiece[], slug: string) => pieces.some((p) => p.slug === slug);

/** Agrega al final; si ya está o se llegó al tope, devuelve la misma lista. */
export function addPiece(pieces: SelectedPiece[], piece: SelectedPiece): SelectedPiece[] {
  if (hasPiece(pieces, piece.slug) || pieces.length >= SELECTION_LIMIT) return pieces;
  return [...pieces, piece];
}

export function removePieces(pieces: SelectedPiece[], slugs: string[]): SelectedPiece[] {
  const drop = new Set(slugs);
  return pieces.filter((p) => !drop.has(p.slug));
}

// --- Almacén del navegador (useSyncExternalStore) -------------------------------------

const EMPTY: SelectedPiece[] = [];
const listeners = new Set<() => void>();
let cachedRaw: string | null = null;
let cached: SelectedPiece[] = EMPTY;

function readRaw(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function getSelection(): SelectedPiece[] {
  const raw = readRaw();
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = parseSelection(raw);
  }
  return cached;
}

export const getServerSelection = () => EMPTY;

export function subscribeSelection(onChange: () => void) {
  listeners.add(onChange);
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === STORAGE_KEY) onChange();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function updateSelection(change: (pieces: SelectedPiece[]) => SelectedPiece[]) {
  const next = change(getSelection());
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Navegación privada o almacenamiento lleno: la selección dura solo en esta visita.
    cachedRaw = JSON.stringify(next);
    cached = next;
  }
  listeners.forEach((listener) => listener());
}
