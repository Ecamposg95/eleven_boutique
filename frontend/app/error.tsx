"use client";

export default function ErrorPage({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="page pb-32 pt-14 md:pt-24">
      <h1 className="display text-68">El catálogo no está disponible por ahora</h1>
      <p className="serif measure mt-6 text-22">
        No fue posible cargar esta página. Intente de nuevo en unos minutos.
      </p>
      <button type="button" onClick={() => retry()} className="btn mt-10">
        Intentar de nuevo
      </button>
    </div>
  );
}
