import { describe, expect, it } from "vitest";
import { loginHref, safeReturnPath } from "./return-path";

describe("safeReturnPath", () => {
  it("acepta rutas internas del panel con su búsqueda", () => {
    expect(safeReturnPath("/admin")).toBe("/admin");
    expect(safeReturnPath("/admin/productos?status=draft&page=2")).toBe("/admin/productos?status=draft&page=2");
    expect(safeReturnPath("/admin/productos/abc-123")).toBe("/admin/productos/abc-123");
  });

  it.each([
    null,
    undefined,
    "",
    "https://evil.test/admin",
    "//evil.test/admin",
    "/\\evil.test",
    "/admin\\..\\..\\evil",
    "/administrador",
    "/admin@evil.test",
    "/admin.evil.test",
    "/admin/../marcas",
    "/admin/%2e%2e/marcas",
    "/admin/%2e%2e%2f%2e%2e/evil",
    "/admin//evil.test",
    "/admin/%2f%2fevil.test",
    "/admin/%5cevil",
    "/admin/\tproductos",
    "/admin/%ZZ",
    "javascript:alert(1)",
    "/marcas",
  ])("rechaza %s", (raw) => {
    expect(safeReturnPath(raw)).toBe("/admin");
  });

  it("no regresa al login: evitaría un bucle", () => {
    expect(safeReturnPath("/admin/login")).toBe("/admin");
    expect(safeReturnPath("/admin/login?next=/admin/marcas")).toBe("/admin");
  });

  it("descarta rutas demasiado largas", () => {
    expect(safeReturnPath(`/admin/${"a".repeat(3000)}`)).toBe("/admin");
  });
});

describe("loginHref", () => {
  it("omite el retorno al inicio", () => {
    expect(loginHref("/admin")).toBe("/admin/login");
    expect(loginHref("https://evil.test")).toBe("/admin/login");
  });
  it("codifica la ruta y marca la sesión expirada", () => {
    expect(loginHref("/admin/productos?page=2", true)).toBe(
      "/admin/login?next=%2Fadmin%2Fproductos%3Fpage%3D2&expirada=1",
    );
  });
});
