# ADR-0001 · Stack base y estructura del repositorio

- **Estado:** aceptado
- **Fecha:** 2026-10-06
- **Decisores:** Emmanuel Campos (producto, Atlas Tech)
- **Relacionados:** ADR-0002 (render de la web pública), task pack v1.0 §5

## Contexto

El task pack pide mantener consistencia con el *Atlas Development Framework* (ADF). Al iniciar
EB-01 se confirmó que **no existe un repositorio ni plantilla ADF reutilizable**: el repo solo
contiene un `README.md` de un commit inicial. Este ADR define la convención que se adopta como
ADF para este proyecto, para que futuros proyectos Atlas puedan reutilizarla o divergir de forma
explícita.

Restricciones del pack que condicionan la decisión:

- Monolito modular con procesos separados para web, API y workers; sin microservicios.
- Web y admin en React + TypeScript + Vite + Router + Zustand.
- API en Python + FastAPI + Pydantic + SQLAlchemy + Alembic, REST versionada bajo `/api/v1`.
- PostgreSQL con `tenant_id` desde el inicio; pgvector para el piloto de similaridad.
- Redis + un único framework de workers (propuesta: Celery).
- Hosting candidato: Railway.

## Decisión

### Repositorio único (monorepo)

```
eleven_boutique/
├── apps/
│   ├── web/          # Sitio público + /admin (React, Vite, React Router, Zustand)
│   └── api/          # FastAPI: módulos de dominio + Alembic
├── workers/          # Proceso Celery (esqueleto hasta E2/E3); importa módulos de apps/api
├── packages/
│   └── contracts/    # Tipos TS generados desde el OpenAPI de la API
├── fixtures/         # Datos DEMO versionados (ficticios), separados de datos reales
├── infra/            # docker-compose, Dockerfiles, configuración Railway
├── docs/             # Arquitectura, ADRs, runbooks, pendientes
└── _source/          # Material del cliente (ignorado por git)
```

### Herramientas

| Área | Elección | Motivo |
|---|---|---|
| Gestor JS | pnpm workspaces | Monorepo ligero, instalación determinista |
| Gestor Python | uv (`pyproject.toml` + `uv.lock`) | Entornos reproducibles y rápidos |
| Lint/format JS | ESLint + Prettier | Estándar del ecosistema React |
| Lint/format Py | Ruff (lint + format) | Una herramienta, rápida |
| Tipos Py | mypy en módulos de dominio | Contratos Pydantic/SQLAlchemy verificados |
| Pruebas | Vitest (web), pytest (API), Playwright (E2E críticos) | Unitarias, integración y E2E según §13 |
| Contratos | OpenAPI generado por FastAPI → tipos TS en `packages/contracts` | Web y agente consumen la misma API; un solo contrato |
| Local | Docker Compose: Postgres (imagen con pgvector) + API; web con Vite dev | Arranque reproducible |
| Despliegue | Railway: servicio web estático, API, Postgres (Redis y worker desde E2/E3) | Elección del pack, confirmada para el preview |

Las versiones mayores concretas se fijan en EB-02 con los lockfiles, verificando compatibilidad
vigente; no se fijan en este ADR.

### Módulos de la API

Cada módulo vive en `apps/api/src/eleven/<módulo>/` con capas `models`, `schemas`, `service`,
`router`. Los módulos se comunican por servicios, no leyendo tablas ajenas.

`catalog`, `media`, `vision`, `commerce`, `conversations`, `integrations`, `content`,
`identity`, `audit`. Solo se crean los módulos que una entrega implementa; el resto queda
documentado, no como carpetas vacías.

### Reglas transversales

- `tenant_id` en toda entidad de negocio; el tenant se resuelve en el servidor (dominio/token),
  nunca desde un parámetro del cliente.
- Importes en `Decimal`/`NUMERIC` o centavos enteros; nunca `float`.
- Tiempos almacenados en UTC; presentación en `America/Mexico_City`, `es-MX`, MXN.
- Configuración por variables de entorno y feature flags (`DEMO_MODE`, `CATALOG_PUBLIC_ENABLED`,
  `VISION_PROCESSING_ENABLED`, `WHATSAPP_AUTOREPLY_ENABLED`, `ATLAS_SYNC_ENABLED`,
  `CHECKOUT_ENABLED`, `PAYMENTS_ENABLED`). Ningún secreto llega al bundle web.
- Datos demo marcados como tales en origen (`is_demo` / tenant demo) y en la interfaz.

## Alcance en E1

Por decisión de producto, E1 incluye **web + API de catálogo mínima**:

- API FastAPI con Postgres sirviendo un catálogo de solo lectura (`GET /api/v1/catalog/...`)
  cargado desde `fixtures/`, con `tenant_id` y migraciones Alembic desde el primer día.
- Sin Redis, workers, admin ni autenticación en E1 (llegan en EB-08+).
- El checkout es solo demostración en el cliente, bajo `CHECKOUT_ENABLED=false`.

## Consecuencias

- (+) Un solo repo con contrato compartido evita que web y agente diverjan en precios o productos.
- (+) La estructura admite workers y módulos nuevos sin reorganizar.
- (−) Dos ecosistemas (Node y Python) en el mismo repo: se mitiga con comandos unificados en el
  README y Docker Compose.
- (−) Esta convención *es* el ADF de facto; si Atlas publica un ADF formal, habrá que conciliar
  mediante un ADR nuevo.
