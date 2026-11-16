import Link from "next/link";
import { jsonLd, SITE_URL } from "@/lib/seo";
import type { Media, ProductDetail } from "@/lib/types";
import { brandHref, productHref } from "@/lib/url";
import { ConsultButton } from "./ConsultButton";
import { sizesOf } from "@/lib/sizes";
import { ProductGallery } from "./ProductGallery";
import { SaveButton } from "./SaveButton";
import { SoldOutLabel } from "./SoldOutLabel";

function orderedGallery(product: ProductDetail): Media[] {
  const images = product.gallery.length
    ? product.gallery
    : ([product.primary_image, product.secondary_image].filter(Boolean) as Media[]);
  return [...images].sort((a, b) => Number(b.is_primary) - Number(a.is_primary) || a.position - b.position);
}

/** Datos estructurados sin `offers`: este sitio no publica precios. */
function productSchema(product: ProductDetail, images: Media[]) {
  const absolute = (url: string) => (url.startsWith("/") ? `${SITE_URL}${url}` : url);
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    url: `${SITE_URL}${productHref(product)}`,
    category: product.category.name,
    image: images.map((image) => absolute(image.url)),
    ...(product.seo_description ? { description: product.seo_description } : {}),
    ...(product.brand.name ? { brand: { "@type": "Brand", name: product.brand.name } } : {}),
  };
}

export function ProductView({ product, demoMode }: { product: ProductDetail; demoMode: boolean }) {
  const images = orderedGallery(product);
  const sizes = sizesOf(product.variants);
  return (
    <article className="page grid gap-8 pb-24 pt-8 lg:grid-cols-12 lg:gap-x-6 lg:pt-12">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: jsonLd(productSchema(product, images)) }}
      />
      <div className="self-start lg:sticky lg:top-[calc(var(--chrome-h)+3rem)] lg:col-span-4 lg:col-start-9 lg:row-start-1">
        {product.brand.name && product.brand.slug ? (
          <p className="label">
            <Link href={brandHref(product.brand.slug)} className="cta">
              {product.brand.name}
            </Link>
          </p>
        ) : null}
        <h1 className="display mt-2 text-68">{product.name}</h1>
        {product.available ? null : <SoldOutLabel className="mt-4 text-17" />}
        {sizes.length ? (
          <div className="mt-6">
            <p className="label muted">Tallas</p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {sizes.map(({ size, available }) => (
                <li
                  key={size}
                  className={`min-w-11 border border-bronze px-3 py-2 text-center text-15 ${
                    available ? "" : "muted line-through"
                  }`}
                >
                  {size}
                  {available ? null : <span className="sr-only">, agotada</span>}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="mt-8">
          {product.consult_url ? (
            <>
              <ConsultButton href={product.consult_url} productSlug={product.slug} />
              <SaveButton
                piece={{
                  slug: product.slug,
                  name: product.name,
                  brand: product.brand.name,
                  href: productHref(product),
                  image: images[0] ? { url: images[0].url, alt: images[0].alt } : null,
                }}
              />
            </>
          ) : demoMode ? (
            <p className="muted text-15">Consulta desactivada: falta configurar WHATSAPP_NUMBER.</p>
          ) : null}
        </div>
      </div>
      <div className="lg:col-span-7 lg:row-start-1">
        <ProductGallery images={images} productName={product.name} />
      </div>
    </article>
  );
}
