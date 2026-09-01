"""Knowledge-network dataset requirements for each native function."""

from __future__ import annotations

from collections.abc import Mapping


OPERATION_CONTRACTS: Mapping[str, frozenset[str]] = {
    "bom_list": frozenset({"bom"}),
    "bom_shared_list": frozenset({"bom"}),
    "material_where_used": frozenset({"bom"}),
    "layered_inventory": frozenset({"bom", "inventory"}),
    "substitute_status": frozenset({"bom", "inventory"}),
    "theoretical_build": frozenset({"bom", "inventory"}),
    "total_sellable": frozenset({"bom", "inventory"}),
    "kitting_net_demand": frozenset({"bom", "inventory", "purchase_order"}),
    "shared_contention": frozenset({"bom", "inventory", "purchase_order"}),
    "max_build_without_po": frozenset({"bom", "inventory"}),
    "leadtime_days": frozenset({"material"}),
    "supply_status": frozenset(
        {"material", "inventory", "purchase_order", "purchase_request", "mrp"}
    ),
    "open_forecast_count": frozenset({"forecast"}),
    "backward_plan": frozenset(
        {
            "forecast",
            "bom",
            "material",
            "inventory",
            "purchase_order",
            "purchase_request",
            "mrp",
        }
    ),
}


def required_datasets(operation_id: str) -> frozenset[str]:
    try:
        return OPERATION_CONTRACTS[operation_id]
    except KeyError as exc:
        raise KeyError(f"unknown operation: {operation_id}") from exc
