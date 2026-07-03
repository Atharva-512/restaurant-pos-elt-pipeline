"""
Business Calendar Deriver.

Derives business calendar attributes (business date, weekday, month,
quarter, year, ...) from an existing datetime value. This module does
not read, parse, or infer timestamps — it only decomposes a datetime
value that has already been produced elsewhere in the pipeline.
"""

from datetime import date, datetime
from typing import Final

# pandas.Timestamp is a subclass of datetime.datetime, so a
# pandas Timestamp is accepted here without importing pandas directly,
# honoring the "no pandas dependency" rule for this module.
_QUARTER_MONTH_DIVISOR: Final[int] = 3

_CALENDAR_KEYS: Final[tuple[str, ...]] = (
    "business_date",
    "weekday",
    "month",
    "month_name",
    "quarter",
    "year",
)


def derive_calendar_attributes(
    timestamp: datetime | None,
) -> dict[str, date | str | int | None]:
    """
    Derive business calendar attributes from a datetime value.

    Accepts any ``datetime.datetime`` instance, including
    ``pandas.Timestamp`` (which subclasses ``datetime.datetime``)
    without requiring a direct pandas dependency.
    Args:
        timestamp: The source datetime value. May be ``None``.

    Returns:
        dict[str, Any]: A dictionary with the following keys:
            - "business_date" (date): The calendar date component.
            - "weekday" (str): Full weekday name (e.g. "Monday").
            - "month" (int): Month number (1-12).
            - "month_name" (str): Full month name (e.g. "January").
            - "quarter" (int): Calendar quarter (1-4).
            - "year" (int): Four-digit year.
        If ``timestamp`` is ``None``, every value in the returned
        dictionary is ``None``.
    """
    if timestamp is None:
        return _empty_calendar_attributes()

    business_date: date = timestamp.date()
    month: int = timestamp.month

    return {
        "business_date": business_date,
        "weekday": timestamp.strftime("%A"),
        "month": month,
        "month_name": timestamp.strftime("%B"),
        "quarter": _derive_quarter(month),
        "year": timestamp.year,
    }


def _derive_quarter(month: int) -> int:
    """
    Derive the calendar quarter (1-4) from a month number.

    Args:
        month: Month number in the range 1-12.

    Returns:
        int: The calendar quarter corresponding to the given month.
    """
    return ((month - 1) // _QUARTER_MONTH_DIVISOR) + 1

def _empty_calendar_attributes() -> dict[str, date | str | int | None]:
    """
    Return an empty calendar attribute dictionary.
    """
    return {
        "business_date": None,
        "weekday": None,
        "month": None,
        "month_name": None,
        "quarter": None,
        "year": None,
    }