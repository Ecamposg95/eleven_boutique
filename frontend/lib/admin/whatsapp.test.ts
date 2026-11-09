import { describe, expect, it } from "vitest";
import { checkWhatsapp, whatsappPreview } from "./whatsapp";

describe("checkWhatsapp", () => {
  it("vacío desactiva la consulta", () => {
    expect(checkWhatsapp("   ")).toEqual({ ok: true, digits: "" });
  });
  it("normaliza formatos habituales a dígitos", () => {
    expect(checkWhatsapp("+52 (55) 1234-5678")).toEqual({ ok: true, digits: "525512345678" });
    expect(checkWhatsapp("52.55.1234.5678")).toEqual({ ok: true, digits: "525512345678" });
  });
  it("avisa sin bloquear si faltan los dígitos de país", () => {
    const check = checkWhatsapp("5512345678");
    expect(check.ok && check.hint).toMatch(/52/);
  });
  it.each(["abc", "55-12x", "1234567", "1234567890123456", "0052551234", "++525512345678"])(
    "rechaza %s",
    (raw) => {
      expect(checkWhatsapp(raw).ok).toBe(false);
    },
  );
  it("acepta los límites de 8 y 15 dígitos", () => {
    expect(checkWhatsapp("12345678").ok).toBe(true);
    expect(checkWhatsapp("123456789012345").ok).toBe(true);
  });
});

describe("whatsappPreview", () => {
  it("arma el enlace wa.me con el texto codificado", () => {
    const link = whatsappPreview("525512345678");
    expect(link.startsWith("https://wa.me/525512345678?text=Hola%2C")).toBe(true);
    expect(link).not.toContain(" ");
  });
});
