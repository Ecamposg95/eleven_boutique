import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PublicSettings } from "@/lib/types";
import { AttentionBlock, DEFAULT_ATTENTION_HEADLINE } from "./AttentionBlock";
import { DetailBand } from "./DetailBand";

const base = {
  demo_mode: false,
  whatsapp_enabled: true,
  site_name: "Eleven",
  hero: { image_url: null, headline: null, subhead: null },
  intro: null,
  boutique: { body: null },
  contact: { body: null },
} satisfies PublicSettings;

const attention = (extra: Partial<NonNullable<PublicSettings["attention"]>> = {}) => ({
  headline: "Hablemos",
  subhead: null,
  image_url: null,
  mobile_image_url: null,
  whatsapp_url: "https://wa.me/525500000000?text=Hola",
  boutique_whatsapp_url: null,
  ...extra,
});

const html = (settings: PublicSettings) => renderToStaticMarkup(<AttentionBlock settings={settings} />);

describe("DetailBand", () => {
  it("sin foto no pinta nada", () => {
    expect(renderToStaticMarkup(<DetailBand detail={undefined} />)).toBe("");
    const detail = { image_url: null, mobile_image_url: "/m.jpg", caption: "Pie" };
    expect(renderToStaticMarkup(<DetailBand detail={detail} />)).toBe("");
  });

  it("una URL no segura cuenta como sin foto", () => {
    const detail = { image_url: "javascript:x", mobile_image_url: null, caption: null };
    expect(renderToStaticMarkup(<DetailBand detail={detail} />)).toBe("");
  });

  it("con foto pinta la franja y el pie", () => {
    const detail = { image_url: "/d.jpg", mobile_image_url: null, caption: " Hecho a mano " };
    const markup = renderToStaticMarkup(<DetailBand detail={detail} />);
    expect(markup).toContain('aria-label="Detalle"');
    expect(markup).toContain(">Hecho a mano<");
  });
});

describe("AttentionBlock", () => {
  it("sin WhatsApp ni Instagram no pinta nada", () => {
    expect(html({ ...base, attention: attention({ whatsapp_url: null }) })).toBe("");
    expect(html(base)).toBe("");
  });

  it("usa el titular guardado", () => {
    expect(html({ ...base, attention: attention() })).toContain(">Hablemos</h2>");
  });

  it("con titular vacío usa el de siempre, nunca un h2 vacío", () => {
    expect(html({ ...base, attention: attention({ headline: "  " }) })).toContain(
      `>${DEFAULT_ATTENTION_HEADLINE}</h2>`,
    );
  });

  it("una API anterior sin attention muestra el bloque si hay Instagram", () => {
    const markup = html({ ...base, instagram_url: "https://www.instagram.com/eleven" });
    expect(markup).toContain(`>${DEFAULT_ATTENTION_HEADLINE}</h2>`);
    expect(markup).toContain('href="https://www.instagram.com/eleven"');
    expect(markup).not.toContain("wa.me");
  });
});
