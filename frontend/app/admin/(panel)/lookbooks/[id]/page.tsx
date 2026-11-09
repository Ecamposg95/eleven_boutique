import type { Metadata } from "next";
import { ContentEditor } from "@/components/admin/ContentEditor";
import { adminGet, requireMe, resolveProductRefs } from "@/lib/admin/server";
import type { AdminLookbook } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Editar lookbook" };

export default async function LookbookPage({ params }: { params: Promise<{ id: string }> }) {
  await requireMe();
  const { id } = await params;
  const item = await adminGet<AdminLookbook>(`/lookbooks/${encodeURIComponent(id)}`);
  const products = await resolveProductRefs(item.product_ids ?? []);
  return <ContentEditor key={item.id} kind="lookbook" item={item} products={products} blocks={item.blocks ?? []} />;
}
