import { describe, expect, it } from "vitest";
import { nextHouse, splitShowroom } from "./showroom";
import type { BrandSummary } from "./types";

const brand = (slug: string, is_featured = false): BrandSummary => ({
  slug,
  name: slug,
  logo_url: null,
  is_featured,
  aliases: [],
  product_count: 0,
});

describe("splitShowroom", () => {
  it("keeps the featured order and leaves the stars out of the rest", () => {
    const all = [brand("acne"), brand("chanel", true), brand("hermes", true), brand("prada")];
    const featured = [brand("hermes", true), brand("chanel", true)];
    const { stars, rest } = splitShowroom(all, featured);
    expect(stars.map((b) => b.slug)).toEqual(["hermes", "chanel"]);
    expect(rest.map((b) => b.slug)).toEqual(["acne", "prada"]);
  });

  it("without stars, every brand is in the rest", () => {
    expect(splitShowroom([brand("acne")], []).rest).toHaveLength(1);
  });
});

describe("nextHouse", () => {
  it("advances and wraps around", () => {
    expect(nextHouse(0, 3)).toBe(1);
    expect(nextHouse(2, 3)).toBe(0);
  });

  it("is safe with no houses", () => {
    expect(nextHouse(0, 0)).toBe(0);
  });
});
