import { describe, expect, it, vi } from "vitest";
import {
  categoryPaths,
  describeCounts,
  editorialPayload,
  isAtlasLocked,
  pollSync,
  runFinished,
  startSync,
} from "./atlas";
import { AdminApiError } from "./client";
import type { AtlasRun, AtlasStatus } from "./types";

const run = (over: Partial<AtlasRun> = {}): AtlasRun => ({
  kind: "incremental", status: "ok", started_at: "2026-11-14T10:00:00Z", finished_at: "2026-11-14T10:00:05Z",
  counts: {}, error: null, note: null, ...over,
});
const status = (last_run: AtlasRun | null): AtlasStatus => ({ enabled: true, last_run, last_ok_at: null, drafts: [] });

describe("describeCounts", () => {
  it("dice los conteos en español y omite los ceros", () => {
    expect(describeCounts({ creadas: 3, actualizadas: 1, bajas: 0, borradores: 2, disponibilidad: 5, eventos_enviados: 4, archivado_omitido: 1 })).toEqual([
      "3 creadas", "1 actualizada", "2 borradores", "5 con disponibilidad actualizada", "4 eventos enviados", "Archivado omitido",
    ]);
  });
  it("sin cambios", () => expect(describeCounts({ creadas: 0 })).toEqual([]));
  it("archivadas", () => expect(describeCounts({ bajas: 2 })).toEqual(["2 archivadas"]));
});

describe("startSync", () => {
  it("202: arranca", async () => {
    expect(await startSync(async () => ({ started: true }))).toEqual({ started: true, message: null });
  });
  it("409 sync_running: «Ya hay una sincronización en curso»", async () => {
    const post = async () => { throw new AdminApiError(409, "sync_running", "Ya hay una sincronización en curso."); };
    expect(await startSync(post)).toEqual({ started: false, message: "Ya hay una sincronización en curso." });
  });
  it("409 atlas_not_configured muestra el mensaje del servidor", async () => {
    const post = async () => { throw new AdminApiError(409, "atlas_not_configured", "Atlas ONE no está configurado."); };
    expect((await startSync(post)).message).toBe("Atlas ONE no está configurado.");
  });
  it("sync_running sin texto del servidor usa el texto fijo", async () => {
    const post = async () => { throw new AdminApiError(409, "sync_running", ""); };
    expect((await startSync(post)).message).toBe("Ya hay una sincronización en curso.");
  });
});

describe("runFinished / pollSync", () => {
  it("termina cuando hay una corrida nueva con fin", () => {
    const before = "2026-11-14T10:00:00Z";
    expect(runFinished(status(run()), before)).toBe(false);
    expect(runFinished(status(run({ started_at: "2026-11-14T11:00:00Z" })), before)).toBe(true);
    expect(runFinished(status(run({ started_at: "2026-11-14T11:00:00Z", finished_at: null })), before)).toBe(false);
    expect(runFinished(status(null), null)).toBe(false);
  });
  it("consulta hasta que termina", async () => {
    const fresh = status(run({ started_at: "2026-11-14T11:00:00Z" }));
    const fetchStatus = vi.fn().mockResolvedValueOnce(status(run())).mockResolvedValueOnce(fresh);
    const sleep = vi.fn(async () => {});
    expect(await pollSync({ fetchStatus, before: "2026-11-14T10:00:00Z", sleep, intervalMs: 1, maxMs: 100 })).toBe(fresh);
    expect(fetchStatus).toHaveBeenCalledTimes(2);
  });
  it("se rinde tras el límite", async () => {
    const fetchStatus = vi.fn().mockResolvedValue(status(run()));
    const sleep = vi.fn(async () => {});
    expect(await pollSync({ fetchStatus, before: "2026-11-14T10:00:00Z", sleep, intervalMs: 10, maxMs: 30 })).toBeNull();
    expect(fetchStatus).toHaveBeenCalledTimes(3);
  });
});

describe("piezas de Atlas", () => {
  const base = { name: "A", slug: "a", brand_id: "b", category_id: "c", is_featured: true, display_order: 1, commercial_added_at: null,
    seo_title: null, seo_description: null, internal_notes: null };
  it("bloquea lo que es de Atlas solo si viene de Atlas", () => {
    expect(isAtlasLocked({ from_atlas: true }, "name")).toBe(true);
    expect(isAtlasLocked({ from_atlas: true }, "seo_title")).toBe(false);
    expect(isAtlasLocked({ from_atlas: false }, "name")).toBe(false);
  });
  it("el PATCH de una pieza de Atlas no manda lo de Atlas y sí «Ocultar en la web»", () => {
    const out = editorialPayload({ from_atlas: true }, { ...base, hidden_on_web: true });
    expect(out).not.toHaveProperty("name");
    expect(out).not.toHaveProperty("slug");
    expect(out).not.toHaveProperty("brand_id");
    expect(out).not.toHaveProperty("category_id");
    expect(out).toMatchObject({ hidden_on_web: true, is_featured: true, display_order: 1 });
  });
  it("una pieza normal manda todo", () => {
    expect(editorialPayload({ from_atlas: false }, { ...base, hidden_on_web: false })).toHaveProperty("name", "A");
  });
});

describe("categoryPaths", () => {
  it("arma la ruta del árbol", () => {
    const list = [
      { id: "1", name: "Ropa", parent_id: null }, { id: "2", name: "Camisas", parent_id: "1" }, { id: "3", name: "Lino", parent_id: "2" },
    ];
    expect(categoryPaths(list)).toEqual([
      { id: "1", name: "Ropa" }, { id: "2", name: "Ropa › Camisas" }, { id: "3", name: "Ropa › Camisas › Lino" },
    ]);
  });
});
