# Tienda nueva — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La portada premium que se vuelve tienda (departamentos con piezas, recién llegado, franja de detalle, bloque de atención con WhatsApp e Instagram) y el área de catálogo `/tienda`, con todas las rutas de pieza y marca bajo ella.

**Architecture:** El backend agrega campos aditivos (foto de portada por departamento, franja de detalle, bloque de atención, Instagram) con una migración Alembic, los expone en la API pública y suma un endpoint de marcas por filtro. El frontend mueve el catálogo a `app/tienda/**` con redirecciones 301 desde las rutas viejas, y la portada sustituye `CategoryRail` y la cuadrícula de Novedades por componentes nuevos. El panel gana los campos para cargar todo.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, pytest (backend, `uv run pytest`) · Next.js 16 App Router, React 19, Tailwind 4, vitest (frontend, `npm run lint`, `npm run typecheck`, `npx vitest run`).

**Spec:** `docs/superpowers/specs/2026-11-14-tienda-nueva-design.md`

## Global Constraints

- Nunca precios, carrito ni existencias exactas en nada público.
- Estilo actual intacto: `docs/design-system.md`, blanco y negro (`.mono`), clases `label`, `display`, `cta`, `btn`, `page`, `section`, `inverse`.
- Teléfono primero: sin desplazamiento horizontal de página, objetivos táctiles ≥ 44 px (`min-h-11`).
- Solo la primera foto de portada se precarga; todo lo demás, diferido. Fotos con versión de teléfono usan `HeroPicture` (`frontend/components/HeroPicture.tsx`).
- Cada sección de portada se oculta sola sin datos; ninguna se ve vacía o rota con 0 piezas publicadas.
- Instagram por defecto: `https://www.instagram.com/eleven.fashionboutique/`.
- Texto por defecto del bloque de atención: titular «Escríbenos. Te asesoramos.»; mensaje de WhatsApp general «Hola, me gustaría recibir atención personalizada de Eleven Boutique.»
- Enlace secundario de línea Boutique: «Línea Boutique (casas premium)», solo si su número es distinto del general.
- El número de WhatsApp nunca se expone fuera de un enlace `wa.me` armado por la API.
- Cambios de base de datos aditivos, en Alembic (`backend/alembic/versions/0005_tienda.py`).
- Rutas de tienda: `/tienda`, `/tienda/[departamento]`, `/tienda/[departamento]/[subcategoría]`, `/tienda/marcas`, `/tienda/marcas/[marca]`, `/tienda/marcas/[marca]/[pieza]`, `/tienda/piezas/[pieza]`. Los slugs `marcas` y `piezas` quedan reservados para departamentos.
- Orden «recientes» usa el parámetro existente: `?sort=recent`.
- Claude no hace `git push`; el dueño corre `! git push origin main`.

## Review Focus

1. Enlaces viejos ya compartidos (`/marcas/x/y`, `/piezas/x`, `/categorias/ropa?category=camisas`, `/novedades`) → deben llegar con 301 a la página nueva equivalente, conservando subcategoría y orden. Prueba en Task 5.
2. Producción con 0 piezas → portada sin pestañas vacías ni carrusel vacío; los departamentos con foto se muestran como fichas que llevan a `/tienda/[departamento]`. Prueba en Task 7 (`departmentPanels`).
3. Slug de marca antiguo (marca renombrada) → la ficha y la marca nuevas bajo `/tienda/marcas` siguen redirigiendo al slug vigente, como hoy. Prueba en Task 5 (navegador).
4. Sin WhatsApp configurado o sin Instagram → el bloque de atención muestra solo lo que existe; sin ninguno, se oculta. Prueba en Task 8 (`attentionLinks`).
5. Mensajes de WhatsApp ya generados tras el cambio → el enlace dentro del mensaje apunta a `/tienda/...` y abre la pieza. Prueba en Task 4.

---

### Task 1: Modelo y migración

**Files:**
- Create: `backend/alembic/versions/0005_tienda.py`
- Modify: `backend/app/models/catalog.py` (clase `Category`), `backend/app/models/content.py` (clase `SiteSettings`), `backend/app/services/admin/media.py` (`_URL_COLUMNS`)
- Test: `backend/tests/test_migrations.py`, `backend/tests/test_admin_media.py`

**Interfaces:**
- Produces (columnas):
  - `categories.cover_asset_id` (FK `media_assets.id`, `ondelete="RESTRICT"`, index), `categories.cover_url` (String 500).
  - `site_settings`: `instagram_url` (String 500); `detail_asset_id`, `detail_image_url`, `detail_mobile_asset_id`, `detail_mobile_image_url`, `detail_caption` (Text); `attention_asset_id`, `attention_image_url`, `attention_mobile_asset_id`, `attention_mobile_image_url`, `attention_headline` (Text), `attention_subhead` (Text). FKs de asset igual que `hero_asset_id`.
- La migración, en `upgrade()`, hace `UPDATE site_settings SET instagram_url = 'https://www.instagram.com/eleven.fashionboutique/' WHERE instagram_url IS NULL`.

- [ ] **Step 1: Pruebas que fallan.** En `test_migrations.py` agrega a `ASSET_FK_COLUMNS` y `NEW_COLUMNS`: `"categories": {"cover_asset_id"}` y, en `site_settings`, los cuatro `*_asset_id` nuevos (más las columnas no-FK en `NEW_COLUMNS`). Agrega `test_instagram_default_is_backfilled`: inserta una fila de `site_settings` con revisión `0004`, sube a `head` y comprueba `instagram_url == "https://www.instagram.com/eleven.fashionboutique/"`. En `test_admin_media.py` agrega `"category_cover"`, `"detail"`, `"attention"` al `parametrize` de uso (patrón de `"hero"`), usando los PATCH de Task 2.
- [ ] **Step 2:** `cd backend && uv run pytest tests/test_migrations.py -q` → FAIL.
- [ ] **Step 3:** Agrega las columnas a los modelos y escribe `0005_tienda.py` (`down_revision = "0004"`, `add_column` con FK inline como en migraciones previas; `downgrade` borra en orden inverso). Agrega las cinco columnas de URL nuevas a `_URL_COLUMNS`.
- [ ] **Step 4:** `uv run pytest tests/test_migrations.py -q` → PASS (las de media pasan tras Task 2).
- [ ] **Step 5:** Commit `Tienda: columnas para portada de departamento, detalle, atención e Instagram`.

### Task 2: Panel (API admin) para los campos nuevos

**Files:**
- Modify: `backend/app/schemas/admin.py` (`CategoryPatch`, `CategoryCreate`, `AdminCategory`, `SettingsPatch`, `AdminSettings`), `backend/app/services/admin/taxonomy.py` (`_category_out`, `create_category`, `update_category`), `backend/app/services/admin/content.py` (`_AUDITED_SETTINGS`, `_TEXT_SETTINGS`, `_settings_out`, `update_settings`)
- Test: `backend/tests/test_admin_catalog.py`

**Interfaces:**
- Consumes: columnas de Task 1; `set_asset`, `asset_or_error` (`services/admin/common.py`).
- Produces:
  - `CategoryPatch.cover_asset_id: uuid.UUID | None`; `AdminCategory.cover_asset_id: uuid.UUID | None`, `cover_url: str | None`. Solo categorías principales: si la categoría tiene `parent_id`, enviar `cover_asset_id` no nulo → 422 `invalid_reference` con mensaje «Solo los departamentos principales llevan foto de portada».
  - `SettingsPatch`: `instagram_url` (https, máx. 500; se valida que el host sea `instagram.com` o `www.instagram.com`, si no 422 `invalid_instagram_url`), `detail_asset_id`, `detail_mobile_asset_id`, `detail_caption` (ShortText), `attention_asset_id`, `attention_mobile_asset_id`, `attention_headline`, `attention_subhead` (LongText). `AdminSettings` devuelve cada `*_asset_id` con su `*_image_url` y los textos.
  - Todos los campos nuevos entran en `_AUDITED_SETTINGS`.

- [ ] **Step 1: Pruebas que fallan.**
  - `test_category_cover_round_trip_only_on_top_level`: PATCH `cover_asset_id` en una principal → 200 y `cover_url == item["url"]`. En una subcategoría → 422. Con `None` → se limpia.
  - `test_settings_detail_attention_and_instagram_round_trip`: PATCH de todos los campos nuevos → GET igual.
  - `test_settings_rejects_non_instagram_url`: `"https://evil.example/x"` → 422 `invalid_instagram_url`. `""` → `instagram_url` queda `None`.
- [ ] **Step 2:** `uv run pytest tests/test_admin_catalog.py -q -k "cover or detail or instagram"` → FAIL.
- [ ] **Step 3:** Implementa siguiendo el patrón de `hero_asset_id` / `hero_mobile_asset_id`.
- [ ] **Step 4:** `uv run pytest -q` → todo PASS (incluidas las de media de Task 1).
- [ ] **Step 5:** Actualiza `docs/admin-api-contract.md` (fila `/settings` y `/categories`). Commit `Panel: foto de departamento, franja de detalle, bloque de atención e Instagram`.

### Task 3: API pública: portadas, atención, detalle y marcas por filtro

**Files:**
- Modify: `backend/app/schemas/public.py`, `backend/app/services/catalog.py` (`list_categories`, `public_settings`), `backend/app/services/whatsapp.py`, `backend/app/api/v1/routes.py`
- Test: `backend/tests/test_public_settings_tienda.py` (nuevo), `backend/tests/test_contract_shapes.py`, `backend/tests/test_demo.py`

**Interfaces:**
- Produces (contrato público):
  - `Category.cover_url: str | None`.
  - `PublicSettings.instagram_url: str | None`.
  - `PublicSettings.detail: { image_url: str | None, mobile_image_url: str | None, caption: str | None }`.
  - `PublicSettings.attention: { headline: str, subhead: str | None, image_url: str | None, mobile_image_url: str | None, whatsapp_url: str | None, boutique_whatsapp_url: str | None }`. `headline` por defecto «Escríbenos. Te asesoramos.». `boutique_whatsapp_url` solo si los dígitos premium existen y difieren de los generales.
  - `whatsapp.build_general_url(digits: str) -> str`: `wa.me` con el mensaje general exacto de Global Constraints.
  - `GET /api/v1/brand-facets?category=<slug opcional>` → `Items[BrandFacet]`, con `BrandFacet = { slug, name, product_count }`. Solo marcas visibles (no clasificación «Sin marca») con piezas visibles en esa categoría y sus hijas, ordenadas por nombre.

- [ ] **Step 1: Pruebas que fallan** en `test_public_settings_tienda.py`:
  - `test_attention_defaults_and_links`: con número general → `attention.headline == "Escríbenos. Te asesoramos."`, el mensaje de `whatsapp_url` es exactamente el de Global Constraints, `boutique_whatsapp_url is None`. Con línea premium distinta → `boutique_whatsapp_url` empieza con `https://wa.me/525599990000?`. Sin números → ambos `None`.
  - `test_attention_never_exposes_the_number_outside_links`: el número no aparece en el cuerpo fuera de las URL `wa.me`.
  - `test_category_cover_url_is_public`.
  - `test_brand_facets_follow_category_and_children`: marcas A (pieza en `camisas`, hija de `ropa`) y B (pieza en `calzado`) → `?category=ropa` devuelve solo A con `product_count == 1`; sin filtro, A y B; las piezas borrador no cuentan; la clasificación «Sin marca» no aparece.
  - Actualiza las formas esperadas en `test_contract_shapes.py` y `test_demo.py` con `instagram_url`, `detail`, `attention` y `cover_url`.
- [ ] **Step 2:** `uv run pytest tests/test_public_settings_tienda.py -q` → FAIL.
- [ ] **Step 3:** Implementa. `attention` y `detail` usan `pick()` como el resto (real gana sobre demo).
- [ ] **Step 4:** `uv run pytest -q` → PASS.
- [ ] **Step 5:** Actualiza `docs/api-contract.md`. Commit `API pública: atención, detalle, Instagram, portadas de departamento y marcas por filtro`.

### Task 4: Enlaces de WhatsApp bajo `/tienda`

**Files:**
- Modify: `backend/app/services/whatsapp.py` (`Piece.link`)
- Test: `backend/tests/test_whatsapp.py`, `backend/tests/test_selection.py`, `docs/api-contract.md`

**Interfaces:**
- Produces: `Piece.link(site_url)` → `{base}/tienda/marcas/{brand_slug}/{slug}` o `{base}/tienda/piezas/{slug}`.

- [ ] **Step 1:** Cambia las URL esperadas en `test_whatsapp.py` (incluida la cadena codificada de `test_exact_template_and_encoding`: `%2Ftienda%2Fmarcas%2Fdolce-gabbana%2Fcamisa`) y en `test_selection.py`.
- [ ] **Step 2:** `uv run pytest tests/test_whatsapp.py tests/test_selection.py -q` → FAIL.
- [ ] **Step 3:** Cambia `Piece.link`.
- [ ] **Step 4:** `uv run pytest -q` → PASS. Actualiza la línea `{url}` en `docs/api-contract.md` (sección WhatsApp).
- [ ] **Step 5:** Commit `WhatsApp: enlaces de pieza bajo /tienda`.

### Task 5: Rutas del frontend bajo `/tienda` y redirecciones

**Files:**
- Move (git mv): `frontend/app/marcas/page.tsx` → `frontend/app/tienda/marcas/page.tsx`; `frontend/app/marcas/[slug]/page.tsx` → `frontend/app/tienda/marcas/[slug]/page.tsx`; `frontend/app/marcas/[slug]/[producto]/page.tsx` → `frontend/app/tienda/marcas/[slug]/[producto]/page.tsx`; `frontend/app/piezas/[slug]/page.tsx` → `frontend/app/tienda/piezas/[slug]/page.tsx`
- Delete: `frontend/app/categorias/[slug]/page.tsx`, `frontend/app/novedades/page.tsx` (los sustituyen las páginas de Task 6 y las redirecciones)
- Modify: `frontend/lib/url.ts`, `frontend/lib/categories.ts` (`categoryHref`, `categoryTiles`), `frontend/next.config.ts` (`redirects()`), `frontend/app/sitemap.ts`, `frontend/components/nav.ts`, `frontend/components/Header.tsx`, cualquier `href="/marcas"`, `"/novedades"` o `"/piezas"` escrito a mano (`rg -n '"/(marcas|novedades|piezas|categorias)' frontend/app frontend/components frontend/lib`)
- Test: `frontend/lib/url.test.ts`, `frontend/lib/categories.test.ts`, `frontend/lib/redirects.test.ts` (nuevo)

**Interfaces:**
- Produces:
  - `productHref(p)` → `/tienda/marcas/{brand}/{slug}` o `/tienda/piezas/{slug}`.
  - `brandHref(slug)` → `/tienda/marcas/{slug}`.
  - `categoryHref(slug)` → `/tienda/{slug}`.
  - `departmentHref(department: string, sub?: string): string` en `lib/url.ts` → `/tienda/{dep}` o `/tienda/{dep}/{sub}`.
  - `SHOP_PATH = "/tienda"`.
  - `LEGACY_REDIRECTS: { source: string; destination: string; permanent: true }[]` exportado desde `frontend/lib/redirects.ts` y usado en `next.config.ts`:
    - `/marcas` → `/tienda/marcas`; `/marcas/:slug` → `/tienda/marcas/:slug`; `/marcas/:slug/:producto` → `/tienda/marcas/:slug/:producto`; `/piezas/:slug` → `/tienda/piezas/:slug`.
    - `/novedades` → `/tienda?sort=recent`.
    - `/categorias/:slug` con query `category` → `/tienda/:slug/:category`; sin ella → `/tienda/:slug` (usa `has: [{ type: "query", key: "category", value: "(?<category>.*)" }]`, en ese orden). El resto de la query (`sort`) se conserva solo.
- La página de marca y la ficha conservan la lógica actual de redirección por slug viejo, ahora hacia `/tienda/marcas/...`.

- [ ] **Step 1: Pruebas que fallan.** `url.test.ts`: las nuevas formas de `productHref`, `brandHref` y `departmentHref("ropa","camisas") === "/tienda/ropa/camisas"`, con codificación de caracteres especiales. `redirects.test.ts`: cada `source` del listado de arriba tiene su `destination` exacto, todas `permanent: true`, y la regla de `/categorias/:slug` con `has category` va antes que la de sin query.
- [ ] **Step 2:** `npx vitest run lib/url.test.ts lib/redirects.test.ts` → FAIL.
- [ ] **Step 3:** Implementa helpers y redirecciones, mueve las páginas y corrige imports y enlaces. En el menú lateral, «Tienda» (`/tienda`) es la primera entrada, encima de Novedades, Categorías y Casas; Novedades apunta a `/tienda?sort=recent`. En el encabezado, enlace «Tienda» a la derecha, antes de Selección/Buscar (en teléfono, solo texto `label`, sin ícono). El sitemap usa `/tienda` y `/tienda/marcas` en lugar de `/marcas` y `/novedades`, más `/tienda/{dep}` por cada departamento con piezas.
- [ ] **Step 4:** `npx vitest run && npm run lint && npm run typecheck` → PASS. Verificación en navegador (dev local): `curl -sI localhost:3000/marcas/acne-studios/pieza-demostracion-01` → `308` con `location: /tienda/marcas/acne-studios/pieza-demostracion-01` (Next usa 308 para `permanent`); `/categorias/ropa?category=camisas&sort=name` → `/tienda/ropa/camisas?sort=name`; slug de marca viejo → redirige a la marca vigente bajo `/tienda/marcas`.
- [ ] **Step 5:** Commit `Tienda: rutas de marcas y piezas bajo /tienda con redirecciones permanentes`.

### Task 6: Listados `/tienda` con filtro por marca

**Files:**
- Create: `frontend/app/tienda/page.tsx`, `frontend/app/tienda/[departamento]/[[...sub]]/page.tsx`, `frontend/components/DepartmentChips.tsx`
- Modify: `frontend/components/CatalogBar.tsx` (prop `brands`), `frontend/lib/categories.ts` (`brandOptions`), `frontend/lib/api.ts` (`getBrandFacets`)
- Test: `frontend/lib/categories.test.ts`

**Interfaces:**
- Consumes: `GET /brand-facets` (Task 3), `departmentHref` y `SHOP_PATH` (Task 5).
- Produces:
  - `getBrandFacets(category?: string): Promise<{ slug: string; name: string; product_count: number }[]>`.
  - `brandOptions(path: string, facets: { slug: string; name: string }[], current: string | undefined, sort: ProductSort | undefined): CatalogOption[]`: «Todas las marcas» y una opción por marca, con `?brand=` y conservando `sort`.
  - `CatalogBar` gana `brands?: CatalogOption[]`. El botón «Filtros» abre una hoja con dos grupos, «Subcategoría» y «Marca». Si hay marca activa, se muestra su nombre junto a «Filtros».
  - Las páginas leen `?brand=` y `?sort=`. La subcategoría va en la ruta. Una marca que no está en las facetas se ignora y no da 404. Un departamento o subcategoría inexistente da `notFound()`. `[[...sub]]` con más de un segmento → `notFound()`.
- `/tienda`: encabezado `PageHeader` con título «Tienda» y los chips de departamentos con piezas (`DepartmentChips`, enlaces a `departmentHref`). Debajo, la cuadrícula (`ProductGrid`), `Pagination` y `CatalogBar` (marcas sin `category`).
- `/tienda/[departamento]`: si el departamento tiene `cover_url`, el encabezado lleva esa foto (4:5 en teléfono, en columna en computadora) dentro de `.mono`. Los chips son de subcategorías, más «Todo [departamento]».
- Metadatos con `pageMeta`; `path` canónico sin `brand`, `sort` ni `page`.

- [ ] **Step 1:** Pruebas de `brandOptions` en `categories.test.ts`: la primera opción es «Todas las marcas» con `current` cuando no hay marca; se conserva `sort`; los `href` van a `path?brand=x&sort=y`.
- [ ] **Step 2:** `npx vitest run lib/categories.test.ts` → FAIL.
- [ ] **Step 3:** Implementa las páginas y los componentes, reutilizando el armado de la vieja página de categoría.
- [ ] **Step 4:** `npx vitest run && npm run lint && npm run typecheck` → PASS. En navegador, a 390 × 844 y 1440 × 900, con `DEMO_MODE=true`: `/tienda`, `/tienda/ropa`, `/tienda/ropa/camisas?brand=<una marca demo>`. Filtrar por marca reduce la cuadrícula; los chips no desbordan la página.
- [ ] **Step 5:** Commit `Tienda: catálogo completo con departamentos, subcategorías y filtro por marca`.

### Task 7: Portada: departamentos con piezas y recién llegado

**Files:**
- Create: `frontend/components/DepartmentTabs.tsx`, `frontend/components/NewArrivals.tsx`
- Modify: `frontend/app/page.tsx`, `frontend/lib/home.ts`
- Delete: `frontend/components/CategoryRail.tsx`, y `categoryTiles` en `lib/categories.ts` si queda sin uso (con su prueba)
- Test: `frontend/lib/home.test.ts`

**Interfaces:**
- Consumes: `Category.cover_url` (Task 3), `departmentHref` (Task 5).
- Produces:
  - `type DepartmentPanel = { slug: string; name: string; href: string; cover: string | null; products: ProductCard[]; total: number }`.
  - `departmentPanels(categories: Category[], samples: { category: Category; items: ProductCard[]; total: number }[]): DepartmentPanel[]`: departamentos principales en orden de catálogo. Incluye uno si tiene piezas o `cover_url`; descarta los que no tienen ninguna de las dos. `cover` pasa por `safeImageSrc`.
  - `DepartmentTabs({ panels }: { panels: DepartmentPanel[] })`, componente cliente:
    - Si algún panel tiene piezas: patrón ARIA de pestañas (`role="tablist"`, flechas izquierda/derecha, Inicio/Fin, `aria-selected`, `aria-controls`). Cada panel muestra la portada 4:5 (si existe) como primera ficha grande, luego hasta 8 `ProductCard`, y «Ver todo {nombre} →» a `href`.
    - Si ningún panel tiene piezas: fila de fichas 4:5 con la portada y el nombre, que llevan a `href`, sin pestañas.
    - En teléfono, pestañas y fichas se deslizan de lado (`overflow-x-auto`, `snap-x`).
  - `NewArrivals({ products }: { products: ProductCard[] })`: carrusel de hasta 12 piezas, con flechas en computadora (mismo mecanismo de `scrollBy` que tenía `CategoryRail`) y deslizamiento en teléfono. «Ver todas →» lleva a `/tienda?sort=recent`. Sin piezas, `null`.
- `page.tsx`:
  - `categorySamples` pide `page_size: 8` por departamento principal y también incluye los que tienen `cover_url` aunque no tengan piezas.
  - `getNovedades({ page_size: 12 })`.
  - En la tarjeta del titular, la acción principal es «Entrar a la tienda» (`/tienda`, clase `cta`) y «Explorar marcas» (`/tienda/marcas`) va como segundo enlace, más discreto (`muted`).
  - Orden de secciones: portada, `DepartmentTabs`, `NewArrivals`, franja de detalle (Task 8), historias, colecciones, presentación, casas destacadas, muro de marcas, «La boutique», bloque de atención (Task 8).

- [ ] **Step 1:** Pruebas de `departmentPanels` en `home.test.ts`:
  - el orden respeta las categorías;
  - una subcategoría nunca es panel;
  - un departamento sin piezas pero con portada se incluye con `products: []`;
  - uno sin piezas ni portada se excluye;
  - una `cover_url` inválida (`"javascript:x"`) queda en `null`.
- [ ] **Step 2:** `npx vitest run lib/home.test.ts` → FAIL.
- [ ] **Step 3:** Implementa los componentes y recompón `page.tsx`.
- [ ] **Step 4:** `npx vitest run && npm run lint && npm run typecheck` → PASS. En navegador, a 390 × 844 y 1440 × 900:
  - con demo, las pestañas cambian con clic y con flechas del teclado, y el carrusel se desliza;
  - con la base local sin piezas (`DEMO_MODE=false`) y una portada de departamento cargada, aparecen fichas sin pestañas y sin secciones vacías;
  - sin errores en consola.
- [ ] **Step 5:** Commit `Portada: departamentos con piezas y recién llegado`.

### Task 8: Portada: franja de detalle, bloque de atención e Instagram

**Files:**
- Create: `frontend/components/DetailBand.tsx`, `frontend/components/AttentionBlock.tsx`, `frontend/components/InstagramLink.tsx`
- Modify: `frontend/lib/types.ts`, `frontend/lib/home.ts`, `frontend/app/page.tsx`, `frontend/components/Footer.tsx`, `frontend/components/Header.tsx` (menú lateral), `frontend/app/layout.tsx` (pasa `instagram_url` a Header y Footer)
- Test: `frontend/lib/home.test.ts`

**Interfaces:**
- Consumes: `PublicSettings.detail`, `.attention`, `.instagram_url` (Task 3); `HeroPicture` y `HeroPhoto` (existentes).
- Produces:
  - Tipos en `lib/types.ts`, espejo exacto del contrato de Task 3. Opcionales en `PublicSettings`, porque una API anterior no los envía.
  - `attentionLinks(settings: PublicSettings): { whatsapp: string | null; boutique: string | null; instagram: string | null }`: solo `https://wa.me/` para WhatsApp y solo `https://(www.)instagram.com/` para Instagram; cualquier otra cosa → `null`.
  - `DetailBand({ detail })`: foto a todo lo ancho. En computadora 21:9 (`aspect-[21/9]`); en teléfono 4:5 con recorte central, o su versión de teléfono vía `HeroPicture`. `caption` opcional en `label`. Dentro de `.mono`. Sin `image_url`, `null`.
  - `AttentionBlock({ attention, instagram })`: sección `inverse`; foto de fondo con `HeroPicture` (16:9 en computadora, 4:5 en teléfono), un degradado para que el texto se lea, y el texto en la mitad izquierda.
    - Titular `display`, subtítulo opcional.
    - Botón principal `btn` «Escribir por WhatsApp» (`target="_blank" rel="noopener noreferrer"`).
    - Botón secundario de borde igual de alto, «Instagram», con ícono más palabra.
    - Enlace `label cta` «Línea Boutique (casas premium)» si existe.
    - Si no hay WhatsApp ni Instagram, `null`.
  - `InstagramLink({ href, className })`: ícono SVG de línea más la palabra «Instagram», `target="_blank" rel="noopener noreferrer"`. Se usa en Footer, en el menú lateral (al pie, junto a «Eleven · Fashion boutique») y en `AttentionBlock`.
- El clic en WhatsApp del bloque no registra evento de pieza: no hay `product_slug`.

- [ ] **Step 1:** Pruebas de `attentionLinks`: devuelve los tres con datos válidos; `whatsapp_url: "http://evil"` → `null`; `instagram_url: "https://evil.com/x"` → `null`; sin `attention` (API anterior) → los tres `null`.
- [ ] **Step 2:** `npx vitest run lib/home.test.ts` → FAIL.
- [ ] **Step 3:** Implementa y coloca en `page.tsx` en el orden de Task 7.
- [ ] **Step 4:** `npx vitest run && npm run lint && npm run typecheck` → PASS. En navegador, a 390 × 844 y 1440 × 900, con datos locales que tengan foto de detalle y de atención: el texto de atención se lee sobre la foto, los botones miden al menos 44 px de alto, Instagram aparece en el pie y en el menú, y `wa.me` abre en otra pestaña.
- [ ] **Step 5:** Commit `Portada: franja de detalle, bloque de atención con WhatsApp e Instagram`.

### Task 9: Panel (UI) para cargar todo

**Files:**
- Modify: `frontend/lib/admin/types.ts`, `frontend/components/admin/CategoryManager.tsx`, `frontend/components/admin/SettingsForm.tsx`
- Test: `frontend/lib/admin/rules.test.ts` (solo si se agrega una regla; si no, verificación en navegador)

**Interfaces:**
- Consumes: Task 2.
- `CategoryManager`: en cada categoría principal, un `AssetField` «Foto de portada del departamento», `ratio="4 / 5"`, hint «Vertical 4:5, ideal 1600 × 2000 px. Encabeza su pestaña en la portada y su página en la tienda.». Hace `PATCH /categories/{id}` con `{ cover_asset_id }`. No se muestra en subcategorías.
- `SettingsForm` gana tres secciones (`a-section`), después de «Imagen de portada»:
  - **Franja de detalle:**
    - `AssetField` computadora, `ratio="21 / 9"`, hint «Panorámica 21:9, ideal 2880 × 1234 px. Lo importante al centro: en teléfono se recortan los lados.».
    - `AssetField` teléfono (opcional), `ratio="4 / 5"`, hint «Opcional, vertical 4:5, ideal 1600 × 2000 px.».
    - `TextField` «Texto sobre la foto (opcional)».
  - **Bloque de atención:**
    - `AssetField` computadora, `ratio="16 / 9"`, hint «Horizontal 16:9, ideal 2880 × 1620 px. Deje tranquila la mitad izquierda: ahí van el texto y los botones.».
    - `AssetField` teléfono, `ratio="4 / 5"`, hint «Vertical 4:5, ideal 1600 × 2000 px.».
    - `TextField` «Titular» (placeholder «Escríbenos. Te asesoramos.»).
    - `TextAreaField` «Subtítulo (opcional)».
  - **Instagram:** `TextField` «Perfil de Instagram» (placeholder `https://www.instagram.com/eleven.fashionboutique/`). El error 422 `invalid_instagram_url` se muestra en el campo.
  - El cuerpo del PATCH incluye todos los campos nuevos (textos vacíos → `null`).

- [ ] **Step 1:** `npm run lint && npm run typecheck` → PASS después de editar los tipos.
- [ ] **Step 2:** Implementa.
- [ ] **Step 3:** En navegador, en el panel local:
  - cargar portada de un departamento, detalle, atención e Instagram, y ver que se guardan y aparecen en la portada;
  - quitar una foto la retira de la portada;
  - una URL de Instagram ajena muestra el error en el campo.
- [ ] **Step 4:** Commit `Panel: cargar portadas de departamento, franja de detalle, atención e Instagram`.

### Task 10: Publicación, fotos en producción y verificación

**Files:**
- Modify: `README.md` (sección «Estado al …»), `docs/design-system.md` (secciones nuevas de portada y `/tienda`)

- [ ] **Step 1:** Suites completas: `cd backend && uv run pytest -q` y `cd frontend && npm run lint && npm run typecheck && npx vitest run` → todo PASS. Actualiza README y design-system. Commit `Documenta la tienda nueva`.
- [ ] **Step 2:** Pide al dueño `! git push origin main`. Espera el despliegue de los dos servicios: `railway deployment list --service web --json` y `--service api`, hasta `SUCCESS` con el commit nuevo. La migración 0005 corre al arrancar la API.
- [ ] **Step 3:** Asigna las fotos en producción por `railway ssh --service api`, buscando `media_assets` por `filename`:

  | filename | destino |
  |---|---|
  | `ChatGPT Image Nov 14_ 2026_ 06_51_11 PM.png` (gabardina) | `categories` slug `ropa`: `cover_asset_id`/`cover_url` |
  | `… 06_52_02 PM.png` (botín) | `calzado` |
  | `… 06_52_10 PM.png` (bolso) | `bolsos` |
  | `… 06_52_27 PM.png` (cinturón) | `accesorios` |
  | `… 06_52_19 PM.png` (piel, 1913 × 822) | `site_settings` real: `detail_asset_id`/`detail_image_url` |
  | `… 06_52_33 PM.png` (boutique) | `site_settings` real: `attention_asset_id`/`attention_image_url` |

  Comprueba con `SELECT` que cada fila quedó con su URL.
- [ ] **Step 4:** Verificación en vivo con Playwright, a 390 × 844 y 1440 × 900:
  - la portada muestra las fichas de los departamentos con foto, la franja de detalle y el bloque de atención con WhatsApp e Instagram, sin errores en consola;
  - `curl -sI https://eleven.boutique/marcas` → 308 a `/tienda/marcas`;
  - `/tienda` responde 200.
- [ ] **Step 5:** Actualiza la memoria `site-state.md` con el nuevo estado.
