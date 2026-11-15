"use client";

import Link from "next/link";
import { useRef } from "react";
import type { ProductCard as Product } from "@/lib/types";
import { SHOP_PATH } from "@/lib/url";
import { ProductCard } from "./ProductCard";

const MAX_PIECES = 12;

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

/** «Recién llegado»: carrusel de las piezas más nuevas, con flechas en computadora y deslizamiento en teléfono. */
export function NewArrivals({ products }: { products: Product[] }) {
  const track = useRef<HTMLUListElement>(null);
  if (products.length === 0) return null;

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
    <section aria-labelledby="recien-t" className="mono pb-14 md:pb-20">
      <div className="page mb-6 flex items-end justify-between gap-6">
        <h2 id="recien-t" className="display text-44">
          Recién llegado
        </h2>
        <div className="flex items-center gap-6">
          <Link href={`${SHOP_PATH}?sort=recent`} className="label cta">
            Ver todas
          </Link>
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
      </div>
      <ul
        ref={track}
        className="flex snap-x snap-mandatory gap-2 overflow-x-auto scroll-smooth px-[var(--rail-pad)] scroll-px-[var(--rail-pad)] [--rail-pad:max(var(--gutter),calc((100vw-100rem)/2+var(--gutter)))] pb-2 [scrollbar-width:none] md:gap-3 [&::-webkit-scrollbar]:hidden"
      >
        {products.slice(0, MAX_PIECES).map((product) => (
          <li
            key={product.slug}
            className="w-[56vw] shrink-0 snap-start sm:w-[34vw] md:w-[22vw] lg:w-[18vw]"
          >
            <ProductCard
              product={product}
              sizes="(min-width: 1024px) 18vw, (min-width: 768px) 22vw, 56vw"
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
