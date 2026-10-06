# Eleven Boutique · Plataforma digital

Presencia digital, catálogo, organización de fotografías, atención por WhatsApp y comercio de
Eleven Boutique, conectable con Atlas ONE. Responsable de producto: Emmanuel Campos / Atlas Tech.

> **Estado actual: EB-02 completo.** Monorepo, Postgres en Docker, API de catálogo de solo
> lectura con 32 productos DEMO y esqueleto web con prerender. La landing y el catálogo visual
> llegan en EB-03 a EB-05.

## Entregas

| Entrega | Resultado | Estado |
|---|---|---|
| E1 · Presencia y borrador | Landing, catálogo, ficha, carrito y checkout de demostración | En curso |
| E2 · Catálogo administrable | Importador, productos, variantes, imágenes y revisión | Pendiente |
| E3 · Piloto de fotografías | Lote procesado, duplicados, sugerencias, asociación y exportación | Pendiente |
| E4 · Atención asistida | Agente de WhatsApp en sandbox y bandeja humana | Pendiente |
| E5 · Conexión Atlas ONE | Productos, disponibilidad y pedidos conciliados | Pendiente |
| E6 · Venta transaccional | Cobro, reserva, pedido, surtido y seguimiento | Pendiente |

## Documentación

- [Arquitectura](docs/architecture.md)
- [ADR-0001 · Stack y estructura del repositorio](docs/adr/0001-stack-y-estructura-del-repositorio.md)
- [ADR-0002 · Render de la web pública (prerender)](docs/adr/0002-render-web-publica-prerender.md)
- [Decisiones y dependencias pendientes](docs/pending-decisions.md)

## Estructura

```
apps/web/            Sitio público y, más adelante, /admin (React Router 8 + Vite, Tailwind 4)
apps/api/            API FastAPI /api/v1 (SQLAlchemy 2.1, Alembic, Pydantic)
fixtures/demo/       Catálogo DEMO ficticio (32 productos, 231 variantes)
infra/db-init/       Inicialización de Postgres local (base eleven_test)
compose.yaml         Postgres + pgvector local; perfil `full` levanta también la API
docs/                Arquitectura, ADRs, pendientes
_source/             Material del cliente (fotos, Excel). Ignorado por git
```

`workers/` y `packages/contracts/` se crean cuando haya código que los use (E2 y EB-05).

## Requisitos

- Node.js 22+ con corepack (`corepack enable` una vez para tener `pnpm` en el PATH)
- Python 3.12+ y [uv](https://docs.astral.sh/uv/)
- Docker con Docker Compose

## Arranque local

```bash
cp .env.example .env     # valores locales, sin secretos
corepack enable          # habilita pnpm (una sola vez por máquina)
pnpm bootstrap           # dependencias web (pnpm) y API (uv)
pnpm db:up               # Postgres en localhost:5433 (crea también eleven_test)
pnpm db:migrate          # migraciones Alembic
pnpm db:seed:demo        # carga el catálogo DEMO; reejecutarlo no duplica
pnpm dev                 # API en :8000 y web en :5173
```

- API: <http://localhost:8000/api/v1/docs> (OpenAPI en `/api/v1/openapi.json`)
- Web: <http://localhost:5173>

API en contenedor (igual que en Railway): `docker compose --profile full up --build`.

## Verificación

```bash
pnpm lint        # ruff + mypy estricto (API) y typecheck (web)
pnpm test        # pytest contra la base eleven_test (requiere pnpm db:up)
pnpm build       # web con HTML prerenderizado en apps/web/build/client
```

## Endpoints disponibles

| Método y ruta | Descripción |
|---|---|
| `GET /api/v1/health` | Estado del servicio |
| `GET /api/v1/site` | Configuración pública del tenant: nombre, WhatsApp, flags |
| `GET /api/v1/catalog/products` | Productos publicados: `q`, `category`, `size`, `color`, `collection`, `price_min`, `price_max`, `sort` (`new`, `name`, `price_asc`, `price_desc`), `limit` (máx. `CATALOG_PAGE_MAX`), `cursor` |
| `GET /api/v1/catalog/products/{slug}` | Ficha con variantes y precios autorizados |
| `GET /api/v1/catalog/facets` | Valores de filtro con conteos y rango de precios |
| `GET /api/v1/catalog/collections` | Colecciones publicadas |
| `GET /api/v1/catalog/variants/{id}/availability` | Siempre `unknown` hasta que exista una fuente autorizada (E5) |

El tenant se resuelve en el servidor (`TENANT_SLUG`); los parámetros del cliente no lo cambian.

## Feature flags

`DEMO_MODE`, `CATALOG_PUBLIC_ENABLED`, `VISION_PROCESSING_ENABLED`, `WHATSAPP_AUTOREPLY_ENABLED`,
`ATLAS_SYNC_ENABLED`, `CHECKOUT_ENABLED`, `PAYMENTS_ENABLED`. Ver `.env.example`. Desactivar un
flag no borra datos.

## Material fuente

Los archivos del cliente se colocan en `_source/` (no se versiona):

```
_source/
  brand/     eleven_boutique_logo_vector.svg
  catalog/   Excel de catálogo
  photos/    muestra de fotografías
```

Los originales nunca se mueven, renombran ni modifican. Solo el logo se copia, sin alterarlo, a
`apps/web`.

## Reglas del proyecto

- Los datos demo están identificados en la interfaz y en origen; nunca se presentan como reales.
- No se inventan sucursales, políticas, precios, marcas verificadas ni disponibilidad.
- Stock desconocido se muestra como *Consultar disponibilidad*; sin precio validado, *Consultar
  precio*.
- El checkout real permanece desactivado (`CHECKOUT_ENABLED=false`) hasta E6.
- Ningún secreto en el repositorio ni en el bundle web.
