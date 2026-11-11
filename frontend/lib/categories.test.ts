import { describe, expect, it } from "vitest";
import {
  categoryHref,
  categoryTiles,
  childCategories,
  filterOptions,
  sortOptions,
  stockedCategories,
  topCategories,
} from "./categories";
import type { Category, ProductCard } from "./types";

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
const product = (url: string): ProductCard => ({
  slug: url,
  name: url,
  brand: { slug: null, name: null },
  category: { slug: "c", name: "C" },
  primary_image: { url, alt: "", is_primary: true, position: 0 },
  secondary_image: null,
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

  it("arma fichas con novedades primero y omite categorías vacías", () => {
    const tiles = categoryTiles(
      [product("/n.jpg")],
      [
        { category: cat("ropa"), total: 3, items: [product("/r.jpg")] },
        { category: cat("calzado"), total: 0, items: [] },
      ],
    );
    expect(tiles).toEqual([
      { href: "/novedades", label: "Novedades", image: "/n.jpg", count: 1 },
      { href: "/categorias/ropa", label: "ROPA", image: "/r.jpg", count: 3 },
    ]);
  });

  it("sin novedades ni piezas no hay fichas", () => {
    expect(
      categoryTiles([], [{ category: cat("ropa"), total: 0, items: [] }]),
    ).toEqual([]);
  });

  it("no repite la foto de otra ficha si la categoría tiene otra", () => {
    const tiles = categoryTiles(
      [product("/a.jpg")],
      [
        {
          category: cat("ropa"),
          total: 2,
          items: [product("/a.jpg"), product("/b.jpg")],
        },
        { category: cat("calzado"), total: 1, items: [product("/a.jpg")] },
      ],
    );
    expect(tiles.map((t) => t.image)).toEqual(["/a.jpg", "/b.jpg", "/a.jpg"]);
  });

  it("codifica el slug en la dirección", () => {
    expect(categoryHref("artículos")).toBe("/categorias/art%C3%ADculos");
  });
});

describe("opciones del catálogo", () => {
  it("el orden conserva la categoría y marca el actual", () => {
    const options = sortOptions(
      "/categorias/ropa",
      { category: "camisas" },
      "name",
    );
    expect(options.map((o) => [o.href, o.current])).toEqual([
      ["/categorias/ropa?category=camisas", false],
      ["/categorias/ropa?category=camisas&sort=recent", false],
      ["/categorias/ropa?category=camisas&sort=name", true],
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
