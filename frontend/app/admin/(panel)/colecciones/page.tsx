import type { Metadata } from "next";
import { ContentList } from "@/components/admin/ContentList";
import { PageHeadStatic } from "@/components/admin/static";
import { adminGetAll, requireMe } from "@/lib/admin/server";
import type { AdminCollection } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Colecciones" };

export default async function CollectionsPage() {
  await requireMe();
  const items = (await adminGetAll<AdminCollection>("/collections")) ?? [];
  return (
    <>
      <PageHeadStatic title="Colecciones" />
      <ContentList
        items={items}
        basePath="/admin/colecciones"
        endpoint="/collections"
        createLabel="Título de la colección"
        createAction="Crear colección"
        emptyMessage="Aún no hay colecciones. Cree la primera y elija sus productos."
      />
    </>
  );
}
