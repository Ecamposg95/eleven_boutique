import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProductView } from "@/components/ProductView";
import { getProduct, getSettings, soft } from "@/lib/api";
import { pageMeta } from "@/lib/seo";
import { decodeSlug, productHref } from "@/lib/url";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await soft(getProduct(decodeSlug((await params).slug)));
  if (!product || product.brand.slug) return { title: "Página no encontrada", robots: { index: false } };
  return pageMeta({
    title: product.seo_title ?? product.name,
    description: product.seo_description ?? `${product.name} en el catálogo de Eleven Boutique.`,
    path: productHref(product),
    image: product.primary_image?.url,
  });
}

export default async function UnbrandedProductPage({ params }: Props) {
  const slug = decodeSlug((await params).slug);
  const [product, settings] = await Promise.all([getProduct(slug), getSettings()]);
  // Las piezas con marca viven solo en /marcas/{marca}/{pieza}.
  if (!product || product.brand.slug) notFound();
  return <ProductView product={product} demoMode={settings.demo_mode} />;
}
