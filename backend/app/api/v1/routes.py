from fastapi import APIRouter, Response

from app.api.v1.admin import router as admin_router
from app.api.v1.deps import DbDep, PageParam, PageSizeParam, SearchParam, SettingsDep, found
from app.models import CatalogEvent
from app.schemas import public as schemas
from app.services import catalog

router = APIRouter(prefix="/api/v1")
router.include_router(admin_router)


@router.get("/health", response_model=schemas.Health)
def health() -> schemas.Health:
    return schemas.Health()


@router.get("/brands", response_model=schemas.Items[schemas.BrandSummary])
def list_brands(db: DbDep, settings: SettingsDep, featured: bool | None = None, q: SearchParam = None):
    return {"items": catalog.list_brands(db, settings.demo_mode, featured=featured, q=q)}


@router.get("/brands/{slug}", response_model=schemas.BrandDetail)
def get_brand(slug: str, db: DbDep, settings: SettingsDep):
    return found(catalog.get_brand(db, slug, settings.demo_mode), "Marca no encontrada")


@router.get("/categories", response_model=schemas.Items[schemas.Category])
def list_categories(db: DbDep):
    return {"items": catalog.list_categories(db)}


@router.get("/products", response_model=schemas.Page[schemas.ProductCard])
def list_products(
    db: DbDep,
    settings: SettingsDep,
    brand: str | None = None,
    category: str | None = None,
    featured: bool | None = None,
    sort: catalog.ProductSort = "display",
    page: PageParam = 1,
    page_size: PageSizeParam = 24,
):
    return catalog.list_products(
        db,
        settings.demo_mode,
        brand=brand,
        category=category,
        featured=featured,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{slug}", response_model=schemas.ProductDetail)
def get_product(slug: str, db: DbDep, settings: SettingsDep):
    return found(catalog.get_product(db, slug, settings), "Pieza no encontrada")


@router.get("/novedades", response_model=schemas.Page[schemas.ProductCard])
def list_novedades(
    db: DbDep, settings: SettingsDep, page: PageParam = 1, page_size: PageSizeParam = 24
):
    return catalog.list_novedades(db, settings.demo_mode, page=page, page_size=page_size)


@router.get("/collections", response_model=schemas.Items[schemas.CollectionSummary])
def list_collections(db: DbDep, settings: SettingsDep):
    return {"items": catalog.list_collections(db, settings.demo_mode)}


@router.get("/collections/{slug}", response_model=schemas.CollectionDetail)
def get_collection(slug: str, db: DbDep, settings: SettingsDep):
    return found(catalog.get_collection(db, slug, settings.demo_mode), "Colección no encontrada")


@router.get("/lookbooks", response_model=schemas.Items[schemas.LookbookSummary])
def list_lookbooks(db: DbDep, settings: SettingsDep):
    return {"items": catalog.list_lookbooks(db, settings.demo_mode)}


@router.get("/lookbooks/{slug}", response_model=schemas.LookbookDetail)
def get_lookbook(slug: str, db: DbDep, settings: SettingsDep):
    return found(catalog.get_lookbook(db, slug, settings.demo_mode), "Lookbook no encontrado")


@router.get("/search", response_model=schemas.SearchResults)
def search(db: DbDep, settings: SettingsDep, q: SearchParam = None):
    return catalog.search(db, q, settings.demo_mode)


@router.get("/site-settings/public", response_model=schemas.PublicSettings)
def site_settings(db: DbDep, settings: SettingsDep):
    return catalog.public_settings(db, settings)


@router.post("/events", status_code=204, response_class=Response)
def create_event(event: schemas.EventIn, db: DbDep, settings: SettingsDep) -> None:
    product = found(
        catalog.find_visible_product(db, event.product_slug, settings.demo_mode),
        "Pieza no encontrada",
    )
    db.add(CatalogEvent(type=event.type, product_id=product.id))
    db.commit()
