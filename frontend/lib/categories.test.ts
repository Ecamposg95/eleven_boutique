import { describe, expect, it } from "vitest";
import {
  categoryHref,
  brandOptions,
  childCategories,
  filterOptions,
  sortOptions,
  stockedCategories,
  topCategories,
} from "./categories";
import type { Category } from "./types";

const cat = (
  slug: string,
  parent: string | null = null,
  product_count = 0,
): Category => ({
  slug,
  name: slug.toUpperCase(),
  parent_slug: parent,
  product_count,
});
describe("categorías", () => {
  const all = [
    cat("ropa"),
    cat("camisas", "ropa"),
    cat("calzado"),
    cat("botas", "calzado"),
  ];

  it("separa principales e hijas", () => {
    expect(topCategories(all).map((c) => c.slug)).toEqual(["ropa", "calzado"]);
    expect(childCategories(all, "calzado").map((c) => c.slug)).toEqual([
      "botas",
    ]);
  });

  it("solo enlaza principales con piezas", () => {
    const list = [
      cat("ropa", null, 2),
      cat("camisas", "ropa", 2),
      cat("calzado"),
    ];
    expect(stockedCategories(list).map((c) => c.slug)).toEqual(["ropa"]);
  });

  it("codifica el slug en la dirección", () => {
    expect(categoryHref("artículos")).toBe("/tienda/art%C3%ADculos");
  });
});

describe("opciones del catálogo", () => {
  it("el orden conserva la categoría y marca el actual", () => {
    const options = sortOptions(
      "/tienda/ropa",
      { category: "camisas" },
      "name",
    );
    expect(options.map((o) => [o.href, o.current])).toEqual([
      ["/tienda/ropa?category=camisas", false],
      ["/tienda/ropa?category=camisas&sort=recent", false],
      ["/tienda/ropa?category=camisas&sort=name", true],
    ]);
  });

  it("los filtros empiezan con «Todas» y conservan el orden", () => {
    const options = filterOptions(
      "/marcas/x",
      [{ slug: "botas", name: "Botas" }],
      "botas",
      "recent",
    );
    expect(options).toEqual([
      { href: "/marcas/x?sort=recent", label: "Todas", current: false },
      {
        href: "/marcas/x?category=botas&sort=recent",
        label: "Botas",
        current: true,
      },
    ]);
  });
});

describe("brandOptions", () => {
  const brands = [
    { slug: "prada", name: "Prada" },
    { slug: "acne-studios", name: "Acne Studios" },
  ];

  it("pone «Todas las marcas» primero y marca como actual si no hay marca", () => {
    const options = brandOptions("/tienda/ropa", brands, undefined, undefined);
    expect(options[0]).toEqual({
      href: "/tienda/ropa",
      label: "Todas las marcas",
      current: true,
    });
    expect(options).toHaveLength(3);
    expect(options.slice(1).every((option) => !option.current)).toBe(true);
  });

  it("conserva el orden elegido en los href", () => {
    const options = brandOptions("/tienda", brands, "prada", "recent");
    expect(options[0]?.href).toBe("/tienda?sort=recent");
    expect(options[0]?.current).toBe(false);
    expect(options[1]).toEqual({
      href: "/tienda?brand=prada&sort=recent",
      label: "Prada",
      current: true,
    });
    expect(options[2]?.href).toBe("/tienda?brand=acne-studios&sort=recent");
  });
});
