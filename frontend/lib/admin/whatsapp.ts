export type WhatsappCheck =
  | { ok: true; digits: string; hint?: string }
  | { ok: false; message: string };

/** Vacío es válido: significa consulta desactivada. Misma regla que el backend: E.164, 8 a 15 dígitos. */
export function checkWhatsapp(raw: string): WhatsappCheck {
  const trimmed = raw.trim();
  if (!trimmed) return { ok: true, digits: "" };
  if (!/^\+?[\d\s().-]+$/.test(trimmed)) {
    return { ok: false, message: "Use solo dígitos y, si lo desea, el signo + inicial." };
  }
  const digits = trimmed.replace(/\D/g, "");
  if (digits.startsWith("0")) {
    return { ok: false, message: "El número empieza con la lada de país, sin ceros: 52 para México." };
  }
  if (digits.length < 8 || digits.length > 15) {
    return { ok: false, message: "El número debe tener entre 8 y 15 dígitos, con la lada de país." };
  }
  if (digits.length === 10) {
    return { ok: true, digits, hint: "Parece faltar la lada de país. Para México, inicie con 52." };
  }
  return { ok: true, digits };
}

const SAMPLE =
  "Hola, me interesa conocer más sobre esta pieza de Eleven Boutique: {marca} — {nombre}.";

export function whatsappPreview(digits: string): string {
  return `https://wa.me/${digits}?text=${encodeURIComponent(SAMPLE)}`;
}
