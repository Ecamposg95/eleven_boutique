"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { HOUSE_MS, nextHouse } from "@/lib/showroom";
import type { BrandSummary } from "@/lib/types";
import { brandHref } from "@/lib/url";
import { BrandMark } from "./BrandMark";

/**
 * Showroom de portada: una casa estrella a la vez, en grande, con fundido lento.
 * Se pausa con el cursor encima, con foco de teclado, con la pestaña oculta y con el botón.
 * Con prefers-reduced-motion arranca en pausa: las casas se recorren con los indicadores.
 */
const REDUCED = "(prefers-reduced-motion: reduce)";

function subscribeReduced(onChange: () => void) {
  const query = window.matchMedia(REDUCED);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

export function HouseShowroom({ houses }: { houses: BrandSummary[] }) {
  const [active, setActive] = useState(0);
  // null: sin elección del visitante, manda prefers-reduced-motion.
  const [choice, setChoice] = useState<boolean | null>(null);
  const reduced = useSyncExternalStore(
    subscribeReduced,
    () => window.matchMedia(REDUCED).matches,
    () => false,
  );
  const stopped = choice ?? reduced;
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  const playing =
    houses.length > 1 && !stopped && !hovered && !focused && !hidden;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(
      () => setActive((index) => nextHouse(index, houses.length)),
      HOUSE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [playing, active, houses.length]);

  return (
    <section
      aria-roledescription="carrusel"
      aria-labelledby="showroom-t"
      className="flex h-[min(80svh,40rem)] min-h-[28rem] flex-col border-y border-bronze/30"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null))
          setFocused(false);
      }}
    >
      <div className="page flex min-h-0 flex-1 flex-col py-10 md:py-14">
        <h2 id="showroom-t" className="label muted">
          Casas destacadas
        </h2>

        <div
          className="wall-in relative min-h-0 flex-1"
          aria-live={playing ? "off" : "polite"}
        >
          {houses.map((house, index) => {
            const current = index === active;
            return (
              <div
                key={house.slug}
                aria-roledescription="casa"
                aria-label={`${index + 1} de ${houses.length}: ${house.name}`}
                inert={!current}
                className={`absolute inset-x-0 bottom-0 transition-opacity duration-[900ms] ease-out ${current ? "opacity-100" : "opacity-0"}`}
              >
                <Link
                  href={brandHref(house.slug)}
                  prefetch={false}
                  className="inline-block decoration-bronze decoration-1 underline-offset-[10px] hover:underline"
                >
                  <BrandMark
                    name={house.name}
                    logoUrl={house.logo_url}
                    textClass="giant block text-[clamp(3.25rem,1rem+9vw,9.5rem)] leading-[0.9]"
                    logoClass="h-28 w-[min(80vw,40rem)] md:h-44"
                  />
                </Link>
              </div>
            );
          })}
        </div>

        <div className="mt-8 flex shrink-0 flex-col gap-6 md:flex-row md:items-end md:justify-between">
          {houses.length > 1 ? (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <ul className="flex flex-wrap gap-1" aria-label="Casas">
                {houses.map((house, index) => (
                  <li key={house.slug}>
                    <button
                      type="button"
                      aria-label={`Ver ${house.name}`}
                      aria-current={index === active ? "true" : undefined}
                      onClick={() => setActive(index)}
                      className="flex h-6 w-7 items-center"
                    >
                      <span
                        aria-hidden="true"
                        className={`block h-px w-full transition-colors duration-300 ${index === active ? "bg-ivory" : "bg-bronze/50"}`}
                      />
                    </button>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => setChoice(!stopped)}
                className="link min-h-6 text-15"
              >
                {stopped ? "Reanudar" : "Pausar"}
              </button>
            </div>
          ) : (
            <span />
          )}
          <Link
            href="/marcas"
            className="label cta shrink-0 self-start md:self-auto"
          >
            Explorar marcas
          </Link>
        </div>
      </div>
    </section>
  );
}
