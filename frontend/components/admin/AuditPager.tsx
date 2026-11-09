"use client";

import { withParams } from "@/lib/url";
import { Pager } from "./ui";

export function AuditPager(props: { page: number; pageSize: number; total: number }) {
  return <Pager {...props} hrefFor={(page) => withParams("/admin/auditoria", { page })} />;
}
