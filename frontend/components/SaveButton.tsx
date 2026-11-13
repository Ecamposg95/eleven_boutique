"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import {
  addPiece,
  getSelection,
  getServerSelection,
  hasPiece,
  removePieces,
  SELECTION_LIMIT,
  subscribeSelection,
  updateSelection,
  type SelectedPiece,
} from "@/lib/selection";

/** Guarda la pieza en «Mi selección» para consultarla junto con otras en un solo mensaje. */
export function SaveButton({ piece }: { piece: SelectedPiece }) {
  const pieces = useSyncExternalStore(subscribeSelection, getSelection, getServerSelection);
  const saved = hasPiece(pieces, piece.slug);
  const full = !saved && pieces.length >= SELECTION_LIMIT;

  return (
    <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1">
      <button
        type="button"
        aria-pressed={saved}
        disabled={full}
        onClick={() =>
          updateSelection((list) => (saved ? removePieces(list, [piece.slug]) : addPiece(list, piece)))
        }
        className="label inline-flex min-h-11 cursor-pointer items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span aria-hidden="true">{saved ? "●" : "○"}</span>
        {saved ? "En tu selección · Quitar" : "Guardar en mi selección"}
      </button>
      {pieces.length > 0 ? (
        <Link href="/seleccion" className="label cta muted">
          Ver selección ({pieces.length})
        </Link>
      ) : null}
      {full ? (
        <p className="muted w-full text-15">Tu selección llegó a {SELECTION_LIMIT} piezas.</p>
      ) : null}
    </div>
  );
}
