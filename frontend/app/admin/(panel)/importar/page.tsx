import type { Metadata } from "next";
import { ImportFlow } from "@/components/admin/ImportFlow";
import { PageHeadStatic } from "@/components/admin/static";
import { requireMe } from "@/lib/admin/server";

export const metadata: Metadata = { title: "Importar" };

export default async function ImportPage() {
  await requireMe("admin");
  return (
    <>
      <PageHeadStatic title="Importar catálogo" />
      <ImportFlow />
    </>
  );
}
