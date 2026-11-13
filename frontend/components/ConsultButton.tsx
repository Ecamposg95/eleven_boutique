"use client";

import type { ConsultEvent } from "@/lib/types";

export function trackConsult(productSlug: string) {
  try {
    const event: ConsultEvent = { type: "whatsapp_click", product_slug: productSlug };
    const body = new Blob([JSON.stringify(event)], { type: "application/json" });
    navigator.sendBeacon("/api/v1/events", body);
  } catch {
    // La medición nunca debe interferir con la consulta.
  }
}

export function ConsultButton({ href, productSlug }: { href: string; productSlug: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="btn w-full sm:w-auto"
      onClick={() => trackConsult(productSlug)}
    >
      Consultar esta pieza
    </a>
  );
}
