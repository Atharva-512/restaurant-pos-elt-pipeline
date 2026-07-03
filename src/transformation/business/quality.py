"""
Business Silver Quality Validator.

Performs lightweight, rule-based quality validation on already-derived
Business Silver attributes (brand, platform, business date, daypart).
This module does not standardize, parse, or derive any values itself —
it only inspects values produced by ``parser.py``, ``brand.py``,
``platform.py``, ``calendar.py``, and ``daypart.py``.
"""

from datetime import date
from typing import Final

# Canonical brand and platform values recognized by the Business
# Silver layer. Kept local to this module so validation stays
# decoupled from the internal lookup tables of ``brand.py`` and
# ``platform.py``.
_KNOWN_BRANDS: Final[frozenset[str]] = frozenset(
    {
        "Thepla House By Tejals",
        "Homely & Healthy",
    }
)

_KNOWN_PLATFORMS: Final[frozenset[str]] = frozenset(
    {
        "Swiggy",
        "Zomato",
        "Delivery",
        "Pick Up",
        "Dine In",
    }
)

# Platforms that legitimately have no associated brand (e.g. walk-in
# or direct channels rather than aggregator/brand storefronts).
_BRANDLESS_PLATFORMS: Final[frozenset[str]] = frozenset(

    {
        "Delivery",
        "Pick Up",
        "Dine In",
    }
)


def _is_missing(value: object) -> bool:
    
    """
    Return True if the supplied value represents a missing value.

    Handles both ``None`` and NaN without requiring a pandas dependency.
    """
    return value is None or value != value

def validate_business_attributes(
    brand: str | None,
    platform: str | None,
    business_date: date | None,
    daypart: str | None,
) -> list[str]:
    """
    Validate a single row's Business Silver attributes.

    Args:
        brand: The standardized brand name, or ``None``.
        platform: The standardized platform name, or ``None``.
        business_date: The derived business date, or ``None``.
        daypart: The derived daypart label, or ``None``.

    Returns:
        list[str]: Validation messages describing any issues found.
        An empty list means the row passed all checks.
    """
    # Normalize missing values coming from pandas.
    if _is_missing(brand):
        brand = None

    if _is_missing(platform):
        platform = None
    
    validation_errors: list[str] = []

    if brand is not None and brand not in _KNOWN_BRANDS:
        validation_errors.append("Unknown brand")

    if platform is not None and platform not in _KNOWN_PLATFORMS:
        validation_errors.append("Unknown platform")

    if business_date is None:
        validation_errors.append("Missing business date")

    if daypart is None:
        validation_errors.append("Missing daypart")

    if brand is not None and platform is None:
        validation_errors.append("Brand exists without platform")

    if (
        platform is not None
        and brand is None
        and platform not in _BRANDLESS_PLATFORMS
    ):
        validation_errors.append("Platform exists without brand")

    return validation_errors
