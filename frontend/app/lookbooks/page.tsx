import type { Metadata } from "next";
import { EditorialCard } from "@/components/EditorialCard";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { getLookbooks } from "@/lib/api";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Lookbooks",
  description: "Historias editoriales con piezas del catálogo de Eleven Boutique.",
  path: "/lookbooks",
});

export default async function LookbooksPage() {
  const lookbooks = await getLookbooks();
  return (
    <>
      <PageHeader title="Lookbooks" />
      <div className="page pb-24">
        {lookbooks.length > 0 ? (
          <ul className="grid gap-x-6 gap-y-16 md:grid-cols-2">
            {lookbooks.map((lookbook, index) => (
              <li key={lookbook.slug} className={index === 0 ? "md:col-span-2" : undefined}>
                <EditorialCard
                  href={`/lookbooks/${encodeURIComponent(lookbook.slug)}`}
                  title={lookbook.title}
                  summary={lookbook.summary}
                  cover={lookbook.cover_url}
                  wide={index === 0}
                />
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="Los lookbooks se publicarán en cuanto estén listos." href="/marcas" action="Explorar marcas" />
        )}
      </div>
    </>
  );
}
