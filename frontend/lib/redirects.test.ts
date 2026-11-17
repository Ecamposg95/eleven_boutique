import { describe, expect, it } from "vitest";
import { LEGACY_REDIRECTS } from "./redirects";

const find = (source: string) => LEGACY_REDIRECTS.filter((rule) => rule.source === source);

describe("LEGACY_REDIRECTS", () => {
  it("todas son permanentes", () => {
    for (const rule of LEGACY_REDIRECTS) expect(rule.permanent).toBe(true);
  });

  it.each([
    ["/marcas", "/tienda/marcas"],
    ["/marcas/:slug", "/tienda/marcas/:slug"],
    ["/marcas/:slug/:producto", "/tienda/marcas/:slug/:producto"],
    ["/piezas/:slug", "/tienda/piezas/:slug"],
    ["/novedades", "/tienda?sort=recent"],
  ])("%s lleva a %s", (source, destination) => {
    const rules = find(source);
    expect(rules).toHaveLength(1);
    expect(rules[0]?.destination).toBe(destination);
  });

  it("/categorias/:slug con category va antes que la regla sin query", () => {
    const [withQuery, without, ...rest] = find("/categorias/:slug");
    if (!withQuery || !without) throw new Error("faltan reglas de /categorias/:slug");
    expect(rest).toHaveLength(0);
    expect(withQuery.has).toEqual([{ type: "query", key: "category", value: "(?<category>.+)" }]);
    expect(withQuery.destination).toBe("/tienda/:slug/:category");
    expect(without.has).toBeUndefined();
    expect(without.destination).toBe("/tienda/:slug");
    expect(LEGACY_REDIRECTS.indexOf(withQuery)).toBeLessThan(LEGACY_REDIRECTS.indexOf(without));
  });
});
