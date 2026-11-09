import { describe, expect, it } from "vitest";
import { filterByName, groupByLetter, groupLetter, normalize } from "./brands";

const brands = [
  { name: "Canadá", aliases: [] },
  { name: "A Bathing Ape", aliases: ["BAPE"] },
  { name: "Éclat", aliases: [] },
  { name: "1017 ALYX 9SM", aliases: ["Alyx"] },
  { name: "(di)vision", aliases: [] },
  { name: "Arc'teryx", aliases: [] },
  { name: "acne Studios", aliases: [] },
  { name: "Ñandú", aliases: [] },
];

describe("normalize", () => {
  it("quita acentos y mayúsculas", () => {
    expect(normalize("  CANADÁ ")).toBe("canada");
  });
});

describe("groupLetter", () => {
  it("archiva acentos bajo la letra base", () => {
    expect(groupLetter("Éclat")).toBe("E");
    expect(groupLetter("Ñandú")).toBe("N");
  });
  it("manda lo que no empieza con letra a #", () => {
    expect(groupLetter("1017 ALYX 9SM")).toBe("#");
    expect(groupLetter("(di)vision")).toBe("#");
    expect(groupLetter("")).toBe("#");
  });
});

describe("groupByLetter", () => {
  const groups = groupByLetter(brands);

  it("ordena letras con # al final", () => {
    expect(groups.map((g) => g.letter)).toEqual(["A", "C", "E", "N", "#"]);
  });
  it("ordena dentro del grupo sin distinguir mayúsculas", () => {
    expect(groups[0]?.items.map((b) => b.name)).toEqual(["A Bathing Ape", "acne Studios", "Arc'teryx"]);
  });
  it("genera anclas válidas", () => {
    expect(groups[0]?.anchor).toBe("letra-a");
    expect(groups.at(-1)?.anchor).toBe("letra-otros");
  });
  it("devuelve vacío sin marcas", () => {
    expect(groupByLetter([])).toEqual([]);
  });
});

describe("filterByName", () => {
  const names = (q: string) => filterByName(brands, q).map((b) => b.name);

  it("encuentra Canadá con o sin acento", () => {
    expect(names("canada")).toEqual(["Canadá"]);
    expect(names("CANADÁ")).toEqual(["Canadá"]);
  });
  it("encuentra por alias", () => {
    expect(names("bape")).toEqual(["A Bathing Ape"]);
    expect(names("BaPe")).toEqual(["A Bathing Ape"]);
  });
  it("ignora puntuación y espacios", () => {
    expect(names("arcteryx")).toEqual(["Arc'teryx"]);
    expect(names("acnestudios")).toEqual(["acne Studios"]);
  });
  it("encuentra nombres que no empiezan con letra", () => {
    expect(names("1017")).toEqual(["1017 ALYX 9SM"]);
    expect(names("division")).toEqual(["(di)vision"]);
  });
  it("sin consulta útil devuelve todo", () => {
    expect(names("  ")).toHaveLength(brands.length);
    expect(names("'")).toHaveLength(brands.length);
  });
  it("sin coincidencias devuelve vacío", () => {
    expect(names("zzz")).toEqual([]);
  });
});
