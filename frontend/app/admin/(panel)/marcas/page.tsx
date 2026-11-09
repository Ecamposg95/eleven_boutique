import type { Metadata } from "next";
import { BrandList } from "@/components/admin/BrandList";
import { PageHeadStatic } from "@/components/admin/static";
import { adminGetAll, requireMe } from "@/lib/admin/server";
import type { Brand } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Marcas" };

export default async function BrandsPage() {
  await requireMe("admin");
  const brands = (await adminGetAll<Brand>("/brands")) ?? [];
  return (
    <>
      <PageHeadStatic title="Marcas" />
      <BrandList brands={brands} />
    </>
  );
}
