# Sincronización con Atlas ONE — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que eleven.boutique traiga de Atlas ONE, cada 5 minutos, las piezas publicadas con variantes, fotos y disponibilidad, sin pisar lo editorial, y le devuelva los clics y selecciones.

**Architecture:** Paquete `app/services/atlas/` (cliente HTTP, ligas de casas/categorías, sincronización, reenvío de eventos) llamado desde `scripts/sync_atlas.py` (cron de Railway) y desde el panel («Sincronizar ahora»). Estado y bitácora en tablas propias (migración `0005`), candado de Postgres para no correr dos a la vez. El sitio público muestra «Agotada» y tallas tachadas a partir de `available`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, httpx, pytest; Next.js (App Router) + vitest.

**Spec:** `docs/superpowers/specs/2026-11-14-sincronizacion-atlas-one-design.md` (contrato del canal: `atlas-one/docs/API_REFERENCE.md` § «Canal Tienda en línea»; implementación de referencia en `atlas-one/app/modules/canal/`).

## Global Constraints

- Rama `feat/sync-atlas-one`; nada a `main` sin permiso (push a `main` despliega solo en Railway).
- La llave (`ATLAS_API_KEY`) nunca en repo, logs, respuestas ni mensajes de error; `last_error` guarda texto sin cabeceras.
- La sincronización nunca toca: `Brand` existentes (salvo crear en borrador), `Category`, `is_featured`, `display_order`, `seo_*`, `internal_notes`, `hidden_on_web`, colecciones, lookbooks, `ProductMedia` con `media_asset_id`.
- `sku` y `slug` de una pieza se fijan al crearla y no cambian.
- Una corrida fallida no avanza `products_since` / `availability_since`; el archivado nocturno solo tras recorrer todas las páginas sin error.
- Ninguna respuesta pública trae ids de Atlas (`external_inventory_id`) ni `atlas_missing`.
- Traslape de sincronización: `updated_since = since − 10 min`; fechas ISO con `Z`.
- Etiqueta pública exacta: «Agotada · consulta disponibilidad».
- Migraciones con Alembic (`backend/alembic/versions/0005_atlas_sync.py`, `down_revision = "0004"`), compatibles con SQLite y Postgres.
- Backend: `cd backend && uv run pytest -q`; front: `cd frontend && npm test && npm run lint && npm run build`.
- Comentarios y textos en español, como el código existente. Commits con las líneas `Co-Authored-By`/`Claude-Session` del harness.

## Review Focus

1. **Atlas caído o lento** — la corrida termina con `status=error` y mensaje claro; el sitio público sigue sirviendo lo último sincronizado (T4).
2. **Una marca de Atlas cuyo nombre coincide con dos casas de la web** (alias duplicado) — no adivinar: la pieza queda en borrador «casa ambigua: X» (T3).
3. **Pieza editada en el panel y luego cambiada en Atlas** — los campos editoriales sobreviven a la siguiente corrida (T4).
4. **Dos corridas simultáneas** (cron + botón) — la segunda sale sin hacer nada y el botón lo dice (T4, T6).
5. **Pieza agotada que vuelve a tener existencia** — la etiqueta desaparece en la siguiente corrida sin intervención (T4, T8).

---

### Task 1: Migración 0005 y modelos

**Files:**
- Create: `backend/alembic/versions/0005_atlas_sync.py`, `backend/app/models/atlas.py`
- Modify: `backend/app/models/catalog.py` (columnas nuevas), `backend/app/models/content.py` (`CatalogEvent.forwarded_at`), `backend/app/models/__init__.py`
- Test: `backend/tests/test_migrations.py` (extender), `backend/tests/test_atlas_models.py`

**Interfaces:**
- Produces: `Product.external_inventory_id` (ya existe; índice único parcial no nulo `uq_products_external_inventory_id`), `Product.available: bool` (default true), `Product.atlas_missing: str|None`, `Product.hidden_on_web: bool` (default false), `Product.gender|model|material: str|None`; `ProductVariant.external_inventory_id: str|None` (único no nulo), `ProductVariant.available: bool` (default true); `CatalogEvent.forwarded_at: datetime|None`; modelos `AtlasSyncState` (`atlas_sync_state`, fila única id=1: `products_since`, `availability_since`, `last_full_at`, `last_run_at`, `last_ok_at`, `last_error`), `AtlasSyncRun` (`atlas_sync_runs`: id uuid, `started_at`, `finished_at`, `kind`, `status`, `counts` JSON, `error`), `AtlasBrandMap` (`atlas_brand_map`: `atlas_brand_id` único, `atlas_name`, `brand_id` FK nullable), `AtlasCategoryMap` (`atlas_category_map`: `atlas_department_id` único, `atlas_name`, `atlas_parent_id`, `category_id` FK nullable).

- [ ] **Step 1:** Pruebas que fallan: la migración sube y baja en SQLite (patrón de `test_migrations.py`); tras subir, todo `catalog_events` existente tiene `forwarded_at` no nulo (la migración los marca); crear dos productos con el mismo `external_inventory_id` → `IntegrityError`; dos con `NULL` → ok; defaults `available=True`, `hidden_on_web=False`.
- [ ] **Step 2:** `cd backend && uv run pytest -q tests/test_migrations.py tests/test_atlas_models.py` → FAIL.
- [ ] **Step 3:** Implementar migración (índices únicos parciales con `sqlite_where`/`postgresql_where`) y modelos.
- [ ] **Step 4:** PASS + suite completa.
- [ ] **Step 5:** Commit `feat(atlas): esquema de sincronización (migración 0005)`.

### Task 2: Cliente de Atlas

**Files:**
- Create: `backend/app/services/atlas/__init__.py`, `backend/app/services/atlas/client.py`
- Modify: `backend/app/config.py` (`atlas_api_url: str = ""`, `atlas_api_key: str = ""`, `atlas_sync_enabled: bool = False`), `backend/pyproject.toml` (`httpx` a dependencias), `backend/uv.lock`
- Test: `backend/tests/test_atlas_client.py`

**Interfaces:**
- Produces: `class AtlasError(Exception)` (mensaje sin la llave); `class AtlasForbidden(AtlasError)`; `class AtlasClient(base_url: str, api_key: str, *, transport: httpx.BaseTransport | None = None, timeout: float = 20.0)` con `iter_pages(path: str, updated_since: datetime | None) -> Iterator[tuple[list[dict], str]]` (items de cada página y el `server_time` de la primera página), `post_lead(payload: dict, idempotency_key: str) -> int` (status), `close()`; `fmt_since(dt: datetime) -> str` (ISO UTC con `Z`).

- [ ] **Step 1:** Pruebas con `httpx.MockTransport`: sigue `next_cursor` hasta null y devuelve el `server_time` de la primera página; manda `Authorization: Bearer <key>` y `updated_since` con `Z`; 5xx/429 reintenta 3 veces respetando `Retry-After` (sleep inyectable, sin dormir de verdad); 401 → `AtlasError` cuyo `str()` no contiene la llave; 403 en `post_lead` → `AtlasForbidden`; `post_lead` manda `Idempotency-Key`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + suite. **Step 5:** Commit `feat(atlas): cliente HTTP del canal`.

### Task 3: Ligas de casas y categorías

**Files:**
- Create: `backend/app/services/atlas/links.py`, `backend/app/services/brand_match.py`
- Test: `backend/tests/test_atlas_links.py`

**Interfaces:**
- Consumes: modelos de T1; `app.services.text.normalize`.
- Produces: `brand_index(db) -> tuple[dict[str, set[uuid.UUID]], dict[uuid.UUID, Brand]]` (nombre y alias normalizados → ids); `sync_brands(db, atlas_brands: list[dict]) -> dict[str, int]` (contadores `ligadas`, `creadas_borrador`); `sync_departments(db, atlas_departments: list[dict]) -> dict[str, int]`; `resolve_brand(db, atlas_brand_id: str | None) -> tuple[Brand | None, str | None]` (casa o motivo: `"casa sin ligar: X"`, `"casa ambigua: X"`, `"casa en borrador: X"`; `None` → clasificación «sin marca»); `resolve_category(db, atlas_department_id: str | None) -> tuple[Category | None, str | None]` (`"categoría sin ligar: Y"`).

- [ ] **Step 1:** Pruebas: marca de Atlas igual a un alias → liga a esa casa y guarda fila en el mapa; mapa existente gana sobre el nombre; nombre que coincide con dos casas → no liga, `resolve_brand` da «casa ambigua»; marca sin casa → crea `Brand(kind=brand, status=draft, validation_status=pending)` y la liga, una sola vez aunque se corra dos veces; nunca modifica una casa existente (compara columnas antes/después); departamentos nuevos quedan con `category_id=None`; departamento que ya no viene → `category_id=None`; `atlas_brand_id=None` → clasificación «sin marca».
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + suite. **Step 5:** Commit `feat(atlas): ligas de casas y categorías`.

### Task 4: Sincronización de piezas y disponibilidad

**Files:**
- Create: `backend/app/services/atlas/sync.py`, `backend/scripts/sync_atlas.py`
- Test: `backend/tests/test_atlas_sync.py`

**Interfaces:**
- Consumes: `AtlasClient` (T2), `links` (T3), modelos (T1).
- Produces: `run_sync(db_factory: Callable[[], Session], client: AtlasClient, *, kind: Literal["incremental","full","manual"] = "incremental", now: Callable[[], datetime] = utcnow) -> AtlasSyncRun | None` (None si no obtuvo el candado); `with_lock(db) -> ContextManager[bool]` (`pg_try_advisory_lock(hashtext('atlas_sync'))` en Postgres; `threading.Lock` no bloqueante en SQLite); `is_nightly_due(state, now) -> bool` (primera corrida tras las 03:00 America/Mexico_City del día sin `last_full_at` de ese día); `forward_events` se llama aquí pero lo implementa T5 (stub que devuelve 0 si T5 no está; T5 lo reemplaza). Script: `python -m scripts.sync_atlas [--full]` sale 0 sin hacer nada si `atlas_sync_enabled` es falso.

- [ ] **Step 1:** Pruebas con un Atlas falso (`MockTransport` que sirve brands/departments/products/availability en memoria):
  - alta: pieza publicada con casa y categoría ligadas → `published`, `published_at = web_published_at`, variantes con `external_inventory_id`, fotos como `ProductMedia` sin `media_asset_id`, `available`;
  - sin categoría ligada → `draft`, `atlas_missing="categoría sin ligar: Y"`; al ligarla, la siguiente corrida la publica y limpia el motivo;
  - casa en borrador → `draft` con «casa en borrador: X»;
  - no pisa lo editorial: poner `is_featured`, `display_order`, `seo_title`, `internal_notes`, `hidden_on_web` y una foto con `media_asset_id`; cambiar nombre en Atlas; tras correr, el nombre cambia y lo editorial sigue igual;
  - `sku`: usa `model` libre; si choca usa el SKU de la primera variante (orden alfabético); si choca, sufijo `-2`; no cambia en corridas siguientes aunque cambie `model`;
  - variante que desaparece en Atlas se borra; nueva se agrega;
  - `deleted:true` → `archived`; vuelve viva → `published` otra vez con el mismo `slug`;
  - disponibilidad: `/availability` con una variante en false → variante false, producto true si queda otra; todas false → producto false; vuelve true → producto true;
  - idempotencia: dos corridas seguidas sin cambios en Atlas → mismo estado, contadores en cero la segunda;
  - Atlas responde 500 en `/products` → corrida `status=error`, `products_since` sin avanzar, piezas existentes intactas;
  - `updated_since` enviado = `products_since − 10 min` con `Z`;
  - nocturna: archiva piezas con `external_inventory_id` que no vinieron; con un 500 a media carga no archiva nada;
  - candado ocupado → `run_sync` devuelve None sin escribir corrida.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar (una transacción por página de productos; estado y bitácora al final; purga de `atlas_sync_runs` > 30 días). **Step 4:** PASS + suite. **Step 5:** Commit `feat(atlas): sincronización de piezas y disponibilidad`.

### Task 5: Reenvío de clics y selecciones

**Files:**
- Create: `backend/app/services/atlas/events.py`
- Modify: `backend/app/services/catalog.py` (`consult_selection` guarda un `CatalogEvent(type="selection")` por pieza visible), `backend/app/services/atlas/sync.py` (llamar `forward_events` en lugar del stub)
- Test: `backend/tests/test_atlas_events.py`, `backend/tests/test_selection.py` (extender)

**Interfaces:**
- Consumes: `AtlasClient.post_lead`, `AtlasForbidden` (T2).
- Produces: `forward_events(db, client, now) -> dict[str, int]` (`enviados`, `descartados`, `error`); payload: `{"source": "web_whatsapp_click"|"web_selection", "product_ids": [<external_inventory_id>], "line": "boutique"|"general", "occurred_at": <ISO Z>}`; `Idempotency-Key` = `str(event.id)`.

- [ ] **Step 1:** Pruebas: clic de pieza de Atlas con casa premium → `line="boutique"`, `source="web_whatsapp_click"`, marca `forwarded_at`; casa no premium o «sin marca» → `general`; evento de 7 días → marcado sin enviar; pieza sin `external_inventory_id` o `product_id` nulo → marcado sin enviar; 403 → deja los eventos sin marcar y devuelve `error=1` sin lanzar; repetir no reenvía; `POST /selection/consult` con 3 piezas guarda 3 eventos `selection`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + suite. **Step 5:** Commit `feat(atlas): reenvío de clics y selecciones`.

### Task 6: API del panel

**Files:**
- Create: `backend/app/api/v1/admin/atlas.py`, `backend/app/services/admin/atlas.py`
- Modify: `backend/app/api/v1/admin/__init__.py` (montar), `backend/app/api/v1/admin/catalog.py` y `backend/app/services/admin/products.py` (quitar `POST /products` y `DELETE /products/{id}` para piezas de Atlas: 409 «Viene de Atlas ONE»; `PATCH` ignora/rechaza 422 los campos que vienen de Atlas en piezas con `external_inventory_id`: `name`, `sku`, `slug`, `brand_id`, `category_id`, `status`; acepta `hidden_on_web` y lo editorial), borrar `backend/app/services/admin/catalog_import.py` y `tests/test_admin_import.py` si ya nada los usa, `backend/app/api/v1/admin/imports.py` (quitar `POST /products` de importación y `GET /template`), `backend/app/schemas/admin.py`
- Test: `backend/tests/test_admin_atlas.py`, ajustar `backend/tests/test_admin_import.py` y `backend/tests/test_admin_catalog.py`

**Interfaces:**
- Consumes: `run_sync` (T4), mapas (T1/T3).
- Produces: `GET /admin/atlas/status` → `{enabled, last_run: {kind,status,started_at,finished_at,counts,error}|null, last_ok_at, drafts: [{id, name, atlas_missing}]}`; `POST /admin/atlas/sync` (rol admin) → corre `run_sync(kind="manual")` en un hilo con su propia sesión, responde 202 `{started: true}` o 409 `{detail: "Ya hay una sincronización en curso"}`; `GET/PATCH /admin/atlas/brand-map` (`[{atlas_brand_id, atlas_name, brand_id}]`, PATCH `{atlas_brand_id, brand_id|null}`), `GET/PATCH /admin/atlas/category-map` (igual con `atlas_department_id`/`category_id`); `AdminProduct` agrega `from_atlas: bool`, `available`, `atlas_missing`, `hidden_on_web`, variantes con `available`.

- [ ] **Step 1:** Pruebas: editor sin rol admin → 403 en sync y mapas; status refleja la última corrida; sync con candado ocupado → 409; PATCH de mapas valida que la casa/categoría exista; crear pieza manual → 409/410 con mensaje; PATCH de `name` en pieza de Atlas → 422; PATCH de `hidden_on_web`, `seo_title`, `is_featured` → ok; importación xlsx → 404/410.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + suite. **Step 5:** Commit `feat(admin): pantalla Atlas ONE en la API y piezas de solo lectura`.

### Task 7: Panel (frontend)

**Files:**
- Create: `frontend/app/admin/(panel)/atlas/page.tsx`, `frontend/components/admin/AtlasPanel.tsx`, `frontend/components/admin/AtlasMaps.tsx`
- Modify: `frontend/components/admin/AdminShell.tsx` (entrada «Atlas ONE»), `frontend/components/admin/ProductEditor.tsx` (campos de Atlas de solo lectura con la marca «Viene de Atlas ONE», casilla «Ocultar en la web», sin botón borrar), `frontend/components/admin/ProductTable.tsx` (columna Disponible/Agotada y motivo de borrador), `frontend/lib/admin/types.ts`, `frontend/lib/admin/client.ts`; borrar `frontend/components/admin/ImportFlow.tsx` y su ruta, y el alta de piezas (`CreateByName` solo si únicamente lo usa productos — verificar con grep)
- Test: `frontend/components/admin/__tests__/AtlasPanel.test.tsx` (o junto a `lib/admin` siguiendo el patrón del repo)

**Interfaces:**
- Consumes: endpoints de T6.

- [ ] **Step 1:** Pruebas vitest: el panel muestra estado y errores de la última corrida; «Sincronizar ahora» llama al endpoint y muestra «Ya hay una sincronización en curso» en 409; los mapas permiten elegir casa/categoría y guardan; el editor de una pieza de Atlas no permite editar nombre ni borrar, sí «Ocultar en la web».
- [ ] **Step 2:** FAIL. **Step 3:** Implementar siguiendo `docs/design-system.md` y componentes `components/admin/ui.tsx`. **Step 4:** `npm test && npm run lint && npm run build` → PASS. **Step 5:** Commit `feat(admin): pantalla Atlas ONE y piezas de solo lectura`.

### Task 8: API pública: agotadas y ocultas

**Files:**
- Modify: `backend/app/services/visibility.py` (`product_visible` exige `hidden_on_web` falso), `backend/app/services/catalog.py` (`_card_fields`, `get_product`, listados ordenan `available DESC` primero dentro de cada orden; `build_consult_url` con texto de agotada), `backend/app/services/whatsapp.py` (`build_consult_url(..., available: bool = True)`), `backend/app/schemas/public.py` (`ProductCard.available: bool`; `ProductDetail.variants: list[{color, size, available}]`), `docs/api-contract.md`
- Test: `backend/tests/test_products.py`, `backend/tests/test_whatsapp.py`, `backend/tests/test_contract_shapes.py`

**Interfaces:**
- Produces: `ProductCard.available`, `ProductDetail.variants[].{color,size,available}`; mensaje de agotada: «Hola, ¿tienen disponible esta pieza de Eleven Boutique: {label}? Referencia: {sku}. Enlace: {link}.»

- [ ] **Step 1:** Pruebas: pieza oculta no aparece en listados, búsqueda, colecciones ni detalle (404); agotada aparece con `available=false` y al final del listado; detalle trae variantes con `available`; ninguna respuesta pública trae `external_inventory_id` ni `atlas_missing` (recorrer el JSON); consult_url de agotada usa el texto nuevo.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + suite. **Step 5:** Commit `feat(catalogo): piezas agotadas visibles y piezas ocultas`.

### Task 9: Sitio público (frontend)

**Files:**
- Modify: `frontend/components/ProductCard.tsx`, `frontend/components/ProductView.tsx`, `frontend/components/ConsultButton.tsx` (si el texto vive ahí), `frontend/lib/api.ts` (tipos)
- Test: vitest junto a los componentes según el patrón del repo

**Interfaces:**
- Consumes: `available` y `variants` de T8.

- [ ] **Step 1:** Pruebas vitest: tarjeta con `available=false` muestra «Agotada · consulta disponibilidad»; ficha lista tallas y las agotadas se ven tachadas (clase y `aria-label` «agotada»); disponible no muestra etiqueta.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar con `docs/design-system.md`. **Step 4:** `npm test && npm run lint && npm run build` → PASS. **Step 5:** Commit `feat(sitio): etiqueta de agotada y tallas`.

### Task 10: Operación (con el usuario, tras fusionar)

- [ ] Documentar en `README.md` el servicio `sync` (Railway cron `*/5 * * * *`, comando `python -m scripts.sync_atlas`, variables `ATLAS_API_URL`, `ATLAS_API_KEY`, `ATLAS_SYNC_ENABLED`, `DATABASE_URL`) y en `atlas-one/docs/API_REFERENCE.md` el `POST /leads` (scope `leads:write`, cuerpo, 201/202, `Idempotency-Key`).
- [ ] Con permiso: el usuario crea la llave en Atlas y las variables en Railway; crear el servicio cron; primera corrida manual desde el panel; revisar mapas de casas y categorías.
