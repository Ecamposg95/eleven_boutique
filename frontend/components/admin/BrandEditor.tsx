"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { AdminApiError, api, errorText } from "@/lib/admin/client";
import type { Brand, Status } from "@/lib/admin/types";
import { brandHref } from "@/lib/url";
import { AssetField } from "./MediaPicker";
import { CheckField, Notice, PageHead, SelectField, StatusLabel, TextAreaField, TextField, useUnsavedWarning } from "./ui";

type Values = {
  name: string;
  slug: string;
  description: string;
  display_order: string;
  is_featured: boolean;
  validation_status: Brand["validation_status"];
  aliases: string[];
  logo_asset_id: string | null;
  editorial_asset_id: string | null;
};

export function BrandEditor({ brand }: { brand: Brand }) {
  const router = useRouter();
  const initial: Values = {
    name: brand.name,
    slug: brand.slug,
    description: brand.description ?? "",
    display_order: String(brand.display_order ?? 0),
    is_featured: brand.is_featured,
    validation_status: brand.validation_status,
    aliases: brand.aliases,
    logo_asset_id: brand.logo_asset_id,
    editorial_asset_id: brand.editorial_asset_id,
  };
  const [saved, setSaved] = useState(initial);
  const [form, setForm] = useState(initial);
  const [logoUrl, setLogoUrl] = useState(brand.logo_url);
  const [editorialUrl, setEditorialUrl] = useState(brand.editorial_image_url);
  const [status, setStatus] = useState<Status>(brand.status);
  const [alias, setAlias] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const dirty = JSON.stringify(form) !== JSON.stringify(saved);
  useUnsavedWarning(dirty);

  const set = <K extends keyof Values>(key: K, value: Values[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setMessage(null);
  };

  const payload = () => ({
    name: form.name.trim(),
    slug: form.slug.trim(),
    description: form.description.trim() || null,
    display_order: Number(form.display_order) || 0,
    is_featured: form.is_featured,
    validation_status: form.validation_status,
    aliases: form.aliases,
    logo_asset_id: form.logo_asset_id,
    editorial_asset_id: form.editorial_asset_id,
  });

  const validate = () => {
    const next: Record<string, string> = {};
    if (!form.name.trim()) next.name = "Escriba el nombre.";
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(form.slug.trim())) next.slug = "Use minúsculas, números y guiones, sin espacios.";
    if (form.display_order && !/^-?\d+$/.test(form.display_order)) next.display_order = "Use un número entero.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const send = async (extra: Partial<{ status: Status }>, done: string) => {
    if (!validate()) {
      setFormError("Revise los campos marcados.");
      return;
    }
    setBusy(true);
    setFormError(null);
    setMessage(null);
    try {
      const updated = await api<Brand>(`/brands/${brand.id}`, { method: "PATCH", json: { ...payload(), ...extra } });
      // Al cambiar el slug el servidor agrega el anterior como alias.
      const next = { ...form, aliases: updated?.aliases ?? form.aliases };
      setForm(next);
      setSaved(next);
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

  const addAlias = () => {
    const clean = alias.trim();
    if (!clean) return;
    if (!form.aliases.some((item) => item.toLowerCase() === clean.toLowerCase())) set("aliases", [...form.aliases, clean]);
    setAlias("");
  };

  return (
    <>
      <PageHead title={saved.name || "Marca"} back={{ href: "/admin/marcas", label: "Volver a marcas" }} />
      <div className="grid gap-x-8 gap-y-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <section aria-labelledby="pub-t" className="a-panel self-start xl:col-start-2">
          <h2 id="pub-t" className="a-h2">
            Publicación
          </h2>
          <p className="mt-2">
            <StatusLabel status={status} />
          </p>
          {brand.kind === "classification" ? (
            <p className="mt-2">«Sin marca» es una clasificación interna. No aparece como marca en el sitio.</p>
          ) : (
            <>
              <div className="mt-3 flex flex-wrap gap-2">
                {status !== "published" ? (
                  <button type="button" className="a-btn a-btn-primary" disabled={busy} onClick={() => void send({ status: "published" }, "Marca publicada.")}>
                    Publicar
                  </button>
                ) : (
                  <button type="button" className="a-btn" disabled={busy} onClick={() => void send({ status: "draft" }, "Marca despublicada.")}>
                    Despublicar
                  </button>
                )}
              </div>
              {status === "published" ? (
                <p className="mt-3">
                  <a href={brandHref(saved.slug)} target="_blank" rel="noreferrer" className="link">
                    Ver en el sitio público
                  </a>
                </p>
              ) : null}
            </>
          )}
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
            <TextField label="Nombre" value={form.name} onChange={(value) => set("name", value)} error={errors.name} required />
            <TextField label="Dirección web (slug)" value={form.slug} onChange={(value) => set("slug", value)} error={errors.slug} hint="Si la cambia, la anterior se conserva como alias y sus enlaces siguen funcionando." />
            <TextAreaField label="Descripción" rows={4} value={form.description} onChange={(value) => set("description", value)} error={errors.description} className="md:col-span-2" />
            <TextField label="Orden de aparición" inputMode="numeric" value={form.display_order} onChange={(value) => set("display_order", value)} error={errors.display_order} />
            <SelectField label="Validación" value={form.validation_status} onChange={(value) => set("validation_status", value as Values["validation_status"])} hint="Indica si el nombre ya se revisó contra la fuente.">
              <option value="pending">Pendiente</option>
              <option value="approved">Validada</option>
            </SelectField>
            <CheckField label="Marca destacada" checked={form.is_featured} onChange={(value) => set("is_featured", value)} />
          </div>

          <section aria-labelledby="alias-t" className="a-section">
            <h2 id="alias-t" className="a-h2">
              Alias
            </h2>
            <p className="a-hint max-w-prose">Otras formas de escribir la marca. Se usan en la búsqueda y para reconocerla al importar.</p>
            {form.aliases.length ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {form.aliases.map((item) => (
                  <li key={item} className="flex items-center gap-2 border border-bronze py-0.5 pl-2 pr-0.5">
                    {item}
                    <button type="button" className="a-btn a-btn-quiet a-btn-small border-0" aria-label={`Quitar alias ${item}`} onClick={() => set("aliases", form.aliases.filter((other) => other !== item))}>
                      Quitar
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-2 flex flex-wrap items-end gap-2">
              <div className="min-w-52 flex-1 sm:max-w-xs">
                <label htmlFor="alias-new" className="a-label">
                  Nuevo alias
                </label>
                <input
                  id="alias-new"
                  className="a-input"
                  value={alias}
                  onChange={(event) => setAlias(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addAlias();
                    }
                  }}
                />
              </div>
              <button type="button" className="a-btn a-btn-quiet" onClick={addAlias}>
                Agregar alias
              </button>
            </div>
          </section>

          <section aria-labelledby="img-t" className="a-section">
            <h2 id="img-t" className="a-h2">
              Imágenes
            </h2>
            <div className="mt-2 grid gap-6 md:grid-cols-2">
              <AssetField
                label="Logotipo"
                url={logoUrl}
                assetId={form.logo_asset_id}
                ratio="2 / 1"
                contain
                hint="Los logotipos se muestran sobre fondo oscuro: hace falta una versión clara, con fondo transparente. Un logotipo negro no se verá."
                onChange={(asset) => {
                  set("logo_asset_id", asset?.id ?? null);
                  setLogoUrl(asset?.url ?? null);
                }}
              />
              <AssetField
                label="Imagen editorial"
                url={editorialUrl}
                assetId={form.editorial_asset_id}
                onChange={(asset) => {
                  set("editorial_asset_id", asset?.id ?? null);
                  setEditorialUrl(asset?.url ?? null);
                }}
              />
            </div>
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
    </>
  );
}
