import { describe, expect, it } from "vitest";
import { addPiece, parseSelection, removePieces, SELECTION_LIMIT, type SelectedPiece } from "./selection";

const piece = (slug: string): SelectedPiece => ({
  slug,
  name: `Pieza ${slug}`,
  brand: "Prada",
  href: `/marcas/prada/${slug}`,
  image: { url: `/media/${slug}.jpg`, alt: "" },
});

describe("parseSelection", () => {
  it("devuelve vacío ante datos ausentes o dañados", () => {
    expect(parseSelection(null)).toEqual([]);
    expect(parseSelection("{no es json")).toEqual([]);
    expect(parseSelection('{"slug":"a"}')).toEqual([]);
  });

  it("descarta entradas inválidas, duplicadas y enlaces externos", () => {
    const raw = JSON.stringify([
      piece("a"),
      piece("a"),
      { slug: "b", name: "B", href: "https://otro.sitio/b" },
      { slug: "c" },
      { slug: "d", name: "D", href: "/piezas/d", brand: "", image: { alt: "sin url" } },
    ]);
    expect(parseSelection(raw)).toEqual([
      piece("a"),
      { slug: "d", name: "D", href: "/piezas/d", brand: null, image: null },
    ]);
  });

  it("respeta el tope", () => {
    const many = Array.from({ length: SELECTION_LIMIT + 5 }, (_, i) => piece(`p${i}`));
    expect(parseSelection(JSON.stringify(many))).toHaveLength(SELECTION_LIMIT);
  });
});

describe("addPiece / removePieces", () => {
  it("agrega al final sin duplicar", () => {
    const one = addPiece([], piece("a"));
    const two = addPiece(one, piece("b"));
    expect(two.map((p) => p.slug)).toEqual(["a", "b"]);
    expect(addPiece(two, piece("a"))).toBe(two);
  });

  it("no pasa del tope", () => {
    const full = Array.from({ length: SELECTION_LIMIT }, (_, i) => piece(`p${i}`));
    expect(addPiece(full, piece("extra"))).toBe(full);
  });

  it("quita varias a la vez", () => {
    const list = [piece("a"), piece("b"), piece("c")];
    expect(removePieces(list, ["a", "c"]).map((p) => p.slug)).toEqual(["b"]);
  });
});
