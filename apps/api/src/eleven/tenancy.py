import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import JSON, Boolean, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from eleven.config import Settings, get_settings
from eleven.db import Base, TimestampMixin, get_session, new_id


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Configuración pública del tenant (p. ej. teléfono de WhatsApp en E.164). Sin secretos.
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def current_tenant(session: SessionDep, settings: SettingsDep) -> Tenant:
    """Tenant de la instancia, resuelto en servidor por configuración.

    Cuando haya varios tenants por instancia se resolverá por dominio o token, nunca por un
    parámetro enviado por el cliente.
    """
    tenant = session.scalar(select(Tenant).where(Tenant.slug == settings.tenant_slug))
    if tenant is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Tenant no configurado")
    return tenant


TenantDep = Annotated[Tenant, Depends(current_tenant)]
