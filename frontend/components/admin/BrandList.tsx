"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { plural } from "@/lib/admin/format";
import type { Brand } from "@/lib/admin/types";
import { CreateByName } from "./CreateByName";
import { Empty, StatusLabel, Thumb } from "./ui";

const normalize = (value: string) => value.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

export function BrandList({ brands }: { brands: Brand[] }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const visible = useMemo(() => {
    const term = normalize(q.trim());
    return brands.filter(
      (brand) =>
        (!status || brand.status === status) &&
        (!term || normalize(brand.name).includes(term) || brand.aliases.some((alias) => normalize(alias).includes(term))),
    );
  }, [brands, q, status]);

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-[minmax(12rem,24rem)_12rem]">
        <div>
          <label htmlFor="b-q" className="a-label">
            Buscar
          </label>
          <input id="b-q" type="search" className="a-input" placeholder="Nombre o alias" value={q} onChange={(event) => setQ(event.target.value)} />
        </div>
        <div>
          <label htmlFor="b-status" className="a-label">
            Estado
          </label>
          <select id="b-status" className="a-input" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Todos</option>
            <option value="draft">Borrador</option>
            <option value="published">Publicado</option>
            <option value="archived">Archivado</option>
          </select>
        </div>
      </div>
      <p role="status" className="muted mt-3">
        {plural(visible.length, "marca", "marcas")}
      </p>
      {visible.length === 0 ? (
        <Empty message={brands.length ? "Ninguna marca coincide con esta búsqueda." : "Aún no hay marcas. Agregue la primera abajo."} />
      ) : (
        <table className="a-table mt-1">
          <caption className="sr-only">Marcas</caption>
          <thead>
            <tr>
              <th scope="col" className="w-24">
                Logotipo
              </th>
              <th scope="col">Marca</th>
              <th scope="col" className="max-md:hidden">
                Validación
              </th>
              <th scope="col" className="max-sm:hidden">
                Productos
              </th>
              <th scope="col" className="max-sm:hidden">
                Estado
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((brand) => (
              <tr key={brand.id}>
                <td>
                  <Thumb src={brand.logo_url} size="4.5rem" ratio="2 / 1" sizes="120px" contain emptyLabel="Sin logo" />
                </td>
                <td>
                  <Link href={`/admin/marcas/${brand.id}`} prefetch={false} className="a-piece hover:underline">
                    {brand.name}
                  </Link>
                  {brand.aliases.length ? <span className="muted block">También: {brand.aliases.slice(0, 3).join(", ")}</span> : null}
                  <span className="block sm:hidden">
                    <StatusLabel status={brand.status} />
                  </span>
                </td>
                <td className="max-md:hidden">{brand.validation_status === "approved" ? "Validada" : "Pendiente"}</td>
                <td className="max-sm:hidden">{brand.product_count}</td>
                <td className="max-sm:hidden">
                  <StatusLabel status={brand.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <section aria-labelledby="nueva-t" className="a-section">
        <h2 id="nueva-t" className="a-h2 mb-2">
          Agregar marca
        </h2>
        <CreateByName endpoint="/brands" field="name" label="Nombre de la marca" action="Agregar marca" basePath="/admin/marcas" />
      </section>
    </>
  );
}
