"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/admin/client";
import { CHECK_FIELDS, saveErrors, settingsBody, settingsForm } from "@/lib/admin/settings";
import type { AdminSettings } from "@/lib/admin/types";
import { checkWhatsapp, whatsappPreview } from "@/lib/admin/whatsapp";
import { AssetField, GalleryField } from "./MediaPicker";
import { Notice, TextAreaField, TextField, useUnsavedWarning } from "./ui";

export function SettingsForm({ settings }: { settings: AdminSettings }) {
  const router = useRouter();
  const initial = settingsForm(settings);
  const [saved, setSaved] = useState(initial);
  const [form, setForm] = useState(initial);
  const [heroUrl, setHeroUrl] = useState(settings.hero_image_url);
  const [mobileUrl, setMobileUrl] = useState(settings.hero_mobile_image_url);
  const [detailUrl, setDetailUrl] = useState(settings.detail_image_url);
  const [detailMobileUrl, setDetailMobileUrl] = useState(settings.detail_mobile_image_url);
  const [attentionUrl, setAttentionUrl] = useState(settings.attention_image_url);
  const [attentionMobileUrl, setAttentionMobileUrl] = useState(settings.attention_mobile_image_url);
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
      setFormError(CHECK_FIELDS);
      return;
    }
    setErrors({});
    setBusy(true);
    setFormError(null);
    setMessage(null);
    const body = settingsBody(form, { general: whatsapp.digits, premium: premium.digits });
    try {
      await api("/settings", { method: "PATCH", json: body });
      const next = { ...form, whatsapp_number: whatsapp.digits, whatsapp_premium_number: premium.digits };
      setForm(next);
      setSaved(next);
      setMessage("Cambios guardados. El sitio público los muestra en menos de un minuto.");
      router.refresh();
    } catch (cause) {
      const { fields, notice } = saveErrors(cause);
      setErrors(fields);
      setFormError(notice);
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
            ratio="16 / 9"
            hint="Horizontal 16:9, ideal 2880 × 1620 px. Se ve en pantallas horizontales, sobre el nombre gigante y en blanco y negro."
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
            hint="Vertical 9:16, ideal 1080 × 1920 px. Se ve en teléfonos y pantallas verticales. Si falta, se recorta la de computadora. Persona en el tercio de arriba: abajo va el nombre gigante."
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
            withMobile
            hint="Se muestran después de la principal, una a la vez con fundido lento. Cada una en horizontal 16:9 (2880 × 1620 px), con su versión de teléfono vertical 9:16 (1080 × 1920 px)."
            onChange={(slides) => set("hero_gallery", slides)}
          />
        </div>
      </section>

      <section aria-labelledby="detail-t" className="a-section">
        <h2 id="detail-t" className="a-h2">
          Franja de detalle
        </h2>
        <div className="mt-2 grid gap-6 md:grid-cols-2">
          <AssetField
            label="Franja en computadora"
            url={detailUrl}
            assetId={form.detail_asset_id}
            ratio="21 / 9"
            hint="Panorámica 21:9, ideal 2880 × 1234 px. Lo importante al centro: en teléfono se recortan los lados."
            onChange={(asset) => {
              set("detail_asset_id", asset?.id ?? null);
              setDetailUrl(asset?.url ?? null);
            }}
          />
          <AssetField
            label="Franja en teléfono (opcional)"
            url={detailMobileUrl}
            assetId={form.detail_mobile_asset_id}
            ratio="4 / 5"
            hint="Opcional, vertical 4:5, ideal 1600 × 2000 px."
            onChange={(asset) => {
              set("detail_mobile_asset_id", asset?.id ?? null);
              setDetailMobileUrl(asset?.url ?? null);
            }}
          />
        </div>
        <TextField className="mt-4" label="Texto sobre la foto (opcional)" value={form.detail_caption} onChange={(value) => set("detail_caption", value)} error={errors.detail_caption} />
      </section>

      <section aria-labelledby="attn-t" className="a-section">
        <h2 id="attn-t" className="a-h2">
          Bloque de atención
        </h2>
        <div className="mt-2 grid gap-6 md:grid-cols-2">
          <AssetField
            label="Atención en computadora"
            url={attentionUrl}
            assetId={form.attention_asset_id}
            ratio="16 / 9"
            hint="Horizontal 16:9, ideal 2880 × 1620 px. Deje tranquila la mitad izquierda: ahí van el texto y los botones."
            onChange={(asset) => {
              set("attention_asset_id", asset?.id ?? null);
              setAttentionUrl(asset?.url ?? null);
            }}
          />
          <AssetField
            label="Atención en teléfono"
            url={attentionMobileUrl}
            assetId={form.attention_mobile_asset_id}
            ratio="4 / 5"
            hint="Vertical 4:5, ideal 1600 × 2000 px."
            onChange={(asset) => {
              set("attention_mobile_asset_id", asset?.id ?? null);
              setAttentionMobileUrl(asset?.url ?? null);
            }}
          />
        </div>
        <div className="mt-4 space-y-4">
          <TextField label="Titular" placeholder="Escríbenos. Te asesoramos." value={form.attention_headline} onChange={(value) => set("attention_headline", value)} error={errors.attention_headline} />
          <TextAreaField label="Subtítulo (opcional)" rows={3} value={form.attention_subhead} onChange={(value) => set("attention_subhead", value)} error={errors.attention_subhead} />
        </div>
      </section>

      <section aria-labelledby="ig-t" className="a-section">
        <h2 id="ig-t" className="a-h2">
          Instagram
        </h2>
        <TextField
          className="mt-2 max-w-xl"
          label="Perfil de Instagram"
          type="url"
          placeholder="https://www.instagram.com/eleven.fashionboutique/"
          value={form.instagram_url}
          onChange={(value) => set("instagram_url", value)}
          error={errors.instagram_url}
        />
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
