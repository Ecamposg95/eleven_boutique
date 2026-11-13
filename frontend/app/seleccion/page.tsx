import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { SelectionView } from "@/components/SelectionView";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Mi selección",
  description: "Las piezas que guardaste para consultarlas juntas con Eleven Boutique.",
  path: "/seleccion",
  noindex: true,
});

export default function SelectionPage() {
  return (
    <>
      <PageHeader title="Mi selección" kicker="Guardada en este dispositivo">
        <p className="measure mt-8 text-17">
          Reúne las piezas que te interesan y envíalas en un solo mensaje. Te atendemos de forma
          personalizada por WhatsApp.
        </p>
      </PageHeader>
      <div className="page">
        <SelectionView />
      </div>
    </>
  );
}
