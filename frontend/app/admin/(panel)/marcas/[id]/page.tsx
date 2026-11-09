import type { Metadata } from "next";
import { BrandEditor } from "@/components/admin/BrandEditor";
import { adminGet, requireMe } from "@/lib/admin/server";
import type { Brand } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Editar marca" };

export default async function BrandPage({ params }: { params: Promise<{ id: string }> }) {
  await requireMe("admin");
  const { id } = await params;
  const brand = await adminGet<Brand>(`/brands/${encodeURIComponent(id)}`);
  return <BrandEditor key={brand.id} brand={brand} />;
}
