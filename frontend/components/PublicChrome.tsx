"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/** El encabezado y el pie públicos no pertenecen al panel, que trae su propia navegación y su <main>. */
export function PublicChrome({ top, footer, children }: { top: ReactNode; footer: ReactNode; children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return <>{children}</>;
  return (
    <>
      {top}
      <main id="contenido" tabIndex={-1} className="flex-1 outline-none">
        {children}
      </main>
      {footer}
    </>
  );
}
