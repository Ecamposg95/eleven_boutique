import type { Metadata } from "next";
import { ContentList } from "@/components/admin/ContentList";
import { PageHeadStatic } from "@/components/admin/static";
import { adminGetAll, requireMe } from "@/lib/admin/server";
import type { AdminLookbook } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Lookbooks" };

export default async function LookbooksPage() {
  await requireMe();
  const items = (await adminGetAll<AdminLookbook>("/lookbooks")) ?? [];
  return (
    <>
      <PageHeadStatic title="Lookbooks" />
      <ContentList
        items={items}
        basePath="/admin/lookbooks"
        endpoint="/lookbooks"
        createLabel="Título del lookbook"
        createAction="Crear lookbook"
        emptyMessage="Aún no hay lookbooks. Cree el primero y componga sus bloques de texto e imagen."
      />
    </>
  );
}
