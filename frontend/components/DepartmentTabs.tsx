"use client";

import Link from "next/link";
import { useId, useRef, useState, type KeyboardEvent } from "react";
import type { DepartmentPanel } from "@/lib/home";
import { CatalogImage } from "./CatalogImage";
import { ProductCard } from "./ProductCard";

const MAX_PIECES = 8;

/** Las fichas se deslizan de lado en teléfono y se acomodan en rejilla desde tablet. */
const SLIDER =
  "-mx-[var(--gutter)] flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-px-[var(--gutter)] px-[var(--gutter)] pb-2 [scrollbar-width:none] md:mx-0 md:px-0 md:pb-0 [&::-webkit-scrollbar]:hidden";

function CoverTile({
  panel,
  className,
  sizes,
}: {
  panel: DepartmentPanel;
  className: string;
  sizes: string;
}) {
  return (
    <li className={className}>
      <Link href={panel.href} className="group flex h-full flex-col">
        <span className="relative block aspect-[4/5] overflow-hidden bg-charcoal">
          <CatalogImage
            src={panel.cover}
            alt=""
            sizes={sizes}
            className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
          />
          {!panel.cover ? (
            <span
              aria-hidden="true"
              className="display absolute inset-0 flex items-center justify-center text-44 text-taupe"
            >
              {panel.name.slice(0, 1)}
            </span>
          ) : null}
        </span>
        <span className="label cta mt-3 self-start">{panel.name}</span>
      </Link>
    </li>
  );
}

/**
 * Departamentos de la tienda en pestañas, cada uno con su portada y sus piezas. Si ningún
 * departamento tiene piezas todavía, quedan solo las portadas como fichas que llevan a la tienda.
 */
export function DepartmentTabs({ panels }: { panels: DepartmentPanel[] }) {
  const baseId = useId();
  const [active, setActive] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);

  if (panels.length === 0) return null;

  const hasPieces = panels.some((panel) => panel.products.length > 0);

  if (!hasPieces) {
    return (
      <section
        aria-labelledby="departamentos-t"
        className="mono page py-14 md:py-20"
      >
        <h2 id="departamentos-t" className="label mb-6">
          Comprar por departamento
        </h2>
        <ul className={SLIDER}>
          {panels.map((panel) => (
            <CoverTile
              key={panel.slug}
              panel={panel}
              className="w-[70vw] shrink-0 snap-start sm:w-[42vw] md:w-[calc((100%-2.25rem)/4)]"
              sizes="(min-width: 1024px) 22vw, (min-width: 768px) 28vw, 70vw"
            />
          ))}
        </ul>
      </section>
    );
  }

  const select = (index: number) => {
    setActive(index);
    tabs.current[index]?.focus();
  };
  const onKeyDown = (event: KeyboardEvent) => {
    const last = panels.length - 1;
    // Las flechas parten de la pestaña con el foco, que puede no ser la activa.
    const focused = tabs.current.findIndex((tab) => tab === event.target);
    const from = focused === -1 ? active : focused;
    const next = {
      ArrowRight: from === last ? 0 : from + 1,
      ArrowLeft: from === 0 ? last : from - 1,
      Home: 0,
      End: last,
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    select(next);
  };

  return (
    <section
      aria-labelledby="departamentos-t"
      className="mono page py-14 md:py-20"
    >
      <h2 id="departamentos-t" className="label mb-6">
        Comprar por departamento
      </h2>
      <div
        role="tablist"
        aria-label="Departamentos"
        onKeyDown={onKeyDown}
        className="-mx-[var(--gutter)] mb-8 flex snap-x gap-2 overflow-x-auto scroll-px-[var(--gutter)] px-[var(--gutter)] [scrollbar-width:none] md:mx-0 md:px-0 [&::-webkit-scrollbar]:hidden"
      >
        {panels.map((panel, index) => (
          <button
            key={panel.slug}
            ref={(node) => {
              tabs.current[index] = node;
            }}
            type="button"
            role="tab"
            id={`${baseId}-tab-${index}`}
            aria-selected={index === active}
            aria-controls={`${baseId}-panel-${index}`}
            tabIndex={index === active ? 0 : -1}
            onClick={() => setActive(index)}
            className={`label inline-flex min-h-11 shrink-0 cursor-pointer snap-start items-center border px-5 transition-colors ${
              index === active
                ? "border-ivory bg-ivory text-ink"
                : "border-bronze/40 hover:border-ivory"
            }`}
          >
            {panel.name}
          </button>
        ))}
      </div>
      {panels.map((panel, index) => (
        <div
          key={panel.slug}
          role="tabpanel"
          id={`${baseId}-panel-${index}`}
          aria-labelledby={`${baseId}-tab-${index}`}
          hidden={index !== active}
        >
          {/* Solo el panel visible pinta sus fichas: los demás no cargan decenas de tarjetas ocultas. */}
          {index === active ? (
            <>
              <ul
                className={`${SLIDER} md:grid md:grid-cols-4 md:gap-y-10 md:overflow-visible`}
              >
                {panel.cover ? (
                  <CoverTile
                    panel={panel}
                    className="w-[78vw] shrink-0 snap-start sm:w-[50vw] md:col-span-2 md:row-span-2 md:w-auto"
                    sizes="(min-width: 768px) 50vw, 78vw"
                  />
                ) : null}
                {panel.products.slice(0, MAX_PIECES).map((product) => (
                  <li
                    key={product.slug}
                    className="w-[56vw] shrink-0 snap-start sm:w-[34vw] md:w-auto"
                  >
                    <ProductCard
                      product={product}
                      sizes="(min-width: 1600px) 360px, (min-width: 768px) 25vw, 56vw"
                    />
                  </li>
                ))}
              </ul>
              <Link href={panel.href} className="label cta mt-6">
                Ver todo {panel.name}
              </Link>
            </>
          ) : null}
        </div>
      ))}
    </section>
  );
}
