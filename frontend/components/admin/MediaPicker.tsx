"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorText, uploadMedia } from "@/lib/admin/client";
import { moveItem } from "@/lib/admin/reorder";
import { createUploadQueue, countUploads, validateImageFile, type UploadItem } from "@/lib/admin/upload-queue";
import type { MediaAsset } from "@/lib/admin/types";
import { Notice, Pager, Thumb } from "./ui";

const PAGE_SIZE = 24;
type Page = { items: MediaAsset[]; total: number };

/** Biblioteca en un diálogo. Permite buscar, subir ahí mismo y elegir una o varias fotos. */
export function MediaPicker({
  open,
  multiple = false,
  title = "Elegir de la biblioteca",
  onClose,
  onPick,
}: {
  open: boolean;
  multiple?: boolean;
  title?: string;
  onClose: () => void;
  onPick: (assets: MediaAsset[]) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picked, setPicked] = useState<Map<string, MediaAsset>>(new Map());
  const [uploads, setUploads] = useState<readonly UploadItem<File, MediaAsset>[]>([]);
  const queue = useRef<ReturnType<typeof createUploadQueue<File, MediaAsset>> | null>(null);

  const load = useCallback(async (query: string, target: number) => {
    try {
      const params = new URLSearchParams({ page: String(target), page_size: String(PAGE_SIZE) });
      if (query) params.set("q", query);
      setData(await api<Page>(`/media?${params}`));
      setError(null);
    } catch (cause) {
      setError(errorText(cause));
    }
  }, []);

  useEffect(() => {
    const dialog = ref.current;
    if (open && dialog && !dialog.open) dialog.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(() => void load(q, page), q ? 250 : 0);
    return () => clearTimeout(timer);
  }, [open, q, page, load]);

  const toggle = (asset: MediaAsset) => {
    if (!multiple) {
      onPick([asset]);
      onClose();
      return;
    }
    setPicked((current) => {
      const next = new Map(current);
      if (next.has(asset.id)) next.delete(asset.id);
      else next.set(asset.id, asset);
      return next;
    });
  };

  const upload = async (files: File[]) => {
    if (!queue.current) {
      queue.current = createUploadQueue<File, MediaAsset>({
        worker: uploadMedia,
        validate: validateImageFile,
        errorMessage: errorText,
        onChange: setUploads,
      });
    }
    queue.current.clearFinished();
    queue.current.add(files);
    await queue.current.idle();
    const done = queue.current.snapshot().flatMap((item) => (item.result ? [item.result] : []));
    setPage(1);
    setQ("");
    await load("", 1);
    if (!multiple && done[0]) {
      onPick([done[0]]);
      onClose();
    } else if (multiple) {
      setPicked((current) => {
        const next = new Map(current);
        for (const asset of done) next.set(asset.id, asset);
        return next;
      });
    }
  };

  const counts = countUploads(uploads);
  const failed = uploads.filter((item) => item.status === "error");

  return (
    <dialog ref={ref} aria-label={title} className="a-dialog a-dialog-wide" onClose={onClose}>
      {open ? (
        <div className="flex h-full flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="a-h2">{title}</h2>
            <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={onClose}>
              Cerrar
            </button>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-48 flex-1">
              <label className="a-label" htmlFor="picker-q">
                Buscar por nombre de archivo o texto alternativo
              </label>
              <input
                id="picker-q"
                type="search"
                className="a-input"
                value={q}
                onKeyDown={(event) => {
                  // El diálogo vive dentro de formularios de edición: Enter no debe guardarlos.
                  if (event.key === "Enter") event.preventDefault();
                }}
                onChange={(event) => {
                  setQ(event.target.value);
                  setPage(1);
                }}
              />
            </div>
            <label className="a-btn a-btn-quiet cursor-pointer focus-within:outline-2 focus-within:outline-bronze">
              Subir desde este equipo
              <input
                type="file"
                multiple={multiple}
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                onChange={(event) => {
                  const files = [...(event.target.files ?? [])];
                  event.target.value = "";
                  if (files.length) void upload(files);
                }}
              />
            </label>
          </div>
          {counts.uploading + counts.queued > 0 ? (
            <p role="status" className="muted">
              Subiendo: {counts.done} de {counts.total}
            </p>
          ) : null}
          {failed.map((item) => (
            <Notice key={item.id} kind="error">
              {item.file.name}: {item.error}
            </Notice>
          ))}
          {error ? <Notice kind="error">{error}</Notice> : null}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {data && data.items.length === 0 ? (
              <p className="py-6">{q ? `Sin resultados para «${q}».` : "La biblioteca está vacía. Suba la primera foto."}</p>
            ) : null}
            <ul className="grid grid-cols-[repeat(auto-fill,minmax(7.5rem,1fr))] gap-2">
              {data?.items.map((asset) => (
                <li key={asset.id}>
                  <button
                    type="button"
                    className="a-pick block w-full cursor-pointer p-1 text-left hover:bg-charcoal"
                    aria-pressed={multiple ? picked.has(asset.id) : undefined}
                    onClick={() => toggle(asset)}
                  >
                    <Thumb src={asset.url} size="100%" sizes="160px" />
                    <span className="mt-1 block truncate">{asset.filename ?? asset.alt ?? "Foto"}</span>
                    {multiple && picked.has(asset.id) ? <span className="block font-medium">Elegida</span> : null}
                  </button>
                </li>
              ))}
            </ul>
            {data ? <Pager page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} /> : null}
          </div>

          {multiple ? (
            <div className="flex items-center justify-end gap-3 border-t border-bronze/40 pt-3">
              <span className="muted">{picked.size} elegidas</span>
              <button
                type="button"
                className="a-btn a-btn-primary"
                disabled={picked.size === 0}
                onClick={() => {
                  onPick([...picked.values()]);
                  setPicked(new Map());
                  onClose();
                }}
              >
                Agregar fotos
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </dialog>
  );
}

/** Campo de imagen única: vista previa, elegir y quitar. */
export function AssetField({
  label,
  url,
  assetId,
  hint,
  ratio = "4 / 3",
  contain,
  onChange,
}: {
  label: string;
  url: string | null | undefined;
  assetId: string | null;
  hint?: string;
  ratio?: string;
  contain?: boolean;
  onChange: (asset: MediaAsset | null) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <p className="a-label">{label}</p>
      <div className="flex flex-wrap items-start gap-3">
        <Thumb src={url} size="9rem" ratio={ratio} sizes="200px" contain={contain} emptyLabel={assetId ? "Imagen elegida" : "Sin imagen"} />
        <div className="flex flex-col items-start gap-2">
          <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-label={`${assetId ? "Cambiar" : "Elegir"}: ${label}`} onClick={() => setOpen(true)}>
            {assetId ? "Cambiar imagen" : "Elegir imagen"}
          </button>
          {assetId ? (
            <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-label={`Quitar: ${label}`} onClick={() => onChange(null)}>
              Quitar
            </button>
          ) : null}
        </div>
      </div>
      {hint ? <p className="a-hint max-w-prose">{hint}</p> : null}
      <MediaPicker open={open} title={label} onClose={() => setOpen(false)} onPick={(assets) => onChange(assets[0] ?? null)} />
    </div>
  );
}

export type GallerySlide = { asset_id: string; url: string };

/** Varias imágenes en orden: añadir desde la biblioteca, mover y quitar. */
export function GalleryField({
  label,
  slides,
  max,
  hint,
  onChange,
}: {
  label: string;
  slides: GallerySlide[];
  max: number;
  hint?: string;
  onChange: (slides: GallerySlide[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const full = slides.length >= max;
  const add = (assets: MediaAsset[]) => {
    const known = new Set(slides.map((slide) => slide.asset_id));
    const fresh = assets.filter((asset) => !known.has(asset.id)).map((asset) => ({ asset_id: asset.id, url: asset.url }));
    onChange([...slides, ...fresh].slice(0, max));
  };
  return (
    <div>
      <p className="a-label">{label}</p>
      {slides.length > 0 ? (
        <ol className="flex flex-wrap gap-4">
          {slides.map((slide, index) => (
            <li key={slide.asset_id} className="flex flex-col items-start gap-1">
              <Thumb src={slide.url} size="9rem" ratio="16 / 10" sizes="200px" />
              <span className="a-hint">Foto {index + 2}</span>
              <div className="flex gap-1">
                <button
                  type="button"
                  className="a-btn a-btn-quiet a-btn-small"
                  aria-label={`Mover antes: foto ${index + 2}`}
                  disabled={index === 0}
                  onClick={() => onChange(moveItem(slides, index, index - 1))}
                >
                  ←
                </button>
                <button
                  type="button"
                  className="a-btn a-btn-quiet a-btn-small"
                  aria-label={`Mover después: foto ${index + 2}`}
                  disabled={index === slides.length - 1}
                  onClick={() => onChange(moveItem(slides, index, index + 1))}
                >
                  →
                </button>
                <button
                  type="button"
                  className="a-btn a-btn-quiet a-btn-small"
                  aria-label={`Quitar: foto ${index + 2}`}
                  onClick={() => onChange(slides.filter((item) => item.asset_id !== slide.asset_id))}
                >
                  Quitar
                </button>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="a-hint">Sin fotos adicionales: la portada muestra solo la principal.</p>
      )}
      <button type="button" className="a-btn a-btn-quiet a-btn-small mt-3" disabled={full} onClick={() => setOpen(true)}>
        {full ? `Máximo ${max} fotos` : "Añadir fotos"}
      </button>
      {hint ? <p className="a-hint max-w-prose">{hint}</p> : null}
      <MediaPicker open={open} multiple title={label} onClose={() => setOpen(false)} onPick={add} />
    </div>
  );
}
