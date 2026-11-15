"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { POLL_ERROR_MESSAGE, describeCounts, fetchAtlasStatus, pollSync, startSync } from "@/lib/admin/atlas";
import { formatDateTime } from "@/lib/admin/format";
import type { AdminCategory, AtlasBrandMapRow, AtlasCategoryMapRow, AtlasStatus, Brand } from "@/lib/admin/types";
import { AtlasMaps } from "./AtlasMaps";
import { Empty, Notice } from "./ui";

/** Estado de la última corrida. Sin estado propio: se prueba como texto. */
export function AtlasStatusView({ status }: { status: AtlasStatus }) {
  const run = status.last_run;
  const failure = run?.error ?? null;
  const counts = run ? describeCounts(run.counts) : [];
  return (
    <section aria-labelledby="atlas-estado-t" className="a-section">
      <h2 id="atlas-estado-t" className="a-h2">
        Estado
      </h2>
      {!status.enabled ? (
        <p className="mt-2">La sincronización con Atlas ONE no está configurada. Hay que definir la dirección y la llave de Atlas ONE en el servidor.</p>
      ) : null}
      {!run ? (
        <p className="mt-2">Todavía no se ha sincronizado.</p>
      ) : (
        <>
          <p className="mt-2">
            Última corrida: {formatDateTime(run.started_at)}
            {run.finished_at ? "" : " (en curso)"}.
          </p>
          {failure ? <Notice kind="error">La última corrida falló: {failure}</Notice> : null}
          {run.note ? (
            <p role="status" className="a-notice mt-2">
              {run.note}
            </p>
          ) : null}
          {!failure && counts.length ? <p className="mt-2">{counts.join(" · ")}.</p> : null}
          {!failure && run.finished_at && !counts.length ? <p className="mt-2">Sin cambios.</p> : null}
        </>
      )}
      {status.last_ok_at ? <p className="muted mt-1">Última corrida buena: {formatDateTime(status.last_ok_at)}</p> : null}
    </section>
  );
}

export function AtlasDrafts({ status }: { status: AtlasStatus }) {
  return (
    <section aria-labelledby="atlas-borradores-t" className="a-section">
      <h2 id="atlas-borradores-t" className="a-h2">
        Piezas en borrador
      </h2>
      {status.drafts.length === 0 ? (
        <p className="mt-2">Ninguna pieza de Atlas ONE está detenida en borrador.</p>
      ) : (
        <>
          <p className="a-hint">
            Estas piezas no se ven en el sitio. Casi siempre basta ligar su marca o su categoría aquí abajo (o publicar
            la casa); si falta algo en la pieza, complétela en Atlas ONE. Luego use «Sincronizar ahora».
          </p>
          <ul className="mt-2">
            {status.drafts.map((draft) => (
              <li key={draft.id} className="border-t border-bronze/30 py-1.5">
                <Link href={`/admin/productos/${draft.id}`} prefetch={false} className="link">
                  {draft.name}
                </Link>
                <span className="muted block">{draft.atlas_missing ?? "Sin motivo registrado."}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export function AtlasPanel({
  initial,
  brands,
  categories,
  brandMap,
  categoryMap,
}: {
  initial: AtlasStatus;
  brands: Pick<Brand, "id" | "name">[];
  categories: Pick<AdminCategory, "id" | "name" | "parent_id">[];
  brandMap: AtlasBrandMapRow[];
  categoryMap: AtlasCategoryMapRow[];
}) {
  const [status, setStatus] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Al salir de la pantalla se deja de consultar.
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);

  const sync = async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    const before = status.last_run?.started_at ?? null;
    const result = await startSync();
    if (!result.started) {
      setError(result.message);
      setBusy(false);
      return;
    }
    setMessage("Sincronizando con Atlas ONE…");
    const controller = new AbortController();
    abort.current = controller;
    try {
      const done = await pollSync({ fetchStatus: fetchAtlasStatus, before, signal: controller.signal });
      if (controller.signal.aborted) return;
      if (done) {
        setStatus(done);
        setMessage(done.last_run?.error ? null : "Sincronización terminada.");
      } else {
        setMessage("La sincronización sigue en curso. Recargue la página en unos minutos para ver el resultado.");
      }
    } catch {
      if (controller.signal.aborted) return;
      setMessage(null);
      setError(POLL_ERROR_MESSAGE);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  return (
    <>
      <div className="a-section">
        <button type="button" className="a-btn a-btn-primary" disabled={busy || !status.enabled} onClick={() => void sync()}>
          {busy ? "Sincronizando…" : "Sincronizar ahora"}
        </button>
        {message ? (
          <p role="status" className="mt-2">
            {message}
          </p>
        ) : null}
        {error ? (
          <div className="mt-2">
            <Notice kind="error">{error}</Notice>
          </div>
        ) : null}
      </div>
      <AtlasStatusView status={status} />
      <AtlasDrafts status={status} />
      {brandMap.length === 0 && categoryMap.length === 0 ? (
        <Empty message="Los mapas de marcas y categorías aparecen después de la primera sincronización." />
      ) : (
        <AtlasMaps brands={brands} categories={categories} brandMap={brandMap} categoryMap={categoryMap} />
      )}
    </>
  );
}
