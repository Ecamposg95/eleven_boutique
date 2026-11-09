# Contrato del panel admin

Base: `/api/v1/admin`. El navegador llama siempre por el mismo origen (rewrite de Next). Errores y paginado iguales a `api-contract.md`. El panel se publica en `/admin` y nunca se indexa.

## Seguridad

- Sesión opaca: token aleatorio en cookie `eleven_admin` (`HttpOnly`, `SameSite=Lax`, `Secure` fuera de desarrollo, 12 h). En base solo se guarda su hash. Nada en `localStorage`.
- Contraseñas con Argon2id. El primer usuario se crea con `python -m scripts.create_admin <email>`, que pide la contraseña o la lee de `ADMIN_PASSWORD`. No hay registro público ni credenciales por defecto.
- Bloqueo de login: 5 fallos en 15 min por email. Misma respuesta para email inexistente y contraseña errónea.
- Mutaciones: rechazar con 403 si `Origin` no está en `CORS_ORIGINS`/`PUBLIC_SITE_URL`.
- Roles `superadmin`, `admin`, `editor`. `editor` gestiona catálogo y fotos. Marcas, ajustes e importación exigen `admin` o superior; usuarios, `superadmin`.
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
| GET/POST | `/products` | Lista con `?q=&status=&brand=&category=&has_photo=&page=&page_size=&sort=` |
| GET/PATCH/DELETE | `/products/{id}` | Campos: `name, slug, brand_id, category_id, status, is_featured, display_order, commercial_added_at, seo_title, seo_description, internal_notes, publish_brand`. Incluye `media`, `variants`, `photo_refs` |
| POST | `/products/bulk` | `{ids, action: publish\|unpublish\|archive\|feature\|unfeature, publish_brand?}` → resultado por id, sin fallar el lote completo |
| POST | `/products/{id}/media` | Asocia `{media_asset_id, alt?}` |
| PATCH | `/products/{id}/media` | Reordena y define principal: `{order: [media_id...], primary_id}` |
| PATCH | `/products/{id}/media/{media_id}` | `{alt}` de la foto en este producto |
| DELETE | `/products/{id}/media/{media_id}` | Desvincula; no borra el archivo |
| GET/POST | `/media` | Multipart, uno o varios archivos. Lista paginada con `?q=&unused=` |
| PATCH/DELETE | `/media/{id}` | `alt`. Borrar da 409 si está en uso |
| POST | `/media/bulk-match` | `{media_asset_ids}` → propuesta por archivo: `{media_asset_id, filename, product_id, match: sku\|photo_ref\|none, candidates}`. Ambiguo = sin asignar. No guarda nada |
| POST | `/media/bulk-assign` | `{items: [{media_asset_id, product_id}]}` |
| GET/POST, GET/PATCH | `/brands`, `/brands/{id}` | `name, slug, logo_asset_id, editorial_asset_id, description, display_order, is_featured, status, validation_status, aliases[]`. Sin fusiones. Cambiar slug conserva el anterior como alias |
| GET/POST, PATCH/DELETE | `/categories`, `/categories/{id}` | `DELETE` da 409 si tiene productos o hijas |
| GET/POST, GET/PATCH/DELETE | `/collections`, `/collections/{id}` | `title, slug, summary, cover_asset_id, status, display_order, product_ids[]` ordenados |
| GET/POST, GET/PATCH/DELETE | `/lookbooks`, `/lookbooks/{id}` | Igual, más `blocks[]` con las formas de `LookbookBlock` |
| GET/PATCH | `/settings` | `whatsapp_number, hero_asset_id, hero_mobile_asset_id, hero_headline, hero_subhead, intro, boutique_body, contact_body` |
| POST | `/imports/products/preview` | Multipart `.xlsx` o `.csv` → `ImportPreview`. No escribe |
| POST | `/imports/products` | `{preview_id, update_existing: bool}` → `ImportResult` |
| GET | `/imports/template` | CSV plantilla |
| GET | `/imports/{id}/report` | CSV de resultados por fila |
| GET | `/audit` | Paginado, solo `admin` o superior |

`GET /site-settings/public` añade `hero.mobile_image_url: string | null`. Las URL públicas de archivos son `/media/...`.

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

Lee solo: `SKU`, `Nombre`, `Departamento`, `Marca`, `Color`, `Talla`, y de `Descripcion` únicamente las referencias que coincidan con `Foto( mujer)? N(+N)*`. Toda otra columna se ignora sin cargarla: precios, costos, stock, IVA, código de barras y el resto del texto de `Descripcion`, que contiene precios históricos.

- **Agrupación:** cada fila es una variante (`product_variants`: `sku` único, `color`, `size`, `product_id`). El SKU base es el SKU sin el sufijo final igual a `-{Talla}`; filas con el mismo SKU base y marca forman un producto. Sin talla, el SKU es su propio producto. `products.sku` = SKU base.
- **Marca:** se resuelve por `brand_aliases` sin distinguir acentos. Vacía o "Sin marca" → clasificación. Desconocida → error de fila; nunca crea marcas sola.
- **Categoría:** por nombre de `Departamento`, sin distinguir acentos. Si no existe, la preview la lista y la importación la crea como categoría raíz. No se deduce de la marca.
- **SKU existente:** la preview lo reporta como conflicto. Con `update_existing=false` se omite; con `true` actualiza nombre, marca, categoría y variantes, sin tocar estado, fotos ni campos editoriales.
- **Siempre `status=draft`, `is_demo=false`.** La importación nunca publica. Idempotente. Slug único derivado de marca y nombre, con sufijo si se repite.

```ts
type ImportPreview = {
  preview_id: string;
  rows: number; products: number; variants: number;
  new_products: number; conflicts: number;
  new_categories: string[];
  errors: { row: number; sku: string | null; message: string }[];
  sample: { sku: string; name: string; brand: string; category: string; variants: number }[];
};
type ImportResult = { import_id: string; created: number; updated: number; skipped: number; errors: number };
```
