"use client";

import { useRef, useState } from "react";
import type { Media } from "@/lib/types";
import { CatalogImage } from "./CatalogImage";

export function ProductGallery({ images, productName }: { images: Media[]; productName: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [current, setCurrent] = useState(0);
  const count = images.length;

  if (count === 0) {
    return <div className="aspect-[4/5] bg-charcoal" />;
  }

  const altFor = (image: Media) => image.alt || productName;
  const step = (delta: number) => setCurrent((index) => (index + delta + count) % count);
  const active = images[current];

  return (
    <>
      <ul className="space-y-4 md:space-y-6">
        {images.map((image, index) => (
          <li key={image.url}>
            {/* showModal guarda el elemento enfocado y le devuelve el foco al cerrar. */}
            <button
              type="button"
              aria-label={`Ampliar imagen ${index + 1} de ${count}: ${altFor(image)}`}
              onClick={() => {
                setCurrent(index);
                dialog.current?.showModal();
              }}
              className="relative block aspect-[4/5] w-full cursor-zoom-in bg-charcoal"
            >
              <CatalogImage
                src={image.url}
                alt=""
                sizes="(min-width: 1600px) 860px, (min-width: 1024px) 56vw, 100vw"
                preload={index === 0}
                className="bg-ink object-contain"
              />
            </button>
          </li>
        ))}
      </ul>

      <dialog
        ref={dialog}
        aria-label={`Imágenes de ${productName}`}
        onKeyDown={(event) => {
          if (event.key === "ArrowRight") step(1);
          if (event.key === "ArrowLeft") step(-1);
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) dialog.current?.close();
        }}
        className="m-0 h-dvh max-h-none w-full max-w-none bg-ink text-ivory open:flex open:flex-col"
      >
        <div className="page flex min-h-[var(--header-h)] items-center justify-between gap-4 text-15">
          <p aria-live="polite">{count > 1 ? `${current + 1} de ${count}` : ""}</p>
          <button type="button" onClick={() => dialog.current?.close()} className="-mr-2 min-h-11 min-w-11 cursor-pointer px-2 text-right">
            Cerrar
          </button>
        </div>
        <div className="relative mx-[var(--gutter)] min-h-0 flex-1">
          {active ? (
            <CatalogImage key={active.url} src={active.url} alt={altFor(active)} sizes="100vw" className="object-contain" />
          ) : null}
        </div>
        <div className="page flex min-h-[var(--header-h)] items-center gap-8 text-15">
          {count > 1 ? (
            <>
              <button type="button" onClick={() => step(-1)} className="min-h-11 min-w-11 cursor-pointer text-left">
                Anterior
              </button>
              <button type="button" onClick={() => step(1)} className="min-h-11 min-w-11 cursor-pointer text-left">
                Siguiente
              </button>
            </>
          ) : null}
        </div>
      </dialog>
    </>
  );
}
