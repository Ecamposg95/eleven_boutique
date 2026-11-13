"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useSyncExternalStore } from "react";
import { NAV_GROUPS, type NavLink } from "./nav";
import { SelectionLink } from "./SelectionLink";
import { Wordmark } from "./Wordmark";

function subscribeScroll(onChange: () => void) {
  window.addEventListener("scroll", onChange, { passive: true });
  return () => window.removeEventListener("scroll", onChange);
}
const useScrolled = () =>
  useSyncExternalStore(
    subscribeScroll,
    () => window.scrollY > 24,
    () => false,
  );

function MenuIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 18 10"
      className="h-2.5 w-[18px]"
      fill="none"
      stroke="currentColor"
    >
      <path d="M0 0.5h18M0 5h18M0 9.5h18" />
    </svg>
  );
}
function SearchIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 14 14"
      className="h-3.5 w-3.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
    >
      <circle cx="6" cy="6" r="4.8" />
      <path d="M9.6 9.6 13 13" />
    </svg>
  );
}
function CloseIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 10 10"
      className="h-2.5 w-2.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
    >
      <path d="M1 1l8 8M9 1l-8 8" />
    </svg>
  );
}

/**
 * Encabezado acrílico: menú a la izquierda, logotipo al centro, búsqueda a la derecha.
 * `overHero`: la portada tiene fotografía a pantalla completa y el encabezado flota encima en claro.
 * El menú es un panel lateral (<dialog>: foco atrapado, Esc y retorno de foco nativos).
 */
const LINK =
  "drawer-link label inline-flex min-h-8 items-center text-[0.8125rem] tracking-[0.14em]";

/** Sección que se despliega dentro del panel (<details>: teclado y lector de pantalla nativos). */
function Fold({
  label,
  links,
  more,
  isCurrent,
  onNavigate,
}: {
  label: string;
  links: NavLink[];
  more?: NavLink;
  isCurrent: (href: string) => boolean;
  onNavigate: () => void;
}) {
  const open = links.some((link) => isCurrent(link.href));
  return (
    <details open={open || undefined} className="group">
      <summary
        className={`${LINK} cursor-pointer list-none gap-3 [&::-webkit-details-marker]:hidden`}
      >
        {label}
        <span aria-hidden="true" className="relative inline-block h-2 w-2">
          <span className="absolute inset-x-0 top-1/2 h-px bg-current" />
          <span className="absolute inset-y-0 left-1/2 w-px bg-current transition-transform duration-200 group-open:scale-y-0" />
        </span>
      </summary>
      <ul className="mb-3 mt-1 space-y-0.5 border-l border-current/15 pl-4">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              onClick={onNavigate}
              aria-current={isCurrent(link.href) ? "page" : undefined}
              className="drawer-link inline-flex min-h-8 items-center text-[0.8125rem] tracking-[0.02em]"
            >
              {link.label}
            </Link>
          </li>
        ))}
        {more ? (
          <li>
            <Link
              href={more.href}
              onClick={onNavigate}
              className="drawer-link label inline-flex min-h-8 items-center text-taupe"
            >
              {more.label}
            </Link>
          </li>
        ) : null}
      </ul>
    </details>
  );
}

export function Header({
  overHero,
  categories = [],
  houses = [],
}: {
  overHero: boolean;
  categories?: NavLink[];
  houses?: NavLink[];
}) {
  const pathname = usePathname();
  const scrolled = useScrolled();
  const menu = useRef<HTMLDialogElement>(null);
  const onPhoto = overHero && pathname === "/" && !scrolled;
  const isCurrent = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);
  const close = () => menu.current?.close();

  return (
    <header
      className={[
        "relative h-[var(--header-h)] border-b transition-colors duration-300",
        onPhoto
          ? "acrylic-dark border-white/15 text-[#efece6]"
          : "acrylic-light border-bronze/30",
      ].join(" ")}
    >
      <div className="page grid h-full grid-cols-[1fr_auto_1fr] items-center gap-6">
        <button
          type="button"
          aria-haspopup="dialog"
          onClick={() => menu.current?.showModal()}
          className="label inline-flex min-h-11 cursor-pointer items-center gap-3 justify-self-start"
        >
          <MenuIcon />
          Menú
        </button>

        <Link
          href="/"
          aria-label="Eleven, inicio"
          className="inline-flex min-h-11 items-center"
        >
          <Wordmark className="h-11 md:h-12" />
        </Link>

        <div className="flex items-center gap-5 justify-self-end sm:gap-7">
          <SelectionLink className="label inline-flex min-h-11 items-center" />
          <Link
            href="/buscar"
            className="label inline-flex min-h-11 items-center gap-2"
          >
            <SearchIcon />
            <span className="hidden sm:inline">Buscar</span>
            <span className="sr-only sm:hidden">Buscar</span>
          </Link>
        </div>
      </div>

      <dialog
        ref={menu}
        aria-label="Menú"
        className="drawer m-0 h-dvh max-h-none w-full max-w-[22rem] bg-[#f7f5f1] p-0 text-[#121212]"
      >
        <div className="flex h-full flex-col overflow-y-auto px-10 pb-10 pt-7">
          <div className="flex items-center justify-between gap-6">
            <button
              type="button"
              onClick={close}
              className="label inline-flex min-h-11 cursor-pointer items-center gap-2"
            >
              <CloseIcon />
              Cerrar
            </button>
            <Link
              href="/buscar"
              onClick={close}
              className="label inline-flex min-h-11 items-center gap-2"
            >
              <SearchIcon />
              Buscar
            </Link>
          </div>

          <nav aria-label="Principal" className="mt-14 space-y-12">
            <ul aria-label="Tienda" className="space-y-1">
              <SelectionLink onNavigate={close} className={LINK} asListItem />
              <li>
                <Link
                  href="/novedades"
                  onClick={close}
                  aria-current={isCurrent("/novedades") ? "page" : undefined}
                  className={LINK}
                >
                  Novedades
                </Link>
              </li>
              {categories.length > 0 ? (
                <li>
                  <Fold
                    label="Categorías"
                    links={categories}
                    isCurrent={isCurrent}
                    onNavigate={close}
                  />
                </li>
              ) : null}
              <li>
                {houses.length > 0 ? (
                  <Fold
                    label="Casas"
                    links={houses}
                    more={{ href: "/marcas", label: "Todas las marcas" }}
                    isCurrent={isCurrent}
                    onNavigate={close}
                  />
                ) : (
                  <Link
                    href="/marcas"
                    onClick={close}
                    aria-current={isCurrent("/marcas") ? "page" : undefined}
                    className={LINK}
                  >
                    Marcas
                  </Link>
                )}
              </li>
              <li>
                <Link
                  href="/colecciones"
                  onClick={close}
                  aria-current={isCurrent("/colecciones") ? "page" : undefined}
                  className={LINK}
                >
                  Colecciones
                </Link>
              </li>
            </ul>
            {NAV_GROUPS.map((group) => (
              <ul
                key={group.label}
                aria-label={group.label}
                className="space-y-1"
              >
                {group.items.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={close}
                      aria-current={isCurrent(item.href) ? "page" : undefined}
                      className={LINK}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            ))}
          </nav>

          <p className="label mt-auto pt-12 text-[#5c5852]">
            Eleven · Fashion boutique
          </p>
        </div>
      </dialog>
    </header>
  );
}
