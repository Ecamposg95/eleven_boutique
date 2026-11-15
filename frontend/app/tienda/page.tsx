import type { Metadata } from "next";
import { CatalogBar } from "@/components/CatalogBar";
import { CatalogListing } from "@/components/CatalogListing";
import { DepartmentChips } from "@/components/DepartmentChips";
import { PageHeader } from "@/components/PageHeader";
import { getBrandFacets, getCategories, getProducts } from "@/lib/api";
import {
  brandOptions,
  categoryHref,
  sortOptions,
  stockedCategories,
} from "@/lib/categories";
import { pageMeta } from "@/lib/seo";
import {
  firstParam,
  PAGE_SIZE,
  parsePage,
  parseSort,
  SHOP_PATH,
} from "@/lib/url";

export const metadata: Metadata = pageMeta({
  title: "Tienda",
  description:
    "Todas las piezas de las casas de lujo en el catálogo de Eleven Boutique.",
  path: SHOP_PATH,
});

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ShopPage({ searchParams }: Props) {
  const query = await searchParams;
  const sort = parseSort(query.sort);
  const page = parsePage(query.page);
  const [categories, facets] = await Promise.all([
    getCategories(),
    getBrandFacets(),
  ]);
  // Una marca que no está en las facetas se ignora.
  const requested = firstParam(query.brand)?.slice(0, 100);
  const brand = facets.some((facet) => facet.slug === requested)
    ? requested
    : undefined;
  const products = await getProducts({
    brand,
    sort,
    page,
    page_size: PAGE_SIZE,
  });

  const departments = stockedCategories(categories).map((department) => ({
    href: categoryHref(department.slug),
    label: department.name,
    current: false,
  }));

  return (
    <>
      <PageHeader title="Tienda">
        <DepartmentChips label="Departamentos" options={departments} />
      </PageHeader>
      <CatalogListing
        products={products}
        path={SHOP_PATH}
        brand={brand}
        sort={sort}
        page={page}
        emptyMessage="Aún no hay piezas publicadas."
      />
      <CatalogBar
        filters={[]}
        brands={brandOptions(SHOP_PATH, facets, brand, sort)}
        sorts={
          products.total > 1 ? sortOptions(SHOP_PATH, { brand }, sort) : []
        }
      />
    </>
  );
}
