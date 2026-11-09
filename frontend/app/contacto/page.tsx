import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { TextBody } from "@/components/TextBody";
import { getSettings } from "@/lib/api";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Contacto",
  description: "Datos de contacto de Eleven Boutique.",
  path: "/contacto",
});

export default async function ContactPage() {
  const settings = await getSettings();
  const body = settings.contact.body?.trim();
  return (
    <>
      <PageHeader title="Contacto" />
      <div className="page pb-32">
        {body ? (
          <TextBody text={body} />
        ) : (
          <p className="serif measure text-30">Los datos de contacto se publicarán una vez confirmados.</p>
        )}
      </div>
    </>
  );
}
