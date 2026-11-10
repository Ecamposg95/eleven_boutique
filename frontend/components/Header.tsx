"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { NAV_ITEMS } from "./nav";
import { Wordmark } from "./Wordmark";

export function Header() {
  const pathname = usePathname();
  const menu = useRef<HTMLDialogElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const isCurrent = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  useEffect(() => {
    // <dialog> ya da foco atrapado, Esc y retorno de foco. Solo falta cerrarlo al pasar a escritorio.
    const desktop = window.matchMedia("(min-width: 1024px)");
    const closeMenu = () => {
      if (desktop.matches) menu.current?.close();
    };
    desktop.addEventListener("change", closeMenu);
    return () => desktop.removeEventListener("change", closeMenu);
  }, []);

  return (
    <header
      className="relative h-[var(--header-h)] border-b border-bronze/30 bg-ink"
    >
      <div className="page flex h-full items-center justify-between gap-6">
        <Link href="/" aria-label="Eleven, inicio" className="inline-flex min-h-11 items-center">
          <Wordmark />
        </Link>

        <nav aria-label="Principal" className="hidden lg:block">
          <ul className="label flex items-center gap-7">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isCurrent(item.href) ? "page" : undefined}
                  className="inline-flex min-h-11 items-center decoration-bronze decoration-1 underline-offset-[6px] hover:underline aria-[current=page]:underline"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <button
          type="button"
          aria-haspopup="dialog"
          aria-expanded={menuOpen}
          onClick={() => {
            menu.current?.showModal();
            setMenuOpen(true);
          }}
          className="label inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-end lg:hidden"
        >
          Menú
        </button>
      </div>

      <dialog
        ref={menu}
        aria-label="Menú"
        onClose={() => setMenuOpen(false)}
        className="m-0 h-dvh max-h-none w-full max-w-none bg-ink text-ivory"
      >
        <div className="page flex h-[var(--header-h)] items-center justify-between">
          <Wordmark />
          <button
            type="button"
            onClick={() => menu.current?.close()}
            className="label -mr-2 inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-end px-2"
          >
            Cerrar
          </button>
        </div>
        <nav aria-label="Principal, menú" className="page pt-8">
          <ul className="space-y-2">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isCurrent(item.href) ? "page" : undefined}
                  onClick={() => menu.current?.close()}
                  className="display inline-flex min-h-12 items-center text-44 decoration-bronze decoration-1 underline-offset-[6px] aria-[current=page]:underline"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </dialog>
    </header>
  );
}
