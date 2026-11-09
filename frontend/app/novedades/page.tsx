import type { Metadata } from "next";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { ProductGrid } from "@/components/ProductGrid";
import { getNovedades } from "@/lib/api";
import { pageMeta } from "@/lib/seo";
import { PAGE_SIZE, parsePage } from "@/lib/url";

export const metadata: Metadata = pageMeta({
  title: "Novedades",
  description: "Las piezas incorporadas más recientemente al catálogo de Eleven Boutique.",
  path: "/novedades",
});

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function NovedadesPage({ searchParams }: Props) {
  const page = parsePage((await searchParams).page);
  const novedades = await getNovedades({ page, page_size: PAGE_SIZE });
  return (
    <>
      <PageHeader title="Novedades" />
      <div className="page pb-24">
        {novedades.items.length > 0 ? (
          <ProductGrid products={novedades.items} />
        ) : novedades.total > 0 ? (
          <EmptyState message="Esta página no tiene piezas." href="/novedades" action="Volver a la primera página" />
        ) : (
          <EmptyState message="Por ahora no hay novedades publicadas." href="/marcas" action="Explorar marcas" />
        )}
        <Pagination path="/novedades" page={page} pageSize={novedades.page_size} total={novedades.total} />
      </div>
    </>
  );
}
