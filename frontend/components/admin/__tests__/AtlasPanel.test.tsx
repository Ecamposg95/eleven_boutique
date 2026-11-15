import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AtlasStatus } from "@/lib/admin/types";
import { AtlasDrafts, AtlasPanel, AtlasStatusView } from "../AtlasPanel";
import { AtlasMaps } from "../AtlasMaps";

const status = (over: Partial<AtlasStatus> = {}): AtlasStatus => ({
  enabled: true, last_ok_at: null, drafts: [],
  last_run: { kind: "incremental", status: "ok", started_at: "2026-11-14T10:00:00Z", finished_at: "2026-11-14T10:00:05Z", counts: { creadas: 2, borradores: 1 }, error: null, note: null },
  ...over,
});
const withRun = (run: Partial<NonNullable<AtlasStatus["last_run"]>>) => status({ last_run: { ...status().last_run!, ...run } });

describe("AtlasStatusView", () => {
  it("muestra los conteos en español", () => {
    const html = renderToStaticMarkup(<AtlasStatusView status={status()} />);
    expect(html).toContain("2 creadas");
    expect(html).toContain("1 borrador");
    expect(html).not.toContain("falló");
  });
  it("muestra el error solo cuando existe", () => {
    const html = renderToStaticMarkup(<AtlasStatusView status={withRun({ status: "error", error: "Atlas respondió 500" })} />);
    expect(html).toContain("La última corrida falló: Atlas respondió 500");
    expect(html).toContain('role="alert"');
  });
  it("la nota es un aviso, no un error", () => {
    const html = renderToStaticMarkup(<AtlasStatusView status={withRun({ note: "Archivado omitido: Atlas devolvió pocas piezas" })} />);
    expect(html).toContain("Archivado omitido: Atlas devolvió pocas piezas");
    expect(html).not.toContain('role="alert"');
  });
  it("sin corridas y sin configurar", () => {
    const html = renderToStaticMarkup(<AtlasStatusView status={status({ enabled: false, last_run: null })} />);
    expect(html).toContain("Todavía no se ha sincronizado");
    expect(html).toContain("no está configurada");
  });
});

describe("AtlasDrafts", () => {
  it("lista las piezas con su motivo", () => {
    const html = renderToStaticMarkup(<AtlasDrafts status={status({ drafts: [{ id: "p1", name: "Camisa lino", atlas_missing: "Falta la foto" }] })} />);
    expect(html).toContain("Camisa lino");
    expect(html).toContain("Falta la foto");
    expect(html).toContain("/admin/productos/p1");
    expect(html).toContain("ligar su marca o su categoría aquí");
    expect(html).toContain("Sincronizar ahora");
    expect(html).not.toContain("hasta que Atlas ONE tenga");
  });
});

describe("AtlasPanel y mapas", () => {
  const props = {
    brands: [{ id: "b1", name: "Marca Uno" }],
    categories: [{ id: "c1", name: "Ropa", parent_id: null }, { id: "c2", name: "Camisas", parent_id: "c1" }],
    brandMap: [{ atlas_brand_id: "10", atlas_name: "MARCA UNO", brand_id: "b1" }],
    categoryMap: [{ atlas_department_id: "20", atlas_name: "CAMISAS", category_id: null }],
  };
  it("ofrece «Sincronizar ahora»", () => {
    expect(renderToStaticMarkup(<AtlasPanel initial={status()} {...props} />)).toContain("Sincronizar ahora");
  });
  it("los mapas permiten elegir casa y categoría con su ruta", () => {
    const html = renderToStaticMarkup(<AtlasMaps {...props} />);
    expect(html).toContain("MARCA UNO");
    expect(html).toContain("Marca Uno");
    expect(html).toContain("Ropa › Camisas");
    expect(html).toContain("Sin ligar");
  });
  it("una marca ligada no se puede desligar (la liga automática la volvería a ligar)", () => {
    const html = renderToStaticMarkup(<AtlasMaps {...props} categoryMap={[]} />);
    expect(html).not.toContain("Sin ligar");
  });
  it("una marca sin ligar pide elegir casa sin ofrecer «Sin ligar»", () => {
    const html = renderToStaticMarkup(
      <AtlasMaps {...props} categoryMap={[]} brandMap={[{ atlas_brand_id: "11", atlas_name: "DOBLE", brand_id: null }]} />,
    );
    expect(html).toContain("Elegir casa");
    expect(html).not.toContain("Sin ligar");
  });
});

describe("ReadOnlyField", () => {
  it("muestra el valor con la marca «Viene de Atlas ONE» y sin campo editable", async () => {
    const { ReadOnlyField } = await import("../ui");
    const html = renderToStaticMarkup(<ReadOnlyField label="Nombre" value="Camisa lino" />);
    expect(html).toContain("Camisa lino");
    expect(html).toContain("Viene de Atlas ONE");
    expect(html).not.toContain("<input");
  });
});
