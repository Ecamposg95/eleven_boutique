# ADR-0002 · Render de la web pública: Vite + prerender

- **Estado:** aceptado
- **Fecha:** 2026-10-06
- **Decisores:** Emmanuel Campos (producto, Atlas Tech)
- **Relacionados:** ADR-0001, task pack v1.0 §5 (SEO)

## Contexto

El pack exige HTML estático generado desde datos aprobados para la landing y las páginas públicas
críticas, y aclara que «el build de una SPA vacía no satisface este requisito». A la vez fija React
+ Vite + Router como stack web. Hay que evitar rutas indexables por cada combinación de filtros y
no emitir schema de precio o stock falso.

Opciones evaluadas:

1. **Vite + React Router con prerender en build** (modo framework de React Router, `ssr: false`
   más lista de rutas a prerenderizar).
2. Next.js para la parte pública (SSG/ISR).
3. Astro para la parte pública con islas React.

## Decisión

Opción 1. La web pública usa React Router en modo framework sobre Vite, **sin servidor SSR en
runtime**, prerenderizando en build:

| Ruta | Estrategia |
|---|---|
| `/` | Prerender con contenido de landing aprobado |
| `/catalogo` | Prerender de la primera página sin filtros; filtros, búsqueda y paginación en cliente vía API, con estado en la URL |
| `/producto/:slug` | Prerender de cada producto **publicado**, leído de la API en build |
| `/carrito`, `/checkout`, `/admin/*` | SPA (sin prerender), `noindex` |

Reglas SEO:

- URLs con parámetros de filtro llevan `<link rel="canonical">` a `/catalogo` y no entran al
  sitemap.
- `sitemap.xml` y `robots.txt` se generan en el mismo build con las rutas prerenderizadas.
- JSON-LD `Product` solo incluye `offers` cuando hay precio validado; `availability` solo con
  disponibilidad autorizada y vigente. En modo demo no se emite schema de producto.
- Las páginas demo llevan `noindex` mientras `DEMO_MODE=true`.

Actualización al publicar: publicar o archivar en el catálogo dispara un rebuild de la web
(deploy hook de Railway). En E1 el rebuild es manual.

## Consecuencias

- (+) Se mantiene el stack del pack; React Router ya es la librería de rutas prevista.
- (+) HTML real para buscadores y vista previa en redes sin operar un servidor Node.
- (−) Cada publicación requiere rebuild. Con miles de productos el build crece.
- **Revisión obligatoria:** reabrir este ADR cuando el catálogo publicado supere ~2,000 productos o
  el tiempo de build supere ~5 minutos, evaluando SSR en la web pública (React Router admite SSR
  sin cambiar de librería) sin alterar la API ni los módulos.
