"""Configuración pública del sitio para la web y, más adelante, el agente."""

from fastapi import APIRouter
from pydantic import BaseModel

from eleven.tenancy import SettingsDep, TenantDep

router = APIRouter(tags=["site"])


class SiteFlags(BaseModel):
    demo_mode: bool
    catalog_public_enabled: bool
    checkout_enabled: bool
    payments_enabled: bool


class SiteOut(BaseModel):
    name: str
    is_demo: bool
    whatsapp_phone: str | None
    flags: SiteFlags


@router.get("/site", response_model=SiteOut)
def get_site(tenant: TenantDep, settings: SettingsDep) -> SiteOut:
    phone = tenant.settings.get("whatsapp_phone")
    return SiteOut(
        name=tenant.name,
        is_demo=tenant.is_demo,
        whatsapp_phone=phone if isinstance(phone, str) else None,
        flags=SiteFlags(
            demo_mode=settings.demo_mode,
            catalog_public_enabled=settings.catalog_public_enabled,
            checkout_enabled=settings.checkout_enabled,
            payments_enabled=settings.payments_enabled,
        ),
    )
