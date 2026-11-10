import type { Metadata } from "next";
import { EditorialCard } from "@/components/EditorialCard";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { getCollections } from "@/lib/api";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Colecciones",
  description: "Selecciones de piezas reunidas por Eleven Boutique.",
  path: "/colecciones",
});

export default async function CollectionsPage() {
  const collections = await getCollections();
  return (
    <>
      <PageHeader title="Colecciones" />
      <div className="page pb-24">
        {collections.length > 0 ? (
          <ul className="grid gap-x-6 gap-y-16 md:grid-cols-2">
            {collections.map((collection, index) => (
              <li key={collection.slug} className={index === 0 ? "md:col-span-2" : undefined}>
                <EditorialCard
                  href={`/colecciones/${encodeURIComponent(collection.slug)}`}
                  title={collection.title}
                  summary={collection.summary}
                  cover={collection.cover_url}
                  wide={index === 0}
                  index={index}
                />
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="Las colecciones se publicarán en cuanto estén listas." href="/marcas" action="Explorar marcas" />
        )}
      </div>
    </>
  );
}
