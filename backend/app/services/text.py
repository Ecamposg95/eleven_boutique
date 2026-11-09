"""Text normalization shared by search, slugs and the brand import."""

import re
import unicodedata

_APOSTROPHES = "'’‘`´ʼ"
_DROPPED = str.maketrans("", "", _APOSTROPHES + ".")
_SEPARATORS = re.compile(r"[-‐‑–—/&,+:;()\s]+")


def normalize(text: str) -> str:
    """Levi's -> levis, Hermès -> hermes, Off-White -> off white, Gallery Dept. -> gallery dept."""
    # Apostrophes go first: NFKD would turn the acute accent sign into a space.
    decomposed = unicodedata.normalize("NFKD", text.translate(_DROPPED))
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SEPARATORS.sub(" ", without_marks.casefold().translate(_DROPPED)).strip()


def build_search_text(text: str) -> str:
    """Normalized text plus its compact form, so `offwhite` also finds Off-White."""
    normalized = normalize(text)
    compact = normalized.replace(" ", "")
    return normalized if compact == normalized else f"{normalized} {compact}"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize(text)).strip("-")


def escape_like(value: str) -> str:
    """Escapes LIKE wildcards; pair with ESCAPE '\\'."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
