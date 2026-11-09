"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useOptimistic, useRef, useState, useTransition } from "react";
import { AdminApiError, api, errorText } from "@/lib/admin/client";
import { formatNumber, plural } from "@/lib/admin/format";
import { type BulkRowInfo, type BulkSummary, chunk, primaryImageUrl, summarizeBulk } from "@/lib/admin/rules";
import type { AdminCategory, Brand, BulkAction, BulkResult, Product } from "@/lib/admin/types";
import { withParams } from "@/lib/url";
import { Empty, Notice, Pager, StatusLabel, Thumb, useConfirm } from "./ui";

const BATCH = 200;
const ALL_PAGE = 60;

const ACTIONS: { action: BulkAction; label: string; doneOne: string; done: string }[] = [
  { action: "publish", label: "Publicar", doneOne: "publicado", done: "publicados" },
  { action: "unpublish", label: "Despublicar", doneOne: "despublicado", done: "despublicados" },
  { action: "archive", label: "Archivar", doneOne: "archivado", done: "archivados" },
  { action: "feature", label: "Destacar", doneOne: "destacado", done: "destacados" },
  { action: "unfeature", label: "Quitar destacado", doneOne: "sin destacar", done: "sin destacar" },
];

export type ProductFilters = {
  q: string;
  status: string;
  brand: string;
  category: string;
  sin_foto: boolean;
  sort: string;
  page: number;
};

type Outcome = { label: string; doneOne: string; done: string; ok: number; failed: BulkSummary["failed"]; skipped: { brand: string; count: number }[] };

function queryOf(filters: ProductFilters) {
  return {
    q: filters.q,
    status: filters.status,
    brand: filters.brand,
    category: filters.category,
    has_photo: filters.sin_foto ? "false" : "",
    sort: filters.sort,
  };
}

export function ProductTable({
  items,
  total,
  pageSize,
  filters: serverFilters,
  brands,
  categories,
}: {
  items: Product[];
  total: number;
  pageSize: number;
  filters: ProductFilters;
  brands: Pick<Brand, "id" | "name">[] | null;
  categories: Pick<AdminCategory, "id" | "name">[] | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  // Los controles responden al instante y dos cambios seguidos se acumulan, sin esperar a la URL.
  const [filters, setOptimisticFilters] = useOptimistic(serverFilters);
  const [q, setQ] = useState(serverFilters.q);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, confirmDialog] = useConfirm();
  // La selección sobrevive al cambio de página: aquí queda con qué nombre mostrar cada fila.
  const known = useRef(new Map<string, BulkRowInfo>());
  for (const row of items) known.current.set(row.id, { id: row.id, name: row.name, brandName: row.brand.name });

  const hrefWith = (change: Partial<ProductFilters>) => {
    const next = { ...filters, page: 1, ...change };
    return withParams("/admin/productos", {
      q: next.q,
      status: next.status,
      brand: next.brand,
      category: next.category,
      sin_foto: next.sin_foto ? 1 : undefined,
      sort: next.sort,
      page: next.page,
    });
  };
  const apply = (change: Partial<ProductFilters>) =>
    startTransition(() => {
      setOptimisticFilters({ ...filters, page: 1, ...change });
      router.replace(hrefWith(change), { scroll: false });
    });

  // Búsqueda con espera breve para no consultar en cada tecla.
  useEffect(() => {
    if (q === filters.q) return;
    const timer = setTimeout(() => apply({ q }), 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo reacciona al texto.
  }, [q]);

  const pageIds = useMemo(() => items.map((row) => row.id), [items]);
  const selectedOnPage = pageIds.filter((id) => selected.has(id)).length;
  const allOnPage = pageIds.length > 0 && selectedOnPage === pageIds.length;
  const headerBox = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (headerBox.current) headerBox.current.indeterminate = selectedOnPage > 0 && !allOnPage;
  }, [selectedOnPage, allOnPage]);

  const toggle = (id: string) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const togglePage = () =>
    setSelected((current) => {
      const next = new Set(current);
      for (const id of pageIds) {
        if (allOnPage) next.delete(id);
        else next.add(id);
      }
      return next;
    });

  /** Reúne los ids de todas las páginas del filtro actual. */
  const selectAllResults = async () => {
    setBusy("Reuniendo resultados");
    setError(null);
    try {
      const ids = new Set(selected);
      for (let page = 1; ; page++) {
        const params = new URLSearchParams({ page: String(page), page_size: String(ALL_PAGE) });
        for (const [key, value] of Object.entries(queryOf(filters))) if (value) params.set(key, value);
        const batch = await api<{ items: Product[]; total: number }>(`/products?${params}`);
        for (const row of batch.items) {
          ids.add(row.id);
          known.current.set(row.id, { id: row.id, name: row.name, brandName: row.brand.name });
        }
        if (batch.items.length === 0 || page * ALL_PAGE >= batch.total) break;
      }
      setSelected(ids);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(null);
    }
  };

  const send = async (ids: string[], action: BulkAction, publishBrand: boolean): Promise<BulkResult[]> => {
    const results: BulkResult[] = [];
    const batches = chunk(ids, BATCH);
    for (const [index, batch] of batches.entries()) {
      if (batches.length > 1) setBusy(`Aplicando: lote ${index + 1} de ${batches.length}`);
      try {
        const body = { ids: batch, action, ...(publishBrand ? { publish_brand: true } : {}) };
        const data = await api<{ results: BulkResult[] }>("/products/bulk", { json: body });
        results.push(...data.results);
      } catch (cause) {
        // Si falla la petición entera, sus filas lo reportan y el resto de los lotes sigue.
        const code = cause instanceof AdminApiError ? cause.code : "request_failed";
        results.push(...batch.map((id) => ({ id, ok: false, error: { code, message: errorText(cause) } })));
      }
    }
    return results;
  };

  const run = async ({ action, label, doneOne, done }: (typeof ACTIONS)[number]) => {
    const ids = [...selected];
    if (ids.length === 0) return;
    if (action === "archive") {
      const accepted = await confirm({
        title: `¿Archivar ${plural(ids.length, "producto", "productos")}?`,
        body: <p>Dejan de verse en el sitio. No se borran: se pueden volver a publicar.</p>,
        confirmLabel: "Archivar",
      });
      if (!accepted) return;
    }
    setBusy(`${label}: aplicando`);
    setError(null);
    setOutcome(null);
    const lookup = (id: string) => known.current.get(id);
    const first = summarizeBulk(await send(ids, action, false), lookup);
    let ok = first.ok.length;
    const failed = [...first.failed];
    const skipped: Outcome["skipped"] = [];
    const succeeded = new Set(first.ok);

    // Una marca a la vez: la dueña decide cada una con su nombre a la vista.
    for (const { brand, ids: blocked } of first.brandBlocked) {
      setBusy(null);
      const accepted = await confirm({
        title: `La marca ${brand} no está publicada. ¿Publicar también la marca?`,
        body: <p>Afecta a {plural(blocked.length, "producto seleccionado", "productos seleccionados")}. Si no la publica, estos productos quedan como están.</p>,
        confirmLabel: "Publicar marca y productos",
        cancelLabel: "Dejarlos como están",
      });
      if (!accepted) {
        skipped.push({ brand, count: blocked.length });
        continue;
      }
      setBusy(`${label}: aplicando`);
      const second = summarizeBulk(await send(blocked, action, true), lookup);
      ok += second.ok.length;
      second.ok.forEach((id) => succeeded.add(id));
      failed.push(...second.failed);
      for (const left of second.brandBlocked) skipped.push({ brand: left.brand, count: left.ids.length });
    }

    setBusy(null);
    setOutcome({ label, doneOne, done, ok, failed, skipped });
    // Lo que falló queda seleccionado para corregirlo y reintentar.
    setSelected((current) => new Set([...current].filter((id) => !succeeded.has(id))));
    startTransition(() => router.refresh());
  };

  const filtered = Boolean(filters.q || filters.status || filters.brand || filters.category || filters.sin_foto);
  const working = busy !== null;
  const activeFilters = [filters.status, filters.brand, filters.category, filters.sin_foto].filter(Boolean).length;

  return (
    <>
      <form
        role="search"
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(14rem,2fr)_repeat(3,minmax(9rem,1fr))_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          apply({ q });
        }}
      >
        <div className="sm:col-span-2 lg:col-span-1">
          <label htmlFor="f-q" className="a-label">
            Buscar
          </label>
          <input id="f-q" type="search" className="a-input" placeholder="Nombre, SKU o marca" value={q} onChange={(event) => setQ(event.target.value)} />
        </div>
        <button
          type="button"
          className="a-btn a-btn-quiet sm:hidden"
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen((value) => !value)}
        >
          {activeFilters ? `Filtros (${activeFilters})` : "Filtros"}
        </button>
        <div className={filtersOpen ? "" : "max-sm:hidden"}>
          <label htmlFor="f-status" className="a-label">
            Estado
          </label>
          <select id="f-status" className="a-input" value={filters.status} onChange={(event) => apply({ status: event.target.value })}>
            <option value="">Todos</option>
            <option value="draft">Borrador</option>
            <option value="published">Publicado</option>
            <option value="archived">Archivado</option>
          </select>
        </div>
        {brands ? (
          <div className={filtersOpen ? "" : "max-sm:hidden"}>
            <label htmlFor="f-brand" className="a-label">
              Marca
            </label>
            <select id="f-brand" className="a-input" value={filters.brand} onChange={(event) => apply({ brand: event.target.value })}>
              <option value="">Todas</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {categories ? (
          <div className={filtersOpen ? "" : "max-sm:hidden"}>
            <label htmlFor="f-category" className="a-label">
              Categoría
            </label>
            <select id="f-category" className="a-input" value={filters.category} onChange={(event) => apply({ category: event.target.value })}>
              <option value="">Todas</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <label
          htmlFor="f-photo"
          className={`inline-flex min-h-10 cursor-pointer items-center gap-2 self-end whitespace-nowrap ${filtersOpen ? "" : "max-sm:hidden"}`}
        >
          <input id="f-photo" type="checkbox" checked={filters.sin_foto} onChange={(event) => apply({ sin_foto: event.target.checked })} />
          Sin foto
        </label>
      </form>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <p role="status" className="muted">
          {pending ? "Actualizando" : plural(total, "producto", "productos")}
        </p>
        <div className="flex items-center gap-2">
          <label htmlFor="f-sort" className="muted">
            Ordenar por
          </label>
          <select id="f-sort" className="a-input w-auto" value={filters.sort} onChange={(event) => apply({ sort: event.target.value })}>
            <option value="">Última edición</option>
            <option value="recent">Ingreso comercial</option>
            <option value="name">Nombre</option>
            <option value="sku">SKU</option>
          </select>
        </div>
      </div>

      {error ? (
        <div className="mt-3">
          <Notice kind="error">{error}</Notice>
        </div>
      ) : null}

      {outcome ? (
        <section aria-label="Resultado de la acción" className="a-panel mt-3" role="status">
          <div className="flex items-start justify-between gap-3">
            <p className="font-medium">
              {outcome.label}: {plural(outcome.ok, outcome.doneOne, outcome.done)}
              {outcome.failed.length ? `, ${formatNumber(outcome.failed.length)} con error` : ""}
              {outcome.skipped.length ? `, ${formatNumber(outcome.skipped.reduce((sum, item) => sum + item.count, 0))} sin cambios` : ""}.
            </p>
            <button type="button" className="a-btn a-btn-quiet a-btn-small" onClick={() => setOutcome(null)}>
              Cerrar
            </button>
          </div>
          {outcome.skipped.map((item) => (
            <p key={item.brand} className="mt-1">
              {plural(item.count, "producto", "productos")} de {item.brand} sin cambios: la marca sigue sin publicar.
            </p>
          ))}
          {outcome.failed.length ? (
            <ul className="mt-2 max-h-64 overflow-y-auto">
              {outcome.failed.map((row) => (
                <li key={row.id} className="border-t border-bronze/30 py-1.5">
                  <Link href={`/admin/productos/${row.id}`} prefetch={false} className="link">
                    {row.name}
                  </Link>
                  : {row.message}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {items.length === 0 ? (
        filtered ? (
          <Empty
            message="Ningún producto coincide con estos filtros."
            action={
              <Link href="/admin/productos" prefetch={false} className="a-btn" onClick={() => setQ("")}>
                Quitar filtros
              </Link>
            }
          />
        ) : (
          <Empty
            message="Aún no hay productos. El catálogo se carga desde un archivo de Excel o CSV."
            action={
              <Link href="/admin/importar" prefetch={false} className="a-btn">
                Importar catálogo
              </Link>
            }
          />
        )
      ) : (
        <div className="mt-2" aria-busy={pending}>
          <table className="a-table">
            <caption className="sr-only">Productos</caption>
            <thead>
              <tr>
                <th scope="col" className="w-10">
                  <input ref={headerBox} type="checkbox" aria-label="Seleccionar los de esta página" checked={allOnPage} onChange={togglePage} />
                </th>
                <th scope="col" className="w-14">
                  <span className="sr-only">Foto</span>
                </th>
                <th scope="col">Producto</th>
                <th scope="col" className="max-md:hidden">
                  Marca
                </th>
                <th scope="col" className="max-lg:hidden">
                  Categoría
                </th>
                <th scope="col" className="max-sm:hidden">
                  Estado
                </th>
                <th scope="col" className="max-xl:hidden">
                  Fotos
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} data-selected={selected.has(row.id) || undefined}>
                  <td>
                    {/* Área táctil amplia: la casilla sola es difícil de acertar en teléfono. */}
                    <label className="-m-2 flex cursor-pointer items-center justify-center p-2">
                      <input
                        type="checkbox"
                        aria-label={`Seleccionar ${row.name}`}
                        checked={selected.has(row.id)}
                        onChange={() => toggle(row.id)}
                      />
                    </label>
                  </td>
                  <td>
                    <Thumb src={primaryImageUrl(row)} size="2.5rem" sizes="64px" emptyLabel="" />
                  </td>
                  <td className="min-w-0">
                    <Link href={`/admin/productos/${row.id}`} prefetch={false} className="a-piece hover:underline">
                      {row.name}
                    </Link>
                    <span className="muted block break-all">{row.sku}</span>
                    {row.is_featured ? <span className="muted block">Destacado</span> : null}
                    {/* En pantallas angostas las columnas ocultas se resumen aquí. */}
                    <span className="block md:hidden">{row.brand.name}</span>
                    <span className="block sm:hidden">
                      <StatusLabel status={row.status} />
                    </span>
                  </td>
                  <td className="max-md:hidden">{row.brand.name}</td>
                  <td className="max-lg:hidden">{row.category.name}</td>
                  <td className="max-sm:hidden">
                    <StatusLabel status={row.status} />
                  </td>
                  <td className="max-xl:hidden">{row.media.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pager
            page={filters.page}
            pageSize={pageSize}
            total={total}
            hrefFor={(page) => hrefWith({ page })}
          />
        </div>
      )}

      {selected.size > 0 || working ? (
        <div className="a-bar" role="region" aria-label="Acciones sobre la selección">
          <p className="font-medium">{plural(selected.size, "seleccionado", "seleccionados")}</p>
          {total > selected.size && total > items.length ? (
            <button type="button" className="a-btn a-btn-quiet a-btn-small" disabled={working} onClick={selectAllResults}>
              <span className="max-sm:hidden">Seleccionar los {formatNumber(total)} resultados</span>
              <span className="sm:hidden">Todos ({formatNumber(total)})</span>
            </button>
          ) : null}
          <button type="button" className="a-btn a-btn-quiet a-btn-small" disabled={working} onClick={() => setSelected(new Set())}>
            Limpiar
          </button>
          <div className="flex w-full gap-2 p-0.5 max-sm:overflow-x-auto sm:flex-wrap lg:ml-auto lg:w-auto">
            {ACTIONS.map((item) => (
              <button
                key={item.action}
                type="button"
                className={`a-btn a-btn-small shrink-0 ${item.action === "publish" ? "a-btn-primary" : ""}`}
                disabled={working || selected.size === 0}
                onClick={() => void run(item)}
              >
                {item.label}
              </button>
            ))}
          </div>
          {busy ? (
            <p role="status" className="w-full">
              {busy}
            </p>
          ) : null}
        </div>
      ) : null}
      {confirmDialog}
    </>
  );
}
