import { describe, expect, it } from "vitest";
import { attentionLinks, closingImage, departmentPanels, giantWord, stripEntries, heroPhotos } from "./home";
import type { BrandSummary, Category, LookbookSummary, ProductCard, PublicSettings } from "./types";

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

describe("heroPhotos", () => {
  const hero = (extra: Partial<PublicSettings["hero"]>): PublicSettings["hero"] => ({
    image_url: null,
    headline: null,
    subhead: null,
    ...extra,
  });

  it("usa las parejas de la API y descarta repetidas, inválidas y versiones iguales", () => {
    expect(
      heroPhotos(
        hero({
          slides: [
            { image_url: "/media/a.jpg", mobile_image_url: "/media/a-tel.jpg" },
            { image_url: "/media/b.jpg", mobile_image_url: "/media/b.jpg" },
            { image_url: "/media/a.jpg", mobile_image_url: null },
            { image_url: "javascript:alert(1)", mobile_image_url: null },
            { image_url: "/media/c.jpg", mobile_image_url: "//otro.sitio/c.jpg" },
          ],
        }),
      ),
    ).toEqual([
      { src: "/media/a.jpg", mobile: "/media/a-tel.jpg" },
      { src: "/media/b.jpg", mobile: null },
      { src: "/media/c.jpg", mobile: null },
    ]);
  });

  it("sin parejas cae a la principal y la galería", () => {
    expect(heroPhotos(hero({ image_url: "/media/a.jpg", gallery: ["/media/b.jpg", "/media/a.jpg"] }))).toEqual([
      { src: "/media/a.jpg", mobile: null },
      { src: "/media/b.jpg", mobile: null },
    ]);
    expect(heroPhotos(hero({}))).toEqual([]);
  });
});

describe("departmentPanels", () => {
  const cat = (slug: string, parent: string | null = null, cover_url: string | null = null): Category => ({
    slug,
    name: slug.toUpperCase(),
    parent_slug: parent,
    product_count: 0,
    cover_url,
  });
  const sample = (category: Category, items: ProductCard[] = [], total = items.length) => ({
    category,
    items,
    total,
  });

  it("respeta el orden de las categorías", () => {
    const ropa = cat("ropa");
    const calzado = cat("calzado");
    const panels = departmentPanels(
      [ropa, calzado],
      [sample(calzado, [product]), sample(ropa, [product])],
    );
    expect(panels.map((p) => p.slug)).toEqual(["ropa", "calzado"]);
    expect(panels[0]).toMatchObject({ name: "ROPA", href: "/tienda/ropa", total: 1 });
  });

  it("una subcategoría nunca es panel", () => {
    const ropa = cat("ropa");
    const camisas = cat("camisas", "ropa");
    const panels = departmentPanels(
      [ropa, camisas],
      [sample(ropa, [product]), sample(camisas, [product])],
    );
    expect(panels.map((p) => p.slug)).toEqual(["ropa"]);
  });

  it("sin piezas pero con portada se incluye con products vacío", () => {
    const ropa = cat("ropa", null, "/r.jpg");
    const panels = departmentPanels([ropa], [sample(ropa)]);
    expect(panels).toEqual([
      { slug: "ropa", name: "ROPA", href: "/tienda/ropa", cover: "/r.jpg", products: [], total: 0 },
    ]);
  });

  it("sin piezas ni portada se excluye", () => {
    const ropa = cat("ropa");
    expect(departmentPanels([ropa], [sample(ropa)])).toEqual([]);
    expect(departmentPanels([ropa], [])).toEqual([]);
  });

  it("una portada inválida queda en null", () => {
    const ropa = cat("ropa", null, "javascript:x");
    const panels = departmentPanels([ropa], [sample(ropa, [product])]);
    expect(panels[0]?.cover).toBeNull();
  });
});

describe("attentionLinks", () => {
  const base = {
    demo_mode: false,
    whatsapp_enabled: true,
    site_name: "Eleven",
    hero: { image_url: null, headline: null, subhead: null },
    intro: null,
    boutique: { body: null },
    contact: { body: null },
  } satisfies PublicSettings;
  const attention = (extra: Partial<NonNullable<PublicSettings["attention"]>>) => ({
    headline: "Escríbenos. Te asesoramos.",
    subhead: null,
    image_url: null,
    mobile_image_url: null,
    whatsapp_url: "https://wa.me/525500000000?text=Hola",
    boutique_whatsapp_url: "https://wa.me/525511111111",
    ...extra,
  });

  it("devuelve los tres enlaces con datos válidos", () => {
    expect(
      attentionLinks({
        ...base,
        attention: attention({}),
        instagram_url: "https://www.instagram.com/eleven",
      }),
    ).toEqual({
      whatsapp: "https://wa.me/525500000000?text=Hola",
      boutique: "https://wa.me/525511111111",
      instagram: "https://www.instagram.com/eleven",
    });
  });

  it("acepta instagram.com sin www", () => {
    expect(attentionLinks({ ...base, instagram_url: "https://instagram.com/eleven" }).instagram).toBe(
      "https://instagram.com/eleven",
    );
  });

  it("un WhatsApp que no es wa.me queda en null", () => {
    const links = attentionLinks({
      ...base,
      attention: attention({ whatsapp_url: "http://evil", boutique_whatsapp_url: "https://wa.me.evil.com/1" }),
    });
    expect(links.whatsapp).toBeNull();
    expect(links.boutique).toBeNull();
  });

  it("un Instagram de otro sitio queda en null", () => {
    expect(attentionLinks({ ...base, instagram_url: "https://evil.com/x" }).instagram).toBeNull();
    expect(attentionLinks({ ...base, instagram_url: "https://instagram.com.evil.com/x" }).instagram).toBeNull();
  });

  it("sin attention (API anterior) los tres son null", () => {
    expect(attentionLinks(base)).toEqual({ whatsapp: null, boutique: null, instagram: null });
  });
});
