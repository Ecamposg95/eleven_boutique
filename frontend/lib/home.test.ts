import { describe, expect, it } from "vitest";
import { closingImage, giantWord, stripEntries } from "./home";
import type { BrandSummary, LookbookSummary, ProductCard } from "./types";

const lookbook = (slug: string): LookbookSummary => ({
  slug,
  title: `Look ${slug}`,
  summary: null,
  cover_url: `/${slug}.jpg`,
});
const brand = (slug: string): BrandSummary => ({
  slug,
  name: slug,
  logo_url: null,
  is_featured: false,
  aliases: [],
  product_count: 0,
});
const product: ProductCard = {
  slug: "p",
  name: "P",
  brand: { slug: null, name: null },
  category: { slug: "c", name: "C" },
  primary_image: { url: "/p.jpg", alt: "", is_primary: true, position: 0 },
  secondary_image: null,
};

describe("stripEntries", () => {
  it("prefiere lookbooks y corta en tres", () => {
    const entries = stripEntries({
      lookbooks: ["a", "b", "c", "d"].map(lookbook),
      novedades: [product],
      brands: [brand("x")],
      boutique: true,
    });
    expect(entries.map((e) => e.href)).toEqual([
      "/lookbooks/a",
      "/lookbooks/b",
      "/lookbooks/c",
    ]);
  });

  it("completa con novedades, casas y boutique", () => {
    const entries = stripEntries({
      lookbooks: [lookbook("a")],
      novedades: [product],
      brands: [brand("x"), brand("y")],
      boutique: true,
    });
    expect(entries.map((e) => e.kicker)).toEqual([
      "Lookbook",
      "Novedades",
      "Las casas",
    ]);
    expect(entries[1]?.image).toBe("/p.jpg");
    expect(entries[2]).toMatchObject({
      title: "2 casas, una boutique",
      image: null,
      mark: "2",
    });
  });

  it("sin contenido no hay entradas", () => {
    expect(
      stripEntries({
        lookbooks: [],
        novedades: [],
        brands: [],
        boutique: false,
      }),
    ).toEqual([]);
  });
});

describe("closingImage", () => {
  it("usa lookbook, luego colección con portada, luego la portada", () => {
    expect(closingImage([lookbook("a")], [], "/h.jpg")).toBe("/a.jpg");
    expect(
      closingImage(
        [],
        [
          {
            slug: "c",
            title: "C",
            summary: null,
            cover_url: "/c.jpg",
            product_count: 1,
          },
        ],
        "/h.jpg",
      ),
    ).toBe("/c.jpg");
    expect(closingImage([], [], null)).toBeNull();
  });
});

describe("giantWord", () => {
  it("toma la primera palabra del nombre", () => {
    expect(giantWord("Eleven Boutique")).toBe("Eleven");
    expect(giantWord("  Eleven  ")).toBe("Eleven");
  });
});
