import { describe, expect, it } from "vitest";
import { bypassOptimizer, cloudinaryLoader, isCloudinary, parseImageHosts, safeImageSrc } from "./images";

describe("parseImageHosts", () => {
  it("limpia la lista", () => {
    expect(parseImageHosts(" a.com, ,b.com ")).toEqual(["a.com", "b.com"]);
    expect(parseImageHosts(undefined)).toEqual([]);
  });
});

describe("safeImageSrc", () => {
  it("acepta rutas absolutas y http(s)", () => {
    expect(safeImageSrc("/demo/a.svg")).toBe("/demo/a.svg");
    expect(safeImageSrc("https://cdn.test/a.jpg")).toBe("https://cdn.test/a.jpg");
  });
  it("rechaza lo que rompería next/image", () => {
    expect(safeImageSrc(null)).toBeNull();
    expect(safeImageSrc("")).toBeNull();
    expect(safeImageSrc("demo/a.svg")).toBeNull();
    expect(safeImageSrc("//cdn.test/a.jpg")).toBeNull();
    expect(safeImageSrc("javascript:alert(1)")).toBeNull();
  });
});

describe("bypassOptimizer", () => {
  it("nunca optimiza SVG", () => {
    expect(bypassOptimizer("/demo/a.svg", [])).toBe(true);
    expect(bypassOptimizer("https://cdn.test/a.SVG?v=1", ["cdn.test"])).toBe(true);
  });
  it("optimiza locales y hosts permitidos", () => {
    expect(bypassOptimizer("/media/a.jpg", [])).toBe(false);
    expect(bypassOptimizer("https://cdn.test/a.jpg", ["cdn.test"])).toBe(false);
  });
  it("deja pasar sin optimizar hosts fuera de la lista", () => {
    expect(bypassOptimizer("https://otro.test/a.jpg", ["cdn.test"])).toBe(true);
    expect(bypassOptimizer("http://cdn.test/a.jpg", ["cdn.test"])).toBe(true);
  });
});

describe("cloudinaryLoader", () => {
  const src = "https://res.cloudinary.com/hf9/image/upload/v1/atlas/product_images/p-1.jpg";
  it("reconoce solo URLs de subida de Cloudinary", () => {
    expect(isCloudinary(src)).toBe(true);
    expect(isCloudinary("https://cdn.test/a.jpg")).toBe(false);
    expect(isCloudinary("/media/a.jpg")).toBe(false);
  });
  it("pide el ancho, formato y calidad automáticos", () => {
    expect(cloudinaryLoader({ src, width: 640 })).toBe(
      "https://res.cloudinary.com/hf9/image/upload/f_auto,q_auto,c_limit,w_640/v1/atlas/product_images/p-1.jpg",
    );
    expect(cloudinaryLoader({ src, width: 320, quality: 70 })).toContain("f_auto,q_70,c_limit,w_320/");
  });
});
