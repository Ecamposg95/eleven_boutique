"use client";

import Image from "next/image";
import { useState } from "react";
import { bypassOptimizer, parseImageHosts, safeImageSrc } from "@/lib/images";

const HOSTS = parseImageHosts(process.env.NEXT_PUBLIC_IMAGE_HOSTS);

type Props = {
  src: string | null | undefined;
  alt: string;
  sizes: string;
  className?: string;
  preload?: boolean;
  onFail?: () => void;
};

/** Imagen que llena su contenedor posicionado. Si falta o falla no pinta nada: queda el tono de fondo. */
export function CatalogImage({ src, alt, sizes, className, preload, onFail }: Props) {
  const [failed, setFailed] = useState(false);
  const safe = safeImageSrc(src);
  if (!safe || failed) return null;
  return (
    <Image
      src={safe}
      alt={alt}
      fill
      sizes={sizes}
      preload={preload}
      unoptimized={bypassOptimizer(safe, HOSTS)}
      className={className}
      onError={() => {
        setFailed(true);
        onFail?.();
      }}
    />
  );
}
