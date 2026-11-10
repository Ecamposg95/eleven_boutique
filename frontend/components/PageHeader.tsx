import type { ReactNode } from "react";

/** Encabezado de página tipo revista: etiqueta opcional, título grande en letra gruesa y filete. */
export function PageHeader({ title, kicker, children }: { title: string; kicker?: string; children?: ReactNode }) {
  return (
    <header className="page pb-10 pt-12 md:pb-16 md:pt-20">
      {kicker ? <p className="label muted mb-4">{kicker}</p> : null}
      <h1 className="display text-104">{title}</h1>
      <span aria-hidden="true" className="mt-6 block h-px w-8 bg-ivory" />
      {children}
    </header>
  );
}
