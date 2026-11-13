"""Kit status values and the date helper shared by the kit check (fn.kitrules) and the plan writer."""

from __future__ import annotations

from typing import Any

KIT_COVERED = "齐套"
KIT_SHORT = "缺料"


def day(value: Any) -> str:
    """Date part of a date or datetime value (``2027-03-01``, ``2027-03-01 08:00:00``, ISO with zone)."""
    text = str(value or "").strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        raise ValueError(f"不是有效日期：{value!r}")
    return text[:10]


__all__ = ["KIT_COVERED", "KIT_SHORT", "day"]
