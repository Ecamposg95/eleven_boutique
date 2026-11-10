import Link from "next/link";
import type { ProductCard as Product } from "@/lib/types";
import { productHref } from "@/lib/url";
import { CatalogImage } from "./CatalogImage";

export function ProductCard({ product, sizes }: { product: Product; sizes: string }) {
  return (
    <Link href={productHref(product)} prefetch={false} className="group block">
      <span className="relative block aspect-[4/5] overflow-hidden bg-charcoal">
        <CatalogImage
          src={product.primary_image?.url}
          alt={product.primary_image?.alt ?? ""}
          sizes={sizes}
          className="bg-ink object-cover"
        />
        <CatalogImage
          src={product.secondary_image?.url}
          alt=""
          sizes={sizes}
          className="crossfade bg-ink object-cover"
        />
      </span>
      <span className="mt-3 block">
        {product.brand.name ? <span className="label muted block">{product.brand.name}</span> : null}
        <span className="mt-1 block text-17 font-medium tracking-[-0.01em] decoration-bronze decoration-1 underline-offset-4 group-hover:underline">
          {product.name}
        </span>
      </span>
    </Link>
  );
}
