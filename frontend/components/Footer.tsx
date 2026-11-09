import Link from "next/link";
import { NAV_ITEMS } from "./nav";
import { Wordmark } from "./Wordmark";

export function Footer() {
  return (
    <footer className="border-t border-bronze/40">
      <div className="page grid gap-10 py-14 md:grid-cols-12">
        <div className="md:col-span-6">
          <Link href="/" aria-label="Eleven, inicio" className="inline-flex min-h-11 items-center">
            <Wordmark className="h-20" />
          </Link>
          <p className="muted measure mt-4 text-15">
            Los nombres de las marcas pertenecen a sus respectivos titulares.
          </p>
        </div>
        <nav aria-label="Pie de página" className="md:col-span-6">
          <ul className="grid grid-cols-2 gap-x-6 text-15 sm:grid-cols-3">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="inline-flex min-h-8 items-center hover:underline">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
