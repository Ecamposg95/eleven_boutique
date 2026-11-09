import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { TextBody } from "@/components/TextBody";
import { getSettings } from "@/lib/api";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "La Boutique",
  description: "Información sobre Eleven Boutique.",
  path: "/la-boutique",
});

export default async function BoutiquePage() {
  const settings = await getSettings();
  const body = settings.boutique.body?.trim();
  return (
    <>
      <PageHeader title="La Boutique" />
      <div className="page pb-32">
        {body ? (
          <TextBody text={body} />
        ) : (
          <p className="serif measure text-30">La información de la boutique se publicará una vez confirmada.</p>
        )}
      </div>
    </>
  );
}
