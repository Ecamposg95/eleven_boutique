import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from eleven.catalog import service
from eleven.catalog.schemas import (
    Availability,
    CollectionOut,
    Facets,
    ProductDetail,
    ProductPage,
    SortKey,
)
from eleven.tenancy import SessionDep, SettingsDep, TenantDep


def require_public_catalog(settings: SettingsDep) -> None:
    if not settings.catalog_public_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Catálogo no disponible")


router = APIRouter(
    prefix="/catalog", tags=["catalog"], dependencies=[Depends(require_public_catalog)]
)


@router.get("/products", response_model=ProductPage)
def list_products(
    session: SessionDep,
    tenant: TenantDep,
    settings: SettingsDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[list[str], Query(max_length=20)] = [],  # noqa: B006
    size: Annotated[list[str], Query(max_length=20)] = [],  # noqa: B006
    color: Annotated[list[str], Query(max_length=20)] = [],  # noqa: B006
    collection: Annotated[str | None, Query(max_length=160)] = None,
    price_min: Annotated[Decimal | None, Query(ge=0)] = None,
    price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    sort: SortKey = "new",
    limit: Annotated[int, Query(ge=1)] = 24,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> ProductPage:
    filters = service.ProductFilters(
        q=q or None,
        category=category,
        size=size,
        color=color,
        collection=collection,
        price_min=price_min,
        price_max=price_max,
    )
    try:
        return service.list_products(
            session,
            tenant.id,
            filters,
            sort,
            min(limit, settings.catalog_page_max),
            cursor,
            settings.media_public_base_url,
        )
    except service.InvalidCursorError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/products/{slug}", response_model=ProductDetail)
def get_product(
    slug: str, session: SessionDep, tenant: TenantDep, settings: SettingsDep
) -> ProductDetail:
    product = service.get_product(session, tenant.id, slug, settings.media_public_base_url)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return product


@router.get("/facets", response_model=Facets)
def get_facets(session: SessionDep, tenant: TenantDep) -> Facets:
    return service.facets(session, tenant.id)


@router.get("/collections", response_model=list[CollectionOut])
def get_collections(session: SessionDep, tenant: TenantDep) -> list[CollectionOut]:
    return service.list_collections(session, tenant.id)


@router.get("/variants/{variant_id}/availability", response_model=Availability)
def get_availability(variant_id: uuid.UUID, session: SessionDep, tenant: TenantDep) -> Availability:
    availability = service.variant_availability(session, tenant.id, variant_id)
    if availability is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return availability
