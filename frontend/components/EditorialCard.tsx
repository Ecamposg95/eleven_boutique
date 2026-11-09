import Link from "next/link";
import { CatalogImage } from "./CatalogImage";

/** Portada, título y resumen. Para colecciones y lookbooks. */
export function EditorialCard({
  href,
  title,
  summary,
  cover,
  wide = false,
}: {
  href: string;
  title: string;
  summary: string | null;
  cover: string | null;
  wide?: boolean;
}) {
  return (
    <Link href={href} prefetch={false} className="group block">
      <span className={`relative block overflow-hidden bg-charcoal ${wide ? "aspect-[8/5] md:aspect-[2/1]" : "aspect-[8/5]"}`}>
        <CatalogImage
          src={cover}
          alt=""
          sizes={wide ? "100vw" : "(min-width: 768px) 50vw, 100vw"}
          className="object-cover"
        />
      </span>
      <span className="display mt-4 block text-44 decoration-bronze decoration-1 underline-offset-4 group-hover:underline">
        {title}
      </span>
      {summary ? <span className="serif muted measure mt-2 block text-22">{summary}</span> : null}
    </Link>
  );
}
