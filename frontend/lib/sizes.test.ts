import { describe, expect, it } from "vitest";
import { sizesOf, sortSizes } from "./sizes";

describe("sortSizes", () => {
  it("ordena la secuencia común sin importar mayúsculas", () => {
    expect(sortSizes(["XL", "m", "XXS", "G", "Ch", "xs", "XXL", "XXXL"])).toEqual([
      "XXS", "xs", "Ch", "m", "G", "XL", "XXL", "XXXL",
    ]);
  });
  it("trata S como Ch y L como G", () => {
    expect(sortSizes(["L", "M", "S"])).toEqual(["S", "M", "L"]);
  });
  it("ordena las numéricas de menor a mayor", () => {
    expect(sortSizes(["10", "8", "9.5", "28"])).toEqual(["8", "9.5", "10", "28"]);
  });
  it("deja las desconocidas al final conservando su orden", () => {
    expect(sortSizes(["Unica", "M", "Extra", "Ch"])).toEqual(["Ch", "M", "Unica", "Extra"]);
  });
});

describe("sizesOf", () => {
  it("agrupa por talla, ordena y marca agotada solo si todas las variantes lo están", () => {
    const variants = [
      { color: "Negro", size: "M", available: false },
      { color: "Blanco", size: "M", available: true },
      { color: "Negro", size: "Ch", available: false },
      { color: null, size: null, available: true },
    ];
    expect(sizesOf(variants)).toEqual([
      { size: "Ch", available: false },
      { size: "M", available: true },
    ]);
  });
  it("vacío sin variantes", () => {
    expect(sizesOf([])).toEqual([]);
  });
});
