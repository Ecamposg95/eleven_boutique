"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import { getSelection, getServerSelection, subscribeSelection } from "@/lib/selection";

/** Acceso a «Mi selección» en el encabezado; solo aparece cuando hay piezas guardadas. */
export function SelectionLink({
  onNavigate,
  className,
  asListItem,
}: {
  onNavigate?: () => void;
  className: string;
  asListItem?: boolean;
}) {
  const count = useSyncExternalStore(subscribeSelection, getSelection, getServerSelection).length;
  if (count === 0) return null;
  const link = (
    <Link href="/seleccion" onClick={onNavigate} className={className} aria-label={`Mi selección, ${count} piezas`}>
      <span aria-hidden="true">
        <span className="hidden sm:inline">Selección </span>({count})
      </span>
    </Link>
  );
  return asListItem ? <li>{link}</li> : link;
}
