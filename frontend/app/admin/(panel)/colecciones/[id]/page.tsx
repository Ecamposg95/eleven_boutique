import type { Metadata } from "next";
import { ContentEditor } from "@/components/admin/ContentEditor";
import { adminGet, requireMe, resolveProductRefs } from "@/lib/admin/server";
import type { AdminCollection } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Editar colección" };

export default async function CollectionPage({ params }: { params: Promise<{ id: string }> }) {
  await requireMe();
  const { id } = await params;
  const item = await adminGet<AdminCollection>(`/collections/${encodeURIComponent(id)}`);
  const products = await resolveProductRefs(item.product_ids ?? []);
  return <ContentEditor key={item.id} kind="collection" item={item} products={products} />;
}
