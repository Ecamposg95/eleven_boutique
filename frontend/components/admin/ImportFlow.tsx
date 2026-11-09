"use client";

import Link from "next/link";
import { useState } from "react";
import { api, errorText } from "@/lib/admin/client";
import { formatNumber, plural } from "@/lib/admin/format";
import type { ImportPreview, ImportResult } from "@/lib/admin/types";
import { Notice } from "./ui";

const BASE = "/api/v1/admin";
const VISIBLE_ERRORS = 100;

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-bronze/30 py-1.5">
      <dt>{label}</dt>
      <dd className="text-17">{formatNumber(value)}</dd>
    </div>
  );
}

export function ImportFlow() {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [updateExisting, setUpdateExisting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const choose = (next: File | null) => {
    setPreview(null);
    setResult(null);
    setError(null);
    if (next && !/\.(xlsx|csv)$/i.test(next.name)) {
      setFile(null);
      setFileError("Use un archivo .xlsx o .csv.");
      return;
    }
    setFileError(null);
    setFile(next);
  };

  const runPreview = async () => {
    if (!file) {
      setFileError("Elija un archivo.");
      return;
    }
    setBusy("Leyendo el archivo");
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      setPreview(await api<ImportPreview>("/imports/products/preview", { form }));
      setUpdateExisting(false);
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(null);
    }
  };

  const run = async () => {
    if (!preview) return;
    setBusy("Importando");
    setError(null);
    try {
      setResult(await api<ImportResult>("/imports/products", { json: { preview_id: preview.preview_id, update_existing: updateExisting } }));
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(null);
    }
  };

  const reset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-4xl">
      <div className="a-notice">
        <p>Todo lo importado llega como borrador: nada se publica solo.</p>
        <p className="mt-1">Los precios nunca se leen. Tampoco costos, existencias ni códigos de barras: esas columnas se ignoran.</p>
      </div>

      {result ? (
        <section aria-labelledby="res-t" className="a-section" data-testid="import-result">
          <h2 id="res-t" className="a-h2">
            Importación terminada
          </h2>
          <dl className="mt-2 max-w-md">
            <Stat label="Productos creados" value={result.created} />
            <Stat label="Productos actualizados" value={result.updated} />
            <Stat label="Omitidos" value={result.skipped} />
            <Stat label="Filas con error" value={result.errors} />
          </dl>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/admin/productos?status=draft" prefetch={false} className="a-btn a-btn-primary">
              Ver borradores
            </Link>
            <a href={`${BASE}/imports/${encodeURIComponent(result.import_id)}/report`} className="a-btn" download>
              Descargar reporte
            </a>
            <button type="button" className="a-btn a-btn-quiet" onClick={reset}>
              Importar otro archivo
            </button>
          </div>
        </section>
      ) : (
        <>
          <section aria-labelledby="archivo-t" className="a-section">
            <h2 id="archivo-t" className="a-h2">
              Archivo
            </h2>
            <div className="mt-2 flex flex-wrap items-start gap-3">
              <div className="min-w-0">
                {/* Control propio: el nativo muestra su texto en el idioma del navegador. */}
                <label className="a-btn a-btn-quiet cursor-pointer focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-bronze">
                  Elegir archivo .xlsx o .csv
                  <input
                    id="import-file"
                    type="file"
                    accept=".xlsx,.csv"
                    className="sr-only"
                    aria-invalid={fileError ? true : undefined}
                    aria-describedby={fileError ? "import-file-error" : undefined}
                    onChange={(event) => choose(event.target.files?.[0] ?? null)}
                  />
                </label>
                <p role="status" className="mt-1 break-all">
                  {file ? file.name : <span className="muted">Ningún archivo elegido</span>}
                </p>
              </div>
              <button type="button" className="a-btn" disabled={Boolean(busy)} onClick={() => void runPreview()}>
                Revisar archivo
              </button>
              <a href={`${BASE}/imports/template`} className="a-btn a-btn-quiet" download>
                Descargar plantilla
              </a>
            </div>
            {fileError ? (
              <p id="import-file-error" className="a-error">
                {fileError}
              </p>
            ) : null}
            <p className="a-hint">Revisar no cambia nada en el catálogo.</p>
          </section>

          {busy ? (
            <p role="status" className="muted mt-3">
              {busy}
            </p>
          ) : null}
          {error ? (
            <div className="mt-3">
              <Notice kind="error">{error}</Notice>
            </div>
          ) : null}

          {preview ? (
            <section aria-labelledby="prev-t" className="a-section" data-testid="import-preview">
              <h2 id="prev-t" className="a-h2">
                Lo que va a pasar
              </h2>
              <dl className="mt-2 max-w-md">
                <Stat label="Filas leídas" value={preview.rows} />
                <Stat label="Productos en el archivo" value={preview.products} />
                <Stat label="Variantes" value={preview.variants} />
                <Stat label="Productos nuevos" value={preview.new_products} />
                <Stat label="SKU que ya existen" value={preview.conflicts} />
                <Stat label="Filas con error" value={preview.errors.length} />
              </dl>

              {preview.new_categories.length ? (
                <div className="mt-4">
                  <h3 className="font-medium">Categorías nuevas que se crearán</h3>
                  <p className="mt-1">{preview.new_categories.join(", ")}</p>
                </div>
              ) : null}

              {preview.conflicts > 0 ? (
                <fieldset className="mt-4">
                  <legend className="font-medium">¿Qué hacer con los {formatNumber(preview.conflicts)} SKU que ya existen?</legend>
                  <label className="mt-2 flex cursor-pointer items-start gap-2">
                    <input type="radio" name="update" className="mt-0.5" checked={!updateExisting} onChange={() => setUpdateExisting(false)} />
                    <span>
                      Omitirlos
                      <span className="muted block">Los productos existentes quedan exactamente como están.</span>
                    </span>
                  </label>
                  <label className="mt-2 flex cursor-pointer items-start gap-2">
                    <input type="radio" name="update" className="mt-0.5" checked={updateExisting} onChange={() => setUpdateExisting(true)} />
                    <span>
                      Actualizarlos
                      <span className="muted block">
                        Se reemplazan nombre, marca, categoría y variantes con lo del archivo. No se tocan estado, fotos ni textos editoriales.
                      </span>
                    </span>
                  </label>
                </fieldset>
              ) : null}

              {preview.errors.length ? (
                <div className="mt-4">
                  <h3 className="font-medium">Filas con error: no se importan</h3>
                  <div className="mt-1 max-h-80 overflow-auto">
                    <table className="a-table">
                      <thead>
                        <tr>
                          <th scope="col">Fila</th>
                          <th scope="col">SKU</th>
                          <th scope="col">Problema</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.errors.slice(0, VISIBLE_ERRORS).map((row) => (
                          <tr key={`${row.row}-${row.sku}`}>
                            <td>{row.row}</td>
                            <td className="break-all">{row.sku}</td>
                            <td>{row.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {preview.errors.length > VISIBLE_ERRORS ? (
                    <p className="a-hint">Se muestran {VISIBLE_ERRORS} de {formatNumber(preview.errors.length)}. El reporte final las incluye todas.</p>
                  ) : null}
                </div>
              ) : null}

              {preview.sample.length ? (
                <div className="mt-4">
                  <h3 className="font-medium">Muestra</h3>
                  <div className="mt-1 overflow-x-auto">
                    <table className="a-table">
                      <thead>
                        <tr>
                          <th scope="col">SKU</th>
                          <th scope="col">Nombre</th>
                          <th scope="col" className="max-sm:hidden">
                            Marca
                          </th>
                          <th scope="col" className="max-md:hidden">
                            Categoría
                          </th>
                          <th scope="col" className="max-sm:hidden">
                            Variantes
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.sample.map((row) => (
                          <tr key={row.sku}>
                            <td className="break-all">{row.sku}</td>
                            <td>{row.name}</td>
                            <td className="max-sm:hidden">{row.brand}</td>
                            <td className="max-md:hidden">{row.category}</td>
                            <td className="max-sm:hidden">{row.variants}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}

              <div className="a-bar">
                <button type="button" className="a-btn a-btn-primary" disabled={Boolean(busy)} onClick={() => void run()}>
                  Importar como {plural(preview.new_products + (updateExisting ? preview.conflicts : 0), "borrador", "borradores")}
                </button>
              </div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
