# Contrato de API pública — primer corte local

Base: `http://localhost:8000/api/v1`. El frontend accede por rewrite de Next (`/api/v1/*`) en cliente y por `API_URL` en servidor.

## Reglas

- Solo registros publicados. Excepción: con `DEMO_MODE=true`, también marcas `kind=brand` no publicadas y registros `is_demo=true`. Con `DEMO_MODE=false` los datos demo nunca salen.
- Jamás hay campos de precio, costo, descuento, notas internas, proveedor ni inventario.
- `kind=classification` ("Sin marca") nunca aparece como marca pública.
- Error uniforme: `{"error": {"code": "not_found", "message": "..."}}`.
- Paginado: `{"items": [...], "total": 0, "page": 1, "page_size": 24}`. Parámetros `page`, `page_size` (máx. 60).

## Formas

```ts
type Media = { url: string; alt: string; is_primary: boolean; position: number };

type BrandSummary = {
  slug: string; name: string; logo_url: string | null;
  is_featured: boolean; aliases: string[]; product_count: number;
};
type BrandDetail = BrandSummary & { description: string | null; editorial_image_url: string | null };

type Category = { slug: string; name: string; parent_slug: string | null };

type ProductCard = {
  slug: string; name: string;
  brand: { slug: string | null; name: string | null };   // null si es "Sin marca"
  category: { slug: string; name: string };
  primary_image: Media | null; secondary_image: Media | null;
};
type ProductDetail = ProductCard & {
  gallery: Media[];
  consult_url: string | null;   // wa.me listo; null si no hay número configurado
  seo_title: string | null; seo_description: string | null; published_at: string | null;
};

type CollectionSummary = { slug: string; title: string; summary: string | null; cover_url: string | null; product_count: number };
type CollectionDetail = CollectionSummary & { products: ProductCard[] };

type LookbookSummary = { slug: string; title: string; summary: string | null; cover_url: string | null };
type LookbookBlock =
  | { type: "text"; position: number; heading: string | null; body: string }
  | { type: "image"; position: number; url: string; alt: string; layout: "full" | "left" | "right" };
type LookbookDetail = LookbookSummary & { blocks: LookbookBlock[]; products: ProductCard[] };

type PublicSettings = {
  demo_mode: boolean;
  whatsapp_enabled: boolean;      // nunca se expone el número por separado
  site_name: string;
  hero: { image_url: string | null; headline: string | null; subhead: string | null; gallery: string[] };
  intro: string | null;
  boutique: { body: string | null };
  contact: { body: string | null };
};
```

## Endpoints

| Método | Ruta | Respuesta | Notas |
|---|---|---|---|
| GET | `/health` | `{status:"ok"}` | |
| GET | `/brands` | `{items: BrandSummary[]}` | Sin paginar, orden alfabético por `name`. `?featured=true`, `?q=` (nombre y alias) |
| GET | `/brands/{slug}` | `BrandDetail` | También resuelve slugs de alias (`bape` → la marca) |
| GET | `/categories` | `{items: Category[]}` | |
| GET | `/products` | paginado `ProductCard` | `?brand=`, `?category=`, `?featured=true`, `?sort=recent\|name\|display` (default `display`) |
| GET | `/products/{slug}` | `ProductDetail` | |
| GET | `/novedades` | paginado `ProductCard` | Por `commercial_added_at` desc; excluye productos sin esa fecha |
| GET | `/collections` | `{items: CollectionSummary[]}` | |
| GET | `/collections/{slug}` | `CollectionDetail` | |
| GET | `/lookbooks` | `{items: LookbookSummary[]}` | |
| GET | `/lookbooks/{slug}` | `LookbookDetail` | |
| GET | `/search` | `{brands: BrandSummary[], products: ProductCard[]}` | `?q=`; sin distinguir mayúsculas ni acentos. Marca, alias, producto, categoría |
| GET | `/site-settings/public` | `PublicSettings` | |
| POST | `/events` | `204` | `{type:"whatsapp_click", product_slug}`. Lista blanca de tipos. No guarda IP, teléfono ni user-agent |

## WhatsApp

`consult_url = https://wa.me/{digits}?text={urlencoded}` con esta plantilla exacta:

> Hola, me interesa conocer más sobre esta pieza de Eleven Boutique: {marca} — {nombre}. Referencia: {sku}. Enlace: {url}. ¿Podrían brindarme atención personalizada?

- `{url}` = `PUBLIC_SITE_URL` + `/marcas/{brand}/{slug}`.
- Número: `site_settings.whatsapp_number`, sembrado desde `WHATSAPP_NUMBER` si existe. Se normaliza a dígitos con validación E.164 (8 a 15 dígitos); si es inválido o falta, `consult_url = null`.
- Línea Boutique: las piezas de marcas con `is_premium` usan `site_settings.whatsapp_premium_number` (sembrado desde `WHATSAPP_PREMIUM_NUMBER`); si falta o es inválido, usan el número general. `whatsapp_enabled` es `true` si hay al menos una línea válida.
- Producto sin marca: la frase usa solo `{nombre}`, sin "{marca} — ". Su URL es `/piezas/{slug}`.

## Imágenes demo

El seed demo crea 12 productos (`DEMO-001`…`DEMO-012`, slug `pieza-demostracion-01`…`12`), cada uno con `/demo/pieza-NN-a.jpg` y `/demo/pieza-NN-b.jpg`. Los archivos viven en `frontend/public/demo/`, con licencia CC0 y créditos en `docs/demo-image-credits.md`. Además, `/demo/editorial-1.jpg` a `/demo/editorial-3.jpg` sirven para portada, colecciones y lookbook.
