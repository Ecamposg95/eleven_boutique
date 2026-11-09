import type { Metadata } from "next";
import { ProductEditor } from "@/components/admin/ProductEditor";
import { adminGet, adminGetAll, requireMe } from "@/lib/admin/server";
import type { AdminCategory, Brand, Product } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Editar producto" };

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  await requireMe();
  const { id } = await params;
  const [product, brands, categories] = await Promise.all([
    adminGet<Product>(`/products/${encodeURIComponent(id)}`),
    adminGetAll<Brand>("/brands"),
    adminGetAll<AdminCategory>("/categories"),
  ]);
  return (
    <ProductEditor
      key={product.id}
      product={product}
      brands={brands?.map(({ id: brandId, name }) => ({ id: brandId, name })) ?? null}
      categories={categories?.map(({ id: categoryId, name }) => ({ id: categoryId, name })) ?? null}
    />
  );
}
