export type UploadStatus = "queued" | "uploading" | "done" | "error";

export type UploadItem<F, R> = {
  id: number;
  file: F;
  status: UploadStatus;
  /** 0 a 1. */
  progress: number;
  error: string | null;
  result: R | null;
};

export type UploadWorker<F, R> = (file: F, onProgress: (fraction: number) => void) => Promise<R>;

export type UploadQueueOptions<F, R> = {
  worker: UploadWorker<F, R>;
  concurrency?: number;
  /** Devuelve el motivo si el archivo no debe ni intentarse. */
  validate?: (file: F) => string | null;
  errorMessage?: (error: unknown) => string;
  onChange?: (items: readonly UploadItem<F, R>[]) => void;
};

export const UPLOAD_CONCURRENCY = 3;

/** Cola con tope de subidas simultáneas. Un fallo no detiene a los demás. */
export function createUploadQueue<F, R>(options: UploadQueueOptions<F, R>) {
  const { worker, validate, onChange } = options;
  const concurrency = Math.max(1, options.concurrency ?? UPLOAD_CONCURRENCY);
  const describe = options.errorMessage ?? ((error) => (error instanceof Error ? error.message : "Falló la subida."));
  let items: UploadItem<F, R>[] = [];
  let nextId = 1;
  let active = 0;
  const waiters: (() => void)[] = [];

  const patch = (id: number, change: Partial<UploadItem<F, R>>) => {
    items = items.map((item) => (item.id === id ? { ...item, ...change } : item));
    onChange?.(items);
  };

  const pump = () => {
    for (const item of items) {
      if (active >= concurrency) break;
      if (item.status !== "queued") continue;
      active += 1;
      item.status = "uploading";
      patch(item.id, { status: "uploading", progress: 0, error: null });
      worker(item.file, (fraction) => patch(item.id, { progress: Math.min(1, Math.max(0, fraction)) }))
        .then((result) => patch(item.id, { status: "done", progress: 1, result }))
        .catch((error: unknown) => patch(item.id, { status: "error", error: describe(error) }))
        .finally(() => {
          active -= 1;
          pump();
          settle();
        });
    }
  };

  const settle = () => {
    if (active === 0 && !items.some((item) => item.status === "queued")) {
      waiters.splice(0).forEach((resolve) => resolve());
    }
  };

  return {
    add(files: readonly F[]) {
      const added = files.map((file): UploadItem<F, R> => {
        const problem = validate?.(file) ?? null;
        return {
          id: nextId++,
          file,
          status: problem ? "error" : "queued",
          progress: 0,
          error: problem,
          result: null,
        };
      });
      items = [...items, ...added];
      onChange?.(items);
      pump();
    },
    /** Reintenta los fallidos que sí pasan la validación. */
    retryFailed() {
      items = items.map((item) =>
        item.status === "error" && !validate?.(item.file)
          ? { ...item, status: "queued" as const, error: null, progress: 0 }
          : item,
      );
      onChange?.(items);
      pump();
    },
    /** Quita lo que aún no empezó. Lo que ya se está subiendo termina. */
    cancelQueued() {
      items = items.filter((item) => item.status !== "queued");
      onChange?.(items);
      settle();
    },
    /** Olvida lo terminado y conserva lo pendiente. */
    clearFinished() {
      items = items.filter((item) => item.status === "queued" || item.status === "uploading");
      onChange?.(items);
    },
    snapshot: (): readonly UploadItem<F, R>[] => items,
    /** Se resuelve cuando no queda nada en curso ni en espera. */
    idle: () =>
      new Promise<void>((resolve) => {
        waiters.push(resolve);
        settle();
      }),
  };
}

export type UploadCounts = { total: number; queued: number; uploading: number; done: number; error: number };

export function countUploads(items: readonly { status: UploadStatus }[]): UploadCounts {
  const counts: UploadCounts = { total: items.length, queued: 0, uploading: 0, done: 0, error: 0 };
  for (const item of items) counts[item.status] += 1;
  return counts;
}

const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** Filtro previo para no gastar la subida. El servidor verifica el contenido real. */
export function validateImageFile(file: { name: string; type: string; size: number }): string | null {
  if (file.type ? !IMAGE_TYPES.has(file.type) : !/\.(jpe?g|png|webp)$/i.test(file.name)) {
    return "Formato no admitido. Use JPEG, PNG o WebP.";
  }
  if (file.size > MAX_UPLOAD_BYTES) return "Pesa más de 20 MB.";
  if (file.size === 0) return "El archivo está vacío.";
  return null;
}
