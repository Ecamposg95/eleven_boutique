import type { Metadata } from "next";
import { CategoryManager } from "@/components/admin/CategoryManager";
import { PageHeadStatic } from "@/components/admin/static";
import { adminGetAll, requireMe } from "@/lib/admin/server";
import type { AdminCategory } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Categorías" };

export default async function CategoriesPage() {
  await requireMe();
  const categories = (await adminGetAll<AdminCategory>("/categories")) ?? [];
  return (
    <>
      <PageHeadStatic title="Categorías" />
      <CategoryManager categories={categories} />
    </>
  );
}
