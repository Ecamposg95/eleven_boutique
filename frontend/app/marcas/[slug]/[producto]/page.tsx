import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { ProductView } from "@/components/ProductView";
import { getBrand, getProduct, getSettings, soft } from "@/lib/api";
import { pageMeta } from "@/lib/seo";
import { decodeSlug, productHref } from "@/lib/url";

type Props = { params: Promise<{ slug: string; producto: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug, producto } = await params;
  const product = await soft(getProduct(decodeSlug(producto)));
  if (!product || !product.brand.slug || product.brand.slug !== decodeSlug(slug)) {
    return { title: "Página no encontrada", robots: { index: false } };
  }
  return pageMeta({
    title: product.seo_title ?? `${product.name}, ${product.brand.name}`,
    description:
      product.seo_description ?? `${product.name} de ${product.brand.name} en el catálogo de Eleven Boutique.`,
    path: productHref(product),
    image: product.primary_image?.url,
  });
}

export default async function ProductPage({ params }: Props) {
  const { slug: rawBrand, producto } = await params;
  const brandSlug = decodeSlug(rawBrand);
  const [product, settings] = await Promise.all([getProduct(decodeSlug(producto)), getSettings()]);
  if (!product || !product.brand.slug) notFound();

  if (product.brand.slug !== brandSlug) {
    // Solo un alias de la misma marca lleva a la ficha; cualquier otra marca es 404.
    const brand = await getBrand(brandSlug);
    if (brand?.slug !== product.brand.slug) notFound();
    permanentRedirect(productHref(product));
  }

  return <ProductView product={product} demoMode={settings.demo_mode} />;
}
