import Link from "next/link";
import type { BrandSummary } from "@/lib/types";
import { brandHref } from "@/lib/url";

/** Los nombres de las casas como un solo párrafo enorme. Cada nombre es un enlace. */
export function BrandWall({ brands, className = "" }: { brands: BrandSummary[]; className?: string }) {
  return (
    <nav aria-label="Casas" className={className}>
      <ul className="wall">
        {brands.map((brand, index) => (
          <li key={brand.slug}>
            <Link href={brandHref(brand.slug)} prefetch={false}>
              {brand.name}
            </Link>
            {index < brands.length - 1 ? <span aria-hidden="true">, </span> : null}
          </li>
        ))}
      </ul>
    </nav>
  );
}
