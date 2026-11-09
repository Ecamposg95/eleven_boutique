import Link from "next/link";
import { jsonLd, SITE_URL } from "@/lib/seo";
import type { Media, ProductDetail } from "@/lib/types";
import { brandHref, productHref } from "@/lib/url";
import { ConsultButton } from "./ConsultButton";
import { ProductGallery } from "./ProductGallery";

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
  return (
    <article className="page grid gap-8 pb-24 pt-8 lg:grid-cols-12 lg:gap-x-6 lg:pt-12">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: jsonLd(productSchema(product, images)) }}
      />
      <div className="self-start lg:sticky lg:top-[calc(var(--chrome-h)+3rem)] lg:col-span-4 lg:col-start-9 lg:row-start-1">
        {product.brand.name && product.brand.slug ? (
          <p className="text-15">
            <Link href={brandHref(product.brand.slug)} className="link">
              {product.brand.name}
            </Link>
          </p>
        ) : null}
        <h1 className="display mt-3 text-44">{product.name}</h1>
        <div className="mt-8">
          {product.consult_url ? (
            <ConsultButton href={product.consult_url} productSlug={product.slug} />
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
