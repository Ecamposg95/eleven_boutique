import type { Metadata } from "next";
import { BrandDirectory } from "@/components/BrandDirectory";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { getBrands } from "@/lib/api";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Marcas",
  description: "Directorio alfabético de las casas presentes en el catálogo de Eleven Boutique.",
  path: "/marcas",
});

export default async function BrandsPage() {
  const brands = await getBrands();
  return (
    <>
      <PageHeader title="Marcas" />
      <div className="page">
        {brands.length > 0 ? (
          <BrandDirectory brands={brands} />
        ) : (
          <EmptyState message="Las marcas se publicarán en cuanto el catálogo esté listo." />
        )}
      </div>
    </>
  );
}
