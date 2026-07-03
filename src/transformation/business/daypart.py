"""
Business Daypart Deriver.

Derives a business daypart label (Breakfast, Lunch, Snacks, Dinner,
Late Night) from an existing datetime value. This module does not
read, parse, or infer timestamps — it only classifies a datetime
value that has already been produced elsewhere in the pipeline.
"""

from datetime import datetime, time
from typing import Final

# pandas.Timestamp is a subclass of datetime.datetime, so a
# pandas Timestamp is accepted here without importing pandas directly,
# honoring the "no pandas dependency" rule for this module.

# Ordered (start_time, end_time, label) daypart boundaries. Boundaries
# are inclusive on both ends. "Late Night" wraps past midnight, so it
# is handled separately from the ordinary same-day ranges.
_DAYPART_RANGES: Final[tuple[tuple[time, time, str], ...]] = (
    (time(5, 0), time(10, 59), "Breakfast"),
    (time(11, 0), time(15, 59), "Lunch"),
    (time(16, 0), time(18, 59), "Snacks"),
    (time(19, 0), time(22, 59), "Dinner"),
)

_LATE_NIGHT_START: Final[time] = time(23, 0)
_LATE_NIGHT_END: Final[time] = time(4, 59)
_LATE_NIGHT_LABEL: Final[str] = "Late Night"


def derive_daypart(timestamp: datetime | None) -> str | None:
    """
    Derive a business daypart label from a datetime value.

    Accepts any ``datetime.datetime`` instance, including
    ``pandas.Timestamp`` (which is itself a subclass of
    ``datetime.datetime``), without requiring a pandas import.

    Daypart boundaries:
        05:00-10:59 -> Breakfast
        11:00-15:59 -> Lunch
        16:00-18:59 -> Snacks
        19:00-22:59 -> Dinner
        23:00-04:59 -> Late Night

    Args:
        timestamp: The source datetime value. May be ``None``.

    Returns:
        str | None: The derived daypart label, or ``None`` if
        ``timestamp`` is ``None``.
    """
    if timestamp is None:
        return None

    time_of_day = timestamp.time()

    for start_time, end_time, label in _DAYPART_RANGES:
        if start_time <= time_of_day <= end_time:
            return label

    if time_of_day >= _LATE_NIGHT_START or time_of_day <= _LATE_NIGHT_END:
        return _LATE_NIGHT_LABEL

    return None
