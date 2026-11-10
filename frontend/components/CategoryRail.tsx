"use client";

import Link from "next/link";
import { useRef } from "react";
import type { CategoryTile } from "@/lib/categories";
import { CatalogImage } from "./CatalogImage";

function Arrow({ flip }: { flip?: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 10"
      className={`h-2.5 w-4 ${flip ? "rotate-180" : ""}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
    >
      <path d="M0 5h15M11 1l4 4-4 4" />
    </svg>
  );
}

/** Carrusel horizontal de categorías: fichas verticales en blanco y negro con desplazamiento por pasos. */
export function CategoryRail({ tiles }: { tiles: CategoryTile[] }) {
  const track = useRef<HTMLUListElement>(null);
  const step = (direction: 1 | -1) => {
    const list = track.current;
    if (!list) return;
    const first = list.firstElementChild as HTMLElement | null;
    list.scrollBy({
      left: direction * (first?.offsetWidth ?? list.clientWidth * 0.8),
      behavior: "smooth",
    });
  };

  return (
    <section aria-labelledby="categorias-titulo" className="py-14 md:py-20">
      <div className="page mb-6 flex items-end justify-between gap-6">
        <h2 id="categorias-titulo" className="label">
          Comprar por categoría
        </h2>
        <div className="hidden gap-2 md:flex">
          <button
            type="button"
            onClick={() => step(-1)}
            aria-label="Anterior"
            className="inline-flex h-11 w-11 cursor-pointer items-center justify-center border border-bronze/40 hover:border-ivory"
          >
            <Arrow flip />
          </button>
          <button
            type="button"
            onClick={() => step(1)}
            aria-label="Siguiente"
            className="inline-flex h-11 w-11 cursor-pointer items-center justify-center border border-bronze/40 hover:border-ivory"
          >
            <Arrow />
          </button>
        </div>
      </div>
      <ul
        ref={track}
        className="flex snap-x snap-mandatory gap-2 overflow-x-auto scroll-smooth px-[var(--rail-pad)] scroll-px-[var(--rail-pad)] [--rail-pad:max(var(--gutter),calc((100vw-100rem)/2+var(--gutter)))] pb-2 [scrollbar-width:none] md:gap-3 [&::-webkit-scrollbar]:hidden"
      >
        {tiles.map((tile) => (
          <li
            key={tile.href}
            className="w-[70vw] shrink-0 snap-start sm:w-[42vw] md:w-[28vw] lg:w-[22vw]"
          >
            <Link href={tile.href} className="group block">
              <div className="mono relative aspect-[4/5] overflow-hidden bg-charcoal">
                {tile.image ? (
                  <CatalogImage
                    src={tile.image}
                    alt=""
                    sizes="(min-width: 1024px) 22vw, (min-width: 768px) 28vw, 70vw"
                    className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
                  />
                ) : (
                  <span
                    aria-hidden="true"
                    className="display absolute inset-0 flex items-center justify-center text-44 text-taupe"
                  >
                    {tile.label.slice(0, 1)}
                  </span>
                )}
              </div>
              <span className="label mt-3 flex items-center justify-between gap-4">
                {tile.label}
                <span
                  aria-hidden="true"
                  className="transition-transform duration-300 group-hover:translate-x-1"
                >
                  <Arrow />
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
