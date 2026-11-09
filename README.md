# Eleven Boutique

Catálogo en línea y gestor de productos de Eleven Boutique (Atlas One). El sitio público muestra piezas, marcas, colecciones y lookbooks sin precios, carrito ni pago; las consultas se dirigen a WhatsApp. El panel admin administra el catálogo.

## Estructura

| Carpeta | Qué es |
|---|---|
| `backend/` | API pública y API del panel (FastAPI, SQLAlchemy, Alembic). SQLite en local, Postgres en producción. Ver [`backend/README.md`](backend/README.md). |
| `frontend/` | Sitio público y panel admin (Next.js App Router, Tailwind). Ver [`frontend/README.md`](frontend/README.md). |
| `docs/` | Contratos de API, sistema de diseño y créditos de imágenes demo. |

### Sitio público (`frontend/app`)

`/` inicio · `/piezas` catálogo · `/marcas` · `/colecciones` · `/lookbooks` · `/novedades` · `/buscar` · `/la-boutique` · `/contacto`

### Panel admin (`/admin`)

Productos, categorías, marcas, colecciones, lookbooks, multimedia, importación (`.xlsx`/`.csv`), configuración del sitio y auditoría. Usuarios con rol `superadmin` o `editor`.

## Levantar en local

Requiere [`uv`](https://docs.astral.sh/uv/) y Node.js.

```sh
# 1. API (terminal 1)
cd backend
uv sync
cp .env.example .env                       # DEMO_MODE=true para ver datos demo
uv run alembic upgrade head
uv run python -m scripts.seed_demo         # con DEMO_MODE=true; sin demo: import_brands + seed_base
uv run python -m scripts.create_admin tu@correo.com
uv run uvicorn app.main:app --port 8000

# 2. Sitio (terminal 2)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

- Sitio: http://localhost:3000
- Panel: http://localhost:3000/admin
- API: http://localhost:8000/api/v1 (documentación en http://localhost:8000/docs)

## Pruebas

```sh
cd backend && uv run pytest -q
cd frontend && npm run lint && npm run typecheck && npm test
```

## Documentación

- [`docs/api-contract.md`](docs/api-contract.md): API pública del catálogo.
- [`docs/admin-api-contract.md`](docs/admin-api-contract.md): API del panel admin.
- [`docs/design-system.md`](docs/design-system.md): sistema de diseño del sitio.
- [`docs/demo-image-credits.md`](docs/demo-image-credits.md): créditos de las imágenes demo.

## Próximos pasos

- Ampliar el alcance de landing a catálogo completo con gestor de productos.
- Integración con Atlas ONE para importar o sincronizar el catálogo de productos (por definir).
