import Link from "next/link";
import { CatalogImage } from "./CatalogImage";

/** Portada en blanco y negro, número, título y resumen. Para colecciones y lookbooks. */
export function EditorialCard({
  href,
  title,
  summary,
  cover,
  index,
  wide = false,
}: {
  href: string;
  title: string;
  summary: string | null;
  cover: string | null;
  index?: number;
  wide?: boolean;
}) {
  return (
    <Link href={href} prefetch={false} className="group block">
      <span
        className={`mono relative block overflow-hidden bg-charcoal ${wide ? "aspect-[4/5] md:aspect-[2/1]" : "aspect-[4/5]"}`}
      >
        <CatalogImage
          src={cover}
          alt=""
          sizes={wide ? "100vw" : "(min-width: 768px) 50vw, 100vw"}
          className="object-cover transition-transform duration-700 group-hover:scale-[1.02]"
        />
      </span>
      <span className="mt-4 flex items-baseline justify-between gap-6">
        <span className="min-w-0">
          {index !== undefined ? <span className="label muted block">{String(index + 1).padStart(2, "0")}</span> : null}
          <span className="display mt-1 block text-30 md:text-44">{title}</span>
        </span>
        <span className="label cta shrink-0">Explorar</span>
      </span>
      {summary ? <span className="serif muted measure mt-2 block text-22">{summary}</span> : null}
    </Link>
  );
}
