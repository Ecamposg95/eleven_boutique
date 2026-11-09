"use client";

import Link from "next/link";
import { useId, useMemo, useState } from "react";
import { filterByName, groupByLetter } from "@/lib/brands";
import type { BrandSummary } from "@/lib/types";
import { brandHref } from "@/lib/url";
import { BrandMark } from "./BrandMark";

export function BrandDirectory({ brands }: { brands: BrandSummary[] }) {
  const inputId = useId();
  const [query, setQuery] = useState("");
  const visible = useMemo(() => filterByName(brands, query), [brands, query]);
  const groups = useMemo(() => groupByLetter(visible), [visible]);
  const trimmed = query.trim();

  return (
    <div className="pb-24">
      <div className="max-w-xl">
        <label htmlFor={inputId} className="block text-15">
          Filtrar por nombre
        </label>
        <input
          id={inputId}
          type="search"
          autoComplete="off"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="field mt-1"
        />
        <p aria-live="polite" className="muted mt-3 text-15">
          {visible.length === 1 ? "1 marca" : `${visible.length} marcas`}
        </p>
      </div>

      {groups.length > 0 ? (
        <>
          <nav
            aria-label="Índice por letra"
            className="sticky top-[var(--chrome-h)] z-10 -mx-[var(--gutter)] mt-8 overflow-x-auto bg-ink px-[var(--gutter)] md:static md:mx-0 md:px-0"
          >
            <ul className="flex md:flex-wrap md:gap-x-1">
              {groups.map((group) => (
                <li key={group.anchor}>
                  <a
                    href={`#${group.anchor}`}
                    aria-label={group.letter === "#" ? "Nombres que no empiezan con letra" : `Letra ${group.letter}`}
                    className="inline-flex min-h-11 min-w-9 items-center justify-center text-15 hover:underline"
                  >
                    {group.letter}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <div className="mt-8 space-y-12 md:mt-16 md:space-y-16">
            {groups.map((group) => (
              <section
                key={group.anchor}
                id={group.anchor}
                aria-labelledby={`${group.anchor}-t`}
                className="scroll-mt-[calc(var(--chrome-h)+3.5rem)] md:grid md:scroll-mt-[calc(var(--chrome-h)+1rem)] md:grid-cols-12 md:gap-x-6"
              >
                <h2 id={`${group.anchor}-t`} className="display text-44 text-bronze md:col-span-2">
                  {group.letter}
                </h2>
                <ul className="mt-3 grid gap-x-6 gap-y-3 md:col-span-10 md:mt-0 lg:grid-cols-2">
                  {group.items.map((brand) => (
                    <li key={brand.slug}>
                      <Link
                        href={brandHref(brand.slug)}
                        prefetch={false}
                        className="inline-block decoration-bronze decoration-1 underline-offset-[6px] hover:underline"
                      >
                        <BrandMark name={brand.name} logoUrl={brand.logo_url} />
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      ) : (
        <div className="mt-12">
          <p className="serif measure text-30">
            Sin resultados para «{trimmed}». Revise la ortografía o explore{" "}
            <button type="button" onClick={() => setQuery("")} className="link cursor-pointer">
              todas las marcas
            </button>
            .
          </p>
        </div>
      )}
    </div>
  );
}
