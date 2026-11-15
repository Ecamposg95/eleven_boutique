# Sincronización con Atlas ONE — diseño

**Fecha:** 2026-11-14 · **Estado:** borrador para revisión
**Contraparte:** canal «Tienda en línea» de Atlas ONE, en producción desde 2026-11-14 (`fb1e88c3`), encendido para la
org 17 «Eleven Fashion» con solo la sucursal Roma 20 contando para disponibilidad. Contrato del canal:
`atlas-one/docs/API_REFERENCE.md` § «Canal Tienda en línea» y `atlas-one/docs/superpowers/specs/2026-11-14-canal-tienda-en-linea-design.md`.

## 1. Qué y por qué

Atlas ONE es la **fuente de verdad del catálogo** de Eleven. eleven.boutique deja de capturar productos: un proceso
periódico trae las piezas que el admin de Eleven **publica en Atlas ONE**, con variantes, fotos y disponibilidad, y las
mantiene al día. La web sigue siendo dueña de lo editorial (casas, categorías, portada, lookbooks, colecciones, textos SEO,
destacados). Además, la web le devuelve a Atlas ONE los clics a WhatsApp y las selecciones, para medir interés por pieza.

La web nunca muestra precio; Atlas ONE nunca le manda precio, costo ni cantidades.

### Decisiones del dueño (2026-11-14)

| # | Tema | Decisión |
|---|------|----------|
| E1 | Quién manda en casas y categorías | **La web.** Sus 77 casas curadas (alias, logo, foto editorial, destacada, **premium**) y su árbol de categorías se conservan. Las marcas de Atlas se ligan a casas por nombre/alias; los departamentos de Atlas a categorías por una tabla de equivalencias editable en el panel. Una marca de Atlas sin casa en la web entra como casa en **borrador** para curarla. `is_premium` de Atlas se ignora. |
| E2 | Pieza agotada | **Visible** con la etiqueta «Agotada · consulta disponibilidad»; su WhatsApp pregunta por esa pieza. Por talla: cada talla se marca disponible/agotada; la ficha queda agotada solo si se acaban todas. |
| E3 | Dónde corre | **Servicio cron de Railway** con la imagen del backend, cada 5 minutos, más un botón «Sincronizar ahora» en el panel. |

### Decisiones propuestas por Claude (el dueño puede corregirlas)

- Publicar en Atlas ⇒ publicado en la web. Si a una pieza le falta casa o categoría ligada, entra en **borrador** y el
  panel muestra el motivo.
- Fotos: se enlazan las URLs de Cloudinary que manda Atlas (`ProductMedia.url`, sin `media_asset_id`); no se procesan con
  Pillow. Fotos editoriales (portada, lookbooks, casas) siguen subiéndose en el panel.
- El panel deja de crear/borrar piezas y se retira el importador xlsx/csv. Lo editorial de la pieza (destacada, orden,
  SEO, notas internas) sigue editable.

### No objetivos
Precios, carrito o pagos · webhooks (Atlas no los tiene) · escribir en Atlas ONE nada salvo métricas/prospectos ·
captura de datos personales (los clics siguen siendo anónimos; el formulario con teléfono no existe aún).

### Anti-objetivos
- Que una falla de la sincronización tumbe o vacíe el sitio público.
- Que la sincronización pise lo editorial (casas, categorías, SEO, destacados, orden).
- Que la llave de Atlas aparezca en el repo, logs o respuestas de la API.
- Dos sincronizaciones corriendo a la vez.

## 2. Estado actual (leído en el código)

- Backend FastAPI + SQLAlchemy 2 + Alembic (migraciones `0001`–`0004`); Postgres en Railway, SQLite en local.
- `Product`: `sku` único, `slug` único, `brand_id` y `category_id` **obligatorios**, `status` draft/published/archived,
  `published_at`, `commercial_added_at`, `external_inventory_id` (sin uso), `photo_refs`, SEO, `is_featured`,
  `display_order`, `is_demo`. `ProductVariant`: `sku` único, color, talla. `ProductMedia`: url, alt, is_primary, position,
  `media_asset_id` opcional.
- `Brand`: kind (brand/classification, existe la clasificación «sin marca»), `is_premium`, `status`, `validation_status`,
  `BrandAlias`. `Category`: árbol con `parent_id`. El importador actual liga marcas con `normalize()` sobre nombre y alias.
- Visibilidad pública centralizada en `app/services/visibility.py`.
- `POST /events` (`whatsapp_click`) guarda `CatalogEvent(type, product_id, occurred_at)` anónimo. `POST /selection/consult`
  arma el WhatsApp de «Mi selección» (no guarda evento hoy).
- Producción: 77 casas, **0 productos publicados**. No hay cron ni worker.

## 3. Diseño

### 3.1 Cliente de Atlas (`app/services/atlas/client.py`)
- Config en `Settings`: `ATLAS_API_URL` (p. ej. `https://app.atlasone.com.mx/api/channel/v1`), `ATLAS_API_KEY` (secreto,
  nunca logueado), `ATLAS_SYNC_ENABLED` (bool, default false). **Una sola llave** con scopes `catalog:read` y
  `leads:write` (se emite así en Atlas `/platform/api-keys`). Si `/leads` responde 403, el paso de eventos se salta y se
  anota en la corrida; el resto de la corrida no falla.
- `httpx` (pasa de dev a dependencia), timeout 20 s, 3 reintentos con backoff en 5xx/429 (respeta `Retry-After`).
- Itera páginas: `{items, next_cursor, server_time}`; `updated_since` en ISO con `Z`.

### 3.2 Estado de sincronización (migración `0005_atlas_sync`)
- `atlas_sync_state` (fila única): `products_since`, `availability_since` (el `server_time` de la última corrida buena),
  `last_full_at`, `last_run_at`, `last_ok_at`, `last_error` (texto corto, sin secretos).
- `atlas_sync_runs`: id, started_at, finished_at, kind (`incremental`|`full`|`manual`), status (`ok`|`error`), contadores
  (creadas, actualizadas, bajas, borradores por falta de liga, disponibilidad cambiada, eventos enviados), error.
  Purga a 30 días.
- `atlas_category_map`: `atlas_department_id` (único) → `category_id` (nullable = sin ligar), `atlas_name`, `atlas_parent_id`.
- `atlas_brand_map`: `atlas_brand_id` (único) → `brand_id` (nullable), `atlas_name`.
- `Product.external_inventory_id` = id de Atlas (índice único parcial no nulo). `ProductVariant.external_inventory_id`
  (columna nueva) = id de variante de Atlas. `Product.available` y `ProductVariant.available` (bool, default true).
  `Product.atlas_missing` (texto nullable: «casa sin ligar: X», «categoría sin ligar: Y»).
- `catalog_events.forwarded_at` (nullable) para el reenvío.
- Candado: `pg_try_advisory_lock` en Postgres; en SQLite un candado de proceso (solo pruebas/local).

### 3.3 Corrida (`app/services/atlas/sync.py`, `scripts/sync_atlas.py`)
Orden de una corrida (sin candado → sale sin hacer nada):
1. **Marcas** (carga completa): cada marca de Atlas se liga por `atlas_brand_map`; si no hay fila, por `normalize()` contra
   nombre/alias de casas (misma lógica del importador, extraída a una función común). Si no hay casa: crea `Brand`
   `kind=brand`, `status=draft`, `validation_status=pending` y la liga. Nunca modifica casas existentes.
2. **Departamentos** (carga completa): alta/actualización de filas en `atlas_category_map` (nombre y padre); las nuevas
   quedan sin ligar. Ids que ya no vienen se marcan sin ligar.
3. **Productos**: `updated_since = products_since − 10 min` (o carga completa si es la nocturna o no hay estado).
   - `deleted:true` → la pieza con ese `external_inventory_id` pasa a `archived` (no se borra: conserva SEO, eventos y
     enlaces).
   - Viva → upsert: nombre, descripción pública, género/modelo/material (columnas nuevas, §3.5), casa (por mapa; sin marca en Atlas → clasificación «sin marca»), categoría (por mapa), variantes
     (upsert por `external_inventory_id`; las que ya no vienen se borran), fotos (reemplaza las `ProductMedia` sin
     `media_asset_id`; las subidas en el panel se conservan), `available`.
   - `sku` y `slug` web se fijan **al crear** la pieza y no cambian. `sku` = `model` de Atlas si existe y está libre; si
     no, el SKU de la primera variante en orden alfabético; si también choca, se agrega `-2`, `-3`… Variante de Atlas sin
     SKU (no debería pasar) → `ATL-<primeros 8 del id>`.
   - Estado: publicada si tiene casa **publicada** y categoría ligada; si no, `draft` con `atlas_missing` («casa en
     borrador: X», «casa sin ligar: X», «categoría sin ligar: Y»). Así el panel lista todo lo que impide que una pieza
     salga. Pieza nueva: `published_at` y `commercial_added_at` = `web_published_at` de Atlas. Una pieza archivada que
     vuelve viva se republica.
   - **Ocultar en la web:** columna nueva `Product.hidden_on_web` (bool, default false) que el admin de la web puede
     prender; la sincronización nunca la toca y la visibilidad pública la respeta. Atlas decide qué está publicado; la
     web solo puede quitar de más, nunca agregar.
   - Nunca toca `is_featured`, `display_order`, `seo_*`, `internal_notes`, colecciones ni lookbooks.
4. **Disponibilidad**: `availability?updated_since = availability_since − 10 min`; aplica `available` a variantes y
   recalcula el del producto (alguna variante disponible).
5. **Eventos**: reenvía `catalog_events` con `forwarded_at IS NULL`, `occurred_at` ≤ 6 días y producto con
   `external_inventory_id`, como `POST /leads` (`source=web_whatsapp_click` | `web_selection`, `line` = boutique si la casa
   es premium, si no general —«sin marca» incluida—, `Idempotency-Key` = id del evento, sin `utm`), y marca
   `forwarded_at`. Una selección de 5 piezas son 5 eventos `selection` (la métrica de Atlas es por pieza). Eventos de más
   de 6 días o sin pieza de Atlas se marcan como reenviados sin enviar. La migración `0005` marca como reenviados todos
   los eventos existentes (no se manda historia vieja).
6. Guarda `server_time` de cada endpoint en el estado **solo si la corrida terminó bien**; registra la corrida.

La **nocturna** (primera corrida después de las 03:00 hora de México) hace carga completa de productos y archiva las
piezas con `external_inventory_id` que Atlas ya no devuelve como publicadas, **solo si recorrió todas las páginas sin
error** (una falla a medias nunca archiva lo no visto).

**Primera corrida:** es una carga completa normal. Hoy Atlas tiene 0 piezas publicadas de Eleven, así que lo que aparezca
en la web es exactamente lo que el admin vaya publicando en Atlas; no hace falta un modo «todo en borrador». La
disponibilidad ya llega calculada por Atlas con solo Roma 20.

### 3.4 Dónde corre
- Servicio Railway nuevo `sync` en el proyecto `eleven-boutique`, misma imagen del backend, comando
  `python -m scripts.sync_atlas`, cron `*/5 * * * *`, variables `DATABASE_URL`, `ATLAS_*`.
- Panel: `POST /admin/atlas/sync` (rol admin) corre la misma función en un hilo con el candado y devuelve la corrida;
  `GET /admin/atlas/status` (última corrida, error, contadores, piezas en borrador por liga).
- Con `ATLAS_SYNC_ENABLED=false` el script sale sin hacer nada (para staging/local).

### 3.5 Panel
- **Atlas ONE** (pantalla nueva): estado de la última corrida, botón «Sincronizar ahora», lista de piezas en borrador con
  su motivo, tabla de equivalencias departamento → categoría (selector del árbol), y marcas de Atlas → casa (selector;
  las creadas en borrador aparecen para curar).
- Piezas: ya no se crean ni se borran; nombre, variantes, fotos de Atlas y disponibilidad se ven de solo lectura con la
  marca «Viene de Atlas ONE». Lo editorial sigue editable.
- Se retira la importación xlsx/csv (endpoint y pantalla) y la creación de piezas.
- Género/modelo/material de Atlas se guardan como atributos de la pieza para filtros futuros (columnas nuevas nullable en
  `products`: `gender`, `model`, `material`); no se muestran aún si el diseño no los contempla.

### 3.6 Sitio público
- `ProductCard`/`ProductDetail` agregan `available` y, en variantes, `available`. Tarjeta y ficha muestran «Agotada ·
  consulta disponibilidad» cuando `available=false`; en la ficha, las tallas agotadas se ven tachadas.
- El WhatsApp de una pieza agotada dice «¿Tienen disponible …?» en vez del texto normal.
- `POST /selection/consult` guarda un `CatalogEvent(type="selection", product_id)` por pieza (anónimo) para reenviarlo.
- Orden de listados: las agotadas al final dentro de cada orden (sin ocultarlas).

## 4. Pruebas
- Cliente contra un servidor falso (httpx MockTransport): paginación, reintentos, 401/429.
- Sync: alta, actualización que no pisa lo editorial, baja → archived, republicar, pieza sin casa/categoría → draft con
  motivo, marca nueva → casa en borrador, variantes que desaparecen, fotos del panel se conservan, disponibilidad por
  talla y por pieza, idempotencia (correr dos veces = mismo estado), corrida fallida no avanza `*_since`, candado.
- Eventos: reenvío con `Idempotency-Key`, viejos y sin pieza se marcan sin enviar, `line` boutique/general.
- API pública: `available` en tarjeta/detalle; agotadas visibles al final; ninguna respuesta pública trae ids de Atlas.
- Front (vitest): etiqueta «Agotada», tallas tachadas, mensaje de WhatsApp de agotada.

## 5. Entrega
Rama en `eleven_boutique`, PRs: **1** cliente + estado + sync (backend, sin cron); **2** panel Atlas ONE + retiro del
importador; **3** sitio público (agotadas); **4** servicio cron en Railway + llave (operativo, con el usuario). Push a
`main` despliega solo (Railway), así que nada a `main` sin permiso.

## 6. Preguntas abiertas
- Texto exacto de la etiqueta y del WhatsApp de agotada (propuesta arriba).
- Si el árbol de categorías de la web necesita categorías nuevas para los departamentos de Eleven (lo decide quien cure
  la tabla de equivalencias).
