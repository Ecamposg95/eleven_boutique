import type { Config } from "@react-router/dev/config";

// ADR-0002: sin servidor SSR en runtime; HTML estático generado en build para las páginas
// públicas. Las rutas de catálogo y fichas se agregan a `prerender` en EB-05.
export default {
  ssr: false,
  prerender: ["/"],
} satisfies Config;
