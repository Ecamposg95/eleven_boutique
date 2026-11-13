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

## Producción

- **Railway**, proyecto `eleven-boutique`, entorno `production`: servicios `web` (`/frontend`),
  `api` (`/backend`) y Postgres. Ambos servicios se despliegan solos al hacer push a `main` en
  GitHub (`Ecamposg95/eleven_boutique`); cada uno solo reconstruye si cambian archivos de su carpeta.
- **Dominio** `eleven.boutique` en Hostinger: `A @ → 153.52.255.5` (borde de Railway) y `www` por CNAME.
- **Panel:** `https://eleven.boutique/admin`. Crear usuarios con
  `railway ssh --service api -- sh -c "cd /app && ADMIN_PASSWORD='…' python -m scripts.create_admin correo@dominio"`
  (contraseña de 12+ caracteres).

## Estado al 2026-11-13

- En vivo: portada a pantalla completa con fotos que rotan y titular «Viste tus propias reglas.»,
  menú lateral con Categorías/Casas, carrusel de categorías, páginas de categoría, barra
  «Filtros · Ordenar», lookbook «Invierno en lana» publicado. Diseño: `docs/design-system.md`.
- Producción tiene 77 marcas y **0 productos publicados**: el carrusel, «Categorías» del menú y las
  páginas de categoría se llenan solos al publicar piezas desde el panel.
- Pendiente de contenido: texto de «La boutique» (activa el cierre de portada), marca y nombre del
  blazer gris (dos fotos ya subidas, sin asignar).
- Pendiente de seguridad: rotar la contraseña del usuario admin creado en esta etapa.
- **«Mi selección»** (2026-11-13): en cada pieza, «Guardar en mi selección»; `/seleccion` reúne las
  piezas y arma un solo mensaje de WhatsApp (dos si se mezclan casas premium con línea Boutique).
  Vive en el navegador (localStorage), sin carrito ni cuenta. API: `POST /selection/consult`.

## Próximos pasos

- Ampliar el alcance de landing a catálogo completo con gestor de productos.
- Integración con Atlas ONE para importar o sincronizar el catálogo de productos (por definir).
