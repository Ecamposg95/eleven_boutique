import { describe, expect, it } from "vitest";
import { brandHref, departmentHref, parsePage, parseSort, productHref, SHOP_PATH, withParams } from "./url";

describe("withParams", () => {
  it("omite vacíos y la página 1", () => {
    expect(withParams("/marcas/x", { category: "", page: 1, sort: undefined })).toBe("/marcas/x");
    expect(withParams("/marcas/x", { category: "bolsos", page: 2 })).toBe("/marcas/x?category=bolsos&page=2");
  });
});

describe("productHref", () => {
  it("usa /tienda/marcas con marca y /tienda/piezas sin marca", () => {
    expect(productHref({ slug: "a", brand: { slug: "b", name: "B" } })).toBe("/tienda/marcas/b/a");
    expect(productHref({ slug: "a", brand: { slug: null, name: null } })).toBe("/tienda/piezas/a");
  });
  it("codifica caracteres especiales", () => {
    expect(productHref({ slug: "a b", brand: { slug: "é", name: "E" } })).toBe("/tienda/marcas/%C3%A9/a%20b");
  });
});

describe("brandHref y departmentHref", () => {
  it("cuelgan de /tienda", () => {
    expect(SHOP_PATH).toBe("/tienda");
    expect(brandHref("acne")).toBe("/tienda/marcas/acne");
    expect(brandHref("é")).toBe("/tienda/marcas/%C3%A9");
    expect(departmentHref("ropa")).toBe("/tienda/ropa");
    expect(departmentHref("ropa", "camisas")).toBe("/tienda/ropa/camisas");
    expect(departmentHref("artículos", "a/b")).toBe("/tienda/art%C3%ADculos/a%2Fb");
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
