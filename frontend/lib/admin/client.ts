import { loginHref } from "./return-path";
import { parseValidationMessage } from "./rules";
import type { MediaAsset } from "./types";

const BASE = "/api/v1/admin";

/** Error de la API con el mensaje listo para mostrar. */
export class AdminApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    /** Errores por campo, si el servidor rechazó el cuerpo. */
    public fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = "AdminApiError";
  }
}

const NETWORK_MESSAGE = "No fue posible conectar con el servidor. Revise la conexión e intente de nuevo.";

function fallbackMessage(status: number): string {
  if (status === 403) return "Este usuario no tiene permiso para esta acción.";
  if (status === 404) return "Este registro ya no existe.";
  if (status === 413) return "El archivo es demasiado grande.";
  return "El servidor no pudo completar la acción. Intente de nuevo.";
}

function parseError(status: number, body: unknown): AdminApiError {
  const error = (body as { error?: Record<string, unknown> } | null)?.error;
  const code = typeof error?.code === "string" ? error.code : `http_${status}`;
  const message = typeof error?.message === "string" && error.message ? error.message : fallbackMessage(status);
  // El mensaje de un 422 es técnico: se reparte por campo y arriba solo se pide revisar.
  if (code === "validation_error") {
    const fields = parseValidationMessage(message);
    const named = Object.keys(fields).length > 0;
    return new AdminApiError(status, code, named ? "Revise los campos marcados." : "El servidor rechazó estos datos. Revíselos e intente de nuevo.", fields);
  }
  return new AdminApiError(status, code, message);
}

function currentPath(): string {
  return `${window.location.pathname}${window.location.search}`;
}

/** Sesión vencida: de vuelta al login, conservando dónde estaba. */
export function goToLogin(): void {
  window.location.assign(loginHref(currentPath(), true));
}

type Options = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  json?: unknown;
  form?: FormData;
  /** El login gestiona su propio 401. */
  noSessionRedirect?: boolean;
};

/** Siempre por el mismo origen y sin caché. */
export async function api<T = unknown>(path: string, options: Options = {}): Promise<T> {
  const { method = options.json !== undefined || options.form ? "POST" : "GET", json, form } = options;
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      credentials: "same-origin",
      cache: "no-store",
      headers: json !== undefined ? { "content-type": "application/json", accept: "application/json" } : { accept: "application/json" },
      body: json !== undefined ? JSON.stringify(json) : form,
    });
  } catch {
    throw new AdminApiError(0, "network", NETWORK_MESSAGE);
  }
  if (response.status === 204) return undefined as T;
  const body: unknown = await response.json().catch(() => null);
  if (response.ok) return body as T;
  if (response.status === 401 && !options.noSessionRedirect) {
    goToLogin();
    throw new AdminApiError(401, "session_expired", "La sesión terminó.");
  }
  throw parseError(response.status, body);
}

export const errorText = (error: unknown): string =>
  error instanceof Error ? error.message : "Ocurrió un error inesperado.";

type UploadBody = { items?: MediaAsset[]; errors?: { message?: string }[] };

/** Un archivo por petición: es lo que permite progreso y error por archivo. Usa XHR por el progreso. */
export function uploadMedia(file: File, onProgress: (fraction: number) => void): Promise<MediaAsset> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("files", file);
    xhr.open("POST", `${BASE}/media`);
    xhr.responseType = "json";
    xhr.setRequestHeader("accept", "application/json");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    xhr.onerror = () => reject(new AdminApiError(0, "network", NETWORK_MESSAGE));
    xhr.onload = () => {
      const body = xhr.response as unknown;
      if (xhr.status === 401) {
        goToLogin();
        reject(new AdminApiError(401, "session_expired", "La sesión terminó."));
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(parseError(xhr.status, body));
        return;
      }
      const data = body as UploadBody;
      // Un archivo rechazado por su contenido llega en 201, dentro de `errors`.
      const asset = data?.items?.[0];
      if (asset) resolve(asset);
      else reject(new AdminApiError(422, "rejected", data?.errors?.[0]?.message ?? "El servidor rechazó el archivo."));
    };
    xhr.send(form);
  });
}
