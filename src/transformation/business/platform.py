"""
Platform Standardizer.

Standardizes already-extracted platform names into a single canonical
form. This module has no knowledge of ``sub_order_type`` and does not
perform any parsing — it only maps known platform name variants to
their canonical representation.
"""

from typing import Final

# Maps a normalized platform key (lowercase, whitespace-trimmed) to its
# canonical platform name. Add new variants here as they are observed
# in the data — no other code changes required.
_CANONICAL_PLATFORMS: Final[dict[str, str]] = {
    "swiggy": "Swiggy",
    "swiggy (toing)": "Swiggy",
    "zomato": "Zomato",
    "delivery": "Delivery",
    "pick up": "Pick Up",
    "dine in": "Dine In",
}


def standardize_platform(platform: str | None) -> str | None:
    """
    Standardize a raw platform name into its canonical form.

    Matching is case-insensitive and tolerant of surrounding
    whitespace. Platforms not present in the known mapping are
    returned unchanged (trimmed only), so unrecognized values are
    never silently dropped.

    Args:
        platform: The raw platform name, typically produced by
            ``parser.parse_sub_order_type()``. May be ``None``.

    Returns:
        str | None: The canonical platform name, the original
        (whitespace-trimmed) platform if unrecognized, or ``None`` if
        the input was ``None`` or blank.
    """
    if platform is None:
        return None

    if not isinstance(platform, str):
        return None

    trimmed_platform = platform.strip()

    if not trimmed_platform:
        return None

    normalized_key = trimmed_platform.lower()

    return _CANONICAL_PLATFORMS.get(normalized_key, trimmed_platform)
