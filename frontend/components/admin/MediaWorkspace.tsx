"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useOptimistic, useRef, useState, useTransition } from "react";
import { AdminApiError, api, errorText, uploadMedia } from "@/lib/admin/client";
import { formatNumber, plural } from "@/lib/admin/format";
import { assignPayload, chunk, confirmAllProposed, type Decision, toDecisions } from "@/lib/admin/rules";
import type { AssignResult, MatchProposal, MediaAsset, ProductRef } from "@/lib/admin/types";
import { countUploads, createUploadQueue, type UploadItem, validateImageFile } from "@/lib/admin/upload-queue";
import { withParams } from "@/lib/url";
import { ProductSearch } from "./ProductSearch";
import { CheckField, Empty, Notice, PageHead, Pager, Thumb, useConfirm } from "./ui";

type Upload = UploadItem<File, MediaAsset>;
const VISIBLE_UPLOADS = 40;
const MATCH_BATCH = 100;

function Uploader({ onDone, onAssign }: { onDone: () => void; onAssign: (assets: MediaAsset[]) => void }) {
  const [items, setItems] = useState<readonly Upload[]>([]);
  const [over, setOver] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const queueRef = useRef<ReturnType<typeof createUploadQueue<File, MediaAsset>> | null>(null);

  const queue = () => {
    queueRef.current ??= createUploadQueue<File, MediaAsset>({
      worker: uploadMedia,
      validate: validateImageFile,
      errorMessage: errorText,
      onChange: setItems,
    });
    return queueRef.current;
  };

  const add = (files: File[]) => {
    if (files.length === 0) return;
    const current = queue();
    current.add(files);
    void current.idle().then(onDone);
  };

  const counts = countUploads(items);
  const active = counts.queued + counts.uploading > 0;

  useEffect(() => {
    if (!active) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [active]);

  // Con cientos de archivos, primero lo que importa: errores y lo que está en curso.
  const shown = useMemo(() => {
    if (showAll || items.length <= VISIBLE_UPLOADS) return items;
    const rank = { error: 0, uploading: 1, queued: 2, done: 3 } as const;
    return [...items].sort((a, b) => rank[a.status] - rank[b.status] || a.id - b.id).slice(0, VISIBLE_UPLOADS);
  }, [items, showAll]);

  const assets = items.flatMap((item) => (item.result ? [item.result] : []));

  return (
    <section aria-labelledby="subir-t" className="a-section">
      <h2 id="subir-t" className="a-h2">
        Subir fotos
      </h2>
      <div
        className="a-drop mt-2"
        data-over={over || undefined}
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setOver(false);
          add([...event.dataTransfer.files]);
        }}
      >
        <p className="max-sm:hidden">Arrastre aquí las fotos, tantas como necesite.</p>
        <label className="a-btn cursor-pointer focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-bronze">
          Elegir fotos
          <input
            data-testid="upload-input"
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            onChange={(event) => {
              const files = [...(event.target.files ?? [])];
              event.target.value = "";
              add(files);
            }}
          />
        </label>
        <p className="muted">JPEG, PNG o WebP, hasta 20 MB cada una.</p>
      </div>

      {items.length > 0 ? (
        <div className="mt-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <p role="status" className="font-medium">
              {active ? `Subiendo: ${formatNumber(counts.done)} de ${formatNumber(counts.total)}` : `${plural(counts.done, "foto subida", "fotos subidas")}`}
              {counts.error ? `, ${plural(counts.error, "con error", "con error")}` : ""}
            </p>
            {counts.error > 0 && !active ? (
              <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={() => queue().retryFailed()}>
                Reintentar las fallidas
              </button>
            ) : null}
            {counts.queued > 0 ? (
              <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={() => queue().cancelQueued()}>
                Cancelar las que faltan
              </button>
            ) : null}
            {!active ? (
              <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={() => queue().clearFinished()}>
                Limpiar lista
              </button>
            ) : null}
          </div>
          <progress className="a-progress mt-2" max={Math.max(1, counts.total)} value={counts.done + counts.error} aria-label="Avance total" />

          {!active && assets.length > 0 ? (
            <div className="a-panel mt-3 flex flex-wrap items-center justify-between gap-3">
              <p>Siguiente paso: revisar a qué producto corresponde cada foto.</p>
              <button
                type="button"
                className="a-btn a-btn-primary"
                onClick={() => {
                  onAssign(assets);
                  queue().clearFinished();
                }}
              >
                Asignar {plural(assets.length, "foto", "fotos")} a productos
              </button>
            </div>
          ) : null}

          <ul className="mt-3 grid gap-x-6 md:grid-cols-2 xl:grid-cols-3" aria-label="Archivos">
            {shown.map((item) => (
              <li key={item.id} data-upload={item.status} className="min-w-0 border-b border-bronze/25 py-1.5">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="truncate" title={item.file.name}>
                    {item.file.name}
                  </span>
                  <span className={item.status === "error" ? "shrink-0 font-medium text-sand" : "muted shrink-0"}>
                    {item.status === "done" ? "Lista" : item.status === "error" ? "Error" : item.status === "queued" ? "En espera" : `${Math.round(item.progress * 100)} %`}
                  </span>
                </div>
                {item.status === "uploading" ? <progress className="a-progress mt-1" max={1} value={item.progress} aria-label={`Avance de ${item.file.name}`} /> : null}
                {item.error ? <p className="a-error">{item.error}</p> : null}
              </li>
            ))}
          </ul>
          {items.length > VISIBLE_UPLOADS ? (
            <button type="button" className="link mt-2 cursor-pointer" onClick={() => setShowAll((value) => !value)}>
              {showAll ? "Mostrar solo lo importante" : `Ver los ${formatNumber(items.length)} archivos`}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

const MATCH_REASON: Record<Decision["match"], string> = {
  sku: "Coincide por SKU",
  photo_ref: "Coincide por referencia de foto",
  none: "Sin coincidencia segura",
};

function productOf(decision: Decision, chosen: Map<string, ProductRef>): ProductRef | null {
  if (!decision.product_id) return null;
  return chosen.get(decision.product_id) ?? decision.candidates.find((item) => item.id === decision.product_id) ?? null;
}

function ReviewRow({
  decision,
  asset,
  product,
  result,
  onChange,
  onChoose,
}: {
  decision: Decision;
  asset: MediaAsset | undefined;
  product: ProductRef | null;
  result: AssignResult | undefined;
  onChange: (patch: Partial<Decision>) => void;
  onChoose: (product: ProductRef) => void;
}) {
  const [searching, setSearching] = useState(false);
  const others = decision.candidates.filter((item) => item.id !== decision.product_id);
  const stateLabel = decision.state === "confirmed" ? "Confirmada" : decision.state === "skipped" ? "Omitida" : "Por revisar";

  return (
    <li data-review={decision.media_asset_id} data-state={decision.state} className="a-lazy-row grid gap-3 border-b border-bronze/30 py-3 sm:grid-cols-[6rem_minmax(0,1fr)_auto] sm:items-start">
      <div className="flex gap-3 sm:block">
        <Thumb src={asset?.url} size="6rem" sizes="160px" alt="" emptyLabel="Foto" />
        <p className="min-w-0 break-all sm:mt-1 sm:hidden">{decision.filename}</p>
      </div>
      <div className="min-w-0">
        <p className="break-all max-sm:hidden">{decision.filename}</p>
        <p className="muted">{MATCH_REASON[decision.match]}</p>
        {product ? (
          <div className="mt-2 flex items-center gap-3">
            {/* bulk-match no trae foto: sin ella se omite, para no sugerir que el producto no tiene. */}
            {product.primary_image_url ? <Thumb src={product.primary_image_url} size="2.5rem" sizes="64px" /> : null}
            <span className="min-w-0">
              <span className="a-piece block">{product.name}</span>
              <span className="muted block break-all">{[product.brand_name, product.sku].filter(Boolean).join(", ")}</span>
            </span>
          </div>
        ) : decision.product_id ? (
          <p className="mt-2">Producto propuesto</p>
        ) : (
          <p className="mt-2 font-medium text-sand">Sin producto elegido</p>
        )}
        {others.length > 0 && decision.state !== "skipped" ? (
          <div className="mt-2">
            <p className="muted">Posibles productos:</p>
            <ul className="mt-1 flex flex-wrap gap-1">
              {others.slice(0, 6).map((item) => (
                <li key={item.id}>
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={() => onChange({ product_id: item.id, state: "confirmed" })}>
                    {item.name}
                    {item.sku ? `, ${item.sku}` : ""}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {searching ? (
          <div className="mt-2 max-w-md">
            <ProductSearch
              label={`Buscar producto para ${decision.filename}`}
              autoFocus
              onPick={(picked) => {
                onChoose(picked);
                setSearching(false);
              }}
            />
          </div>
        ) : null}
        {result && !result.ok ? <p className="a-error">{result.error?.message ?? "No se pudo asignar."}</p> : null}
        {result?.ok ? <p className="mt-1 font-medium">Asignada</p> : null}
      </div>
      {result?.ok ? null : (
        <div className="flex flex-wrap items-center gap-2 sm:w-64 sm:justify-end">
          <span className={decision.state === "pending" ? "muted w-full sm:text-right" : "w-full font-medium sm:text-right"}>{stateLabel}</span>
          <button
            type="button"
            className={`a-btn a-btn-small ${decision.state === "confirmed" ? "" : "a-btn-primary"}`}
            aria-disabled={!decision.product_id}
            aria-pressed={decision.state === "confirmed"}
            onClick={() => {
              if (decision.product_id) onChange({ state: decision.state === "confirmed" ? "pending" : "confirmed" });
            }}
          >
            Confirmar
          </button>
          <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-expanded={searching} onClick={() => setSearching((value) => !value)}>
            Cambiar
          </button>
          <button
            type="button"
            className="a-btn a-btn-quiet a-btn-small"
            aria-pressed={decision.state === "skipped"}
            onClick={() => onChange({ state: decision.state === "skipped" ? "pending" : "skipped" })}
          >
            Omitir
          </button>
        </div>
      )}
    </li>
  );
}

function BulkAssign({ assets, onClose }: { assets: MediaAsset[]; onClose: () => void }) {
  const router = useRouter();
  const [decisions, setDecisions] = useState<Decision[] | null>(null);
  const [chosen, setChosen] = useState<Map<string, ProductRef>>(new Map());
  const [results, setResults] = useState<Map<string, AssignResult>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState<"all" | "proposed" | "none">("all");
  const byId = useMemo(() => new Map(assets.map((asset) => [asset.id, asset])), [assets]);
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    let stale = false;
    (async () => {
      try {
        const proposals: MatchProposal[] = [];
        for (const batch of chunk(assets.map((asset) => asset.id), MATCH_BATCH)) {
          const data = await api<{ items: MatchProposal[] }>("/media/bulk-match", { json: { media_asset_ids: batch } });
          proposals.push(...data.items);
        }
        if (!stale) {
          setDecisions(toDecisions(proposals));
          heading.current?.focus();
        }
      } catch (cause) {
        if (!stale) setError(errorText(cause));
      }
    })();
    return () => {
      stale = true;
    };
  }, [assets]);

  const patch = useCallback((id: string, change: Partial<Decision>) => {
    setDecisions((current) => current?.map((item) => (item.media_asset_id === id ? { ...item, ...change } : item)) ?? null);
  }, []);

  const open = (decisions ?? []).filter((item) => !results.get(item.media_asset_id)?.ok);
  const toAssign = assignPayload(open);
  const assigned = [...results.values()].filter((result) => result.ok).length;
  const proposedPending = open.filter((item) => item.state === "pending" && item.product_id).length;
  const visible = open.filter((item) => (view === "all" ? true : view === "proposed" ? Boolean(item.product_id) : !item.product_id));

  const assign = async () => {
    setBusy(true);
    setError(null);
    const next = new Map(results);
    try {
      for (const batch of chunk(toAssign, MATCH_BATCH)) {
        try {
          const data = await api<{ results: AssignResult[] }>("/media/bulk-assign", { json: { items: batch } });
          for (const result of data.results) next.set(result.media_asset_id, result);
        } catch (cause) {
          for (const item of batch) {
            next.set(item.media_asset_id, {
              media_asset_id: item.media_asset_id,
              ok: false,
              error: { code: "request_failed", message: errorText(cause) },
            });
          }
        }
      }
      setResults(next);
      router.refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="asignar-t" className="a-section">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="asignar-t" ref={heading} tabIndex={-1} className="a-h2 outline-none">
          Asignar fotos a productos
        </h2>
        <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={onClose}>
          {open.length === 0 ? "Terminar" : "Salir de la asignación"}
        </button>
      </div>
      <p className="a-hint max-w-prose">
        Nada se guarda hasta pulsar «Asignar». Las fotos que omita quedan en la biblioteca y se pueden asignar después.
      </p>
      {error ? (
        <div className="mt-2">
          <Notice kind="error">{error}</Notice>
        </div>
      ) : null}
      {!decisions && !error ? (
        <p role="status" className="muted mt-3">
          Buscando el producto de cada foto
        </p>
      ) : null}
      {decisions ? (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <fieldset className="flex flex-wrap gap-1">
              <legend className="sr-only">Mostrar</legend>
              {(
                [
                  ["all", `Todas (${open.length})`],
                  ["proposed", `Con propuesta (${open.filter((item) => item.product_id).length})`],
                  ["none", `Sin propuesta (${open.filter((item) => !item.product_id).length})`],
                ] as const
              ).map(([key, label]) => (
                <button key={key} type="button" aria-pressed={view === key} className={`a-btn a-btn-small ${view === key ? "a-btn-primary" : "a-btn-quiet"}`} onClick={() => setView(key)}>
                  {label}
                </button>
              ))}
            </fieldset>
            {proposedPending > 0 ? (
              <button type="button" className="a-btn a-btn-small lg:ml-auto" onClick={() => setDecisions((current) => (current ? confirmAllProposed(current) : current))}>
                {proposedPending === 1 ? "Confirmar la propuesta" : `Confirmar las ${formatNumber(proposedPending)} propuestas`}
              </button>
            ) : null}
          </div>

          {open.length === 0 ? (
            <p role="status" className="a-notice mt-3">
              {plural(assigned, "foto asignada", "fotos asignadas")}. Revise los productos para publicarlos.
            </p>
          ) : visible.length === 0 ? (
            <p className="mt-4">No hay fotos en esta vista.</p>
          ) : (
            <ul className="mt-2">
              {visible.map((decision) => (
                <ReviewRow
                  key={decision.media_asset_id}
                  decision={decision}
                  asset={byId.get(decision.media_asset_id)}
                  product={productOf(decision, chosen)}
                  result={results.get(decision.media_asset_id)}
                  onChange={(change) => patch(decision.media_asset_id, change)}
                  onChoose={(product) => {
                    setChosen((current) => new Map(current).set(product.id, product));
                    patch(decision.media_asset_id, { product_id: product.id, state: "confirmed" });
                  }}
                />
              ))}
            </ul>
          )}

          {open.length > 0 ? (
            <div className="a-bar">
              <button type="button" className="a-btn a-btn-primary" disabled={busy || toAssign.length === 0} onClick={() => void assign()}>
                {busy ? "Asignando" : `Asignar ${plural(toAssign.length, "foto", "fotos")}`}
              </button>
              <p role="status" aria-live="polite">
                {assigned > 0 ? `${plural(assigned, "asignada", "asignadas")}. ` : ""}
                {open.filter((item) => item.state === "pending").length} por revisar, {open.filter((item) => item.state === "skipped").length} omitidas.
              </p>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function LibraryTile({ asset, onChanged }: { asset: MediaAsset; onChanged: () => void }) {
  const [alt, setAlt] = useState(asset.alt);
  const [saved, setSaved] = useState(asset.alt);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, dialog] = useConfirm();

  const saveAlt = async () => {
    if (alt === saved) return;
    try {
      await api(`/media/${asset.id}`, { method: "PATCH", json: { alt } });
      setSaved(alt);
      setNote("Guardado");
      setError(null);
    } catch (cause) {
      setError(errorText(cause));
    }
  };

  const remove = async () => {
    const accepted = await confirm({
      title: "¿Eliminar esta foto de la biblioteca?",
      body: <p>{asset.filename}: no está en uso. Esta acción no se puede deshacer.</p>,
      confirmLabel: "Eliminar foto",
    });
    if (!accepted) return;
    try {
      await api(`/media/${asset.id}`, { method: "DELETE" });
      onChanged();
    } catch (cause) {
      setError(
        cause instanceof AdminApiError && cause.status === 409
          ? "Esta foto está en uso. Quítela primero del producto, marca o colección que la usa."
          : errorText(cause),
      );
    }
  };

  const inUse = asset.in_use;
  return (
    <li data-asset={asset.id} className="min-w-0">
      <Thumb src={asset.url} alt={saved} size="100%" sizes="(max-width: 640px) 50vw, 220px" />
      <p className="mt-1 truncate" title={asset.filename ?? undefined}>
        {asset.filename ?? "Foto"}
      </p>
      <p className="muted">{inUse ? "En uso" : "Sin usar"}</p>
      <div className="mt-1">
        <label htmlFor={`lib-alt-${asset.id}`} className="a-label">
          Texto alternativo
        </label>
        <input
          id={`lib-alt-${asset.id}`}
          className="a-input"
          value={alt}
          aria-describedby={error ? `lib-err-${asset.id}` : undefined}
          onChange={(event) => {
            setAlt(event.target.value);
            setNote(null);
          }}
          onBlur={() => void saveAlt()}
        />
      </div>
      {note ? (
        <p role="status" className="a-hint">
          {note}
        </p>
      ) : null}
      {error ? (
        <p id={`lib-err-${asset.id}`} role="alert" className="a-error">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        className="a-btn a-btn-quiet a-btn-small mt-2 w-full"
        aria-disabled={inUse}
        aria-label={inUse ? `No se puede eliminar ${asset.filename ?? "la foto"}: está en uso` : `Eliminar ${asset.filename ?? "la foto"}`}
        onClick={() => {
          if (inUse) setError("Esta foto está en uso. Quítela primero del producto, marca o colección que la usa.");
          else void remove();
        }}
      >
        Eliminar
      </button>
      {dialog}
    </li>
  );
}

export function MediaWorkspace({
  items,
  total,
  page,
  pageSize,
  q: initialQ,
  unused: serverUnused,
}: {
  items: MediaAsset[];
  total: number;
  page: number;
  pageSize: number;
  q: string;
  unused: boolean;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [unused, setOptimisticUnused] = useOptimistic(serverUnused);
  const [q, setQ] = useState(initialQ);
  const [assignAssets, setAssignAssets] = useState<MediaAsset[] | null>(null);
  const [loadingUnused, setLoadingUnused] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const href = (change: { q?: string; unused?: boolean; page?: number }) => {
    const next = { q, unused, page: 1, ...change };
    return withParams("/admin/multimedia", { q: next.q, sin_usar: next.unused ? 1 : undefined, page: next.page });
  };
  const go = (change: { q?: string; unused?: boolean; page?: number }) =>
    startTransition(() => {
      if (change.unused !== undefined) setOptimisticUnused(change.unused);
      router.replace(href(change), { scroll: false });
    });

  useEffect(() => {
    if (q === initialQ) return;
    const timer = setTimeout(() => go({ q }), 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo reacciona al texto.
  }, [q]);

  const refresh = useCallback(() => startTransition(() => router.refresh()), [router]);

  /** Retoma el trabajo: toda foto sin usar entra a la revisión, también tras recargar la página. */
  const assignUnused = async () => {
    setLoadingUnused(true);
    setError(null);
    try {
      const assets: MediaAsset[] = [];
      for (let current = 1; ; current++) {
        const data = await api<{ items: MediaAsset[]; total: number }>(`/media?unused=true&page=${current}&page_size=60`);
        assets.push(...data.items);
        if (data.items.length === 0 || assets.length >= data.total) break;
      }
      setAssignAssets(assets);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setLoadingUnused(false);
    }
  };

  if (assignAssets) {
    return (
      <>
        <PageHead title="Multimedia" />
        <BulkAssign
          assets={assignAssets}
          onClose={() => {
            setAssignAssets(null);
            refresh();
          }}
        />
      </>
    );
  }

  return (
    <>
      <PageHead title="Multimedia" />
      <Uploader onDone={refresh} onAssign={setAssignAssets} />

      <section aria-labelledby="biblioteca-t" className="a-section">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="biblioteca-t" className="a-h2">
            Biblioteca
          </h2>
          <button type="button" className="a-btn a-btn-quiet a-btn-small" disabled={loadingUnused} onClick={() => void assignUnused()}>
            Asignar las fotos sin usar
          </button>
        </div>
        {error ? (
          <div className="mt-2">
            <Notice kind="error">{error}</Notice>
          </div>
        ) : null}
        <form
          role="search"
          className="mt-2 flex flex-wrap items-end gap-x-4 gap-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            go({ q });
          }}
        >
          <div className="min-w-52 flex-1 sm:max-w-md">
            <label htmlFor="lib-q" className="a-label">
              Buscar
            </label>
            <input id="lib-q" type="search" className="a-input" placeholder="Archivo o texto alternativo" value={q} onChange={(event) => setQ(event.target.value)} />
          </div>
          <CheckField label="Sin usar" checked={unused} onChange={(value) => go({ unused: value })} />
          <p role="status" className="muted inline-flex min-h-10 items-center self-end">
            {pending ? "Actualizando" : plural(total, "foto", "fotos")}
          </p>
        </form>
        {items.length === 0 ? (
          <Empty message={q || unused ? "Ninguna foto coincide con esta búsqueda." : "La biblioteca está vacía. Suba las primeras fotos arriba."} />
        ) : (
          <ul className="mt-4 grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(11rem,1fr))]" aria-busy={pending}>
            {items.map((asset) => (
              <LibraryTile key={asset.id} asset={asset} onChanged={refresh} />
            ))}
          </ul>
        )}
        <Pager page={page} pageSize={pageSize} total={total} hrefFor={(target) => href({ page: target })} />
      </section>
    </>
  );
}
