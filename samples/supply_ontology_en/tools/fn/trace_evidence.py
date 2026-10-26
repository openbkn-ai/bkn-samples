"""Business-owned evidence declarations for the supply-chain sample."""

from __future__ import annotations


def bom_intersection_evidence(result: dict) -> dict | None:
    """Declare only a complete structure intersection; never stock or kitting."""
    products, codes = result.get("products"), result.get("shared_codes")
    count = result.get("shared_count")
    if (
        not isinstance(products, list)
        or len(products) < 2
        or any(not isinstance(p, str) or not p.strip() or p != p.strip() for p in products)
        or len(set(products)) != len(products)
        or not isinstance(codes, list)
        or any(not isinstance(c, str) or not c.strip() or c != c.strip() for c in codes)
        or codes != sorted(set(codes))
        or type(count) is not int
        or count != len(codes)
        or count > 5_000
        or "depth" not in result
        or type(result.get("include_substitute")) is not bool
        or (result.get("depth") is not None and (type(result["depth"]) is not int or result["depth"] < 0))
        or result.get("caliber") != "structure_intersect_only"
        or result.get("truncated") is True
        or result.get("partial") is True
    ):
        return None
    content = {key: result[key] for key in (
        "products", "include_substitute", "depth", "shared_codes", "shared_count", "caliber"
    )}
    return {"claim_type": "bom.structure_intersection/v1", "complete": True, "content": content}
