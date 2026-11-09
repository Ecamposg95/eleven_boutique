import type { Metadata } from "next";
import { SettingsForm } from "@/components/admin/SettingsForm";
import { PageHeadStatic } from "@/components/admin/static";
import { adminGet, requireMe } from "@/lib/admin/server";
import type { AdminSettings } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Configuración" };

export default async function SettingsPage() {
  await requireMe("admin");
  const settings = await adminGet<AdminSettings>("/settings");
  return (
    <>
      <PageHeadStatic title="Configuración" />
      <SettingsForm settings={settings} />
    </>
  );
}
