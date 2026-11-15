"""Upsert de piezas de Atlas ONE en el catálogo de la web.

Atlas manda en nombre, ficha, casa/categoría (vía los mapas), variantes, fotos sin `media_asset_id`,
disponibilidad y estado. Nunca se tocan `is_featured`, `display_order`, `seo_*`, `internal_notes`,
`hidden_on_web`, colecciones ni lookbooks. `sku` y `slug` se fijan al crear y no cambian.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    KIND_BRAND,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    VALIDATION_PENDING,
    Brand,
    Category,
    Product,
    ProductMedia,
    ProductVariant,
)
from app.services.admin.common import unique_slug
from app.services.atlas.links import Resolver

PLACEHOLDER_BRAND = "Pendiente de ligar (Atlas ONE)"
MAX_SKU = 100
MAX_NAME = 300
MAX_MISSING = 300
MAX_URL = 500


def assign(record: Any, **values: Any) -> bool:
    """Asigna solo lo que cambia; True si algo cambió (los contadores dependen de ello)."""
    changed = False
    for field, value in values.items():
        if getattr(record, field) != value:
            setattr(record, field, value)
            changed = True
    return changed


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _variant_sku(item: dict) -> str:
    return ((item.get("sku") or "").strip() or f"ATL-{item['id'][:8]}")[:MAX_SKU]


def _with_suffix(base: str, n: int) -> str:
    suffix = f"-{n}"
    return base[: MAX_SKU - len(suffix)] + suffix


class ProductSync:
    """Aplica páginas de `/products`. Una instancia por corrida (comparte el Resolver)."""

    def __init__(self, db: Session, resolver: Resolver, counts: dict[str, int], now: datetime) -> None:
        self.db = db
        self.resolver = resolver
        self.counts = counts
        self.now = now
        self._slugs: set[str] | None = None
        self._fallback_brand: Brand | None = None
        self._fallback_category: Category | None = None

    # --- página -----------------------------------------------------------------------

    def apply_page(self, items: list[dict]) -> set[str]:
        """Devuelve los ids de Atlas de las piezas vivas de la página."""
        ids = [item["id"] for item in items]
        existing = {
            product.external_inventory_id: product
            for product in self.db.scalars(
                select(Product)
                .where(Product.external_inventory_id.in_(ids))
                .options(selectinload(Product.variants), selectinload(Product.media))
            )
        }
        live: set[str] = set()
        for item in items:
            product = existing.get(item["id"])
            if item.get("deleted"):
                if product is not None and assign(product, status=STATUS_ARCHIVED):
                    self.counts["bajas"] += 1
                continue
            live.add(item["id"])
            existing[item["id"]] = self._upsert(item, product)
        return live

    def _upsert(self, item: dict, product: Product | None) -> Product:
        created = product is None
        reasons: list[str] = []
        brand_id, slug_brand = self._brand(item, product, reasons)
        category_id = self._category(item, product, reasons)
        name = ((item.get("name") or "").strip() or (product.name if product else "")
                or (item.get("model") or "").strip() or f"Pieza {item['id'][:8]}")[:MAX_NAME]

        if product is None:
            base = f"{slug_brand.name} {name}" if slug_brand is not None else name
            if self._slugs is None:
                self._slugs = set(self.db.scalars(select(Product.slug)))
            product = Product(
                sku=self._new_sku(item),
                slug=unique_slug(base, self._slugs, fallback="pieza"),
                name=name,
                brand_id=brand_id,
                category_id=category_id,
                status=STATUS_DRAFT,
                external_inventory_id=item["id"],
                commercial_added_at=parse_time(item.get("web_published_at")),
                is_demo=False,
                photo_refs=[],
            )
            self.db.add(product)
        was = (product.status, product.atlas_missing)

        changed = assign(
            product,
            name=name,
            admin_description=item.get("description"),
            gender=item.get("gender"),
            model=item.get("model"),
            material=item.get("material"),
            brand_id=brand_id,
            category_id=category_id,
            available=bool(item.get("available", True)),
        )
        changed |= self._variants(product, item.get("variants") or [])
        changed |= self._photos(product, item.get("images") or [], name)

        status = STATUS_DRAFT if reasons else STATUS_PUBLISHED
        missing = "; ".join(reasons)[:MAX_MISSING] or None
        changed |= assign(product, status=status, atlas_missing=missing)
        if status == STATUS_PUBLISHED and product.published_at is None:
            product.published_at = parse_time(item.get("web_published_at")) or self.now
            changed = True

        if created:
            self.counts["creadas"] += 1
        elif changed:
            self.counts["actualizadas"] += 1
        if status == STATUS_DRAFT and (created or was != (status, missing)):
            self.counts["borradores"] += 1
        return product

    # --- casa y categoría -------------------------------------------------------------

    def _brand(self, item: dict, product: Product | None, reasons: list[str]):
        """(brand_id, casa para el slug o None). Sin casa usable conserva la actual o usa un respaldo."""
        atlas_brand_id = item.get("brand_id")
        brand, reason = self.resolver.brand(atlas_brand_id)
        if brand is not None:
            return brand.id, brand if brand.kind == KIND_BRAND else None
        reasons.append(reason)
        # Casa en borrador o archivada: la pieza se liga a ella para que publicarla la destrabe.
        row = self.resolver.brand_maps.get(atlas_brand_id) if atlas_brand_id else None
        mapped = self.resolver.brands.get(row.brand_id) if row and row.brand_id else None
        if mapped is not None:
            return mapped.id, mapped if mapped.kind == KIND_BRAND else None
        if product is not None:
            return product.brand_id, None
        return self._placeholder_brand().id, None

    def _category(self, item: dict, product: Product | None, reasons: list[str]):
        category, reason = self.resolver.category(item.get("department_id"))
        if category is not None:
            return category.id
        reasons.append(reason)
        if product is not None:
            return product.category_id
        return self._placeholder_category().id

    def _placeholder_brand(self) -> Brand:
        """`brand_id` es obligatorio: «Sin marca» o una casa interna en borrador (nunca pública)."""
        if self._fallback_brand is None:
            brand = self.resolver.no_brand or self.db.scalar(
                select(Brand).where(Brand.name == PLACEHOLDER_BRAND)
            )
            if brand is None:
                taken = set(self.db.scalars(select(Brand.slug)))
                brand = Brand(
                    name=PLACEHOLDER_BRAND,
                    original_name=PLACEHOLDER_BRAND,
                    slug=unique_slug(PLACEHOLDER_BRAND, taken),
                    kind=KIND_BRAND,
                    status=STATUS_DRAFT,
                    validation_status=VALIDATION_PENDING,
                )
                self.db.add(brand)
                self.db.flush()
            self._fallback_brand = brand
        return self._fallback_brand

    def _placeholder_category(self) -> Category:
        """`category_id` es obligatorio: la pieza en borrador se aparca en la primera categoría."""
        if self._fallback_category is None:
            category = self.db.scalar(select(Category).order_by(Category.display_order, Category.slug))
            if category is None:
                raise RuntimeError("No hay categorías: no se puede registrar una pieza sin categoría ligada")
            self._fallback_category = category
        return self._fallback_category

    # --- SKU --------------------------------------------------------------------------

    def _product_sku_free(self, sku: str) -> bool:
        return self.db.scalar(select(Product.id).where(Product.sku == sku)) is None

    def _new_sku(self, item: dict) -> str:
        model = (item.get("model") or "").strip()[:MAX_SKU]
        if model and self._product_sku_free(model):
            return model
        variant_skus = sorted(_variant_sku(v) for v in item.get("variants") or [])
        base = variant_skus[0] if variant_skus else (model or f"ATL-{item['id'][:8]}")
        if self._product_sku_free(base):
            return base
        n = 2
        while not self._product_sku_free(_with_suffix(base, n)):
            n += 1
        return _with_suffix(base, n)

    def _variant_sku_free(self, sku: str, own: ProductVariant | None) -> bool:
        stmt = select(ProductVariant.id).where(ProductVariant.sku == sku)
        if own is not None and own.id is not None:
            stmt = stmt.where(ProductVariant.id != own.id)
        return self.db.scalar(stmt) is None

    def _free_variant_sku(self, base: str, own: ProductVariant | None) -> str:
        if own is not None and own.sku == base:
            return base
        if self._variant_sku_free(base, own):
            return base
        n = 2
        while True:
            candidate = _with_suffix(base, n)
            if own is not None and own.sku == candidate:
                return candidate
            if self._variant_sku_free(candidate, own):
                return candidate
            n += 1

    # --- variantes y fotos ------------------------------------------------------------

    def _variants(self, product: Product, incoming: list[dict]) -> bool:
        wanted = {item["id"] for item in incoming}
        changed = False
        for variant in list(product.variants):
            if variant.external_inventory_id not in wanted:
                product.variants.remove(variant)
                changed = True
        if changed:
            self.db.flush()  # libera SKUs antes de insertar
        current = {v.external_inventory_id: v for v in product.variants}
        for item in incoming:
            variant = current.get(item["id"])
            if variant is None:
                # Una variante que Atlas movió de pieza deja la anterior.
                moved = self.db.scalar(
                    select(ProductVariant).where(ProductVariant.external_inventory_id == item["id"])
                )
                if moved is not None:
                    self.db.delete(moved)
                    self.db.flush()
                variant = ProductVariant(
                    external_inventory_id=item["id"], sku=self._free_variant_sku(_variant_sku(item), None)
                )
                product.variants.append(variant)
                current[item["id"]] = variant
                changed = True
            changed |= assign(
                variant,
                sku=self._free_variant_sku(_variant_sku(item), variant),
                color=item.get("color"),
                size=item.get("size"),
                available=bool(item.get("available", True)),
            )
        return changed

    def _photos(self, product: Product, images: list[dict], name: str) -> bool:
        """Reemplaza solo las fotos de Atlas (sin `media_asset_id`); las del panel se quedan."""
        kept = [m for m in product.media if m.media_asset_id is not None]
        used = {m.position for m in kept}
        ordered = [img for _, img in sorted(enumerate(images), key=lambda t: (t[1].get("position") or 0, t[0]))]
        primary = None
        if ordered and not any(m.is_primary for m in kept):
            primary = next((i for i, img in enumerate(ordered) if img.get("is_primary")), 0)
        desired = []
        position = 0
        for index, image in enumerate(ordered):
            while position in used:
                position += 1
            alt = (image.get("alt") or "").strip() or name
            desired.append((image["url"][:MAX_URL], alt[:MAX_URL], position, index == primary))
            position += 1
        ours = [m for m in product.media if m.media_asset_id is None]
        current = sorted(((m.url, m.alt, m.position, m.is_primary) for m in ours), key=lambda t: t[2])
        if current == desired:
            return False
        for media in ours:
            product.media.remove(media)
        if ours:
            self.db.flush()  # libera posiciones (único product_id + position)
        for url, alt, pos, is_primary in desired:
            product.media.append(ProductMedia(url=url, alt=alt, position=pos, is_primary=is_primary))
        return True


# Freno de la nocturna: una carga completa vacía o recortada (canal apagado, cambio de
# configuración, falla de Atlas) no debe vaciar el sitio.
ARCHIVE_MAX_SHARE = 0.30
ARCHIVE_MIN_POPULATION = 10


def archive_missing(db: Session, seen: set[str]) -> tuple[int, str | None]:
    """Nocturna completa: archiva las piezas de Atlas que ya no vinieron publicadas.

    Devuelve (archivadas, nota). Si la carga no trajo piezas vivas, o archivaría más del 30% de
    las piezas de Atlas no archivadas (con al menos 10), no archiva nada y la nota lo explica.
    """
    candidates = list(
        db.scalars(
            select(Product).where(
                Product.external_inventory_id.is_not(None), Product.status != STATUS_ARCHIVED
            )
        )
    )
    missing = [p for p in candidates if p.external_inventory_id not in seen]
    if not missing:
        return 0, None
    if not seen:
        return 0, f"archivado omitido: la carga completa no trajo piezas ({len(missing)} sin archivar)"
    population = len(candidates)
    if population >= ARCHIVE_MIN_POPULATION and len(missing) > ARCHIVE_MAX_SHARE * population:
        return 0, (
            f"archivado omitido: archivaría {len(missing)} de {population} piezas (más del 30%)"
        )
    for product in missing:
        product.status = STATUS_ARCHIVED
    return len(missing), None


def apply_availability(db: Session, items: list[dict]) -> int:
    """Disponibilidad por talla y recálculo de la pieza. Ignora variantes que no conocemos."""
    ids = {item["variant_id"] for item in items}
    variants = {
        v.external_inventory_id: v
        for v in db.scalars(select(ProductVariant).where(ProductVariant.external_inventory_id.in_(ids)))
    }
    changed = 0
    touched = set()
    for item in items:
        variant = variants.get(item["variant_id"])
        if variant is None:
            continue
        if assign(variant, available=bool(item["available"])):
            changed += 1
        touched.add(variant.product_id)
    if touched:
        for product in db.scalars(
            select(Product)
            .where(Product.id.in_(touched), Product.external_inventory_id.is_not(None))
            .options(selectinload(Product.variants))
        ):
            if assign(product, available=any(v.available for v in product.variants)):
                changed += 1
    return changed
