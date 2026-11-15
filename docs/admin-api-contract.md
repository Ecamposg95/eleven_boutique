# Contrato del panel admin

Base: `/api/v1/admin`. El navegador llama siempre por el mismo origen (rewrite de Next). Errores y paginado iguales a `api-contract.md`. El panel se publica en `/admin` y nunca se indexa.

## Seguridad

- Sesión opaca: token aleatorio en cookie `eleven_admin` (`HttpOnly`, `SameSite=Lax`, `Secure` fuera de desarrollo, 12 h). En base solo se guarda su hash. Nada en `localStorage`.
- Contraseñas con Argon2id. El primer usuario se crea con `python -m scripts.create_admin <email>`, que pide la contraseña o la lee de `ADMIN_PASSWORD`. No hay registro público ni credenciales por defecto.
- Bloqueo de login: 5 fallos en 15 min por email. Misma respuesta para email inexistente y contraseña errónea.
- Mutaciones: rechazar con 403 si `Origin` no está en `CORS_ORIGINS`/`PUBLIC_SITE_URL`.
- Roles `superadmin`, `admin`, `editor`. `editor` gestiona catálogo y fotos. Marcas, ajustes y la pantalla Atlas ONE exigen `admin` o superior; usuarios, `superadmin`.
- `audit_logs` registra usuario, operación, entidad, id, fecha y cambios `{campo: [antes, después]}`, sin secretos ni hashes.
- 401 sin sesión, 403 sin rol. Estos endpoints nunca aceptan ni devuelven precio, costo, stock ni código de barras.

## Reglas de publicación

Un producto solo pasa a `published` si tiene nombre, marca (o clasificación "Sin marca"), categoría y al menos una foto. Si su marca no está publicada, la respuesta es `409 brand_unpublished`; el cliente puede reenviar con `publish_brand: true`, lo que publica ambos y lo audita. `published_at` se fija la primera vez. Quitar la última foto de un producto publicado da 409. Nunca hay borrado físico de registros vinculados: `DELETE` archiva. El estado público sigue dependiendo de `status`, como en `visibility.py`.

## Endpoints

| Método | Ruta | Notas |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → cookie y `Me` |
| POST | `/auth/logout` | Revoca la sesión |
| GET | `/auth/me` | `Me = {id, email, role}` |
| GET | `/dashboard` | `{products: {draft, published, archived, without_photo}, brands: {draft, published}, consult_clicks_30d, whatsapp_configured}` |
| GET | `/products` | Lista con `?q=&status=&brand=&category=&has_photo=&page=&page_size=&sort=` |
| POST | `/products` | Retirado: 410 «Las piezas se publican desde Atlas ONE» |
| GET/PATCH/DELETE | `/products/{id}` | Campos: `name, slug, brand_id, category_id, status, is_featured, display_order, commercial_added_at, seo_title, seo_description, internal_notes, publish_brand, hidden_on_web`. Incluye `media` (con `read_only`), `variants` (con `available`), `photo_refs`, `from_atlas, available, atlas_missing, hidden_on_web, gender, model, material, admin_description`. En una pieza de Atlas (`from_atlas`) `name, slug, brand_id, category_id, status` dan 422 «Este campo viene de Atlas ONE», `DELETE` da 409, y sus fotos de Atlas (`read_only`) no se editan ni se borran (422); lo editorial (`hidden_on_web, is_featured, display_order, seo_*, internal_notes`, colecciones, fotos subidas al panel) sigue libre |
| POST | `/products/bulk` | `{ids, action: publish\|unpublish\|archive\|feature\|unfeature, publish_brand?}` → resultado por id, sin fallar el lote completo. En piezas de Atlas, `publish/unpublish/archive` fallan con 422 |
| POST | `/products/{id}/media` | Asocia `{media_asset_id, alt?}` |
| PATCH | `/products/{id}/media` | Reordena y define principal: `{order: [media_id...], primary_id}` |
| PATCH | `/products/{id}/media/{media_id}` | `{alt}` de la foto en este producto |
| DELETE | `/products/{id}/media/{media_id}` | Desvincula; no borra el archivo |
| GET/POST | `/media` | Multipart, uno o varios archivos. Lista paginada con `?q=&unused=` |
| PATCH/DELETE | `/media/{id}` | `alt`. Borrar da 409 si está en uso |
| POST | `/media/bulk-match` | `{media_asset_ids}` → propuesta por archivo: `{media_asset_id, filename, product_id, match: sku\|photo_ref\|none, candidates}`. Ambiguo = sin asignar. No guarda nada |
| POST | `/media/bulk-assign` | `{items: [{media_asset_id, product_id}]}` |
| GET/POST, GET/PATCH | `/brands`, `/brands/{id}` | `name, slug, logo_asset_id, editorial_asset_id, description, display_order, is_featured, is_premium, status, validation_status, aliases[]`. `is_premium` manda las consultas de sus piezas a la línea Boutique. Sin fusiones. Cambiar slug conserva el anterior como alias |
| GET/POST, PATCH/DELETE | `/categories`, `/categories/{id}` | `DELETE` da 409 si tiene productos o hijas |
| GET/POST, GET/PATCH/DELETE | `/collections`, `/collections/{id}` | `title, slug, summary, cover_asset_id, status, display_order, product_ids[]` ordenados |
| GET/POST, GET/PATCH/DELETE | `/lookbooks`, `/lookbooks/{id}` | Igual, más `blocks[]` con las formas de `LookbookBlock` |
| GET/PATCH | `/settings` | `whatsapp_number` (línea Ventas), `whatsapp_premium_number` (línea Boutique), `hero_asset_id, hero_mobile_asset_id, hero_gallery_asset_ids` (lista ordenada, máx. 8; la respuesta trae `hero_gallery: [{asset_id, url}]`), `hero_headline, hero_subhead, intro, boutique_body, contact_body` |
| GET | `/atlas/status` | `admin`. `{enabled, last_run: {kind, status, started_at, finished_at, counts, error} \| null, last_ok_at, drafts: [{id, name, atlas_missing}]}` |
| POST | `/atlas/sync` | `admin`. Corre una sincronización manual en segundo plano: 202 `{started: true}`; 409 si ya hay una en curso o no está configurada |
| GET/PATCH | `/atlas/brand-map` | `admin`. `[{atlas_brand_id, atlas_name, brand_id}]`; PATCH `{atlas_brand_id, brand_id \| null}`. Solo casas de tipo marca; 422 si no existe o es la casa interna «Pendiente de ligar (Atlas ONE)» |
| GET/PATCH | `/atlas/category-map` | `admin`. `[{atlas_department_id, atlas_name, category_id}]`; PATCH `{atlas_department_id, category_id \| null}` |
| GET | `/audit` | Paginado, solo `admin` o superior |

`GET /site-settings/public` añade `hero.mobile_image_url: string | null` y `hero.gallery: string[]` (fotos extra que se turnan después de la principal). Las URL públicas de archivos son `/media/...`.

## Decisiones de implementación

- **Origin:** si falta en una mutación, 403. Debe coincidir exacto: `127.0.0.1:3000` falla si solo está configurado `localhost:3000`.
- **`sku` de producto:** `POST /products` lo acepta opcional o genera `ELV-…`. Se devuelve, pero `PATCH` no lo cambia.
- **Usuarios:** sin endpoints. Se gestionan solo con `scripts.create_admin`.
- **Rol y `publish_brand`:** publicar una marca exige `admin`; un `editor` que lo envíe sobre una marca sin publicar recibe 403.
- **Preview:** no toca el catálogo, pero escribe una fila en `import_runs` con las columnas permitidas, necesaria para el commit. 410 `preview_expired`, 409 `preview_already_used`.
- **Paginado admin:** `page_size` hasta 200. `/categories` devuelve el árbol completo con forma paginada.
- **Respuestas:** bulk `{results: [{id, ok, error}]}`; bulk-assign `{results: [{media_asset_id, product_id, ok, error}]}`; subida `{items, errors}`, 201 con éxito parcial y error si nada se guardó. Candidatos de match `{id, sku, name}`.
- **Galería:** las llamadas devuelven el producto actualizado. `media_id` es el id del vínculo de galería, no el del archivo.
- **Códigos:** 429 `too_many_attempts` con `Retry-After`; 409 `photo_required`, `brand_unpublished`, `last_photo`.
- **Permisos de `editor`:** lee marcas y gestiona categorías, colecciones y lookbooks.
- **Importación:** producto sin cambios cuenta como `skipped`. `update_existing` agrega y actualiza variantes y refresca `photo_refs`, pero no borra variantes ausentes. Un SKU sin talla y otro con talla del mismo SKU base y marca se unen. Celdas con fórmula son error de fila y su texto se descarta.
- **Ajustes públicos:** `public_settings` prefiere la fila real sobre la demo.

## Fotos

- Solo JPEG, PNG y WebP, verificados por contenido, no por extensión. Máx. 20 MB y 60 MP.
- Se reescriben con Pillow: orientación aplicada, sin EXIF, lado mayor máx. 2400 px. Nombre aleatorio; el nombre original se guarda solo como dato, sanitizado.
- `StorageBackend` con implementación local (`MEDIA_ROOT`, default `backend/media/`, en `.gitignore`), preparado para S3. FastAPI sirve `/media`; Next hace rewrite de `/media/:path*` al backend.

## Importación de catálogo

Retirada: las piezas llegan de Atlas ONE (sincronización). Ya no existen `/imports/*` ni la creación manual de piezas.
