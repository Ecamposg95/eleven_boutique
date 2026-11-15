"use client";

import { getImageProps } from "next/image";
import { useState } from "react";
import { bypassOptimizer, parseImageHosts } from "@/lib/images";
import type { HeroPhoto } from "@/lib/home";
import { CatalogImage } from "./CatalogImage";

const HOSTS = parseImageHosts(process.env.NEXT_PUBLIC_IMAGE_HOSTS);
/** Pantalla vertical (teléfono, tableta parada) → versión de teléfono. */
const PORTRAIT = "(orientation: portrait)";

/**
 * Foto de portada con dirección de arte: el navegador baja solo la versión que corresponde a la
 * forma de la pantalla. Sin versión de teléfono es una imagen normal.
 */
export function HeroPicture({
  photo,
  sizes,
  className,
  preload,
}: {
  photo: HeroPhoto;
  sizes: string;
  className: string;
  preload: boolean;
}) {
  const [failed, setFailed] = useState(false);
  if (!photo.mobile) {
    return <CatalogImage src={photo.src} alt="" sizes={sizes} preload={preload} className={className} />;
  }
  if (failed) return null;

  const common = { alt: "", fill: true, sizes } as const;
  const {
    props: { srcSet: mobileSet },
  } = getImageProps({ ...common, src: photo.mobile, unoptimized: bypassOptimizer(photo.mobile, HOSTS) });
  const { props } = getImageProps({
    ...common,
    src: photo.src,
    unoptimized: bypassOptimizer(photo.src, HOSTS),
    loading: preload ? "eager" : "lazy",
    fetchPriority: preload ? "high" : undefined,
  });

  return (
    <picture>
      <source media={PORTRAIT} srcSet={mobileSet ?? photo.mobile} sizes={sizes} />
      {/* eslint-disable-next-line jsx-a11y/alt-text -- props de getImageProps traen alt vacío: decorativa */}
      <img {...props} className={className} onError={() => setFailed(true)} />
    </picture>
  );
}
