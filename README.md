# Eleven Boutique · Plataforma digital

Presencia digital, catálogo, organización de fotografías, atención por WhatsApp y comercio de
Eleven Boutique, conectable con Atlas ONE. Responsable de producto: Emmanuel Campos / Atlas Tech.

> **Estado actual: EB-01 (documentación base).** Todavía no hay código ejecutable; los comandos
> de abajo describen el arranque que se implementa en EB-02 y se marcarán como verificados
> cuando existan.

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

## Estructura (objetivo de EB-02)

```
apps/web/            Sitio público y /admin (React, TypeScript, Vite, React Router, Zustand)
apps/api/            API FastAPI /api/v1 (SQLAlchemy, Alembic, Pydantic)
workers/             Proceso Celery (desde E2/E3)
packages/contracts/  Tipos TS generados desde OpenAPI
fixtures/            Datos DEMO ficticios, versionados
infra/               docker-compose, Dockerfiles, Railway
docs/                Arquitectura, ADRs, runbooks
_source/             Material del cliente (fotos, Excel). Ignorado por git
```

## Requisitos (previstos)

- Node.js LTS + pnpm
- Python 3.12+ + uv
- Docker y Docker Compose

## Comandos (previstos, se implementan en EB-02)

```bash
cp .env.example .env            # variables sin secretos reales
docker compose up -d db         # Postgres con pgvector
pnpm install                    # dependencias web
uv sync --project apps/api      # dependencias API
pnpm db:migrate                 # migraciones Alembic
pnpm db:seed:demo               # carga fixtures DEMO
pnpm dev                        # web + API en modo desarrollo
pnpm lint && pnpm test          # verificación
pnpm build                      # build con prerender de páginas públicas
```

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
