/**
 * Direcciones anteriores a /tienda. Ya circulan en WhatsApp e Instagram, así que redirigen de
 * forma permanente. En /categorias/:slug la regla con `category` va primero: Next usa la primera
 * que coincide, y el resto de la query (`sort`) se conserva sola.
 */
export const LEGACY_REDIRECTS: {
  source: string;
  destination: string;
  permanent: true;
  has?: { type: "query"; key: string; value: string }[];
}[] = [
  { source: "/marcas", destination: "/tienda/marcas", permanent: true },
  { source: "/marcas/:slug", destination: "/tienda/marcas/:slug", permanent: true },
  { source: "/marcas/:slug/:producto", destination: "/tienda/marcas/:slug/:producto", permanent: true },
  { source: "/piezas/:slug", destination: "/tienda/piezas/:slug", permanent: true },
  { source: "/novedades", destination: "/tienda?sort=recent", permanent: true },
  {
    source: "/categorias/:slug",
    has: [{ type: "query", key: "category", value: "(?<category>.*)" }],
    destination: "/tienda/:slug/:category",
    permanent: true,
  },
  { source: "/categorias/:slug", destination: "/tienda/:slug", permanent: true },
];
