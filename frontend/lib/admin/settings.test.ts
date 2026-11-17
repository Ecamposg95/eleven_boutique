import { describe, expect, it } from "vitest";
import { AdminApiError } from "./client";
import { CHECK_FIELDS, saveErrors, settingsBody, settingsForm } from "./settings";
import type { AdminSettings } from "./types";

const empty = settingsForm({} as AdminSettings);

describe("settingsBody", () => {
  it("los textos vacíos o en blanco viajan como null", () => {
    const body = settingsBody(
      { ...empty, instagram_url: "  ", attention_headline: "", detail_caption: " Pie " },
      { general: "", premium: "" },
    );
    expect(body.instagram_url).toBeNull();
    expect(body.attention_headline).toBeNull();
    expect(body.detail_caption).toBe("Pie");
    expect(body.whatsapp_number).toBeNull();
    expect(body.whatsapp_premium_number).toBeNull();
  });

  it("usa los dígitos normalizados y manda todos los campos nuevos", () => {
    const body = settingsBody(
      {
        ...empty,
        instagram_url: " https://www.instagram.com/eleven/ ",
        detail_asset_id: "d",
        detail_mobile_asset_id: null,
        attention_asset_id: "a",
        attention_mobile_asset_id: "am",
        hero_gallery: [{ asset_id: "g", url: "/g.jpg" }],
      },
      { general: "525500000000", premium: "525599990000" },
    );
    expect(body).toMatchObject({
      whatsapp_number: "525500000000",
      whatsapp_premium_number: "525599990000",
      instagram_url: "https://www.instagram.com/eleven/",
      detail_asset_id: "d",
      detail_mobile_asset_id: null,
      attention_asset_id: "a",
      attention_mobile_asset_id: "am",
      hero_gallery_slides: [{ asset_id: "g", mobile_asset_id: null }],
    });
  });
});

describe("saveErrors", () => {
  it("Instagram inválido va al campo y el aviso no repite el mensaje", () => {
    const cause = new AdminApiError(422, "invalid_instagram_url", "El enlace debe ser de instagram.com");
    expect(saveErrors(cause)).toEqual({
      fields: { instagram_url: "El enlace debe ser de instagram.com" },
      notice: CHECK_FIELDS,
    });
  });

  it("errores por campo del servidor remiten a los campos", () => {
    const cause = new AdminApiError(422, "validation_error", "Datos inválidos", { intro: "Muy largo" });
    expect(saveErrors(cause)).toEqual({ fields: { intro: "Muy largo" }, notice: CHECK_FIELDS });
  });

  it("sin campos, el aviso lleva el mensaje del servidor", () => {
    const cause = new AdminApiError(500, "server_error", "El servidor no pudo completar la acción.");
    expect(saveErrors(cause)).toEqual({ fields: {}, notice: "El servidor no pudo completar la acción." });
  });

  it("un error que no es de la API usa el texto genérico", () => {
    expect(saveErrors(new Error("Sin red")).notice).toBe("Sin red");
    expect(saveErrors("x").notice).toBe("Ocurrió un error inesperado.");
  });
});
