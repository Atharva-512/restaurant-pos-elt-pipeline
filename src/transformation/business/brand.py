"""
Brand Standardizer.

Standardizes already-extracted brand names into a single canonical
form. This module has no knowledge of ``sub_order_type`` and does not
perform any parsing — it only maps known brand name variants to their
canonical representation.
"""
from typing import Final

import re

# Maps a normalized brand key (lowercase, whitespace-collapsed, "and"
# unified to "&") to its canonical brand name. Add new variants here
# as they are observed in the data — no other code changes required.
_CANONICAL_BRANDS: Final[dict[str, str]] = {
    "thepla house": "Thepla House By Tejals",
    "thepla house by tejals": "Thepla House By Tejals",
    "homely healthy": "Homely & Healthy",
    "homely & healthy": "Homely & Healthy",
    "homely & healthy app": "Homely & Healthy",
}

_WHITESPACE_PATTERN: Final = re.compile(r"\s+")
_AND_PATTERN: Final = re.compile(r"\band\b")


def standardize_brand(brand: str | None) -> str | None:
    """
    Standardize a raw brand name into its canonical form.

    Matching is case-insensitive and tolerant of whitespace variations
    and "and" / "&" spelling differences (e.g. "Homely and Healthy"
    and "Homely & Healthy" both resolve to the same canonical brand).
    Brands not present in the known mapping are returned unchanged
    (trimmed only), so unrecognized values are never silently dropped.

    Args:
        brand: The raw brand name, typically produced by
            ``parser.parse_sub_order_type()``. May be ``None``.

    Returns:
        str | None: The canonical brand name, the original
        (whitespace-trimmed) brand if unrecognized, or ``None`` if the
        input was ``None``.
    """
    if brand is None:
        return None

    if not isinstance(brand, str):
        return None

    trimmed_brand = brand.strip()

    if not trimmed_brand:
        return None

    normalized_key = _normalize_brand_key(trimmed_brand)

    return _CANONICAL_BRANDS.get(normalized_key, trimmed_brand)


def _normalize_brand_key(brand: str) -> str:
    """
    Build a normalized lookup key for a brand name.

    Normalization steps:
      1. Lowercase the value.
      2. Unify "and" with "&" so both spellings map to the same key.
      3. Collapse repeated whitespace into single spaces.

    Args:
        brand: A whitespace-trimmed brand name.

    Returns:
        str: The normalized key used for canonical lookup.
    """
    lowered_brand = brand.lower()
    unified_brand = _AND_PATTERN.sub("&", lowered_brand)
    collapsed_brand = _WHITESPACE_PATTERN.sub(" ", unified_brand).strip()

    return collapsed_brand
