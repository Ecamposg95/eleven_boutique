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
      <PageHeader title="La Boutique" kicker="Eleven · Fashion boutique" />
      <div className="page pb-32 md:grid md:grid-cols-12 md:gap-x-6">
        {body ? (
          <div className="md:col-span-7 md:col-start-4">
            <TextBody text={body} />
          </div>
        ) : (
          <p className="serif measure text-30">La información de la boutique se publicará una vez confirmada.</p>
        )}
      </div>
    </>
  );
}
