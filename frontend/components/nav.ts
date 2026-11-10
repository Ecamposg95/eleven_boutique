export const NAV_ITEMS = [
  { href: "/marcas", label: "Marcas" },
  { href: "/colecciones", label: "Colecciones" },
  { href: "/novedades", label: "Novedades" },
  { href: "/lookbooks", label: "Lookbooks" },
  { href: "/la-boutique", label: "La Boutique" },
  { href: "/contacto", label: "Contacto" },
  { href: "/buscar", label: "Buscar" },
] as const;

/** El panel lateral agrupa el menú como una revista: tienda, editorial y la casa. */
export const NAV_GROUPS = [
  {
    label: "Tienda",
    items: [
      { href: "/marcas", label: "Marcas" },
      { href: "/novedades", label: "Novedades" },
      { href: "/colecciones", label: "Colecciones" },
    ],
  },
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
