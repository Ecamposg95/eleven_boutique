"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { nextHouse } from "@/lib/showroom";
import { CatalogImage } from "./CatalogImage";

/** Cuánto permanece cada foto de portada antes del fundido a la siguiente. */
export const SLIDE_MS = 6000;
const REDUCED = "(prefers-reduced-motion: reduce)";

function subscribeReduced(onChange: () => void) {
  const query = window.matchMedia(REDUCED);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/**
 * Fotos de portada apiladas que se turnan con fundido lento. Una sola foto no rota.
 * Se pausa con la pestaña oculta y con el botón; con prefers-reduced-motion arranca en pausa.
 */
export function HeroSlides({
  images,
  sizes,
  imageClassName = "",
  controlsClassName = "absolute inset-x-0 bottom-0 px-4 pb-3",
}: {
  images: string[];
  sizes: string;
  imageClassName?: string;
  controlsClassName?: string;
}) {
  const [active, setActive] = useState(0);
  const [choice, setChoice] = useState<boolean | null>(null);
  const reduced = useSyncExternalStore(subscribeReduced, () => window.matchMedia(REDUCED).matches, () => false);
  const [hidden, setHidden] = useState(false);
  const stopped = choice ?? reduced;
  const playing = images.length > 1 && !stopped && !hidden;

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => setActive((index) => nextHouse(index, images.length)), SLIDE_MS);
    return () => window.clearTimeout(timer);
  }, [playing, active, images.length]);

  return (
    <>
      {images.map((src, index) => (
        <div
          key={src}
          aria-hidden={index !== active}
          className={`absolute inset-0 transition-opacity duration-[1200ms] ease-out ${index === active ? "opacity-100" : "opacity-0"}`}
        >
          <CatalogImage src={src} alt="" sizes={sizes} preload={index === 0} className={`object-cover ${imageClassName}`} />
        </div>
      ))}
      {images.length > 1 ? (
        <div className={`flex items-center justify-between gap-4 text-[#efece6] ${controlsClassName}`}>
          <ul className="flex gap-1" aria-label="Fotos de portada">
            {images.map((src, index) => (
              <li key={src}>
                <button
                  type="button"
                  aria-label={`Ver foto ${index + 1} de ${images.length}`}
                  aria-current={index === active ? "true" : undefined}
                  onClick={() => setActive(index)}
                  className="flex h-6 w-7 cursor-pointer items-center"
                >
                  <span
                    aria-hidden="true"
                    className={`block h-px w-full transition-opacity duration-300 ${index === active ? "bg-current" : "bg-current opacity-40"}`}
                  />
                </button>
              </li>
            ))}
          </ul>
          <button type="button" onClick={() => setChoice(!stopped)} className="label min-h-6 cursor-pointer">
            {stopped ? "Reanudar" : "Pausar"}
          </button>
        </div>
      ) : null}
    </>
  );
}
