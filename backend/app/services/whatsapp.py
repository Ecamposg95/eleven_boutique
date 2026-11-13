import re
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Piece:
    brand_slug: str | None  # None for "Sin marca": the phrase and URL drop the brand.
    brand_name: str | None
    name: str
    slug: str
    sku: str

    def label(self) -> str:
        return self.name if self.brand_slug is None else f"{self.brand_name} — {self.name}"

    def link(self, site_url: str) -> str:
        base = site_url.rstrip("/")
        if self.brand_slug is None:
            return f"{base}/piezas/{self.slug}"
        return f"{base}/marcas/{self.brand_slug}/{self.slug}"


def _wa_url(digits: str, message: str) -> str:
    return f"https://wa.me/{digits}?text={quote(message, safe='')}"


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
    piece = Piece(brand_slug, brand_name, name, slug, sku)
    message = (
        f"Hola, me interesa conocer más sobre esta pieza de Eleven Boutique: {piece.label()}. "
        f"Referencia: {sku}. Enlace: {piece.link(site_url)}. ¿Podrían brindarme atención personalizada?"
    )
    return _wa_url(digits, message)


def build_selection_url(*, digits: str, site_url: str, pieces: list[Piece]) -> str:
    """One message for several pieces ("Mi selección"); a single piece keeps the product template."""
    if len(pieces) == 1:
        p = pieces[0]
        url = build_consult_url(
            digits=digits,
            site_url=site_url,
            brand_slug=p.brand_slug,
            brand_name=p.brand_name,
            name=p.name,
            slug=p.slug,
            sku=p.sku,
        )
        assert url is not None
        return url
    lines = [
        f"{i}. {p.label()}. Referencia: {p.sku}. Enlace: {p.link(site_url)}"
        for i, p in enumerate(pieces, start=1)
    ]
    message = (
        "Hola, me interesa conocer más sobre estas piezas de Eleven Boutique:\n\n"
        + "\n".join(lines)
        + "\n\n¿Podrían brindarme atención personalizada?"
    )
    return _wa_url(digits, message)
