import { AdminApiError, errorText } from "./client";
import type { AdminSettings } from "./types";

/** Estado del formulario de Ajustes: textos como cadena (vacía = sin valor) e ids de imagen. */
export function settingsForm(settings: AdminSettings) {
  return {
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
    instagram_url: settings.instagram_url ?? "",
    detail_asset_id: settings.detail_asset_id,
    detail_mobile_asset_id: settings.detail_mobile_asset_id,
    detail_caption: settings.detail_caption ?? "",
    attention_asset_id: settings.attention_asset_id,
    attention_mobile_asset_id: settings.attention_mobile_asset_id,
    attention_headline: settings.attention_headline ?? "",
    attention_subhead: settings.attention_subhead ?? "",
  };
}

export type SettingsFormState = ReturnType<typeof settingsForm>;

const text = (value: string) => value.trim() || null;

/** Cuerpo del PATCH /settings. Los textos vacíos viajan como `null` para borrar el valor. */
export function settingsBody(
  form: SettingsFormState,
  digits: { general: string; premium: string },
) {
  return {
    whatsapp_number: digits.general || null,
    whatsapp_premium_number: digits.premium || null,
    hero_asset_id: form.hero_asset_id,
    hero_mobile_asset_id: form.hero_mobile_asset_id,
    hero_gallery_slides: form.hero_gallery.map((slide) => ({
      asset_id: slide.asset_id,
      mobile_asset_id: slide.mobile_asset_id ?? null,
    })),
    hero_headline: text(form.hero_headline),
    hero_subhead: text(form.hero_subhead),
    intro: text(form.intro),
    boutique_body: text(form.boutique_body),
    contact_body: text(form.contact_body),
    instagram_url: text(form.instagram_url),
    detail_asset_id: form.detail_asset_id,
    detail_mobile_asset_id: form.detail_mobile_asset_id,
    detail_caption: text(form.detail_caption),
    attention_asset_id: form.attention_asset_id,
    attention_mobile_asset_id: form.attention_mobile_asset_id,
    attention_headline: text(form.attention_headline),
    attention_subhead: text(form.attention_subhead),
  };
}

export const CHECK_FIELDS = "Revise los campos marcados.";

/**
 * Errores de un guardado fallido. Si el servidor señala campos, el detalle va junto a cada campo y
 * el aviso general solo remite a ellos: así el mismo mensaje no aparece dos veces.
 */
export function saveErrors(cause: unknown): { fields: Record<string, string>; notice: string } {
  if (!(cause instanceof AdminApiError)) return { fields: {}, notice: errorText(cause) };
  const fields =
    cause.code === "invalid_instagram_url" ? { instagram_url: cause.message } : cause.fields;
  return { fields, notice: Object.keys(fields).length > 0 ? CHECK_FIELDS : cause.message };
}
