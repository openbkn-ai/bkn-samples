"""BKN fact requirements for calculations executed inside native Functions.

The caller supplies business parameters only. The native Function uses this
plan to query the knowledge network through ``sandbox_sdk.bkn``,
keeps rows in its sandbox, and then invokes the tested pure calculation module.
It deliberately has no
``resolved_context`` or caller-managed snapshot contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections.abc import Callable, Mapping
from typing import Any

from fn.contracts import OPERATION_CONTRACTS
from fn.leadtime import leadtime_details
from fn.bom import is_main_row
from fn import (
    CannotCompute,
    backward_plan,
    bom_list,
    bom_shared_list,
    kitting_net_demand,
    layered_inventory,
    max_build_without_po,
    material_where_used,
    open_forecast_count,
    shared_contention,
    substitute_status,
    supply_status,
    theoretical_build,
    total_sellable,
)
from fn.material_assurance import material_coverage, replenishment_draft, validate_inputs
from fn.read_complete import read_complete
from fn.snapshot import build_snapshot
from fn.warehouse import resolve_warehouse_scope


@dataclass(frozen=True)
class QueryRequirement:
    """One logical calculation dataset and its knowledge-network object type."""

    dataset: str
    object_type_id: str


@dataclass(frozen=True)
class ManagedQueryPlan:
    """Facts a native Function must acquire internally from the BKN."""

    operation: str
    requirements: tuple[QueryRequirement, ...]
    execution_host: str = "native_function_sandbox"

    @property
    def datasets(self) -> tuple[str, ...]:
        return tuple(requirement.dataset for requirement in self.requirements)


_OBJECT_TYPES = {
    "bom": "supply_ontology_hand_bom",
    "inventory": "supply_ontology_hand_inventory",
    "material": "supply_ontology_hand_material",
    "purchase_order": "supply_ontology_hand_po",
    "purchase_request": "supply_ontology_hand_pr",
    "mrp": "supply_ontology_hand_mrp",
    "forecast": "supply_ontology_hand_forecast",
    "product": "supply_ontology_hand_product",
}

KN_ID = "supply_ontology_hand"
_PAGE_SIZE = 500
_MAX_ROWS_PER_DATASET = 5_000


def managed_query_plan(operation: str) -> ManagedQueryPlan:
    """Return the BKN facts an operation loads within its Function sandbox."""
    try:
        datasets = OPERATION_CONTRACTS[operation]
    except KeyError as exc:
        raise KeyError(f"unknown operation: {operation}") from exc
    return ManagedQueryPlan(
        operation=operation,
        requirements=tuple(
            QueryRequirement(dataset=dataset, object_type_id=_OBJECT_TYPES[dataset])
            for dataset in _ordered_datasets(datasets)
        ),
    )


def load_bkn_rows(
    operation: str,
    query_object_instance: Callable[..., Mapping[str, Any]],
    parameters: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Load the facts an operation needs through ``sandbox_sdk.bkn``.

    The Function owns its reads: callers provide business parameters only.
    The injected callable is normally ``bkn.query_object_instance``; keeping it
    explicit makes the query shape independently testable without credentials.
    """
    if operation == "shortage_rule":raise CannotCompute("shortage_rule requires its dedicated native event adapter")
    params = dict(parameters or {})
    _validate_operation_parameters(operation, params)
    if operation == "material_coverage":
        def complete(dataset, condition):
            return read_complete(query_object_instance, {"kn_id": KN_ID, "ot_id": _OBJECT_TYPES[dataset], "condition": condition}, _page_rows,
                                 page_size=_PAGE_SIZE, max_rows=_MAX_ROWS_PER_DATASET)
        product = str(params["product"]).strip()
        bom = complete("bom", _equal_condition("bom_material_code", product))
        codes = {product} | {str(r.get("material_code") or "").strip() for r in bom if _is_main_bom_row(r)}
        inventory = complete("inventory", _in_condition("material_code", sorted(codes)))
        return {"bom": bom, "inventory": inventory}
    rows_by_dataset: dict[str, list[dict[str, Any]]] = {}
    product_codes = _product_codes(operation, params)
    material_codes = set(product_codes)
    for requirement in managed_query_plan(operation).requirements:
        dataset = requirement.dataset
        if dataset == "forecast" and operation == "backward_plan" and params.get("forecast_id"):
            forecast_id = str(params["forecast_id"]).strip()
            collected = _load_forecast_by_id(query_object_instance, forecast_id)
            forecast_product = str(collected[0].get("material_number") or "").strip()
            if not forecast_product:
                raise CannotCompute(f"预测单 {forecast_id} 缺少产品编码")
            if product_codes and product_codes != {forecast_product}:
                raise CannotCompute(f"预测单 {forecast_id} 的产品为 {forecast_product}，与请求产品不一致")
            product_codes = {forecast_product}
            material_codes.update(product_codes)
        elif dataset == "bom" and operation == "material_where_used":
            collected = _load_bom_ancestor_rows(
                query_object_instance,
                str(params.get("material_code") or "").strip(),
            )
        elif dataset == "bom" and operation == "substitute_status" and params.get("material_code"):
            collected = _load_bom_rows_for_material_substitutes(
                query_object_instance,
                str(params.get("material_code") or "").strip(),
            )
            # A material-level substitution check must load inventory for every
            # member of the matched alternate groups, not only the material the
            # caller named.  Otherwise the relationship is correct but every
            # alternate appears to have zero available stock.
            material_codes.update(
                str(row.get("material_code") or "").strip()
                for row in collected
                if str(row.get("material_code") or "").strip()
            )
        elif dataset == "bom" and product_codes:
            # The sample's BOM resource stores each complete multi-level tree
            # under its root product.  One root-key query is both exact and
            # bounded; recursive parent ``IN`` queries become slow for a wide
            # level even when the finished BOM itself is modest (for example
            # product 382-000005 has 399 primary lines).
            collected = _load_root_bom_rows(
                query_object_instance,
                product_codes,
            )
            material_codes.update(
                str(row.get("material_code") or "").strip()
                for row in collected
                if str(row.get("material_code") or "").strip()
                and (_include_substitute_branch(operation, params) or _is_main_bom_row(row))
            )
        elif dataset == "inventory" and operation == "substitute_status" and params.get("material_code"):
            # The alternate set is deliberately small.  Query each candidate
            # exactly: some BKN data resources do not apply a multi-value `in`
            # condition on inventory consistently, which would otherwise scan
            # the whole inventory table and trip the safety bound.
            collected = []
            for material_code in sorted(material_codes):
                collected.extend(
                    _query_rows(
                        query_object_instance,
                        requirement.object_type_id,
                        _equal_condition("material_code", material_code),
                    )
                )
        else:
            collected = _load_dataset_rows(
                operation,
                dataset,
                requirement.object_type_id,
                query_object_instance,
                params,
                material_codes,
            )
        rows_by_dataset[dataset] = collected
        if (
            operation == "backward_plan"
            and dataset == "forecast"
            and not product_codes
        ):
            product_codes.update(
                str(row.get("material_number") or "").strip()
                for row in collected
                if str(row.get("material_number") or "").strip()
            )
            material_codes.update(product_codes)
    return rows_by_dataset


def _load_forecast_by_id(query_object_instance, forecast_id: str) -> list[dict[str, Any]]:
    """Prefer the exact business ID; only fall back for legacy numeric keys."""
    rows = _query_rows(query_object_instance, _OBJECT_TYPES["forecast"], _equal_condition("id", forecast_id))
    canonical = _canonical_document_id(forecast_id)
    if not rows and canonical != forecast_id:
        rows = _query_rows(query_object_instance, _OBJECT_TYPES["forecast"], _equal_condition("id", canonical))
    if not rows:
        raise CannotCompute(f"预测单不存在：{forecast_id}")
    if len(rows) != 1:
        raise CannotCompute(f"预测单 ID 匹配不唯一：{forecast_id}")
    return rows


def _validate_operation_parameters(operation: str, params: Mapping[str, Any]) -> None:
    """Reject malformed business inputs before a Function reads BKN facts."""
    if operation == "material_coverage":
        validate_inputs(params.get("product"), params.get("qty"), params.get("demand_purpose"), params.get("warehouse_scope", "all"))
    elif operation == "shared_contention":
        demands = params.get("demands")
        if not isinstance(demands, list) or len(demands) < 2:
            raise ValueError(
                "demands 必须是至少两项的对象数组："
                '[{"product":"产品编码","qty":数量}, ...]'
            )
        for index, demand in enumerate(demands, start=1):
            if not isinstance(demand, Mapping):
                raise ValueError(
                    f"demands[{index}] 必须是对象，格式为 "
                    '{"product":"产品编码","qty":数量}'
                )
            product = demand.get("product") or demand.get("product_code")
            qty = demand.get("qty", demand.get("demand_qty"))
            if not isinstance(product, str) or not product.strip():
                raise ValueError(f"demands[{index}].product 不能为空")
            if isinstance(qty, bool) or not isinstance(qty, (int, float)):
                raise ValueError(f"demands[{index}].qty 必须是数值")
    elif operation == "backward_plan":
        required = {"substitute_enabled": "替代料策略 substitute_enabled"}
        if not str(params.get("forecast_id") or "").strip():
            required.update(
                {
                    "product": "产品编码 product",
                    "demand_qty": "需求数量 demand_qty",
                    "demand_end": "交付截止日 demand_end",
                }
            )
        for field, label in required.items():
            value = params.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"生产计划齐套倒排缺少必填参数：{label}")
        if not str(params.get("forecast_id") or "").strip():
            if isinstance(params.get("demand_qty"), bool) or not isinstance(
                params.get("demand_qty"), (int, float)
            ):
                raise ValueError("生产计划齐套倒排的 demand_qty 必须是数值")
        if not isinstance(params.get("substitute_enabled"), bool):
            raise ValueError("生产计划齐套倒排的 substitute_enabled 必须为 true 或 false")


def _load_dataset_rows(
    operation: str,
    dataset: str,
    object_type_id: str,
    query_object_instance: Callable[..., Mapping[str, Any]],
    params: Mapping[str, Any],
    material_codes: set[str],
) -> list[dict[str, Any]]:
    """Load one logical dataset through bounded, server-side business filters."""
    collected: list[dict[str, Any]] = []
    for condition in _dataset_conditions(operation, dataset, params, material_codes):
        remaining = _MAX_ROWS_PER_DATASET - len(collected)
        if remaining <= 0:
            raise ValueError(f"{object_type_id} 查询结果超过 {_MAX_ROWS_PER_DATASET} 行，请缩小业务范围后重试")
        collected.extend(
            _query_rows(
                query_object_instance,
                object_type_id,
                condition,
                max_rows=remaining,
            )
        )
    return collected


def _query_rows(
    query_object_instance: Callable[..., Mapping[str, Any]],
    object_type_id: str,
    condition: Mapping[str, Any] | None,
    *,
    max_rows: int = _MAX_ROWS_PER_DATASET,
) -> list[dict[str, Any]]:
    """Read one bounded, server-filtered object collection."""
    collected: list[dict[str, Any]] = []
    offset = 0
    search_after: list[Any] | None = None
    while len(collected) < max_rows:
        query: dict[str, Any] = {
            "kn_id": KN_ID,
            "ot_id": object_type_id,
            "limit": min(_PAGE_SIZE, max_rows - len(collected)),
        }
        if condition:
            query["condition"] = dict(condition)
        if search_after:
            query["search_after"] = search_after
        else:
            query["offset"] = offset
        page = dict(query_object_instance(**query) or {})
        page_rows = _page_rows(page)
        if not page_rows:
            break
        collected.extend(page_rows)
        # A short page is complete regardless of a stale / advisory
        # ``search_after`` value returned by the backing resource.  Checking
        # this before cursor continuation prevents repeated reads of the same
        # short page and preserves the Interaction operation budget.
        if len(page_rows) < query["limit"]:
            break
        search_after = page.get("search_after") or None
        if search_after:
            continue
        offset += len(page_rows)
    if len(collected) >= max_rows:
        raise ValueError(f"{object_type_id} 查询结果超过 {_MAX_ROWS_PER_DATASET} 行，请缩小业务范围后重试")
    return collected


def _load_root_bom_rows(
    query_object_instance: Callable[..., Mapping[str, Any]],
    roots: set[str],
) -> list[dict[str, Any]]:
    """Read the denormalized BOM tree once by its root product code."""
    values = sorted(roots)
    condition = (
        _equal_condition("bom_material_code", values[0])
        if len(values) == 1
        else _in_condition("bom_material_code", values)
    )
    return _query_rows(query_object_instance, _OBJECT_TYPES["bom"], condition)


def _load_bom_rows_by_material(
    query_object_instance: Callable[..., Mapping[str, Any]], material_code: str
) -> list[dict[str, Any]]:
    if not material_code:
        raise ValueError("物料反查产品缺少物料编码 material_code")
    return _query_rows(
        query_object_instance,
        _OBJECT_TYPES["bom"],
        _equal_condition("material_code", material_code),
    )


def _load_bom_ancestor_rows(query_object_instance, material_code: str) -> list[dict[str, Any]]:
    """Acquire parent links as well as direct hits for non-expanded BOMs."""
    pending = [material_code]
    seen = set()
    rows = []
    identities = set()
    while pending:
        child = pending.pop(0)
        if not child or child in seen:
            continue
        seen.add(child)
        for row in _load_bom_rows_by_material(query_object_instance, child):
            identity = tuple(sorted((key, repr(value)) for key, value in row.items()))
            if identity not in identities:
                identities.add(identity)
                rows.append(row)
                if len(rows) > _MAX_ROWS_PER_DATASET:
                    raise CannotCompute("物料反查结果超过安全上限，请缩小范围")
            parent = str(row.get("parent_material_code") or "").strip()
            if parent and parent not in seen:
                pending.append(parent)
    return rows


def _load_bom_rows_for_material_substitutes(
    query_object_instance: Callable[..., Mapping[str, Any]], material_code: str
) -> list[dict[str, Any]]:
    matches = _load_bom_rows_by_material(query_object_instance, material_code)
    group_keys = {
        (
            str(row.get("bom_material_code") or "").strip(),
            str(row.get("parent_material_code") or "").strip(),
            str(row.get("alt_group_no") or "").strip(),
        )
        for row in matches
        if str(row.get("alt_group_no") or "").strip()
    }
    roots = {
        str(row.get("bom_material_code") or "").strip()
        for row in matches
        if str(row.get("bom_material_code") or "").strip()
    }
    if not roots or not group_keys:
        return matches
    # The root query returns the whole denormalized BOM tree.  Keep only the
    # exact alternate groups that contain the requested material; inventory
    # must not be fetched for unrelated nodes in the same product tree.
    return [
        row
        for row in _load_root_bom_rows(query_object_instance, roots)
        if (
            str(row.get("bom_material_code") or "").strip(),
            str(row.get("parent_material_code") or "").strip(),
            str(row.get("alt_group_no") or "").strip(),
        )
        in group_keys
    ]


def _is_main_bom_row(row: Mapping[str, Any]) -> bool:
    """Use the same primary rule for inventory acquisition and calculation.

    ERP marks the whole replacement group alt_method=替代, including its
    priority-zero main. Excluding those mains here silently removes their
    component and raw-material inventory while retaining their BOM demand.
    """
    return is_main_row(dict(row))


def _include_substitute_branch(operation: str, params: Mapping[str, Any]) -> bool:
    """Only traverse alternate BOM branches when that operation explicitly needs them."""
    if operation == "substitute_status":
        return True
    if operation in {"bom_list", "bom_shared_list", "layered_inventory"}:
        return bool(params.get("include_substitute"))
    return bool(params.get("substitute_enabled"))


def _product_codes(operation: str, params: Mapping[str, Any]) -> set[str]:
    # A single-material function must not fall through to unfiltered reads.
    # ``product_code`` is also accepted by the forecast-count contract.
    values: list[Any] = [
        params.get("product"),
        params.get("product_code"),
        params.get("material_code"),
    ]
    if operation == "bom_shared_list":
        values.extend(params.get("products") or [])
    if operation == "shared_contention":
        values.extend(
            item.get("product") or item.get("product_code")
            for item in (params.get("demands") or [])
            if isinstance(item, Mapping)
        )
    return {str(value).strip() for value in values if str(value or "").strip()}


def _dataset_conditions(
    operation: str,
    dataset: str,
    params: Mapping[str, Any],
    material_codes: set[str],
) -> tuple[dict[str, Any] | None, ...]:
    if dataset == "forecast":
        forecast_id = str(params.get("forecast_id") or "").strip()
        if forecast_id:
            return (_equal_condition("id", forecast_id),)
        product_code = str(params.get("product_code") or params.get("product") or "").strip()
        if product_code:
            return (_equal_condition("material_number", product_code),)
        return (None,)
    field_by_dataset = {
        "material": "material_code",
        "inventory": "material_code",
        "purchase_order": "material_number",
        "purchase_request": "material_number",
        "mrp": "materialplanid_number",
    }
    field = field_by_dataset.get(dataset)
    if field and material_codes:
        return (
            _scoped_dataset_condition(
                operation,
                dataset,
                params,
                _in_condition(field, sorted(material_codes)),
            ),
        )
    return (None,)


def _scoped_dataset_condition(
    operation: str,
    dataset: str,
    params: Mapping[str, Any],
    material_condition: dict[str, Any],
) -> dict[str, Any]:
    """Add only filters that are semantically required by the operation."""
    conditions: list[dict[str, Any]] = [material_condition]
    if dataset == "inventory" and operation in {"kitting_net_demand", "backward_plan"}:
        warehouses = resolve_warehouse_scope(params.get("warehouse_scope", "all"))
        if warehouses:
            conditions.append(_in_condition("warehouse", warehouses))
        conditions.append(_equal_condition("stock_status", "可用"))
    if dataset in {"purchase_order", "purchase_request"} and operation in {"kitting_net_demand", "backward_plan"}:
        conditions.append(_not_equal_condition("rowclosestatus_title", "已关闭"))
    if dataset == "mrp" and operation == "backward_plan":
        conditions.append(_not_equal_condition("closestatus_title", "已关闭"))
    return _and_condition(conditions)


def _equal_condition(field: str, value: str) -> dict[str, Any]:
    return {"field": field, "operation": "==", "value": value, "value_from": "const"}


def _in_condition(field: str, values: list[str]) -> dict[str, Any]:
    return {"field": field, "operation": "in", "value": values, "value_from": "const"}


def _not_equal_condition(field: str, value: str) -> dict[str, Any]:
    return {"field": field, "operation": "!=", "value": value, "value_from": "const"}


def _and_condition(conditions: list[dict[str, Any]]) -> dict[str, Any]:
    if len(conditions) == 1:
        return conditions[0]
    return {"operation": "and", "sub_conditions": conditions}


def _canonical_document_id(value: str) -> str:
    """Legacy fallback only; exact business IDs must be queried first."""
    return str(int(value)) if value.isdigit() else value


def _page_rows(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize documented and legacy Context Loader row envelopes."""
    for key in ("datas", "data", "rows"):
        rows = page.get(key)
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _ordered_datasets(datasets: frozenset[str]) -> tuple[str, ...]:
    """Keep generated run_code plans deterministic and dependency-oriented."""
    order = (
        "forecast",
        "product",
        "bom",
        "material",
        "inventory",
        "purchase_order",
        "purchase_request",
        "mrp",
    )
    return tuple(dataset for dataset in order if dataset in datasets)


def execute_from_bkn_rows(
    operation: str, rows: Mapping[str, Any], parameters: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute one tested calculation using facts already read in ``run_code``.

    ``rows`` stays inside the Context Loader sandbox.  This adapter intentionally
    accepts neither trace IDs nor a caller assembled context payload.
    """
    if operation not in OPERATION_CONTRACTS:
        raise KeyError(f"unknown operation: {operation}")
    if operation == "shortage_rule":raise CannotCompute("shortage_rule requires its dedicated native event adapter")
    params = dict(parameters)
    snapshot = build_snapshot(dict(rows))
    product = params.get("product")
    scope = params.get("warehouse_scope", "all")
    substitute = params.get("substitute_enabled")
    if operation == "replenishment_draft":
        return {**replenishment_draft(params.get("coverage")), "action_type_id": KN_ID + "_act_replen_draft"}
    if operation == "material_coverage":
        return material_coverage(snapshot, product, params.get("qty"), demand_purpose=params.get("demand_purpose"), warehouse_scope=scope)
    if operation == "bom_list":
        return bom_list(
            snapshot,
            product,
            depth=params.get("depth", 1),
            include_substitute=params.get("include_substitute", False),
            report_grain=params.get("report_grain", "summary"),
            page_size=params.get("page_size", 100),
            offset=params.get("offset", 0),
        )
    if operation == "bom_shared_list":
        return bom_shared_list(snapshot, params.get("products") or [], depth=params.get("depth"), include_substitute=params.get("include_substitute", False))
    if operation == "material_where_used":
        return material_where_used(
            snapshot,
            params.get("material_code"),
            report_grain=params.get("report_grain", "summary"),
            include_substitute=params.get("include_substitute", True),
        )
    if operation == "layered_inventory":
        return layered_inventory(snapshot, product, depth=params.get("depth", 1), warehouse_scope=scope, include_substitute=params.get("include_substitute", False))
    if operation == "substitute_status":
        return substitute_status(
            snapshot,
            product,
            material_code=params.get("material_code"),
            warehouse_scope=scope,
            substitute_enabled=substitute,
        )
    if operation == "theoretical_build":
        return theoretical_build(
            snapshot,
            product,
            warehouse_scope=scope,
            substitute_enabled=substitute,
            report_grain=params.get("report_grain", "summary"),
        )
    if operation == "total_sellable":
        return total_sellable(snapshot, product, production_scope=params.get("production_scope", "all"), finished_goods_scope=params.get("finished_goods_scope", "all"), substitute_enabled=substitute)
    if operation == "kitting_net_demand":
        return kitting_net_demand(
            snapshot,
            product,
            params.get("qty"),
            warehouse_scope=scope,
            substitute_enabled=substitute,
            report_grain=params.get("report_grain", "summary"),
        )
    if operation == "shared_contention":
        return shared_contention(
            snapshot,
            params.get("demands") or [],
            warehouse_scope=scope,
            substitute_enabled=substitute,
            report_grain=params.get("report_grain", "summary"),
        )
    if operation == "max_build_without_po":
        return max_build_without_po(
            snapshot,
            product,
            warehouse_scope=scope,
            substitute_enabled=substitute,
            report_grain=params.get("report_grain", "summary"),
        )
    if operation == "leadtime_days":
        material_code = params.get("material_code")
        return {**leadtime_details(snapshot, material_code), "object_type_id": _OBJECT_TYPES["material"]}
    if operation == "supply_status":
        return supply_status(snapshot, params.get("material_code"), due_date=params.get("due_date"), gross_requirement=params.get("gross_requirement", 0), warehouse_scope=scope, child_short=params.get("child_short", False), today=date.fromisoformat(params.get("business_date", "2026-08-25")))
    if operation == "open_forecast_count":
        return open_forecast_count(
            rows.get("forecast") or [],
            product_code=params.get("product_code"),
            report_grain=params.get("report_grain", "summary"),
        )
    return backward_plan(snapshot, product, forecast_id=params.get("forecast_id"), demand_end=params.get("demand_end"), demand_qty=params.get("demand_qty"), business_date=params.get("business_date"), warehouse_scope=scope, substitute_enabled=substitute, report_grain=params.get("report_grain", "summary"))


__all__ = [
    "ManagedQueryPlan",
    "QueryRequirement",
    "execute_from_bkn_rows",
    "load_bkn_rows",
    "managed_query_plan",
]
