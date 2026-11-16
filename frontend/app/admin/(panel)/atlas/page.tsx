import type { Metadata } from "next";
import { AtlasPanel } from "@/components/admin/AtlasPanel";
import { PageHeadStatic } from "@/components/admin/static";
import { brandMapOptions } from "@/lib/admin/atlas";
import { adminGet, adminGetAll, requireMe } from "@/lib/admin/server";
import type { AdminCategory, AtlasBrandMapRow, AtlasCategoryMapRow, AtlasStatus, Brand } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Atlas ONE" };

export default async function AtlasPage() {
  await requireMe("admin");
  const [status, brandMap, categoryMap, brands, categories] = await Promise.all([
    adminGet<AtlasStatus>("/atlas/status"),
    adminGet<AtlasBrandMapRow[]>("/atlas/brand-map"),
    adminGet<AtlasCategoryMapRow[]>("/atlas/category-map"),
    adminGetAll<Brand>("/brands"),
    adminGetAll<AdminCategory>("/categories"),
  ]);
  return (
    <>
      <PageHeadStatic title="Atlas ONE" />
      <AtlasPanel
        initial={status}
        brandMap={brandMap}
        categoryMap={categoryMap}
        brands={brandMapOptions(brands ?? [])}
        categories={(categories ?? []).map(({ id, name, parent_id }) => ({ id, name, parent_id }))}
      />
    </>
  );
}
