import { describe, expect, it } from "vitest";
import { rhythmSlot } from "./rhythm";

const wideDesktop = (total: number) =>
  Array.from({ length: total }, (_, i) => i).filter((i) => rhythmSlot(i, total).wideDesktop);
const wideMobile = (total: number) =>
  Array.from({ length: total }, (_, i) => i).filter((i) => rhythmSlot(i, total).wideMobile);

describe("rhythmSlot", () => {
  it("duplica cada sexta pieza en escritorio", () => {
    expect(wideDesktop(24)).toEqual([5, 11, 17]);
  });
  it("no duplica si faltan piezas para rodearla", () => {
    expect(wideDesktop(6)).toEqual([]);
    expect(wideDesktop(8)).toEqual([]);
    expect(wideDesktop(9)).toEqual([5]);
  });
  it("da ancho completo a una de cada 5 en móvil", () => {
    expect(wideMobile(12)).toEqual([4, 9]);
  });
});
