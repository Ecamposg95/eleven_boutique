"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { AdminApiError, api, errorText } from "@/lib/admin/client";
import { moveItem, withPositions } from "@/lib/admin/reorder";
import type { AdminBlock, AdminCollection, BlockImage, ProductRef, Status } from "@/lib/admin/types";
import { MediaPicker, AssetField } from "./MediaPicker";
import { ProductSearch } from "./ProductSearch";
import { Notice, PageHead, SelectField, StatusLabel, TextAreaField, TextField, Thumb, useConfirm, useDragReorder, useUnsavedWarning } from "./ui";

/** Lista ordenada de productos: arrastrar, botones de mover y búsqueda para agregar. */
function OrderedProducts({ products, onChange }: { products: ProductRef[]; onChange: (next: ProductRef[]) => void }) {
  const [announce, setAnnounce] = useState("");
  const move = (from: number, to: number) => {
    if (to < 0 || to >= products.length) return;
    onChange(moveItem(products, from, to));
    setAnnounce(`Producto movido a la posición ${to + 1} de ${products.length}.`);
  };
  const { handleProps, targetProps } = useDragReorder(move);
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0">
        <p className="sr-only" role="status">
          {announce}
        </p>
        {products.length === 0 ? (
          <p className="border border-dashed border-bronze p-4">Sin productos. Búsquelos para agregarlos.</p>
        ) : (
          <ol>
            {products.map((product, index) => (
              <li key={product.id} data-picked={product.id} className="flex items-center gap-3 border-b border-bronze/30 py-1.5" {...targetProps(index)}>
                <span className="a-drag flex shrink-0 items-center gap-2" {...handleProps(index)}>
                  <span className="muted w-6 text-right">{index + 1}</span>
                  <Thumb src={product.primary_image_url} size="2.5rem" sizes="64px" emptyLabel="" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="a-piece block truncate">{product.name}</span>
                  <span className="muted block truncate">{[product.brand_name, product.sku].filter(Boolean).join(", ")}</span>
                </span>
                <span className="flex shrink-0 flex-wrap justify-end gap-1">
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-disabled={index === 0} aria-label={`Mover antes ${product.name}`} onClick={() => move(index, index - 1)}>
                    Antes
                  </button>
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-disabled={index === products.length - 1} aria-label={`Mover después ${product.name}`} onClick={() => move(index, index + 1)}>
                    Después
                  </button>
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-label={`Quitar ${product.name}`} onClick={() => onChange(products.filter((other) => other.id !== product.id))}>
                    Quitar
                  </button>
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
      <ProductSearch label="Agregar producto" excludeIds={products.map((item) => item.id)} onPick={(product) => onChange([...products, product])} />
    </div>
  );
}

type KeyedBlock = AdminBlock & { key: string };

function BlockEditor({ blocks, onChange }: { blocks: KeyedBlock[]; onChange: (next: KeyedBlock[]) => void }) {
  const [pickFor, setPickFor] = useState<string | "new" | null>(null);
  const [announce, setAnnounce] = useState("");
  const nextKey = useRef(0);
  const newKey = () => `n${nextKey.current++}`;

  const update = (key: string, change: Partial<AdminBlock>) =>
    onChange(blocks.map((block) => (block.key === key ? ({ ...block, ...change } as KeyedBlock) : block)));
  const move = (from: number, to: number) => {
    if (to < 0 || to >= blocks.length) return;
    onChange(withPositions(moveItem(blocks, from, to)));
    setAnnounce(`Bloque movido a la posición ${to + 1} de ${blocks.length}.`);
  };
  const { handleProps, targetProps } = useDragReorder(move);

  return (
    <div>
      <p className="sr-only" role="status">
        {announce}
      </p>
      {blocks.length === 0 ? <p className="border border-dashed border-bronze p-4">Sin bloques. Agregue un texto o una imagen.</p> : null}
      <ol className="space-y-3">
        {blocks.map((block, index) => (
          <li key={block.key} data-block={block.type} className="a-panel" {...targetProps(index)}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="a-drag font-medium" {...handleProps(index)}>
                {index + 1}. {block.type === "text" ? "Texto" : "Imagen"}
              </span>
              <span className="flex flex-wrap gap-1">
                <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-disabled={index === 0} aria-label={`Mover antes el bloque ${index + 1}`} onClick={() => move(index, index - 1)}>
                  Antes
                </button>
                <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-disabled={index === blocks.length - 1} aria-label={`Mover después el bloque ${index + 1}`} onClick={() => move(index, index + 1)}>
                  Después
                </button>
                <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-label={`Quitar el bloque ${index + 1}`} onClick={() => onChange(withPositions(blocks.filter((other) => other.key !== block.key)))}>
                  Quitar
                </button>
              </span>
            </div>
            {block.type === "text" ? (
              <div className="mt-3 space-y-3">
                <TextField label="Subtítulo (opcional)" value={block.heading ?? ""} onChange={(value) => update(block.key, { heading: value || null })} />
                <TextAreaField label="Texto" rows={4} value={block.body} onChange={(value) => update(block.key, { body: value })} />
              </div>
            ) : (
              <div className="mt-3 flex flex-wrap items-start gap-4">
                <Thumb src={block.url} size="9rem" ratio="4 / 3" sizes="200px" emptyLabel="Sin imagen" />
                <div className="min-w-52 flex-1 space-y-3">
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={() => setPickFor(block.key)}>
                    Cambiar imagen
                  </button>
                  <TextField label="Texto alternativo" value={block.alt} onChange={(value) => update(block.key, { alt: value })} />
                  <SelectField label="Disposición" value={block.layout} onChange={(value) => update(block.key, { layout: value as BlockImage["layout"] })}>
                    <option value="full">Ancho completo</option>
                    <option value="left">A la izquierda</option>
                    <option value="right">A la derecha</option>
                  </SelectField>
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="a-btn a-btn-quiet"
          onClick={() => onChange([...blocks, { key: newKey(), type: "text", position: blocks.length, heading: null, body: "" }])}
        >
          Agregar texto
        </button>
        <button type="button" className="a-btn a-btn-quiet" onClick={() => setPickFor("new")}>
          Agregar imagen
        </button>
      </div>
      <MediaPicker
        open={pickFor !== null}
        title="Elegir imagen del bloque"
        onClose={() => setPickFor(null)}
        onPick={(assets) => {
          const asset = assets[0];
          if (!asset) return;
          if (pickFor === "new") {
            onChange([...blocks, { key: newKey(), type: "image", position: blocks.length, url: asset.url, alt: asset.alt, layout: "full" }]);
          } else if (pickFor) {
            update(pickFor, { url: asset.url } as Partial<AdminBlock>);
          }
        }}
      />
    </div>
  );
}

export function ContentEditor({
  kind,
  item,
  products: initialProducts,
  blocks: initialBlocks,
}: {
  kind: "collection" | "lookbook";
  item: AdminCollection;
  products: ProductRef[];
  blocks?: AdminBlock[];
}) {
  const router = useRouter();
  const isLookbook = kind === "lookbook";
  const base = isLookbook ? "/lookbooks" : "/collections";
  const listPath = isLookbook ? "/admin/lookbooks" : "/admin/colecciones";
  const publicPath = isLookbook ? "/lookbooks" : "/colecciones";
  const noun = isLookbook ? "Lookbook" : "Colección";

  const toValues = () => ({
    title: item.title,
    slug: item.slug,
    summary: item.summary ?? "",
    display_order: String(item.display_order ?? 0),
    cover_asset_id: item.cover_asset_id,
    products: initialProducts,
    blocks: (initialBlocks ?? []).map((block, index): KeyedBlock => ({ ...block, key: `s${index}` })),
  });
  const [saved, setSaved] = useState(toValues);
  const [form, setForm] = useState(saved);
  const [coverUrl, setCoverUrl] = useState(item.cover_url ?? null);
  const [status, setStatus] = useState<Status>(item.status);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, dialog] = useConfirm();

  const dirty = JSON.stringify(form) !== JSON.stringify(saved);
  useUnsavedWarning(dirty);

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setMessage(null);
  };

  const send = async (extra: { status?: Status }, done: string) => {
    const next: Record<string, string> = {};
    if (!form.title.trim()) next.title = "Escriba el título.";
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(form.slug.trim())) next.slug = "Use minúsculas, números y guiones, sin espacios.";
    if (form.display_order && !/^-?\d+$/.test(form.display_order)) next.display_order = "Use un número entero.";
    const emptyText = form.blocks.some((block) => block.type === "text" && !block.body.trim());
    if (emptyText) next.blocks = "Hay bloques de texto vacíos. Escríbalos o quítelos.";
    setErrors(next);
    if (Object.keys(next).length) {
      setFormError("Revise los campos marcados.");
      return;
    }
    setBusy(true);
    setFormError(null);
    setMessage(null);
    try {
      const body = {
        title: form.title.trim(),
        slug: form.slug.trim(),
        summary: form.summary.trim() || null,
        display_order: Number(form.display_order) || 0,
        cover_asset_id: form.cover_asset_id,
        product_ids: form.products.map((product) => product.id),
        ...(isLookbook
          ? {
              blocks: form.blocks.map((keyed, position) => {
                const block: Partial<KeyedBlock> = { ...keyed, position };
                delete block.key;
                return block;
              }),
            }
          : {}),
        ...extra,
      };
      await api(`${base}/${item.id}`, { method: "PATCH", json: body });
      setSaved(form);
      if (extra.status) setStatus(extra.status);
      setMessage(done);
      router.refresh();
    } catch (cause) {
      if (cause instanceof AdminApiError) setErrors(cause.fields);
      setFormError(errorText(cause));
    } finally {
      setBusy(false);
    }
  };

  const archive = async () => {
    const accepted = await confirm({
      title: `¿Archivar ${isLookbook ? "este lookbook" : "esta colección"}?`,
      body: <p>Deja de verse en el sitio. No se borra.</p>,
      confirmLabel: "Archivar",
    });
    if (!accepted) return;
    try {
      await api(`${base}/${item.id}`, { method: "DELETE" });
      setStatus("archived");
      setMessage(`${noun} archivado.`.replace("Colección archivado", "Colección archivada"));
      router.refresh();
    } catch (cause) {
      setFormError(errorText(cause));
    }
  };

  return (
    <>
      <PageHead title={saved.title || noun} back={{ href: listPath, label: isLookbook ? "Volver a lookbooks" : "Volver a colecciones" }} />
      <div className="grid gap-x-8 gap-y-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <section aria-labelledby="pub-t" className="a-panel self-start xl:col-start-2">
          <h2 id="pub-t" className="a-h2">
            Publicación
          </h2>
          <p className="mt-2">
            <StatusLabel status={status} />
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {status !== "published" ? (
              <button type="button" className="a-btn a-btn-primary" disabled={busy} onClick={() => void send({ status: "published" }, "Publicado.")}>
                Publicar
              </button>
            ) : (
              <button type="button" className="a-btn" disabled={busy} onClick={() => void send({ status: "draft" }, "Despublicado.")}>
                Despublicar
              </button>
            )}
            {status !== "archived" ? (
              <button type="button" className="a-btn a-btn-quiet" disabled={busy} onClick={() => void archive()}>
                Archivar
              </button>
            ) : null}
          </div>
          {status === "published" ? (
            <p className="mt-3">
              <a href={`${publicPath}/${encodeURIComponent(saved.slug)}`} target="_blank" rel="noreferrer" className="link">
                Ver en el sitio público
              </a>
            </p>
          ) : null}
        </section>

        <form
          noValidate
          className="min-w-0 xl:col-start-1 xl:row-start-1"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            void send({}, "Cambios guardados.");
          }}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <TextField label="Título" value={form.title} onChange={(value) => set("title", value)} error={errors.title} required />
            <TextField label="Dirección web (slug)" value={form.slug} onChange={(value) => set("slug", value)} error={errors.slug} />
            <TextAreaField label="Resumen" rows={3} value={form.summary} onChange={(value) => set("summary", value)} error={errors.summary} className="md:col-span-2" />
            <TextField label="Orden de aparición" inputMode="numeric" value={form.display_order} onChange={(value) => set("display_order", value)} error={errors.display_order} />
            <AssetField
              label="Portada"
              url={coverUrl}
              assetId={form.cover_asset_id}
              onChange={(asset) => {
                set("cover_asset_id", asset?.id ?? null);
                setCoverUrl(asset?.url ?? null);
              }}
            />
          </div>

          {isLookbook ? (
            <section aria-labelledby="bloques-t" className="a-section">
              <h2 id="bloques-t" className="a-h2 mb-2">
                Bloques
              </h2>
              {errors.blocks ? <p className="a-error mb-2">{errors.blocks}</p> : null}
              <BlockEditor blocks={form.blocks} onChange={(next) => set("blocks", next)} />
            </section>
          ) : null}

          <section aria-labelledby="prod-t" className="a-section">
            <h2 id="prod-t" className="a-h2 mb-2">
              Productos
            </h2>
            <OrderedProducts products={form.products} onChange={(next) => set("products", next)} />
          </section>

          <div className={dirty || message ? "a-bar" : "a-bar a-bar-rest"}>
            <button type="submit" className="a-btn a-btn-primary" disabled={busy || !dirty}>
              Guardar cambios
            </button>
            {dirty ? <span>Hay cambios sin guardar.</span> : null}
            {message ? <span role="status">{message}</span> : null}
          </div>
          {formError ? (
            <div className="mt-2">
              <Notice kind="error">{formError}</Notice>
            </div>
          ) : null}
        </form>
      </div>
      {dialog}
    </>
  );
}
