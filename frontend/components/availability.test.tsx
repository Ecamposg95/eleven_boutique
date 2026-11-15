import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ProductCard as Card, ProductDetail } from "@/lib/types";
import { ProductCard } from "./ProductCard";
import { ProductView } from "./ProductView";

const card = (available: boolean): Card => ({
  slug: "x", name: "Pieza", brand: { slug: "b", name: "Marca" },
  category: { slug: "c", name: "Cat" }, primary_image: null, secondary_image: null, available,
});
const detail = (available: boolean, variants: ProductDetail["variants"]): ProductDetail => ({
  ...card(available), gallery: [], consult_url: "https://wa.me/1", seo_title: null,
  seo_description: null, published_at: null, variants,
});
const LABEL = "Agotada · consulta disponibilidad";

describe("ProductCard", () => {
  it("agotada muestra la etiqueta", () => {
    expect(renderToStaticMarkup(<ProductCard product={card(false)} sizes="10vw" />)).toContain(LABEL);
  });
  it("disponible no la muestra", () => {
    expect(renderToStaticMarkup(<ProductCard product={card(true)} sizes="10vw" />)).not.toContain("Agotada");
  });
});

describe("ProductView", () => {
  const variants = [
    { color: "Negro", size: "M", available: true },
    { color: "Negro", size: "Ch", available: false },
    { color: "Negro", size: "XL", available: true },
  ];
  it("lista tallas ordenadas y tacha las agotadas con aria-label", () => {
    const html = renderToStaticMarkup(<ProductView product={detail(true, variants)} demoMode={false} />);
    expect(html.indexOf(">Ch<")).toBeLessThan(html.indexOf(">M<"));
    expect(html.indexOf(">M<")).toBeLessThan(html.indexOf(">XL<"));
    expect(html).toContain('aria-label="Ch, agotada"');
    expect(html).toMatch(/line-through[^>]*aria-label="Ch, agotada"|aria-label="Ch, agotada"[^>]*line-through/);
    expect(html).not.toContain('aria-label="M, agotada"');
    expect(html).not.toContain(LABEL);
  });
  it("pieza agotada muestra la etiqueta en la ficha", () => {
    expect(renderToStaticMarkup(<ProductView product={detail(false, [])} demoMode={false} />)).toContain(LABEL);
  });
  it("sin variantes no hay lista de tallas", () => {
    expect(renderToStaticMarkup(<ProductView product={detail(true, [])} demoMode={false} />)).not.toContain("Tallas");
  });
});
