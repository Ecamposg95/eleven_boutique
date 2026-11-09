"""Products, brands and categories. Reading brands is open to editors: the product form needs it."""

import uuid

from fastapi import APIRouter, Response

from app.api.v1.admin.deps import AdminOnly, AdminPageSize, CurrentUser
from app.api.v1.deps import DbDep, PageParam, SearchParam
from app.schemas import admin as schemas
from app.services.admin import products, taxonomy

router = APIRouter()


@router.get("/products", response_model=schemas.Page[schemas.AdminProduct])
def list_products(
    db: DbDep,
    q: SearchParam = None,
    status: schemas.Status | None = None,
    brand: str | None = None,
    category: str | None = None,
    has_photo: bool | None = None,
    sort: products.ProductSort = "updated",
    page: PageParam = 1,
    page_size: AdminPageSize = 24,
):
    return products.list_products(
        db,
        q=q,
        status=status,
        brand=brand,
        category=category,
        has_photo=has_photo,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post("/products", response_model=schemas.AdminProduct, status_code=201)
def create_product(body: schemas.ProductCreate, db: DbDep, user: CurrentUser):
    return products.create_product(db, body, user)


@router.post("/products/bulk", response_model=schemas.ProductBulkOut)
def bulk_products(body: schemas.ProductBulkIn, db: DbDep, user: CurrentUser):
    return products.bulk_action(db, body, user)


@router.get("/products/{product_id}", response_model=schemas.AdminProduct)
def get_product(product_id: uuid.UUID, db: DbDep):
    return products.product_out(products.get_product(db, product_id))


@router.patch("/products/{product_id}", response_model=schemas.AdminProduct)
def update_product(product_id: uuid.UUID, body: schemas.ProductPatch, db: DbDep, user: CurrentUser):
    return products.update_product(db, product_id, body, user)


@router.delete("/products/{product_id}", response_model=schemas.AdminProduct)
def archive_product(product_id: uuid.UUID, db: DbDep, user: CurrentUser):
    return products.archive_product(db, product_id, user)


@router.post("/products/{product_id}/media", response_model=schemas.AdminProduct, status_code=201)
def add_product_media(
    product_id: uuid.UUID, body: schemas.ProductMediaAdd, db: DbDep, user: CurrentUser
):
    return products.add_media(db, product_id, body, user)


@router.patch("/products/{product_id}/media", response_model=schemas.AdminProduct)
def reorder_product_media(
    product_id: uuid.UUID, body: schemas.ProductMediaOrder, db: DbDep, user: CurrentUser
):
    return products.reorder_media(db, product_id, body, user)


@router.patch("/products/{product_id}/media/{media_id}", response_model=schemas.AdminProduct)
def update_product_media_alt(
    product_id: uuid.UUID, media_id: uuid.UUID, body: schemas.MediaPatch, db: DbDep, user: CurrentUser
):
    return products.update_media_alt(db, product_id, media_id, body.alt, user)


@router.delete("/products/{product_id}/media/{media_id}", response_model=schemas.AdminProduct)
def remove_product_media(product_id: uuid.UUID, media_id: uuid.UUID, db: DbDep, user: CurrentUser):
    return products.remove_media(db, product_id, media_id, user)


@router.get("/brands", response_model=schemas.Page[schemas.AdminBrand])
def list_brands(
    db: DbDep,
    q: SearchParam = None,
    status: schemas.Status | None = None,
    page: PageParam = 1,
    page_size: AdminPageSize = 24,
):
    return taxonomy.list_brands(db, q=q, status=status, page=page, page_size=page_size)


@router.post("/brands", response_model=schemas.AdminBrand, status_code=201)
def create_brand(body: schemas.BrandCreate, db: DbDep, user: AdminOnly):
    return taxonomy.create_brand(db, body, user)


@router.get("/brands/{brand_id}", response_model=schemas.AdminBrand)
def get_brand(brand_id: uuid.UUID, db: DbDep):
    return taxonomy.get_brand(db, brand_id)


@router.patch("/brands/{brand_id}", response_model=schemas.AdminBrand)
def update_brand(brand_id: uuid.UUID, body: schemas.BrandPatch, db: DbDep, user: AdminOnly):
    return taxonomy.update_brand(db, brand_id, body, user)


@router.get("/categories", response_model=schemas.Page[schemas.AdminCategory])
def list_categories(db: DbDep):
    return taxonomy.list_categories(db)


@router.post("/categories", response_model=schemas.AdminCategory, status_code=201)
def create_category(body: schemas.CategoryCreate, db: DbDep, user: CurrentUser):
    return taxonomy.create_category(db, body, user)


@router.patch("/categories/{category_id}", response_model=schemas.AdminCategory)
def update_category(category_id: uuid.UUID, body: schemas.CategoryPatch, db: DbDep, user: CurrentUser):
    return taxonomy.update_category(db, category_id, body, user)


@router.delete("/categories/{category_id}", status_code=204, response_class=Response)
def delete_category(category_id: uuid.UUID, db: DbDep, user: CurrentUser) -> None:
    taxonomy.delete_category(db, category_id, user)
