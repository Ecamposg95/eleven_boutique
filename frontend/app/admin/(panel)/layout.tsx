import type { ReactNode } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { requireMe } from "@/lib/admin/server";

export default async function PanelLayout({ children }: { children: ReactNode }) {
  const me = await requireMe();
  return <AdminShell me={me}>{children}</AdminShell>;
}
