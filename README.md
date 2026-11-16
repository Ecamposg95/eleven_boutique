# Eleven Boutique

Catálogo en línea y gestor de productos de Eleven Boutique (Atlas One). El sitio público muestra piezas, marcas, colecciones y lookbooks sin precios, carrito ni pago; las consultas se dirigen a WhatsApp. El panel admin administra el catálogo.

## Estructura

| Carpeta | Qué es |
|---|---|
| `backend/` | API pública y API del panel (FastAPI, SQLAlchemy, Alembic). SQLite en local, Postgres en producción. Ver [`backend/README.md`](backend/README.md). |
| `frontend/` | Sitio público y panel admin (Next.js App Router, Tailwind). Ver [`frontend/README.md`](frontend/README.md). |
| `docs/` | Contratos de API, sistema de diseño y créditos de imágenes demo. |

### Sitio público (`frontend/app`)

`/` inicio · `/tienda` catálogo (departamentos y subcategorías en la ruta) · `/tienda/marcas` · `/tienda/piezas/[slug]` · `/colecciones` · `/lookbooks` · `/buscar` · `/la-boutique` · `/contacto`

Las rutas antiguas `/marcas`, `/piezas`, `/novedades` y `/categorias` redirigen de forma permanente a `/tienda`.

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

## Estado al 16 de noviembre de 2026

- **Tienda nueva** (rama `tienda-nueva`). Diseño: `docs/design-system.md`.
- **Portada premium:** portada con «Entrar a la tienda», pestañas por departamento con sus piezas
  recientes, «Recién llegado», franja de detalle y bloque de atención con WhatsApp, Línea Boutique
  e Instagram.
- **`/tienda`:** departamentos, subcategorías en la ruta (`/tienda/[departamento]/[subcategoría]`),
  filtro por marca y `?sort=recent`. Marcas y piezas viven en `/tienda/marcas` y `/tienda/piezas`.
- **Redirecciones permanentes** desde `/marcas`, `/piezas`, `/novedades` y `/categorias`. Los enlaces
  de WhatsApp de cada pieza apuntan a `/tienda`.
- **Instagram** en el pie y en el menú lateral, si hay URL configurada.
- **Panel:** nuevos campos para la portada de cada departamento (4:5, 1600 × 2000 px), la franja de
  detalle (21:9, 2880 × 1234 px; teléfono 4:5), el bloque de atención (16:9, 2880 × 1620 px;
  teléfono 4:5) y la URL de Instagram. Una URL de Instagram mal formada devuelve 422.
- Los slugs `marcas` y `piezas` están reservados: no pueden usarse como departamento.
- **Migración 0006** (`alembic upgrade head`): columnas de portada de departamento, detalle,
  atención e Instagram.
- Producción tiene 77 marcas y **0 productos publicados**: departamentos, «Recién llegado» y las
  páginas de la tienda se llenan solos al publicar piezas desde el panel.
- Pendiente de contenido: texto de «La boutique», marca y nombre del blazer gris (dos fotos ya
  subidas, sin asignar), y las fotos nuevas de departamento, detalle y atención.
- Pendiente de seguridad: rotar la contraseña del usuario admin creado en esta etapa.
- **«Mi selección»** (2026-11-13): en cada pieza, «Guardar en mi selección»; `/seleccion` reúne las
  piezas y arma un solo mensaje de WhatsApp (dos si se mezclan casas premium con línea Boutique).
  Vive en el navegador (localStorage), sin carrito ni cuenta. API: `POST /selection/consult`.

## Próximos pasos

- Ampliar el alcance de landing a catálogo completo con gestor de productos.
- Integración con Atlas ONE para importar o sincronizar el catálogo de productos (por definir).
