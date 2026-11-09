import type { Metadata } from "next";
import { MediaWorkspace } from "@/components/admin/MediaWorkspace";
import { adminGet, requireMe } from "@/lib/admin/server";
import type { MediaAsset } from "@/lib/admin/types";
import { firstParam, parsePage } from "@/lib/url";

export const metadata: Metadata = { title: "Multimedia" };

const PAGE_SIZE = 48;

export default async function MediaPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireMe();
  const params = await searchParams;
  const q = firstParam(params.q) ?? "";
  const unused = firstParam(params.sin_usar) === "1";
  const page = parsePage(params.page);
  const data = await adminGet<{ items: MediaAsset[]; total: number }>("/media", {
    q,
    unused: unused ? "true" : undefined,
    page,
    page_size: PAGE_SIZE,
  });
  return <MediaWorkspace items={data.items} total={data.total} page={page} pageSize={PAGE_SIZE} q={q} unused={unused} />;
}
