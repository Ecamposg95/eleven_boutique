# Eleven Boutique: backend

API pública del catálogo y API del panel admin (FastAPI, SQLAlchemy, Alembic). Contratos: `../docs/api-contract.md` y `../docs/admin-api-contract.md`.

## Puesta en marcha

Requiere [`uv`](https://docs.astral.sh/uv/). Todos los comandos se corren desde `backend/`.

```sh
uv sync
cp .env.example .env                 # para ver datos demo: DEMO_MODE=true
uv run alembic upgrade head
uv run python -m scripts.import_brands
uv run python -m scripts.seed_base   # categorías y fila real de site_settings
uv run python -m scripts.seed_demo   # solo con DEMO_MODE=true; también corre los dos anteriores
uv run python -m scripts.publish_brands [--apply]  # publica las marcas en borrador; sin --apply solo simula
uv run uvicorn app.main:app --port 8000
```

API en `http://localhost:8000/api/v1`, documentación en `/docs`.

`publish_brands` deja en borrador las marcas pendientes de revisión (`PENDING_REVIEW` en `app/data/brand_rules.py`), las clasificaciones como "Sin marca" y las archivadas. Cada publicación queda en la auditoría.

## Panel admin

No hay usuarios ni credenciales por defecto. El primero se crea así (pide la contraseña, mínimo 12 caracteres, o la lee de `ADMIN_PASSWORD`):

```sh
uv run python -m scripts.create_admin correo@ejemplo.com                     # superadmin
uv run python -m scripts.create_admin otro@ejemplo.com --role editor
uv run python -m scripts.create_admin correo@ejemplo.com --reset-password    # cierra sus sesiones
```

- `APP_ENV=development` permite la cookie de sesión sin `Secure`. Cualquier otro valor, o no definirlo, la exige.
- Las mutaciones exigen un `Origin` que esté en `CORS_ORIGINS` o `PUBLIC_SITE_URL`. Una petición sin `Origin` (curl, servidor a servidor) recibe 403.
- Las fotos se reescriben y se guardan en `MEDIA_ROOT` (por defecto `media/`, fuera de git) y se sirven en `/media`. Para otro almacenamiento, implementa `StorageBackend` en `app/services/admin/storage.py`.
- Importación: `.xlsx` o `.csv`. Solo se leen `SKU`, `Nombre`, `Departamento`, `Marca`, `Color`, `Talla` y las referencias `Foto N` de `Descripcion`. Marcas y categorías base deben existir antes (`import_brands`, `seed_base`).

## Pruebas

```sh
uv run pytest -q
```

## Postgres

`uv sync --extra postgres` y `DATABASE_URL=postgresql+psycopg://usuario:clave@host/base`.
