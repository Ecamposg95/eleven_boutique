"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useRef, useState } from "react";
import { Wordmark } from "@/components/Wordmark";
import { api } from "@/lib/admin/client";
import { navFor } from "@/lib/admin/rules";
import type { Me } from "@/lib/admin/types";

const ROLE_LABEL: Record<Me["role"], string> = { superadmin: "Superadministrador", admin: "Administrador", editor: "Editor" };

function NavList({ me, onNavigate }: { me: Me; onNavigate?: () => void }) {
  const pathname = usePathname();
  const isCurrent = (href: string) => (href === "/admin" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`));
  return (
    <ul>
      {navFor(me.role).map((item) => (
        <li key={item.href}>
          <Link
            href={item.href}
            prefetch={false}
            onClick={onNavigate}
            className="a-nav-link"
            aria-current={isCurrent(item.href) ? "page" : undefined}
          >
            {item.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Account({ me }: { me: Me }) {
  const [busy, setBusy] = useState(false);
  const logout = async () => {
    setBusy(true);
    try {
      await api("/auth/logout", { method: "POST", noSessionRedirect: true });
    } catch {
      // Si la sesión ya no existe, el resultado es el mismo.
    }
    // Navegación completa: descarta lo que el router tenga en memoria.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- justo eso se busca aquí.
    window.location.assign("/admin/login");
  };
  return (
    <div className="px-5">
      <p className="break-words" title={me.email}>
        {me.email}
      </p>
      <p className="muted">{ROLE_LABEL[me.role]}</p>
      <button type="button" onClick={logout} disabled={busy} className="a-btn a-btn-quiet a-btn-small mt-2">
        Cerrar sesión
      </button>
    </div>
  );
}

export function AdminShell({ me, children }: { me: Me; children: ReactNode }) {
  const menu = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  return (
    <div className="a-shell">
      <aside className="a-rail max-lg:hidden">
        <Link href="/admin" prefetch={false} aria-label="Eleven, inicio del panel" className="mb-5 inline-flex px-5">
          <Wordmark />
        </Link>
        <nav aria-label="Panel" className="flex-1">
          <NavList me={me} />
        </nav>
        <div className="mt-6">
          <p className="mb-3 px-5">
            <a href="/" target="_blank" rel="noreferrer" className="link">
              Ver sitio público
            </a>
          </p>
          <Account me={me} />
        </div>
      </aside>

      <div className="min-w-0">
        <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-bronze/40 bg-ink px-4 lg:hidden">
          <Link href="/admin" prefetch={false} aria-label="Eleven, inicio del panel" className="inline-flex min-h-11 items-center">
            <Wordmark />
          </Link>
          <button
            type="button"
            aria-haspopup="dialog"
            aria-expanded={open}
            onClick={() => {
              menu.current?.showModal();
              setOpen(true);
            }}
            className="inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-end"
          >
            Menú
          </button>
        </div>
        <dialog
          ref={menu}
          aria-label="Menú del panel"
          onClose={() => setOpen(false)}
          className="m-0 h-dvh max-h-none w-full max-w-none overflow-y-auto bg-ink text-ivory"
        >
          <div className="flex h-14 items-center justify-between px-4">
            <Wordmark />
            <button
              type="button"
              onClick={() => menu.current?.close()}
              className="inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-end"
            >
              Cerrar
            </button>
          </div>
          <nav aria-label="Panel, menú" className="py-2">
            <NavList me={me} onNavigate={() => menu.current?.close()} />
          </nav>
          <div className="mt-4 border-t border-bronze/40 py-4">
            <Account me={me} />
          </div>
        </dialog>
        <main id="contenido" tabIndex={-1} className="a-main">
          {children}
        </main>
      </div>
    </div>
  );
}
