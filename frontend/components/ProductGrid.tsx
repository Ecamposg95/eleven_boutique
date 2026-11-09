import { rhythmSlot, type RhythmSlot } from "@/lib/rhythm";
import type { ProductCard as Product } from "@/lib/types";
import { ProductCard } from "./ProductCard";

/** Ancho real de cada celda según su lugar en el ritmo, en móvil y en escritorio. */
function sizesFor(slot: RhythmSlot): string {
  const desktop = slot.wideDesktop
    ? "(min-width: 1600px) 740px, (min-width: 768px) 50vw"
    : "(min-width: 1600px) 360px, (min-width: 768px) 25vw";
  return `${desktop}, ${slot.wideMobile ? "100vw" : "50vw"}`;
}

export function ProductGrid({ products }: { products: Product[] }) {
  return (
    <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-12 md:gap-x-6 md:gap-y-14">
      {products.map((product, index) => {
        const slot = rhythmSlot(index, products.length);
        return (
          <li
            key={product.slug}
            className={[
              slot.wideMobile ? "col-span-2" : "col-span-1",
              slot.wideDesktop ? "md:col-span-6 md:row-span-2" : "md:col-span-3",
            ].join(" ")}
          >
            <ProductCard product={product} sizes={sizesFor(slot)} />
          </li>
        );
      })}
    </ul>
  );
}
