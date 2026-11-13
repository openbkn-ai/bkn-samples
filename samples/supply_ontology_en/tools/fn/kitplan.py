"""Kit status values and the date helper shared by the kit check (fn.kitrules) and the plan writer."""

from __future__ import annotations

from typing import Any

KIT_COVERED = "Covered"
KIT_SHORT = "Short"
# Short at the start only by materials whose purchase request, placed now, arrives in time.
KIT_PENDING = "Covered (Order Pending)"


def day(value: Any) -> str:
    """Date part of a date or datetime value (``2027-03-01``, ``2027-03-01 08:00:00``, ISO with zone)."""
    text = str(value or "").strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        raise ValueError(f"not a valid date: {value!r}")
    return text[:10]


__all__ = ["KIT_COVERED", "KIT_PENDING", "KIT_SHORT", "day"]
