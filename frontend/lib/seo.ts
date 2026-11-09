import type { Metadata } from "next";

export const SITE_NAME = "Eleven Boutique";
export const DEFAULT_DESCRIPTION = "Catálogo digital multimarca de lujo para clientes en México.";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");

type PageMeta = {
  title: string;
  description?: string | null;
  path: string;
  image?: string | null;
  noindex?: boolean;
};

export function pageMeta({ title, description, path, image, noindex }: PageMeta): Metadata {
  const text = description?.trim() || DEFAULT_DESCRIPTION;
  // Las redes sociales no aceptan SVG como imagen de vista previa.
  const ogImage = image && !/\.svg($|[?#])/i.test(image) ? [{ url: image }] : undefined;
  return {
    title,
    description: text,
    alternates: { canonical: path },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description: text,
      url: path,
      siteName: SITE_NAME,
      locale: "es_MX",
      type: "website",
      images: ogImage,
    },
    robots: noindex ? { index: false, follow: true } : undefined,
  };
}

/** Serializa JSON-LD sin permitir que el contenido cierre el <script>. */
export function jsonLd(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
