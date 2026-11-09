"use client";

import { useEffect, useId, useState } from "react";
import { api, errorText } from "@/lib/admin/client";
import { primaryImageUrl } from "@/lib/admin/rules";
import type { Product, ProductRef } from "@/lib/admin/types";
import { Thumb } from "./ui";

function toProductRef(row: Product): ProductRef {
  return {
    id: row.id,
    name: row.name,
    sku: row.sku,
    brand_name: row.brand.name,
    primary_image_url: primaryImageUrl(row),
  };
}

/** Búsqueda de producto en el servidor: el catálogo es demasiado grande para un select. */
export function ProductSearch({
  label = "Buscar producto",
  excludeIds,
  autoFocus,
  onPick,
}: {
  label?: string;
  excludeIds?: readonly string[];
  autoFocus?: boolean;
  onPick: (product: ProductRef) => void;
}) {
  const id = useId();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<ProductRef[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) return;
    let stale = false;
    const timer = setTimeout(async () => {
      try {
        const data = await api<{ items: Product[] }>(`/products?${new URLSearchParams({ q: term, page_size: "8" })}`);
        if (!stale) {
          setResults(data.items.map(toProductRef));
          setError(null);
        }
      } catch (cause) {
        if (!stale) setError(errorText(cause));
      }
    }, 250);
    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [q]);

  const short = q.trim().length < 2;
  const visible = short ? null : results?.filter((item) => !excludeIds?.includes(item.id));

  return (
    <div>
      <label htmlFor={id} className="a-label">
        {label}
      </label>
      <input
        id={id}
        type="search"
        className="a-input"
        placeholder="Nombre, SKU o marca"
        value={q}
        autoFocus={autoFocus}
        onKeyDown={(event) => {
          // Vive dentro de formularios de edición: Enter no debe guardarlos.
          if (event.key === "Enter") event.preventDefault();
        }}
        onChange={(event) => setQ(event.target.value)}
      />
      {error ? (
        <p role="alert" className="a-error">
          {error}
        </p>
      ) : null}
      <p role="status" className="a-hint">
        {short ? "Escriba al menos 2 letras." : visible ? `${visible.length} resultados` : "Buscando"}
      </p>
      {visible?.length ? (
        <ul className="mt-1 max-h-72 overflow-y-auto border border-bronze/40">
          {visible.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex w-full cursor-pointer items-center gap-3 p-2 text-left hover:bg-charcoal"
                onClick={() => {
                  onPick(item);
                  setQ("");
                  setResults(null);
                }}
              >
                <Thumb src={item.primary_image_url} size="2.25rem" sizes="64px" emptyLabel="" />
                <span className="min-w-0">
                  <span className="a-piece block truncate">{item.name}</span>
                  <span className="muted block truncate">{[item.brand_name, item.sku].filter(Boolean).join(", ")}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
