# Task pack para Atlas ONE: canal «Tienda en línea» (catálogo para Eleven Boutique)

> Pega este documento completo en la sesión de Claude Code del repo `atlas-one`.
> Escrito el 2026-11-13 desde el proyecto `eleven_boutique`, a partir de una lectura del código de
> `atlas-one` (sin ejecutarlo). Verifica cada ruta de archivo antes de usarla.

---

## Prompt maestro

Eres el equipo de Atlas ONE. Vas a construir el **canal «Tienda en línea»**: una forma segura y
genérica de que una tienda web externa lea el catálogo de una organización y le devuelva prospectos.
El primer consumidor es **Eleven Boutique** (organización «Eleven Fashion», preset
`ATLAS_POS_BOUTIQUE`), cuyo sitio vive en `eleven.boutique` (otro repo, FastAPI + Next.js, en
Railway). Atlas ONE será la **fuente de verdad del catálogo**; la tienda guarda una copia sincronizada
y nunca escribe productos.

Antes de escribir código:
1. Usa tu flujo habitual de diseño (brainstorming → spec en `docs/superpowers/specs/` → plan).
2. Confirma con el dueño las decisiones marcadas como **[DECIDIR]**.
3. Respeta las restricciones de abajo: `main` despliega solo a producción en IONOS y ahí cobran
   otras tiendas (Kaory, Ginebra, Imaltzin, Eleven Fashion).

### Por qué

La boutique quiere un catálogo en línea **fiel a lo que tiene en venta**: cada pieza que entra a
Atlas ONE con existencias aparece en la web, y lo que se agota deja de ofrecerse, sin capturar nada
dos veces. La web **solo muestra el producto, nunca precios**; la venta se cierra por WhatsApp. Más
adelante la web mandará a Atlas ONE los prospectos que genera (clics a WhatsApp, selecciones de
piezas) para darles seguimiento y, después, atenderlos con agentes.

### Objetivos

1. **API keys de servidor a servidor funcionando**, ligadas a una organización y con scopes.
2. **API de catálogo de solo lectura** para el canal web, con sincronización incremental.
3. **Campos de catálogo que hoy faltan** para una tienda de moda: publicar en web, galería, marcas
   premium, subcategorías.
4. **Disponibilidad web** calculada desde las existencias, sin exponer cantidades ni precios.
5. *(Fase 2)* **Recepción de prospectos** desde la web hacia CRM.

### No objetivos

- Carrito, pagos, precios en línea o pedidos web.
- Agentes de IA o WhatsApp Business API (proyecto posterior).
- Código específico de Eleven: todo debe servir a cualquier organización que active el canal.
- Que la tienda escriba productos, marcas o existencias en Atlas ONE.

### Anti-objetivos (aunque funcione, sería un fracaso)

- Que la API de canal **devuelva precio, costo, IVA, proveedor o cantidades exactas** de existencias.
- Que una key de una organización pueda leer datos de otra.
- Que el tráfico de la web afecte al punto de venta (consultas pesadas sin paginar, sin índices).
- Un cambio de esquema que rompa o bloquee a los tenants que ya cobran.

---

## Lo que ya existe (leído en el código, verifícalo)

| Tema | Estado | Dónde |
|---|---|---|
| Multi-tenant | `organization_id` vía `TenantMixin`, filtros en `app/core/tenant_query.py` | `app/core/` |
| API keys | Tabla `api_key`, formato `atlas_{prefix8}_{secret32}`, SHA-256, CRUD de plataforma. `verify_api_key` **no está conectado** al flujo de auth | `app/modules/platform/api_keys.py`, `app/routers/platform/api_keys.py` |
| Productos | `Product` (UUID; name, description, `image_url` única, brand_id, department_id, gender, model, material, `is_active`, `approval_status`) | `app/modules/products/models.py` |
| Variantes | `ProductVariant` (sku único por org, barcode, color, size, price, cost…) | mismo archivo |
| Marcas | `Brand` (name, logo_url). Sin `is_premium` | mismo archivo |
| Departamentos | `Department` plano, sin padre | mismo archivo |
| Existencias | `stock_on_hand` por sucursal + variante; kardex `inventory_movements` | módulo de inventario |
| Visibilidad por sucursal | `product_branch_status` (`is_active_pos`, `is_active_hq`) | `app/modules/products/models.py` |
| Eventos | Outbox, hoy solo `SalesDocumentCreated` | `app/core/events.py` |
| Imágenes | Cloudinary | `app/utils/image_storage.py` |
| Migraciones | `ALTER` idempotentes, sin Alembic | `scripts/railway_init.py` |
| Deploy | push a `main` → CI → IONOS (`app.atlasone.com.mx`) | `.github/workflows/ci.yml`, `docs/infra/` |

---

## Tareas

### T1. API keys conectadas al auth (bloqueante para todo lo demás)

- Dependencia FastAPI `require_api_key(scope)` que lea `Authorization: Bearer atlas_…` (o
  `X-Api-Key`), use `verify_api_key`, rechace keys revocadas y fije el contexto de tenant con el
  `organization_id` de la key (si la tabla `api_key` no lo tiene, agrégalo de forma idempotente).
- Scopes mínimos: `catalog:read` y `leads:write`. Una key sin el scope → 403.
- La key nunca autentica rutas de usuario; un JWT de usuario nunca autentica las rutas de canal.
- Rate limit por key, aunque sea básico (p. ej. 120 req/min) y respuesta 429.
- UI o comando de plataforma para emitir, listar (solo prefijo) y revocar keys por organización.
  La key completa se muestra **una sola vez**.
- Tests: key válida, revocada, de otra org, sin scope, ausente.

### T2. Campos de catálogo para el canal web (aditivo, con defaults seguros)

Todos con `ALTER … ADD COLUMN IF NOT EXISTS` en `scripts/railway_init.py`, con default que **no
cambie el comportamiento actual** de ningún tenant:

- `products.web_published BOOLEAN NOT NULL DEFAULT false`: el dueño decide qué sale en la web.
- `products.web_published_at TIMESTAMPTZ NULL`.
- Galería: tabla nueva `product_images` (id, organization_id, product_id, url, alt, position,
  is_primary, created_at, updated_at, deleted_at). Migración: copiar `products.image_url` como
  imagen primaria. `image_url` se conserva y se mantiene sincronizada con la primaria para no romper
  el POS.
- `brands.is_premium BOOLEAN NOT NULL DEFAULT false`: en Eleven, las casas premium se atienden en
  otra línea de WhatsApp.
- `departments.parent_id UUID NULL` (FK a `departments`, misma org, máximo 2 niveles): permite
  «Ropa → Camisas».
- `updated_at` confiable (con índice) en products, product_variants, product_images, brands y
  departments. Si `AuditMixin` ya lo da, asegúrate de que **todo** cambio lo actualice, incluidas
  las ediciones masivas e importaciones.
- UI de producto: casilla «Publicar en tienda en línea», galería ordenable (Cloudinary). UI de marca:
  «Marca premium». UI de departamentos: elegir departamento padre.
- Activar el canal por organización como **módulo** (como los demás módulos por org). Si el módulo
  está apagado, la UI no muestra estos controles y la API de canal responde 404 o 403.

### T3. Disponibilidad web (sin cantidades)

- Configuración por organización: **qué sucursales cuentan para la web** (default: todas las activas).
- Por variante: `available = existencias > 0` en esas sucursales (y variante no borrada, producto
  activo y aprobado).
- Por producto: `available = alguna variante disponible`.
- Cambios de existencias (venta, compra, traspaso, ajuste, conteo) deben hacer visible el cambio a la
  sincronización. Opción recomendada: tabla `channel_availability(organization_id, variant_id,
  available, changed_at)` actualizada **solo cuando cambia el booleano**, con índice por
  `(organization_id, changed_at)`. Así el POS no paga el costo en cada venta, y la web pregunta «qué
  cambió desde X».
- **[DECIDIR]** Si se publica alguna señal de «pocas piezas». Recomendación: no; solo booleano.

### T4. API de catálogo para el canal (solo lectura, scope `catalog:read`)

Prefijo sugerido: `/api/channel/v1`. Todas paginadas por cursor (`?cursor=&limit=`, máx. 200),
ordenadas por `(updated_at, id)` y con `?updated_since=<ISO8601>` para sincronizar por partes.
Respuesta: `{ "items": [...], "next_cursor": "..." | null, "server_time": "<ISO8601>" }`. La web
guarda `server_time` como siguiente `updated_since`.

```
GET /api/channel/v1/brands
  { id, name, logo_url, is_premium, updated_at, deleted: bool }

GET /api/channel/v1/departments
  { id, name, parent_id, position?, updated_at, deleted: bool }

GET /api/channel/v1/products
  Solo productos de la org con web_published = true (los despublicados/borrados salen como
  { id, deleted: true, updated_at } para que la web los retire).
  {
    id, name, description, brand_id, department_id,
    gender, model, material,
    available: bool,
    images: [{ url, alt, position, is_primary }],
    variants: [{ id, sku, color, size, available: bool, updated_at }],
    updated_at, web_published_at, deleted: false
  }

GET /api/channel/v1/products/{id}            mismo shape
GET /api/channel/v1/availability?updated_since=
  [{ product_id, variant_id, available, changed_at }]   ligero, para consultar cada pocos minutos
```

Reglas:
- **Lista blanca de campos**: los schemas de respuesta del canal son propios (`extra="forbid"`); nunca
  reutilices los schemas internos que traen precio, costo, IVA o proveedor. Test que lo verifique.
- `updated_at` del producto también sube cuando cambian su galería, variantes, marca o departamento.
- Índices para que estas consultas no hagan escaneos completos.
- Sin CORS abierto para estas rutas: las consume un servidor, no un navegador.
- Documentar en `docs/API_REFERENCE.md` con ejemplos.

### T5. Eventos (opcional en fase 1, recomendado)

- Agregar al outbox `CatalogProductChanged` y `CatalogAvailabilityChanged` (con org, ids y
  `changed_at`).
- Webhook saliente por organización (URL + secreto HMAC-SHA256 en `X-Atlas-Signature`, reintentos con
  backoff). El cuerpo solo trae ids; la web vuelve a leer por la API. Si no da tiempo, la web
  funciona con sondeo de `availability` cada 2 a 5 minutos.

### T6 (fase 2). Prospectos desde la web (scope `leads:write`)

```
POST /api/channel/v1/leads
  {
    source: "web_whatsapp_click" | "web_selection" | "web_form",
    product_ids: [uuid],              // piezas de interés
    line: "general" | "boutique",
    name?: string, phone?: string, email?: string,
    utm?: { source, medium, campaign }, occurred_at
  }
  → 201 { lead_id }
```

- Modelo nuevo de prospecto (o extensión de `customers`) con `source`, `status` (nuevo, contactado,
  ganado, perdido), `owner_user_id`, piezas de interés y fecha. Si llega un teléfono que ya es
  cliente, ligarlo a ese cliente en vez de duplicar.
- Vista en Atlas ONE «Prospectos web» por organización.
- Idempotencia con header `Idempotency-Key`.
- **[DECIDIR]** Si el clic a WhatsApp anónimo (sin teléfono) cuenta como prospecto o solo como métrica.

---

## Restricciones

- **Producción compartida.** Cada push a `main` se despliega a IONOS con todos los tenants. Trabaja
  en rama, con PR y CI en verde. Todo cambio de esquema es aditivo e idempotente; nada de renombrar
  ni borrar columnas.
- **Aislamiento de tenant** en cada consulta nueva (usa `tenant_query`). Tests con dos organizaciones.
- **Nada de precios ni costos** en el canal, ni siquiera en campos opcionales.
- **Rendimiento:** la web hace una carga inicial completa y luego solo pide cambios. Ninguna ruta de
  canal debe cargar el POS: paginación obligatoria e índices por `(organization_id, updated_at)`.
- **Imágenes:** URLs públicas de Cloudinary; la web las descarga o las enlaza. Nada de URLs firmadas
  que caduquen.
- **Sin datos personales en la API de catálogo.**

## Criterios de aceptación

1. Con una key `catalog:read` de la org de Eleven, `GET /api/channel/v1/products` devuelve solo los
   productos publicados de esa org, con galería, variantes y `available`, y **ningún** campo de
   precio, costo o cantidad (test automático de lista blanca).
2. Con la key de otra org no se ve nada de Eleven. Sin key: 401. Sin scope: 403. Revocada: 401.
3. Vender la última pieza en el POS hace que `/availability?updated_since=` la reporte como
   `available: false` en la siguiente consulta.
4. Despublicar un producto lo hace aparecer como `{deleted: true}` en la siguiente sincronización.
5. Marcas con `is_premium` y departamentos con `parent_id` salen en sus endpoints.
6. Ningún tenant existente nota cambios: los defaults dejan todo igual y la suite de pruebas pasa.
7. Documentación de la API de canal con ejemplos de request y respuesta.

## Decisiones abiertas para el dueño [DECIDIR]

1. **Unidad de publicación:** propuesta = 1 producto de Atlas = 1 ficha en la web; sus variantes
   (talla/color) se muestran como tallas disponibles. Si Eleven maneja piezas únicas, cada producto
   tendría una sola variante.
2. **Qué SKU usa la web como «Referencia»** en el mensaje de WhatsApp: propuesta = `model` del
   producto si existe; si no, el SKU de la primera variante.
3. **Sucursales que cuentan** para la disponibilidad web.
4. **Nombre y dominio oficiales:** en Atlas aparece «Eleven Fashion» / `elevenboutique.mx`; el sitio
   usa «Eleven Boutique» / `eleven.boutique`.
5. Si se publica alguna señal de «pocas piezas».
6. Si el clic anónimo a WhatsApp crea prospecto.

## Qué hará el lado de Eleven Boutique (para que sepas quién consume)

- Un job en el backend de Eleven sincroniza el catálogo con la key `catalog:read`: carga inicial
  completa y luego `updated_since`, y `availability` cada pocos minutos. Guarda `atlas_id` como
  identificador externo y genera sus propios slugs.
- La parte editorial (portada, lookbooks, colecciones, marcas destacadas, textos SEO) sigue en el
  panel de Eleven.
- Eleven decide cómo mostrar una pieza agotada (ocultarla o «consulta disponibilidad»); Atlas solo
  entrega el booleano.
- En fase 2, Eleven envía los clics a WhatsApp y las selecciones a `/leads`.

## Entrega esperada

1. Spec y plan en `docs/superpowers/specs/` y `docs/superpowers/plans/`.
2. PR(s) en orden: T1 → T2 → T3 → T4 (→ T5) y T6 por separado.
3. Una key `catalog:read` de la org de Eleven, entregada al dueño por un canal seguro. **Nunca en el
   repo ni en el chat.**
4. La URL base de producción de la API de canal y un ejemplo real de respuesta, sin datos sensibles.
