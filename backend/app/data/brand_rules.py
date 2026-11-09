"""Normalization table for the brand import. Editorial decisions live here, not in the import logic."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalRule:
    canonical: str
    sources: tuple[str, ...]
    slug: str | None = None  # Derived from `canonical` when omitted.


CANONICAL_RULES: tuple[CanonicalRule, ...] = (
    CanonicalRule("A Bathing Ape / BAPE", ("A Bathing Ape", "BAPE"), slug="a-bathing-ape"),
    CanonicalRule("AMI Paris", ("Ami Alexandre Mattiussi", "Ami Paris")),
    CanonicalRule("Ferragamo", ("Ferragamo", "Salvatore Ferragamo")),
    CanonicalRule("Canada Goose", ("Canadá Goose",)),
)

# Source names that are not brands: never in the public directory.
CLASSIFICATIONS: tuple[str, ...] = ("Sin marca",)

# Independent records, never merged with lookalikes, flagged for human review.
PENDING_REVIEW: tuple[str, ...] = (
    "Asaali",
    "Asali Jean",
    "Thierry Mugler",
    "Pali",
    "Steve McQueen",
    "Subhuman",
    "Unfathomable",
    "VSTAR 2",
)
