"use client";

import { useState } from "react";
import { safeImageSrc } from "@/lib/images";
import { CatalogImage } from "./CatalogImage";

/** Logotipo si existe y carga; si no, el nombre en Cormorant. */
export function BrandMark({
  name,
  logoUrl,
  textClass = "text-44",
  logoClass = "h-12 w-48",
}: {
  name: string;
  logoUrl: string | null;
  textClass?: string;
  logoClass?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!safeImageSrc(logoUrl) || failed) {
    return <span className={`display ${textClass}`}>{name}</span>;
  }
  return (
    <span className={`relative inline-block align-middle ${logoClass}`}>
      <CatalogImage
        src={logoUrl}
        alt={name}
        sizes="192px"
        className="object-contain object-left"
        onFail={() => setFailed(true)}
      />
    </span>
  );
}
