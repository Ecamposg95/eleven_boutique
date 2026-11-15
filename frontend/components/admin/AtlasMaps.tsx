"use client";

import { useState } from "react";
import { categoryPaths, saveBrandMap, saveCategoryMap, unlinkedFirst } from "@/lib/admin/atlas";
import { errorText } from "@/lib/admin/client";
import type { AdminCategory, AtlasBrandMapRow, AtlasCategoryMapRow, Brand } from "@/lib/admin/types";
import { Notice } from "./ui";

type Option = { id: string; name: string };

/** Una fila del mapa: lo elegido se guarda al instante. */
function MapRow({
  rowKey,
  atlasName,
  value,
  options,
  save,
  unlinkable = true,
}: {
  rowKey: string;
  atlasName: string;
  value: string | null;
  options: Option[];
  save: (id: string | null) => Promise<unknown>;
  /** Marcas: no se desligan, porque la liga automática las volvería a ligar en la siguiente corrida. */
  unlinkable?: boolean;
}) {
  const [current, setCurrent] = useState(value ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const id = `map-${rowKey}`;
  // Si el valor del servidor cambia, la fila lo sigue (ajuste durante el render, sin efecto).
  const [seen, setSeen] = useState(value);
  if (seen !== value) {
    setSeen(value);
    setCurrent(value ?? "");
  }

  const change = async (next: string) => {
    const previous = current;
    setCurrent(next);
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await save(next || null);
      setSaved(true);
    } catch (cause) {
      setCurrent(previous);
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <tr>
      <td>
        <label htmlFor={id}>{atlasName}</label>
      </td>
      <td>
        <select id={id} className="a-input" value={current} disabled={busy} onChange={(event) => void change(event.target.value)}>
          {unlinkable ? (
            <option value="">Sin ligar</option>
          ) : current === "" ? (
            <option value="" disabled>
              Elegir casa…
            </option>
          ) : null}
          {options.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name}
            </option>
          ))}
        </select>
        {saved ? (
          <span role="status" className="muted">
            Guardado.
          </span>
        ) : null}
        {error ? <Notice kind="error">{error}</Notice> : null}
      </td>
    </tr>
  );
}

function MapTable({ title, caption, hint, rows }: { title: string; caption: string; hint: string; rows: React.ReactNode }) {
  return (
    <section aria-label={title} className="a-section">
      <h2 className="a-h2">{title}</h2>
      <p className="a-hint">{hint}</p>
      <div className="mt-2 overflow-x-auto">
        <table className="a-table">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              <th scope="col">En Atlas ONE</th>
              <th scope="col">En el sitio</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>
  );
}

export function AtlasMaps({
  brands,
  categories,
  brandMap,
  categoryMap,
}: {
  brands: Pick<Brand, "id" | "name">[];
  categories: Pick<AdminCategory, "id" | "name" | "parent_id">[];
  brandMap: AtlasBrandMapRow[];
  categoryMap: AtlasCategoryMapRow[];
}) {
  const categoryOptions = categoryPaths(categories);
  return (
    <>
      <MapTable
        title="Marcas"
        caption="Marcas de Atlas ONE y su casa en el sitio"
        hint="Las piezas de una marca sin ligar quedan en borrador hasta que la ligue a una casa del sitio."
        rows={unlinkedFirst(brandMap, (row) => row.brand_id).map((row) => (
          <MapRow
            key={row.atlas_brand_id}
            rowKey={`b-${row.atlas_brand_id}`}
            atlasName={row.atlas_name}
            value={row.brand_id}
            options={brands}
            unlinkable={false}
            save={(id) => (id ? saveBrandMap(row.atlas_brand_id, id) : Promise.resolve())}
          />
        ))}
      />
      <MapTable
        title="Categorías"
        caption="Departamentos de Atlas ONE y su categoría en el sitio"
        hint="Las piezas de un departamento sin ligar quedan en borrador hasta que lo ligue a una categoría."
        rows={unlinkedFirst(categoryMap, (row) => row.category_id).map((row) => (
          <MapRow
            key={row.atlas_department_id}
            rowKey={`c-${row.atlas_department_id}`}
            atlasName={row.atlas_name}
            value={row.category_id}
            options={categoryOptions}
            save={(id) => saveCategoryMap(row.atlas_department_id, id)}
          />
        ))}
      />
    </>
  );
}
