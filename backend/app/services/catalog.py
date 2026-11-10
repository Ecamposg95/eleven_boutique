"""Read side of the public API: queries plus the mapping to explicit response schemas."""

from typing import Literal

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload, selectinload

from app.config import Settings
from app.models import (
    BLOCK_TEXT,
    KIND_BRAND,
    KIND_CLASSIFICATION,
    Brand,
    BrandAlias,
    Category,
    Collection,
    CollectionProduct,
    Lookbook,
    LookbookProduct,
    Product,
    ProductMedia,
    SiteSettings,
)
from app.schemas import public as schemas
from app.services.text import escape_like, normalize
from app.services.visibility import brand_visible, product_visible, record_visible
from app.services.whatsapp import build_consult_url, normalize_number

ProductSort = Literal["recent", "name", "display"]
SEARCH_PRODUCT_LIMIT = 60
DEFAULT_SITE_NAME = "Eleven Boutique"


def _contains(column, normalized_query: str) -> ColumnElement[bool]:
    return column.like(f"%{escape_like(normalized_query)}%", escape="\\")


# --- Brands ---------------------------------------------------------------------------


def _public_aliases(brand: Brand) -> list[str]:
    """Hides the canonical name and variants differing only by accents or case (spelling fixes)."""
    canonical = normalize(brand.name)
    ordered = sorted(
        brand.aliases, key=lambda a: (a.source_position is None, a.source_position or 0, a.alias)
    )
    return [alias.alias for alias in ordered if normalize(alias.alias) != canonical]


def _product_counts(db: Session, demo_mode: bool) -> dict:
    rows = db.execute(
        select(Product.brand_id, func.count())
        .join(Product.brand)
        .where(product_visible(demo_mode))
        .group_by(Product.brand_id)
    )
    return {owner_id: count for owner_id, count in rows}


def _brand_summary(brand: Brand, counts: dict) -> schemas.BrandSummary:
    return schemas.BrandSummary(
        slug=brand.slug,
        name=brand.name,
        logo_url=brand.logo_url,
        is_featured=brand.is_featured,
        aliases=_public_aliases(brand),
        product_count=counts.get(brand.id, 0),
    )


def _brand_name_match(query: str) -> ColumnElement[bool]:
    alias_match = select(BrandAlias.brand_id).where(_contains(BrandAlias.search_text, query))
    return or_(_contains(Brand.search_text, query), Brand.id.in_(alias_match))


def list_brands(
    db: Session, demo_mode: bool, *, featured: bool | None = None, q: str | None = None
) -> list[schemas.BrandSummary]:
    stmt = select(Brand).options(selectinload(Brand.aliases)).where(brand_visible(demo_mode))
    if featured is not None:
        stmt = stmt.where(Brand.is_featured.is_(featured))
    if q is not None and q.strip():
        query = normalize(q)
        if not query:
            return []
        stmt = stmt.where(_brand_name_match(query))
    brands = db.scalars(stmt).all()
    counts = _product_counts(db, demo_mode)
    # Sorted here because SQL collations disagree on accents across databases. Featured brands
    # are the home page showroom, so the editor's display_order sets their sequence.
    if featured:
        ordered = sorted(brands, key=lambda brand: (brand.display_order, normalize(brand.name)))
    else:
        ordered = sorted(brands, key=lambda brand: normalize(brand.name))
    return [_brand_summary(brand, counts) for brand in ordered]


def _resolve_brand(db: Session, slug: str, demo_mode: bool) -> Brand | None:
    base = select(Brand).options(selectinload(Brand.aliases)).where(brand_visible(demo_mode))
    brand = db.scalar(base.where(Brand.slug == slug))
    if brand is not None:
        return brand
    alias_owner = select(BrandAlias.brand_id).where(BrandAlias.slug == slug)
    return db.scalar(base.where(Brand.id.in_(alias_owner)))


def get_brand(db: Session, slug: str, demo_mode: bool) -> schemas.BrandDetail | None:
    brand = _resolve_brand(db, slug, demo_mode)
    if brand is None:
        return None
    summary = _brand_summary(brand, _product_counts(db, demo_mode))
    return schemas.BrandDetail(
        **summary.model_dump(),
        description=brand.description,
        editorial_image_url=brand.editorial_image_url,
    )


# --- Categories -----------------------------------------------------------------------


def list_categories(db: Session) -> list[schemas.Category]:
    categories = db.scalars(select(Category).order_by(Category.display_order, Category.slug)).all()
    slug_by_id = {category.id: category.slug for category in categories}
    return [
        schemas.Category(
            slug=category.slug,
            name=category.name,
            parent_slug=slug_by_id.get(category.parent_id),
        )
        for category in categories
    ]


def _category_and_children(column_match: ColumnElement[bool]) -> Select:
    matching = select(Category.id).where(column_match)
    return select(Category.id).where(
        or_(Category.id.in_(matching), Category.parent_id.in_(matching))
    )


# --- Products -------------------------------------------------------------------------


def _media(media: ProductMedia) -> schemas.Media:
    return schemas.Media(
        url=media.url, alt=media.alt, is_primary=media.is_primary, position=media.position
    )


def _card_fields(product: Product) -> dict:
    gallery = product.media  # Ordered by position.
    primary = next((m for m in gallery if m.is_primary), gallery[0] if gallery else None)
    secondary = next((m for m in gallery if m is not primary), None)
    is_classification = product.brand.kind == KIND_CLASSIFICATION
    return {
        "slug": product.slug,
        "name": product.name,
        "brand": schemas.CardBrand(
            slug=None if is_classification else product.brand.slug,
            name=None if is_classification else product.brand.name,
        ),
        "category": schemas.CardCategory(slug=product.category.slug, name=product.category.name),
        "primary_image": _media(primary) if primary else None,
        "secondary_image": _media(secondary) if secondary else None,
    }


def _card(product: Product) -> schemas.ProductCard:
    return schemas.ProductCard(**_card_fields(product))


def _visible_products(demo_mode: bool) -> Select:
    return (
        select(Product)
        .join(Product.brand)
        .options(
            contains_eager(Product.brand),
            joinedload(Product.category),
            selectinload(Product.media),
        )
        .where(product_visible(demo_mode))
    )


def _paginate(db: Session, stmt: Select, page: int, page_size: int) -> schemas.Page:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    products = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return schemas.Page[schemas.ProductCard](
        items=[_card(product) for product in products],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_products(
    db: Session,
    demo_mode: bool,
    *,
    brand: str | None = None,
    category: str | None = None,
    featured: bool | None = None,
    sort: ProductSort = "display",
    page: int = 1,
    page_size: int = 24,
) -> schemas.Page:
    stmt = _visible_products(demo_mode)
    if brand is not None:
        resolved = _resolve_brand(db, brand, demo_mode)
        if resolved is None:
            return schemas.Page[schemas.ProductCard](
                items=[], total=0, page=page, page_size=page_size
            )
        stmt = stmt.where(Product.brand_id == resolved.id)
    if category is not None:
        stmt = stmt.where(Product.category_id.in_(_category_and_children(Category.slug == category)))
    if featured is not None:
        stmt = stmt.where(Product.is_featured.is_(featured))

    if sort == "recent":
        stmt = stmt.order_by(Product.commercial_added_at.desc().nulls_last())
    elif sort == "display":
        stmt = stmt.order_by(Product.display_order)
    stmt = stmt.order_by(Product.search_text, Product.slug)
    return _paginate(db, stmt, page, page_size)


def list_novedades(db: Session, demo_mode: bool, *, page: int, page_size: int) -> schemas.Page:
    stmt = (
        _visible_products(demo_mode)
        .where(Product.commercial_added_at.is_not(None))
        .order_by(Product.commercial_added_at.desc(), Product.slug)
    )
    return _paginate(db, stmt, page, page_size)


def effective_whatsapp_digits(db: Session, settings: Settings, *, premium: bool = False) -> str | None:
    """The stored number wins; the env var covers a database that was not seeded yet.

    premium=True is the boutique line for premium brands. Without one, those pieces use the
    general line, so a missing premium number never hides the consult button.
    """
    row = db.scalar(select(SiteSettings).where(SiteSettings.is_demo.is_(False)))
    general = normalize_number((row.whatsapp_number if row else None) or settings.whatsapp_number)
    if not premium:
        return general
    stored = row.whatsapp_premium_number if row else None
    return normalize_number(stored or settings.whatsapp_premium_number) or general


def any_whatsapp_digits(db: Session, settings: Settings) -> bool:
    return bool(effective_whatsapp_digits(db, settings) or effective_whatsapp_digits(db, settings, premium=True))


def get_product(db: Session, slug: str, settings: Settings) -> schemas.ProductDetail | None:
    stmt = _visible_products(settings.demo_mode).where(Product.slug == slug)
    product = db.scalar(stmt)
    if product is None:
        return None
    is_classification = product.brand.kind == KIND_CLASSIFICATION
    return schemas.ProductDetail(
        **_card_fields(product),
        gallery=[_media(media) for media in product.media],
        consult_url=build_consult_url(
            digits=effective_whatsapp_digits(db, settings, premium=product.brand.is_premium),
            site_url=settings.site_base_url,
            brand_slug=None if is_classification else product.brand.slug,
            brand_name=None if is_classification else product.brand.name,
            name=product.name,
            slug=product.slug,
            sku=product.sku,
        ),
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        published_at=product.published_at,
    )


def find_visible_product(db: Session, slug: str, demo_mode: bool) -> Product | None:
    return db.scalar(
        select(Product).join(Product.brand).where(product_visible(demo_mode), Product.slug == slug)
    )


# --- Collections and lookbooks --------------------------------------------------------


def _visible_product_counts(db: Session, join_model, owner_column, demo_mode: bool) -> dict:
    rows = db.execute(
        select(owner_column, func.count())
        .join(Product, Product.id == join_model.product_id)
        .join(Product.brand)
        .where(product_visible(demo_mode))
        .group_by(owner_column)
    )
    return {owner_id: count for owner_id, count in rows}


def _related_cards(
    db: Session, join_model, owner_column, owner_id, demo_mode: bool
) -> list[schemas.ProductCard]:
    stmt = (
        _visible_products(demo_mode)
        .join(join_model, join_model.product_id == Product.id)
        .where(owner_column == owner_id)
        .order_by(join_model.position, Product.slug)
    )
    return [_card(product) for product in db.scalars(stmt).all()]


def _collection_summary(collection: Collection, counts: dict) -> schemas.CollectionSummary:
    return schemas.CollectionSummary(
        slug=collection.slug,
        title=collection.title,
        summary=collection.summary,
        cover_url=collection.cover_url,
        product_count=counts.get(collection.id, 0),
    )


def _collection_counts(db: Session, demo_mode: bool) -> dict:
    return _visible_product_counts(
        db, CollectionProduct, CollectionProduct.collection_id, demo_mode
    )


def list_collections(db: Session, demo_mode: bool) -> list[schemas.CollectionSummary]:
    collections = db.scalars(
        select(Collection)
        .where(record_visible(Collection, demo_mode))
        .order_by(Collection.display_order, Collection.slug)
    ).all()
    counts = _collection_counts(db, demo_mode)
    return [_collection_summary(collection, counts) for collection in collections]


def get_collection(db: Session, slug: str, demo_mode: bool) -> schemas.CollectionDetail | None:
    collection = db.scalar(
        select(Collection).where(record_visible(Collection, demo_mode), Collection.slug == slug)
    )
    if collection is None:
        return None
    summary = _collection_summary(collection, _collection_counts(db, demo_mode))
    products = _related_cards(
        db, CollectionProduct, CollectionProduct.collection_id, collection.id, demo_mode
    )
    return schemas.CollectionDetail(**summary.model_dump(), products=products)


def _lookbook_summary_fields(lookbook: Lookbook) -> dict:
    return {
        "slug": lookbook.slug,
        "title": lookbook.title,
        "summary": lookbook.summary,
        "cover_url": lookbook.cover_url,
    }


def list_lookbooks(db: Session, demo_mode: bool) -> list[schemas.LookbookSummary]:
    lookbooks = db.scalars(
        select(Lookbook)
        .where(record_visible(Lookbook, demo_mode))
        .order_by(Lookbook.display_order, Lookbook.slug)
    ).all()
    return [schemas.LookbookSummary(**_lookbook_summary_fields(item)) for item in lookbooks]


def _block(block) -> schemas.TextBlock | schemas.ImageBlock:
    content = block.content
    if block.type == BLOCK_TEXT:
        return schemas.TextBlock(
            position=block.position, heading=content.get("heading"), body=content["body"]
        )
    return schemas.ImageBlock(
        position=block.position,
        url=content["url"],
        alt=content["alt"],
        layout=content.get("layout", "full"),
    )


def get_lookbook(db: Session, slug: str, demo_mode: bool) -> schemas.LookbookDetail | None:
    lookbook = db.scalar(
        select(Lookbook)
        .options(selectinload(Lookbook.blocks))
        .where(record_visible(Lookbook, demo_mode), Lookbook.slug == slug)
    )
    if lookbook is None:
        return None
    return schemas.LookbookDetail(
        **_lookbook_summary_fields(lookbook),
        blocks=[_block(block) for block in lookbook.blocks],
        products=_related_cards(
            db, LookbookProduct, LookbookProduct.lookbook_id, lookbook.id, demo_mode
        ),
    )


# --- Search ---------------------------------------------------------------------------


def search(db: Session, q: str | None, demo_mode: bool) -> schemas.SearchResults:
    query = normalize(q or "")
    if not query:
        return schemas.SearchResults(brands=[], products=[])
    product_stmt = (
        _visible_products(demo_mode)
        .where(
            or_(
                _contains(Product.search_text, query),
                Product.category_id.in_(
                    _category_and_children(_contains(Category.search_text, query))
                ),
                # Limited to real brands so "sin marca" never matches through the classification.
                (Brand.kind == KIND_BRAND) & _brand_name_match(query),
            )
        )
        .order_by(Product.display_order, Product.search_text, Product.slug)
        .limit(SEARCH_PRODUCT_LIMIT)
    )
    products = db.scalars(product_stmt).all()
    return schemas.SearchResults(
        brands=list_brands(db, demo_mode, q=q),
        products=[_card(product) for product in products],
    )


# --- Site settings --------------------------------------------------------------------


def _pick_gallery(real: SiteSettings | None, demo: SiteSettings | None) -> list[dict[str, str]]:
    # Like pick(): the real gallery wins whenever it has photos.
    return (real.hero_gallery if real else None) or (demo.hero_gallery if demo else None) or []


def public_settings(db: Session, settings: Settings) -> schemas.PublicSettings:
    rows = db.scalars(select(SiteSettings)).all()
    real = next((row for row in rows if not row.is_demo), None)
    demo = next((row for row in rows if row.is_demo), None) if settings.demo_mode else None

    def pick(field: str) -> str | None:
        # Real content wins, so edits made in the admin panel also show with DEMO_MODE=true.
        return getattr(real, field, None) or getattr(demo, field, None)

    return schemas.PublicSettings(
        demo_mode=settings.demo_mode,
        whatsapp_enabled=any_whatsapp_digits(db, settings),
        site_name=pick("site_name") or DEFAULT_SITE_NAME,
        hero=schemas.Hero(
            image_url=pick("hero_image_url"),
            mobile_image_url=pick("hero_mobile_image_url"),
            headline=pick("hero_headline"),
            subhead=pick("hero_subhead"),
            gallery=[slide["url"] for slide in _pick_gallery(real, demo)],
        ),
        intro=pick("intro"),
        boutique=schemas.BodyText(body=pick("boutique_body")),
        contact=schemas.BodyText(body=pick("contact_body")),
    )
