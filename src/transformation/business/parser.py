"""
Sub Order Type Parser.

Parses the raw ``sub_order_type`` field found in POS exports into its
constituent ``brand`` and ``platform`` components.

This module is a pure, dependency-free string parser. It has no
awareness of DataFrames, files, or the wider pipeline — it is intended
to be composed into the Business Silver pipeline by the caller.
"""

_BRAND_PLATFORM_SEPARATOR: str = " - "


def parse_sub_order_type(sub_order_type: str | None) -> tuple[str | None, str | None]:
    """
    Parse a raw ``sub_order_type`` value into ``(brand, platform)``.

    The value is expected in one of two shapes:
      - "<brand> - <platform>" (e.g. an aggregator order), which is
        split into a brand and a platform.
      - A bare channel name with no separator (e.g. "Dine In",
        "Delivery", "Pick Up"), which has no brand and is treated
        entirely as the platform.

    Examples:
        "Thepla House By Tejals - Zomato"
            -> ("Thepla House By Tejals", "Zomato")
        "Homely & Healthy App - Swiggy (Toing)"
            -> ("Homely & Healthy App", "Swiggy (Toing)")
        "Dine In"
            -> (None, "Dine In")
        "Delivery"
            -> (None, "Delivery")
        "Pick Up"
            -> (None, "Pick Up")

    Args:
        sub_order_type: The raw sub order type string. May be ``None``
            or an empty/whitespace-only string.

    Returns:
        tuple[str | None, str | None]: A ``(brand, platform)`` tuple.
        ``brand`` is ``None`` when the value has no separator.
        ``platform`` is ``None`` only when the input itself is empty
        or ``None``.
    """
    if sub_order_type is None:
        return None, None

    trimmed_value = sub_order_type.strip()

    if not trimmed_value:
        return None, None

    if _BRAND_PLATFORM_SEPARATOR in trimmed_value:
        brand, platform = trimmed_value.rsplit(_BRAND_PLATFORM_SEPARATOR, 1)
        brand = brand.strip() or None
        platform = platform.strip() or None
        return brand, platform

    return None, trimmed_value
