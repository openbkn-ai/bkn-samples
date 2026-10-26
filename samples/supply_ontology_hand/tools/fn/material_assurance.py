"""Stock-only material coverage and non-executable replenishment proposals."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from .allocation import finite_quantity, net_requirements
from .bom import classify_bom_row, is_main_row, product_bom_rows
from .errors import CannotCompute
from .warehouse import resolve_warehouse_scope

MODEL_VERSION = "material-assurance.stock-only.v1"
PURPOSES = {"customer_delivery", "new_production"}


def validate_inputs(product, qty, demand_purpose, warehouse_scope="all"):
    if not isinstance(product, str) or not product.strip():
        raise CannotCompute("product must be a nonempty product code")
    if isinstance(qty, bool) or not isinstance(qty, (int, float)):
        raise CannotCompute("qty must be a positive integer number of kits")
    quantity = finite_quantity(qty, "qty", positive=True)
    if not quantity.is_integer() or quantity > 2**53:
        raise CannotCompute("qty must be an exactly representable integer number of kits")
    if not isinstance(demand_purpose, str) or demand_purpose not in PURPOSES:
        raise CannotCompute("demand_purpose must be customer_delivery or new_production")
    if warehouse_scope is None or warehouse_scope == "" or warehouse_scope == []:
        raise CannotCompute("warehouse_scope must be all, a known preset or a nonempty warehouse list")
    if isinstance(warehouse_scope, list) and any(not isinstance(w, str) or not w.strip() for w in warehouse_scope):
        raise CannotCompute("warehouse list entries must be nonempty names")
    resolve_warehouse_scope(warehouse_scope)
    return int(quantity)


def _digest(rows):
    canonical = sorted(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) for row in rows)
    return "sha256:" + hashlib.sha256("\n".join(canonical).encode()).hexdigest()


def material_coverage(snap, product, qty, *, demand_purpose, warehouse_scope="all"):
    quantity = validate_inputs(product, qty, demand_purpose, warehouse_scope)
    product = product.strip()
    bom = product_bom_rows(snap, product)
    if not bom:
        raise CannotCompute("complete product BOM is required")
    versions = {str(row.get("bom_version") or "").strip() for row in bom}
    if "" in versions or len(versions) != 1:
        raise CannotCompute("BOM must contain one explicit source version; mixed or missing versions cannot be combined")
    mains = {(str(r.get("parent_material_code") or product).strip(), str(r.get("alt_group_no") or "").strip())
             for r in bom if classify_bom_row(r) == "group_main"}
    for row in bom:
        if classify_bom_row(row) == "substitute":
            key = (str(row.get("parent_material_code") or product).strip(), str(row.get("alt_group_no") or "").strip())
            if key not in mains:raise CannotCompute("replacement candidate has no main in its parent/group")
    include_finished = demand_purpose == "customer_delivery"
    def allocate(amount):
        return net_requirements(snap, product, amount, scope=warehouse_scope,
                                substitute_enabled=False, include_finished_goods=include_finished)
    allocation = allocate(quantity)
    if not float(allocation["finished_goods_allocated_qty"]).is_integer():
        raise CannotCompute("finished-goods inventory must represent whole kits")
    # Search only up to this demand, rather than presenting unlimited theoretical
    # capacity as coverage. Each trial gets a fresh request-local inventory pool.
    low, high = 0, quantity
    while low < high:
        mid = (low + high + 1) // 2
        if allocate(mid)["feasible"]:
            low = mid
        else:
            high = mid - 1
    grouped = defaultdict(list)
    for line in allocation["lines"]:
        if line["is_leaf"] and line["net_requirement"] > 1e-9:
            grouped[line["material_code"]].append(line)
    gaps = [{"material_code": code, "material_name": lines[0]["material_name"],
             "shortage_qty": sum(line["net_requirement"] for line in lines),
             "positions": lines} for code, lines in sorted(grouped.items())]
    codes = {product} | {str(r.get("material_code") or "").strip() for r in bom if is_main_row(r)}
    warehouses = resolve_warehouse_scope(warehouse_scope)
    inventory = [r for r in snap.inventory if r.get("material_code") in codes
                 and (not warehouses or r.get("warehouse") in warehouses)]
    provenance = {"bom_version": next(iter(versions)), "bom_row_count": len(bom),
                  "bom_primary_row_count": sum(is_main_row(r) for r in bom),
                  "bom_digest": _digest(bom), "inventory_row_count": len(inventory),
                  "inventory_digest": _digest(inventory),
                  "data_collected_at": datetime.now(timezone.utc).isoformat(),
                  "collection_semantics": "live reads are not a transactional database snapshot"}
    finished = allocation["finished_goods_allocated_qty"]
    return {"model_version": MODEL_VERSION, "product_code": product,
            "demand_purpose": demand_purpose, "demand_qty": quantity,
            "covered_qty": low, "uncovered_qty": quantity - low,
            "fully_covered": low == quantity, "finished_goods_allocated_qty": finished,
            "manufacturing_covered_qty": low - finished,
            "requested_assembly_qty": allocation["root_net_demand"],
            "warehouse_scope": warehouse_scope, "warehouse_filter": warehouses,
            "substitute_enabled": False, "include_in_transit": False,
            "gaps": gaps, "allocations": allocation["lines"], "provenance": provenance,
            "not_evaluated": ["delivery_date", "production_capacity", "supplier", "cost", "MOQ", "safety_stock"]}


def replenishment_draft(coverage):
    """Return a proposal only; never persist it or contact a business system."""
    if not isinstance(coverage, dict) or coverage.get("model_version") != MODEL_VERSION:
        raise CannotCompute("draft requires a material-assurance coverage result")
    quantity = validate_inputs(coverage.get("product_code"), coverage.get("demand_qty"), coverage.get("demand_purpose"), coverage.get("warehouse_scope"))
    if isinstance(coverage.get("covered_qty"), bool):raise CannotCompute("covered_qty must be numeric")
    covered = finite_quantity(coverage.get("covered_qty"), "covered_qty")
    if not covered.is_integer() or covered > quantity or coverage.get("uncovered_qty") != quantity-covered:
        raise CannotCompute("draft coverage quantities are inconsistent")
    provenance = coverage.get("provenance")
    if not isinstance(provenance, dict) or not provenance.get("bom_version") or not provenance.get("data_collected_at"):
        raise CannotCompute("draft is missing source provenance")
    for field in ("bom_digest", "inventory_digest"):
        if not isinstance(provenance.get(field), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", provenance[field]):
            raise CannotCompute("draft source digest is missing or invalid")
    if not isinstance(coverage.get("gaps"), list):raise CannotCompute("draft gaps must be a complete list")
    seen = set()
    for gap in coverage["gaps"]:
        if not isinstance(gap, dict) or not isinstance(gap.get("material_code"), str) or not gap["material_code"].strip():
            raise CannotCompute("draft gap material identity is missing")
        if gap["material_code"] in seen:raise CannotCompute("draft gaps contain duplicate materials")
        seen.add(gap["material_code"])
        if isinstance(gap.get("shortage_qty"), bool) or not isinstance(gap.get("shortage_qty"), (int, float)):raise CannotCompute("draft shortage quantity is invalid")
        finite_quantity(gap.get("shortage_qty"), "shortage_qty", positive=True)
    if (covered == quantity) != (not coverage["gaps"]):raise CannotCompute("draft gaps conflict with coverage status")
    if coverage.get("fully_covered") is not (covered == quantity):raise CannotCompute("draft coverage status is inconsistent")
    items = [{"material_code": gap["material_code"], "quantity": gap["shortage_qty"]}
             for gap in coverage["gaps"]]
    basis = {key: coverage[key] for key in ("model_version", "product_code", "demand_purpose", "demand_qty", "warehouse_scope")}
    stable_coverage = copy.deepcopy(coverage)
    for field in ("data_collected_at", "query_started_at", "query_completed_at"):
        stable_coverage["provenance"].pop(field, None)
    basis["supplied_coverage_digest"] = _digest([stable_coverage])
    basis.update(bom_digest=coverage["provenance"]["bom_digest"],
                 inventory_digest=coverage["provenance"]["inventory_digest"], items=items)
    return {"draft_id": "material-replenishment-" + _digest([basis]).split(":")[1],
            "status": "draft", "persisted": False, "executable": False,
            "items": items, "coverage": coverage,
            "basis_validation": "structure_only_not_requeried",
            "supplied_coverage_digest": basis["supplied_coverage_digest"],
            "unresolved_inputs": ["delivery_date", "production_capacity", "supplier", "cost", "MOQ", "safety_stock"]}
