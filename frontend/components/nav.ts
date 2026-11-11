export const NAV_ITEMS = [
  { href: "/marcas", label: "Marcas" },
  { href: "/colecciones", label: "Colecciones" },
  { href: "/novedades", label: "Novedades" },
  { href: "/lookbooks", label: "Lookbooks" },
  { href: "/la-boutique", label: "La Boutique" },
  { href: "/contacto", label: "Contacto" },
  { href: "/buscar", label: "Buscar" },
] as const;

export type NavLink = { href: string; label: string };

/**
 * El panel lateral agrupa el menú como una revista. La tienda abre con Novedades; «Categorías» y
 * «Casas» se despliegan con el catálogo real (components/Header.tsx) y luego vienen estos grupos.
 */
export const NAV_GROUPS = [
  {
    label: "Editorial",
    items: [{ href: "/lookbooks", label: "Lookbooks" }],
  },
  {
    label: "La casa",
    items: [
      { href: "/la-boutique", label: "La Boutique" },
      { href: "/contacto", label: "Contacto" },
    ],
  },
] as const;
