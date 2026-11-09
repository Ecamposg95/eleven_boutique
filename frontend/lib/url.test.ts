import { describe, expect, it } from "vitest";
import { parsePage, parseSort, productHref, withParams } from "./url";

describe("withParams", () => {
  it("omite vacíos y la página 1", () => {
    expect(withParams("/marcas/x", { category: "", page: 1, sort: undefined })).toBe("/marcas/x");
    expect(withParams("/marcas/x", { category: "bolsos", page: 2 })).toBe("/marcas/x?category=bolsos&page=2");
  });
});

describe("productHref", () => {
  it("usa /marcas con marca y /piezas sin marca", () => {
    expect(productHref({ slug: "a", brand: { slug: "b", name: "B" } })).toBe("/marcas/b/a");
    expect(productHref({ slug: "a", brand: { slug: null, name: null } })).toBe("/piezas/a");
  });
});

describe("parsePage", () => {
  it("solo acepta enteros positivos", () => {
    expect(parsePage("3")).toBe(3);
    expect(parsePage(["2", "9"])).toBe(2);
    for (const bad of ["0", "-1", "abc", "1.5", undefined]) expect(parsePage(bad)).toBe(1);
  });
});

describe("parseSort", () => {
  it("usa lista blanca", () => {
    expect(parseSort("recent")).toBe("recent");
    expect(parseSort("name")).toBe("name");
    expect(parseSort("display")).toBeUndefined();
    expect(parseSort("x")).toBeUndefined();
  });
});
