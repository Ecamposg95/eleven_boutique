"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import {
  getSelection,
  getServerSelection,
  removePieces,
  subscribeSelection,
  updateSelection,
} from "@/lib/selection";
import type { SelectionConsult, SelectionLine } from "@/lib/types";
import { CatalogImage } from "./CatalogImage";
import { trackConsult } from "./ConsultButton";
import { EmptyState } from "./EmptyState";

type Result = { key: string; data: SelectionConsult | null };

async function fetchConsult(slugs: string[]): Promise<SelectionConsult | null> {
  try {
    const response = await fetch("/api/v1/selection/consult", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_slugs: slugs }),
    });
    return response.ok ? ((await response.json()) as SelectionConsult) : null;
  } catch {
    return null;
  }
}

const pieces_ = (n: number) => (n === 1 ? "1 pieza" : `${n} piezas`);

function lineLabel(line: SelectionLine, split: boolean) {
  const n = line.product_slugs.length;
  if (!split) return n === 1 ? "Consultar esta pieza" : `Consultar las ${n} piezas`;
  return line.boutique ? `Consultar ${pieces_(n)} en línea Boutique` : `Consultar ${pieces_(n)}`;
}

/** Lista de «Mi selección» y los enlaces de WhatsApp que arma la API (uno por línea). */
export function SelectionView() {
  const pieces = useSyncExternalStore(subscribeSelection, getSelection, getServerSelection);
  const key = pieces.map((p) => p.slug).join("\n");
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    if (!key) return;
    let active = true;
    fetchConsult(key.split("\n")).then((data) => {
      if (!active) return;
      // Las piezas que ya no están publicadas se retiran solas.
      if (data?.missing_slugs.length) updateSelection((list) => removePieces(list, data.missing_slugs));
      setResult({ key, data });
    });
    return () => {
      active = false;
    };
  }, [key]);

  // Antes de hidratar el servidor no conoce la selección: no se muestra el estado vacío todavía.
  const hydrated = useSyncExternalStore(subscribeSelection, () => true, () => false);
  if (!hydrated) return <div className="min-h-64" aria-busy="true" />;

  if (pieces.length === 0) {
    return (
      <EmptyState
        message="Aún no guardas piezas. Usa «Guardar en mi selección» en cualquier pieza del catálogo."
        href="/novedades"
        action="Ver novedades"
      />
    );
  }

  const current = result?.key === key ? result : null;
  const lines = current?.data?.lines ?? [];
  const reachable = new Set(lines.flatMap((line) => line.product_slugs));
  const split = lines.length > 1;

  return (
    <div className="grid gap-12 pb-24 lg:grid-cols-12 lg:gap-x-6">
      <ul className="grid grid-cols-2 gap-x-4 gap-y-10 sm:grid-cols-3 lg:col-span-8">
        {pieces.map((piece) => (
          <li key={piece.slug}>
            <Link href={piece.href} prefetch={false} className="group block">
              <span className="relative block aspect-[4/5] overflow-hidden bg-charcoal">
                <CatalogImage
                  src={piece.image?.url}
                  alt={piece.image?.alt ?? ""}
                  sizes="(min-width: 1024px) 22vw, (min-width: 640px) 30vw, 46vw"
                  className="bg-ink object-cover"
                />
              </span>
              <span className="mt-3 block">
                {piece.brand ? <span className="label muted block">{piece.brand}</span> : null}
                <span className="mt-1 block text-17 font-medium tracking-[-0.01em] decoration-bronze decoration-1 underline-offset-4 group-hover:underline">
                  {piece.name}
                </span>
              </span>
            </Link>
            <button
              type="button"
              onClick={() => updateSelection((list) => removePieces(list, [piece.slug]))}
              className="label muted mt-1 inline-flex min-h-11 cursor-pointer items-center"
              aria-label={`Quitar ${piece.name} de la selección`}
            >
              Quitar
            </button>
            {current?.data && !reachable.has(piece.slug) ? (
              <p className="muted text-15">Sin línea de consulta disponible.</p>
            ) : null}
          </li>
        ))}
      </ul>

      <aside className="self-start lg:sticky lg:top-[calc(var(--chrome-h)+3rem)] lg:col-span-4">
        <p className="label muted">{pieces_(pieces.length)}</p>
        <div className="mt-6 space-y-3" aria-live="polite">
          {!current ? (
            <p className="muted text-15">Preparando tu mensaje…</p>
          ) : !current.data ? (
            <p className="text-15">No pudimos preparar el mensaje. Intenta de nuevo en un momento.</p>
          ) : lines.length === 0 ? (
            <p className="muted text-15">La consulta por WhatsApp no está disponible por ahora.</p>
          ) : (
            lines.map((line) => (
              <a
                key={line.url}
                href={line.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn w-full"
                onClick={() => line.product_slugs.forEach(trackConsult)}
              >
                {lineLabel(line, split)}
              </a>
            ))
          )}
          {split ? (
            <p className="muted text-15">
              Las casas premium se atienden en nuestra línea Boutique, por eso van en un mensaje aparte.
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => updateSelection(() => [])}
          className="label muted mt-8 inline-flex min-h-11 cursor-pointer items-center"
        >
          Vaciar selección
        </button>
      </aside>
    </div>
  );
}
