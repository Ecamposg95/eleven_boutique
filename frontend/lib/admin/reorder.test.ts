import { describe, expect, it } from "vitest";
import { mediaOrderPayload, moveItem, resolvePrimary, setPrimary, withPositions } from "./reorder";

describe("moveItem", () => {
  it("mueve hacia adelante y hacia atrás", () => {
    expect(moveItem(["a", "b", "c", "d"], 0, 2)).toEqual(["b", "c", "a", "d"]);
    expect(moveItem(["a", "b", "c", "d"], 3, 1)).toEqual(["a", "d", "b", "c"]);
  });
  it("no cambia nada fuera de rango y no muta la original", () => {
    const list = ["a", "b"];
    expect(moveItem(list, -1, 1)).toEqual(list);
    expect(moveItem(list, 0, 2)).toEqual(list);
    expect(moveItem(list, 1, 1)).toEqual(list);
    moveItem(list, 0, 1);
    expect(list).toEqual(["a", "b"]);
  });
});

describe("principal", () => {
  const list = [
    { id: "a", is_primary: false },
    { id: "b", is_primary: true },
  ];
  it("resuelve la marcada o la primera", () => {
    expect(resolvePrimary(list)).toBe("b");
    expect(resolvePrimary([{ id: "x", is_primary: false }])).toBe("x");
    expect(resolvePrimary([])).toBeNull();
  });
  it("deja una sola principal", () => {
    expect(setPrimary(list, "a").filter((item) => item.is_primary).map((item) => item.id)).toEqual(["a"]);
  });
  it("arma el cuerpo de reordenar", () => {
    expect(mediaOrderPayload(moveItem(list, 1, 0))).toEqual({ order: ["b", "a"], primary_id: "b" });
  });
});

it("withPositions numera desde cero", () => {
  expect(withPositions([{ position: 5 }, { position: 1 }])).toEqual([{ position: 0 }, { position: 1 }]);
});
