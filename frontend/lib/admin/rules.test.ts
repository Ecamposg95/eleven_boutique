import { describe, expect, it } from "vitest";
import {
  assignPayload,
  auditLabel,
  auditValue,
  chunk,
  confirmAllProposed,
  hasRole,
  missingForPublish,
  navFor,
  parseValidationMessage,
  primaryImageUrl,
  summarizeBulk,
  toDecisions,
} from "./rules";
import type { MatchProposal } from "./types";

describe("roles", () => {
  it("ordena los roles", () => {
    expect(hasRole("superadmin", "admin")).toBe(true);
    expect(hasRole("editor", "admin")).toBe(false);
  });
  it("el editor no ve marcas, ajustes, importación ni auditoría", () => {
    const labels = navFor("editor").map((item) => item.label);
    expect(labels).toContain("Productos");
    for (const hidden of ["Marcas", "Configuración", "Importar", "Auditoría"]) expect(labels).not.toContain(hidden);
    expect(navFor("admin").map((item) => item.label)).toContain("Marcas");
  });
});

describe("missingForPublish", () => {
  const ok = { name: "Bolso", brand_id: "b", category_id: "c", media: [{}] };
  it("sin faltantes", () => expect(missingForPublish(ok)).toEqual([]));
  it("explica la foto faltante", () => {
    expect(missingForPublish({ ...ok, media: [] })).toEqual(["Falta al menos una foto"]);
  });
  it("lista todo lo que falta", () => {
    expect(missingForPublish({ name: " ", brand_id: null, category_id: null, media: [] })).toHaveLength(4);
  });
});

describe("summarizeBulk", () => {
  const rows: Record<string, { id: string; name: string; brandName: string | null }> = {
    a: { id: "a", name: "Bolso", brandName: "Loewe" },
    b: { id: "b", name: "Reloj", brandName: "Loewe" },
    c: { id: "c", name: "Cinto", brandName: "Prada" },
    d: { id: "d", name: "Saco", brandName: null },
  };
  it("separa éxitos, errores y bloqueos por marca", () => {
    const summary = summarizeBulk(
      [
        { id: "a", ok: false, error: { code: "brand_unpublished", message: "La marca Loewe no está publicada" } },
        { id: "b", ok: false, error: { code: "brand_unpublished", message: "La marca Loewe no está publicada" } },
        { id: "c", ok: true, error: null },
        { id: "d", ok: false, error: { code: "photo_required", message: "Falta al menos una foto" } },
      ],
      (id) => rows[id],
    );
    expect(summary.ok).toEqual(["c"]);
    expect(summary.brandBlocked).toEqual([{ brand: "Loewe", ids: ["a", "b"] }]);
    expect(summary.failed).toEqual([{ id: "d", name: "Saco", message: "Falta al menos una foto" }]);
  });
  it("usa el mensaje del servidor y tolera filas desconocidas", () => {
    const summary = summarizeBulk([{ id: "z", ok: false, error: { code: "x", message: "Otro" } }], () => undefined);
    expect(summary.failed[0]).toEqual({ id: "z", name: "z", message: "Otro" });
  });
});

it("chunk parte en lotes", () => {
  expect(chunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
});

describe("asignación masiva", () => {
  const proposals: MatchProposal[] = [
    { media_asset_id: "1", filename: "a.jpg", product_id: "p1", match: "sku", candidates: [] },
    { media_asset_id: "2", filename: "b.jpg", product_id: null, match: "none", candidates: [] },
    { media_asset_id: "3", filename: "c.jpg", product_id: "p3", match: "photo_ref", candidates: [] },
  ];
  it("nada se asigna sin confirmar", () => {
    expect(assignPayload(toDecisions(proposals))).toEqual([]);
  });
  it("confirmar todas respeta lo omitido y lo que no tiene propuesta", () => {
    const decisions = toDecisions(proposals).map((decision) =>
      decision.media_asset_id === "3" ? { ...decision, state: "skipped" as const } : decision,
    );
    expect(assignPayload(confirmAllProposed(decisions))).toEqual([{ media_asset_id: "1", product_id: "p1" }]);
  });
});

describe("primaryImageUrl", () => {
  it("prefiere la principal y cae a la primera", () => {
    expect(primaryImageUrl({ media: [{ url: "a", is_primary: false }, { url: "b", is_primary: true }] })).toBe("b");
    expect(primaryImageUrl({ media: [{ url: "a", is_primary: false }] })).toBe("a");
    expect(primaryImageUrl({ media: [] })).toBeNull();
  });
});

describe("parseValidationMessage", () => {
  it("separa por campo y conserva solo el texto propio del servidor", () => {
    expect(
      parseValidationMessage("body.slug: Value error, debe contener solo minúsculas; body.name: String should have at least 1 character"),
    ).toEqual({ slug: "Debe contener solo minúsculas.", name: "Revise este campo." });
  });
  it("ignora lo que no viene del cuerpo", () => {
    expect(parseValidationMessage("query.page: Input should be valid")).toEqual({});
    expect(parseValidationMessage("Solicitud inválida")).toEqual({});
  });
  it("toma el campo raíz de errores anidados", () => {
    expect(parseValidationMessage("body.blocks.0.text.body: Field required")).toEqual({ blocks: "Revise este campo." });
  });
});

describe("auditoría legible", () => {
  it("traduce operación y entidad", () => {
    expect(auditLabel("update", "lookbook")).toBe("Editó: lookbook");
    expect(auditLabel("link_media", "product")).toBe("Agregó foto a: producto");
    expect(auditLabel("login", "admin_user")).toBe("Inició sesión");
  });
  it("muestra tal cual lo desconocido", () => {
    expect(auditLabel("merge", "thing")).toBe("merge: thing");
  });
  it("traduce valores", () => {
    expect(auditValue("draft")).toBe("borrador");
    expect(auditValue(null)).toBe("vacío");
    expect(auditValue(true)).toBe("sí");
    expect(auditValue("Bolso")).toBe("Bolso");
    expect(auditValue(["a"])).toBe('["a"]');
  });
});
