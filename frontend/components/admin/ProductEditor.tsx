"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { AdminApiError, api, errorText, uploadMedia } from "@/lib/admin/client";
import { formatDateTime } from "@/lib/admin/format";
import { mediaOrderPayload, moveItem, setPrimary } from "@/lib/admin/reorder";
import { missingForPublish } from "@/lib/admin/rules";
import type { AdminCategory, Brand, MediaAsset, Product, ProductMediaItem, Status } from "@/lib/admin/types";
import { createUploadQueue, validateImageFile } from "@/lib/admin/upload-queue";
import { productHref } from "@/lib/url";
import { MediaPicker } from "./MediaPicker";
import { CheckField, Notice, PageHead, SelectField, StatusLabel, TextAreaField, TextField, Thumb, useConfirm, useDragReorder, useUnsavedWarning } from "./ui";

type FormValues = {
  name: string;
  slug: string;
  brand_id: string;
  category_id: string;
  is_featured: boolean;
  display_order: string;
  commercial_added_at: string;
  seo_title: string;
  seo_description: string;
  internal_notes: string;
};

function toForm(product: Product): FormValues {
  return {
    name: product.name,
    slug: product.slug,
    brand_id: product.brand_id,
    category_id: product.category_id,
    is_featured: product.is_featured,
    display_order: String(product.display_order ?? 0),
    commercial_added_at: product.commercial_added_at?.slice(0, 10) ?? "",
    seo_title: product.seo_title ?? "",
    seo_description: product.seo_description ?? "",
    internal_notes: product.internal_notes ?? "",
  };
}

function PhotoManager({
  product,
  media,
  onMedia,
}: {
  product: Product;
  media: ProductMediaItem[];
  onMedia: (next: ProductMediaItem[]) => void;
}) {
  const router = useRouter();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announce, setAnnounce] = useState("");
  const [uploading, setUploading] = useState<string | null>(null);
  const [confirm, dialog] = useConfirm();

  const persist = async (next: ProductMediaItem[], message: string) => {
    const previous = media;
    onMedia(next);
    setError(null);
    try {
      await api(`/products/${product.id}/media`, { method: "PATCH", json: mediaOrderPayload(next) });
      setAnnounce(message);
    } catch (cause) {
      onMedia(previous);
      setError(errorText(cause));
    }
  };

  const move = (from: number, to: number) => {
    if (to < 0 || to >= media.length) return;
    void persist(moveItem(media, from, to), `Foto movida a la posición ${to + 1} de ${media.length}.`);
  };
  const { handleProps, targetProps } = useDragReorder(move);

  const attach = async (assets: MediaAsset[]) => {
    setError(null);
    const problems: string[] = [];
    for (const asset of assets) {
      try {
        await api(`/products/${product.id}/media`, { json: { media_asset_id: asset.id } });
      } catch (cause) {
        problems.push(`${asset.filename ?? "Foto"}: ${errorText(cause)}`);
      }
    }
    if (problems.length) setError(problems.join(" "));
    try {
      const fresh = await api<Product>(`/products/${product.id}`);
      onMedia(fresh.media);
      setAnnounce("Fotos agregadas.");
    } catch (cause) {
      setError(errorText(cause));
    }
    router.refresh();
  };

  const uploadFiles = async (files: File[]) => {
    setUploading(`Subiendo ${files.length}`);
    const queue = createUploadQueue<File, MediaAsset>({
      worker: uploadMedia,
      validate: validateImageFile,
      errorMessage: errorText,
    });
    queue.add(files);
    await queue.idle();
    const items = queue.snapshot();
    setUploading(null);
    const assets = items.flatMap((item) => (item.result ? [item.result] : []));
    if (assets.length) await attach(assets);
    const failed = items.filter((item) => item.status === "error");
    if (failed.length) setError(failed.map((item) => `${item.file.name}: ${item.error}`).join(" "));
  };

  const remove = async (item: ProductMediaItem) => {
    const accepted = await confirm({
      title: "¿Quitar esta foto del producto?",
      body: <p>El archivo sigue en la biblioteca.</p>,
      confirmLabel: "Quitar foto",
    });
    if (!accepted) return;
    setError(null);
    try {
      await api(`/products/${product.id}/media/${item.id}`, { method: "DELETE" });
      onMedia(media.filter((other) => other.id !== item.id));
      setAnnounce("Foto quitada.");
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof AdminApiError && cause.status === 409
          ? "Un producto publicado necesita al menos una foto. Agregue otra o despublique el producto antes de quitarla."
          : errorText(cause),
      );
    }
  };

  const saveAlt = async (item: ProductMediaItem, input: HTMLInputElement) => {
    const alt = input.value;
    if (alt === item.alt) return;
    try {
      const fresh = await api<Product>(`/products/${product.id}/media/${item.id}`, { method: "PATCH", json: { alt } });
      onMedia(fresh.media);
      setAnnounce("Texto alternativo guardado.");
    } catch (cause) {
      input.value = item.alt;
      setError(errorText(cause));
    }
  };

  const primaryId = media.find((item) => item.is_primary)?.id ?? media[0]?.id;

  return (
    <section aria-labelledby="fotos-t" className="a-section">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="fotos-t" className="a-h2">
          Fotos
        </h2>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="a-btn a-btn-small" onClick={() => setPickerOpen(true)}>
            Elegir de la biblioteca
          </button>
          <label className="a-btn a-btn-small cursor-pointer focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-bronze">
            Subir fotos
            <input
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={(event) => {
                const files = [...(event.target.files ?? [])];
                event.target.value = "";
                if (files.length) void uploadFiles(files);
              }}
            />
          </label>
        </div>
      </div>
      <p className="sr-only" role="status">
        {announce}
      </p>
      {uploading ? (
        <p role="status" className="muted mt-2">
          {uploading}
        </p>
      ) : null}
      {error ? (
        <div className="mt-2">
          <Notice kind="error">{error}</Notice>
        </div>
      ) : null}
      {product.photo_refs?.length ? (
        <p className="a-hint">Referencia de foto en el archivo importado: {product.photo_refs.join(", ")}</p>
      ) : null}
      {media.length === 0 ? (
        <p className="mt-3 border border-dashed border-bronze p-5">
          Este producto no tiene fotos. Agregue al menos una para poder publicarlo.
        </p>
      ) : (
        <>
          <p className="a-hint">Arrastre una foto para cambiar el orden, o use los botones de mover. La principal es la que se ve en listados.</p>
          <ol className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] gap-4">
            {media.map((item, index) => (
              <li key={item.id} data-photo={item.id} {...targetProps(index)}>
                <div className="a-drag relative aspect-[4/5] bg-charcoal" {...handleProps(index)}>
                  <Thumb src={item.url} alt={item.alt} size="100%" sizes="240px" />
                  {item.id === primaryId ? (
                    <span className="absolute left-0 top-0 bg-ivory px-2 py-0.5 text-ink">Principal</span>
                  ) : null}
                </div>
                <p className="muted mt-1">
                  Posición {index + 1} de {media.length}
                </p>
                <div className="mt-1 grid grid-cols-2 gap-1">
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-disabled={index === 0} aria-label={`Mover antes la foto ${index + 1}`} onClick={() => move(index, index - 1)}>
                    Antes
                  </button>
                  <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-disabled={index === media.length - 1} aria-label={`Mover después la foto ${index + 1}`} onClick={() => move(index, index + 1)}>
                    Después
                  </button>
                  {item.id !== primaryId ? (
                    <button type="button" className="a-btn a-btn-quiet a-btn-small col-span-2" onClick={() => void persist(setPrimary(media, item.id), `Foto ${index + 1} marcada como principal.`)}>
                      Hacer principal
                    </button>
                  ) : null}
                  <button type="button" className="a-btn a-btn-quiet a-btn-small col-span-2" onClick={() => void remove(item)}>
                    Quitar
                  </button>
                </div>
                <div className="mt-2">
                  <label htmlFor={`alt-${item.id}`} className="a-label">
                    Texto alternativo
                  </label>
                  <input
                    id={`alt-${item.id}`}
                    key={item.alt}
                    className="a-input"
                    defaultValue={item.alt}
                    onBlur={(event) => void saveAlt(item, event.target)}
                  />
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
      <MediaPicker open={pickerOpen} multiple title="Agregar fotos al producto" onClose={() => setPickerOpen(false)} onPick={(assets) => void attach(assets)} />
      {dialog}
    </section>
  );
}

export function ProductEditor({
  product,
  brands,
  categories,
}: {
  product: Product;
  brands: Pick<Brand, "id" | "name">[] | null;
  categories: Pick<AdminCategory, "id" | "name">[] | null;
}) {
  const router = useRouter();
  const [saved, setSaved] = useState(() => toForm(product));
  const [form, setForm] = useState(saved);
  const [status, setStatus] = useState<Status>(product.status);
  const [media, setMedia] = useState(product.media);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, dialog] = useConfirm();
  const formRef = useRef<HTMLFormElement>(null);

  const dirty = JSON.stringify(form) !== JSON.stringify(saved);
  useUnsavedWarning(dirty);

  const set = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setMessage(null);
  };

  const payload = () => ({
    name: form.name.trim(),
    slug: form.slug.trim(),
    // El servidor no admite null aquí; validate() exige ambos.
    brand_id: form.brand_id,
    category_id: form.category_id,
    is_featured: form.is_featured,
    display_order: Number(form.display_order) || 0,
    // A mediodía UTC: la fecha elegida no cambia al convertirla a la zona horaria de México.
    commercial_added_at: form.commercial_added_at ? `${form.commercial_added_at}T12:00:00Z` : null,
    seo_title: form.seo_title.trim() || null,
    seo_description: form.seo_description.trim() || null,
    internal_notes: form.internal_notes.trim() || null,
  });

  const validate = () => {
    const next: Record<string, string> = {};
    if (!form.name.trim()) next.name = "Escriba el nombre.";
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(form.slug.trim())) next.slug = "Use minúsculas, números y guiones, sin espacios.";
    if (!form.brand_id) next.brand_id = "Elija una marca o «Sin marca».";
    if (!form.category_id) next.category_id = "Elija una categoría.";
    if (form.display_order && !/^-?\d+$/.test(form.display_order)) next.display_order = "Use un número entero.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const save = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!validate()) {
      setFormError("Revise los campos marcados.");
      return false;
    }
    setBusy(true);
    setFormError(null);
    setMessage(null);
    try {
      await api(`/products/${product.id}`, { method: "PATCH", json: payload() });
      setSaved(form);
      setMessage("Cambios guardados.");
      router.refresh();
      return true;
    } catch (cause) {
      if (cause instanceof AdminApiError) setErrors(cause.fields);
      setFormError(errorText(cause));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const changeStatus = async (next: Status, publishBrand = false): Promise<void> => {
    if (dirty && !validate()) {
      setFormError("Revise los campos marcados.");
      return;
    }
    setBusy(true);
    setFormError(null);
    setMessage(null);
    try {
      // Publicar guarda también lo escrito: lo que se publica es lo que se ve en pantalla.
      const body = { ...(dirty ? payload() : {}), status: next, ...(publishBrand ? { publish_brand: true } : {}) };
      await api(`/products/${product.id}`, { method: "PATCH", json: body });
      setSaved(form);
      setStatus(next);
      setMessage(next === "published" ? "Producto publicado." : next === "archived" ? "Producto archivado." : "Producto despublicado.");
      router.refresh();
    } catch (cause) {
      if (cause instanceof AdminApiError && cause.code === "brand_unpublished") {
        const name = brands?.find((brand) => brand.id === form.brand_id)?.name ?? product.brand.name;
        setBusy(false);
        const accepted = await confirm({
          title: `La marca ${name} no está publicada. ¿Publicar también la marca?`,
          body: <p>Sin la marca publicada, este producto no se puede publicar.</p>,
          confirmLabel: "Publicar marca y producto",
          cancelLabel: "Dejar en borrador",
        });
        if (accepted) return changeStatus(next, true);
        return;
      }
      setFormError(errorText(cause));
    } finally {
      setBusy(false);
    }
  };

  const missing = missingForPublish({ name: form.name, brand_id: form.brand_id || null, category_id: form.category_id || null, media });
  // «Sin marca» es una clasificación: su ficha vive en /piezas.
  const isBrand = product.brand.kind === "brand";
  const publicHref = productHref({ slug: saved.slug, brand: { slug: isBrand ? product.brand.slug : null, name: isBrand ? product.brand.name : null } });

  return (
    <>
      <PageHead title={saved.name || "Producto"} back={{ href: "/admin/productos", label: "Volver a productos" }} />
      <div className="grid gap-x-8 gap-y-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0 xl:col-start-2 xl:row-start-1">
          <section aria-labelledby="pub-t" className="a-panel xl:sticky xl:top-4">
            <h2 id="pub-t" className="a-h2">
              Publicación
            </h2>
            <p className="mt-2">
              <StatusLabel status={status} />
            </p>
            {product.published_at ? <p className="muted mt-1">Publicado por primera vez: {formatDateTime(product.published_at)}</p> : null}
            {status !== "published" && missing.length ? (
              <ul id="faltantes" className="mt-3 space-y-1">
                {missing.map((item) => (
                  <li key={item} className="font-medium text-sand">
                    {item}
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {status !== "published" ? (
                <button
                  type="button"
                  className="a-btn a-btn-primary"
                  aria-disabled={missing.length > 0 || busy}
                  aria-describedby={missing.length ? "faltantes" : undefined}
                  onClick={() => {
                    if (missing.length === 0 && !busy) void changeStatus("published");
                  }}
                >
                  Publicar
                </button>
              ) : (
                <button type="button" className="a-btn" disabled={busy} onClick={() => void changeStatus("draft")}>
                  Despublicar
                </button>
              )}
              {status !== "archived" ? (
                <button
                  type="button"
                  className="a-btn a-btn-quiet"
                  disabled={busy}
                  onClick={async () => {
                    const accepted = await confirm({
                      title: "¿Archivar este producto?",
                      body: <p>Deja de verse en el sitio. No se borra: se puede volver a publicar.</p>,
                      confirmLabel: "Archivar",
                    });
                    if (accepted) void changeStatus("archived");
                  }}
                >
                  Archivar
                </button>
              ) : null}
            </div>
            {status === "published" ? (
              <p className="mt-3">
                <a href={publicHref} target="_blank" rel="noreferrer" className="link">
                  Ver en el sitio público
                </a>
              </p>
            ) : null}
          </section>
        </div>

        <div className="min-w-0 xl:row-start-1">
          <form ref={formRef} onSubmit={save} noValidate aria-labelledby="datos-t" className="a-section">
            <h2 id="datos-t" className="a-h2">
              Datos
            </h2>
            {product.sku ? <p className="muted mt-1">SKU base: {product.sku}</p> : null}
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <TextField label="Nombre" value={form.name} onChange={(value) => set("name", value)} error={errors.name} required className="md:col-span-2" />
              <SelectField label="Marca" value={form.brand_id} onChange={(value) => set("brand_id", value)} error={errors.brand_id} disabled={!brands}
                hint={!brands ? "Este usuario no puede cambiar la marca." : undefined}>
                <option value="">Sin elegir</option>
                {(brands ?? [{ id: product.brand.id, name: product.brand.name }]).map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </SelectField>
              <SelectField label="Categoría" value={form.category_id} onChange={(value) => set("category_id", value)} error={errors.category_id}>
                <option value="">Sin elegir</option>
                {(categories ?? []).map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </SelectField>
              <TextField label="Dirección web (slug)" value={form.slug} onChange={(value) => set("slug", value)} error={errors.slug} hint="Cambiarla rompe los enlaces ya compartidos." />
              <TextField label="Orden de aparición" inputMode="numeric" value={form.display_order} onChange={(value) => set("display_order", value)} error={errors.display_order} hint="Los números menores aparecen primero." />
              <TextField label="Fecha de ingreso comercial" type="date" value={form.commercial_added_at} onChange={(value) => set("commercial_added_at", value)} error={errors.commercial_added_at} hint="Ordena la sección Novedades." />
              <CheckField label="Destacado en la portada" checked={form.is_featured} onChange={(value) => set("is_featured", value)} className="self-end" />
              <TextField label="Título para buscadores" value={form.seo_title} onChange={(value) => set("seo_title", value)} error={errors.seo_title} className="md:col-span-2" />
              <TextAreaField label="Descripción para buscadores" rows={2} value={form.seo_description} onChange={(value) => set("seo_description", value)} error={errors.seo_description} className="md:col-span-2" />
              <TextAreaField label="Notas internas" rows={3} value={form.internal_notes} onChange={(value) => set("internal_notes", value)} error={errors.internal_notes} hint="No se muestran en el sitio." className="md:col-span-2" />
            </div>
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

          <PhotoManager product={product} media={media} onMedia={setMedia} />

          <section aria-labelledby="var-t" className="a-section">
            <h2 id="var-t" className="a-h2">
              Variantes
            </h2>
            {product.variants.length === 0 ? (
              <p className="mt-2">Este producto no tiene variantes.</p>
            ) : (
              <>
                <p className="a-hint">Vienen del archivo importado. Para cambiarlas, actualice el archivo y vuelva a importar.</p>
                <div className="mt-2 overflow-x-auto">
                  <table className="a-table">
                    <thead>
                      <tr>
                        <th scope="col">SKU</th>
                        <th scope="col">Talla</th>
                        <th scope="col">Color</th>
                      </tr>
                    </thead>
                    <tbody>
                      {product.variants.map((variant) => (
                        <tr key={variant.id}>
                          <td className="break-all">{variant.sku}</td>
                          <td>{variant.size ?? ""}</td>
                          <td>{variant.color ?? ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
          <p className="mt-6">
            <Link href="/admin/productos" prefetch={false} className="link">
              Volver a productos
            </Link>
          </p>
        </div>
      </div>
      {dialog}
    </>
  );
}
