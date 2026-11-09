import re
from urllib.parse import quote

_ALLOWED = re.compile(r"\+?[\d\s().-]+")


def normalize_number(raw: str | None) -> str | None:
    """Digits of a valid E.164 number (8 to 15 digits, no leading zero), otherwise None."""
    if not raw or not _ALLOWED.fullmatch(raw.strip()):
        return None
    digits = re.sub(r"\D", "", raw)
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        return None
    return digits


def build_consult_url(
    *,
    digits: str | None,
    site_url: str,
    brand_slug: str | None,
    brand_name: str | None,
    name: str,
    slug: str,
    sku: str,
) -> str | None:
    if digits is None:
        return None
    base = site_url.rstrip("/")
    if brand_slug is None:
        piece = name
        link = f"{base}/piezas/{slug}"
    else:
        piece = f"{brand_name} — {name}"
        link = f"{base}/marcas/{brand_slug}/{slug}"
    message = (
        f"Hola, me interesa conocer más sobre esta pieza de Eleven Boutique: {piece}. "
        f"Referencia: {sku}. Enlace: {link}. ¿Podrían brindarme atención personalizada?"
    )
    return f"https://wa.me/{digits}?text={quote(message, safe='')}"
