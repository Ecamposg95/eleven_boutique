import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CatalogImage } from "@/components/CatalogImage";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { ProductGrid } from "@/components/ProductGrid";
import { getCollection, soft } from "@/lib/api";
import { safeImageSrc } from "@/lib/images";
import { pageMeta } from "@/lib/seo";
import { decodeSlug } from "@/lib/url";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const collection = await soft(getCollection(decodeSlug((await params).slug)));
  if (!collection) return { title: "Colecciones" };
  return pageMeta({
    title: collection.title,
    description: collection.summary ?? `${collection.title}, colección de Eleven Boutique.`,
    path: `/colecciones/${encodeURIComponent(collection.slug)}`,
    image: collection.cover_url,
  });
}

export default async function CollectionPage({ params }: Props) {
  const collection = await getCollection(decodeSlug((await params).slug));
  if (!collection) notFound();
  const cover = safeImageSrc(collection.cover_url);
  return (
    <>
      <PageHeader title={collection.title}>
        {collection.summary ? <p className="serif measure mt-5 text-22">{collection.summary}</p> : null}
      </PageHeader>
      {cover ? (
        <div className="relative mb-16 aspect-[4/3] bg-charcoal md:mb-24 md:aspect-[5/2]">
          <CatalogImage src={cover} alt="" sizes="100vw" preload className="object-cover" />
        </div>
      ) : null}
      <div className="page pb-24">
        {collection.products.length > 0 ? (
          <ProductGrid products={collection.products} />
        ) : (
          <EmptyState message="Esta colección aún no tiene piezas publicadas." href="/colecciones" action="Ver todas las colecciones" />
        )}
      </div>
    </>
  );
}
