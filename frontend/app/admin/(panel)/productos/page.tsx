import type { Metadata } from "next";
import { ProductTable, type ProductFilters } from "@/components/admin/ProductTable";
import { PageHeadStatic } from "@/components/admin/static";
import { adminGet, adminGetAll, requireMe } from "@/lib/admin/server";
import type { AdminCategory, Brand, Product } from "@/lib/admin/types";
import { firstParam, parsePage } from "@/lib/url";

export const metadata: Metadata = { title: "Productos" };

const PAGE_SIZE = 50;
const STATUSES = new Set(["draft", "published", "archived"]);
const SORTS = new Set(["recent", "name", "sku"]);

export default async function ProductsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireMe();
  const params = await searchParams;
  const status = firstParam(params.status) ?? "";
  const sort = firstParam(params.sort) ?? "";
  const filters: ProductFilters = {
    q: firstParam(params.q) ?? "",
    status: STATUSES.has(status) ? status : "",
    brand: firstParam(params.brand) ?? "",
    category: firstParam(params.category) ?? "",
    sin_foto: firstParam(params.sin_foto) === "1",
    sort: SORTS.has(sort) ? sort : "",
    page: parsePage(params.page),
  };

  const [data, brands, categories] = await Promise.all([
    adminGet<{ items: Product[]; total: number; page_size?: number }>("/products", {
      q: filters.q,
      status: filters.status,
      brand: filters.brand,
      category: filters.category,
      has_photo: filters.sin_foto ? "false" : undefined,
      sort: filters.sort,
      page: filters.page,
      page_size: PAGE_SIZE,
    }),
    adminGetAll<Brand>("/brands"),
    adminGetAll<AdminCategory>("/categories"),
  ]);

  return (
    <>
      <PageHeadStatic title="Productos" />
      <ProductTable
        items={data.items}
        total={data.total}
        pageSize={data.page_size ?? PAGE_SIZE}
        filters={filters}
        brands={brands?.map(({ id, name }) => ({ id, name })) ?? null}
        categories={categories?.map(({ id, name }) => ({ id, name })) ?? null}
      />
    </>
  );
}
