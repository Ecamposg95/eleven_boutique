"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { AdminApiError, api, errorText } from "@/lib/admin/client";
import type { AdminSettings } from "@/lib/admin/types";
import { checkWhatsapp, whatsappPreview } from "@/lib/admin/whatsapp";
import { AssetField, GalleryField } from "./MediaPicker";
import { Notice, TextAreaField, TextField, useUnsavedWarning } from "./ui";

export function SettingsForm({ settings }: { settings: AdminSettings }) {
  const router = useRouter();
  const initial = {
    whatsapp_number: settings.whatsapp_number ?? "",
    whatsapp_premium_number: settings.whatsapp_premium_number ?? "",
    hero_asset_id: settings.hero_asset_id,
    hero_mobile_asset_id: settings.hero_mobile_asset_id,
    hero_gallery: settings.hero_gallery ?? [],
    hero_headline: settings.hero_headline ?? "",
    hero_subhead: settings.hero_subhead ?? "",
    intro: settings.intro ?? "",
    boutique_body: settings.boutique_body ?? "",
    contact_body: settings.contact_body ?? "",
  };
  const [saved, setSaved] = useState(initial);
  const [form, setForm] = useState(initial);
  const [heroUrl, setHeroUrl] = useState(settings.hero_image_url);
  const [mobileUrl, setMobileUrl] = useState(settings.hero_mobile_image_url);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const dirty = JSON.stringify(form) !== JSON.stringify(saved);
  useUnsavedWarning(dirty);

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setMessage(null);
  };

  const whatsapp = checkWhatsapp(form.whatsapp_number);
  const premium = checkWhatsapp(form.whatsapp_premium_number);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!whatsapp.ok || !premium.ok) {
      setErrors({
        ...(whatsapp.ok ? {} : { whatsapp_number: whatsapp.message }),
        ...(premium.ok ? {} : { whatsapp_premium_number: premium.message }),
      });
      setFormError("Revise los campos marcados.");
      return;
    }
    setErrors({});
    setBusy(true);
    setFormError(null);
    setMessage(null);
    const body = {
      whatsapp_number: whatsapp.digits || null,
      whatsapp_premium_number: premium.digits || null,
      hero_asset_id: form.hero_asset_id,
      hero_mobile_asset_id: form.hero_mobile_asset_id,
      hero_gallery_asset_ids: form.hero_gallery.map((slide) => slide.asset_id),
      hero_headline: form.hero_headline.trim() || null,
      hero_subhead: form.hero_subhead.trim() || null,
      intro: form.intro.trim() || null,
      boutique_body: form.boutique_body.trim() || null,
      contact_body: form.contact_body.trim() || null,
    };
    try {
      await api("/settings", { method: "PATCH", json: body });
      const next = { ...form, whatsapp_number: whatsapp.digits, whatsapp_premium_number: premium.digits };
      setForm(next);
      setSaved(next);
      setMessage("Cambios guardados. El sitio público los muestra en menos de un minuto.");
      router.refresh();
    } catch (cause) {
      if (cause instanceof AdminApiError) setErrors(cause.fields);
      setFormError(errorText(cause));
    } finally {
      setBusy(false);
    }
  };

  const liveError = errors.whatsapp_number ?? (form.whatsapp_number && !whatsapp.ok ? whatsapp.message : null);
  const premiumError =
    errors.whatsapp_premium_number ?? (form.whatsapp_premium_number && !premium.ok ? premium.message : null);

  return (
    <form onSubmit={submit} noValidate className="max-w-4xl">
      <section aria-labelledby="wa-t" className="a-section">
        <h2 id="wa-t" className="a-h2">
          WhatsApp
        </h2>
        <TextField
          className="mt-2 max-w-sm"
          label="Línea Ventas: todas las piezas"
          type="tel"
          inputMode="tel"
          autoComplete="off"
          placeholder="52 55 1234 5678"
          value={form.whatsapp_number}
          onChange={(value) => set("whatsapp_number", value)}
          error={liveError}
          hint={whatsapp.ok && whatsapp.hint ? whatsapp.hint : "Con lada de país, sin ceros iniciales. Si lo deja vacío, el botón de consulta no aparece."}
        />
        <TextField
          className="mt-4 max-w-sm"
          label="Línea Boutique: marcas premium"
          type="tel"
          inputMode="tel"
          autoComplete="off"
          placeholder="52 55 1234 5678"
          value={form.whatsapp_premium_number}
          onChange={(value) => set("whatsapp_premium_number", value)}
          error={premiumError}
          hint={
            premium.ok && premium.hint
              ? premium.hint
              : "Atiende las piezas de las marcas marcadas como premium. Si lo deja vacío, esas piezas usan la línea Ventas."
          }
        />
        {whatsapp.ok && whatsapp.digits ? (
          <div className="a-notice mt-3 max-w-2xl">
            <p className="font-medium">Así queda el enlace de cada pieza</p>
            <p data-testid="wa-preview" className="muted mt-1 break-all">
              {whatsappPreview(whatsapp.digits)}
            </p>
          </div>
        ) : null}
      </section>

      <section aria-labelledby="hero-t" className="a-section">
        <h2 id="hero-t" className="a-h2">
          Imagen de portada
        </h2>
        <div className="mt-2 grid gap-6 md:grid-cols-2">
          <AssetField
            label="Portada en computadora"
            url={heroUrl}
            assetId={form.hero_asset_id}
            ratio="4 / 5"
            hint="Vertical 4:5, ideal 1920 × 2400 px. Se monta sobre el nombre gigante y se ve en blanco y negro."
            onChange={(asset) => {
              set("hero_asset_id", asset?.id ?? null);
              setHeroUrl(asset?.url ?? null);
            }}
          />
          <AssetField
            label="Portada en teléfono"
            url={mobileUrl}
            assetId={form.hero_mobile_asset_id}
            ratio="9 / 16"
            hint="Opcional: la portada usa la misma foto vertical en teléfono. Puede dejarlo vacío."
            onChange={(asset) => {
              set("hero_mobile_asset_id", asset?.id ?? null);
              setMobileUrl(asset?.url ?? null);
            }}
          />
        </div>
        <div className="mt-6">
          <GalleryField
            label="Más fotos de portada (se turnan)"
            slides={form.hero_gallery}
            max={8}
            hint="Se muestran después de la principal, una a la vez con fundido lento. Mismo formato: vertical 4:5, ideal 1920 × 2400 px."
            onChange={(slides) => set("hero_gallery", slides)}
          />
        </div>
      </section>

      <section aria-labelledby="text-t" className="a-section">
        <h2 id="text-t" className="a-h2">
          Textos
        </h2>
        <div className="mt-2 space-y-4">
          <TextField label="Titular de portada" value={form.hero_headline} onChange={(value) => set("hero_headline", value)} error={errors.hero_headline} />
          <TextField label="Subtítulo de portada" value={form.hero_subhead} onChange={(value) => set("hero_subhead", value)} error={errors.hero_subhead} />
          <TextAreaField label="Presentación en la portada" rows={3} value={form.intro} onChange={(value) => set("intro", value)} error={errors.intro} />
          <TextAreaField label="Texto de La boutique" rows={6} value={form.boutique_body} onChange={(value) => set("boutique_body", value)} error={errors.boutique_body} hint="Separe los párrafos con una línea en blanco." />
          <TextAreaField label="Texto de Contacto" rows={4} value={form.contact_body} onChange={(value) => set("contact_body", value)} error={errors.contact_body} />
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
  );
}
