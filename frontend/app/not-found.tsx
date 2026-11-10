import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Página no encontrada", robots: { index: false } };

export default function NotFound() {
  return (
    <div className="page pb-32 pt-14 md:pt-24">
      <h1 className="display text-68">Esta página no existe</h1>
      <p className="serif measure mt-6 text-22">
        Puede que la dirección haya cambiado o que la pieza ya no esté publicada.
      </p>
      <div className="mt-10 flex flex-wrap items-center gap-6">
        <Link href="/marcas" className="btn">
          Explorar marcas
        </Link>
        <Link href="/buscar" className="label cta px-2">
          Buscar
        </Link>
      </div>
    </div>
  );
}
