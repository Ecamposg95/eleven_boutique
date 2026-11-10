"use client";

import Link from "next/link";
import { useRef } from "react";
import type { CatalogOption } from "@/lib/categories";

function CloseIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 10 10"
      className="h-2.5 w-2.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
    >
      <path d="M1 1l8 8M9 1l-8 8" />
    </svg>
  );
}

function Sheet({
  title,
  options,
  sheet,
}: {
  title: string;
  options: CatalogOption[];
  sheet: React.RefObject<HTMLDialogElement | null>;
}) {
  const close = () => sheet.current?.close();
  return (
    <dialog
      ref={sheet}
      aria-label={title}
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
      className="sheet fixed inset-x-0 bottom-0 top-auto m-0 max-h-[75dvh] w-full max-w-none bg-[#f7f5f1] p-0 text-[#121212]"
    >
      <div className="page flex flex-col gap-8 pb-10 pt-6">
        <div className="flex items-center justify-between gap-6 border-b border-[#121212]/15 pb-4">
          <h2 className="label">{title}</h2>
          <button
            type="button"
            onClick={close}
            className="label inline-flex min-h-11 cursor-pointer items-center gap-2"
          >
            <CloseIcon />
            Cerrar
          </button>
        </div>
        <ul className="grid gap-x-10 gap-y-1 sm:grid-cols-2 md:grid-cols-3">
          {options.map((option) => (
            <li key={option.href}>
              <Link
                href={option.href}
                scroll={false}
                onClick={close}
                aria-current={option.current ? "page" : undefined}
                className="drawer-link label inline-flex min-h-10 items-center text-[0.8125rem] tracking-[0.14em]"
              >
                {option.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </dialog>
  );
}

/**
 * Barra flotante abajo al centro con «Filtros · Ordenar». Cada botón abre una hoja inferior
 * (<dialog>: foco atrapado, Esc y retorno de foco nativos). Un grupo sin opciones no se muestra.
 */
export function CatalogBar({
  filters,
  sorts,
}: {
  filters: CatalogOption[];
  sorts: CatalogOption[];
}) {
  const filterSheet = useRef<HTMLDialogElement>(null);
  const sortSheet = useRef<HTMLDialogElement>(null);
  const showFilters = filters.length > 1;
  const showSorts = sorts.length > 1;
  if (!showFilters && !showSorts) return null;

  const active = filters.find((option, index) => option.current && index > 0);
  const button =
    "label inline-flex min-h-11 cursor-pointer items-center gap-2 px-6";

  return (
    <>
      <div className="pointer-events-none fixed inset-x-0 bottom-5 z-30 flex justify-center px-4 md:bottom-8">
        <div className="acrylic-card pointer-events-auto flex items-center rounded-full bg-[#121212]/80 text-[#efece6] shadow-[0_10px_40px_rgb(18_18_18/0.18)]">
          {showFilters ? (
            <button
              type="button"
              aria-haspopup="dialog"
              onClick={() => filterSheet.current?.showModal()}
              className={button}
            >
              Filtros
              {active ? (
                <span className="opacity-60">· {active.label}</span>
              ) : null}
            </button>
          ) : null}
          {showFilters && showSorts ? (
            <span aria-hidden="true" className="h-4 w-px bg-white/30" />
          ) : null}
          {showSorts ? (
            <button
              type="button"
              aria-haspopup="dialog"
              onClick={() => sortSheet.current?.showModal()}
              className={button}
            >
              Ordenar
            </button>
          ) : null}
        </div>
      </div>
      {showFilters ? (
        <Sheet title="Filtros" options={filters} sheet={filterSheet} />
      ) : null}
      {showSorts ? (
        <Sheet title="Ordenar" options={sorts} sheet={sortSheet} />
      ) : null}
    </>
  );
}
