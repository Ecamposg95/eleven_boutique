"use client";

export default function AdminError({ retry }: { error: Error; retry: () => void }) {
  return (
    <main id="contenido" tabIndex={-1} className="a-main outline-none">
      <h1 className="a-h1">No fue posible cargar esta pantalla</h1>
      <p className="measure mt-2">El servidor del catálogo no respondió. Lo que ya estaba guardado sigue guardado.</p>
      <button type="button" onClick={() => retry()} className="a-btn mt-5">
        Intentar de nuevo
      </button>
    </main>
  );
}
