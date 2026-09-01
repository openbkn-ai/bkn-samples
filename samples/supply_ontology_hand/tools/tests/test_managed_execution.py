"""Contracts for run_code-managed supply calculation execution."""

import pytest

from fn.contracts import OPERATION_CONTRACTS
from support_bkn_rows import bkn_rows


def test_every_operation_has_a_bkn_managed_query_plan():
    from managed_execution import managed_query_plan

    for operation, datasets in OPERATION_CONTRACTS.items():
        plan = managed_query_plan(operation)

        assert plan.operation == operation
        assert set(plan.datasets) == set(datasets)
        assert {item.dataset for item in plan.requirements} == set(datasets)
        assert all(item.object_type_id.startswith("supply_ontology_hand_") for item in plan.requirements)


def test_managed_query_plan_has_no_caller_owned_context_payload():
    from managed_execution import managed_query_plan

    plan = managed_query_plan("backward_plan")

    assert not hasattr(plan, "resolved_context")
    assert not hasattr(plan, "snapshot_id")
    assert plan.execution_host == "native_function_sandbox"


def test_backward_plan_plan_declares_its_complete_bkn_fact_set():
    from managed_execution import managed_query_plan

    plan = managed_query_plan("backward_plan")

    assert [item.dataset for item in plan.requirements] == [
        "forecast",
        "bom",
        "material",
        "inventory",
        "purchase_order",
        "purchase_request",
        "mrp",
    ]


def test_managed_execution_runs_backward_plan_from_internal_bkn_rows():
    from managed_execution import execute_from_bkn_rows

    result = execute_from_bkn_rows(
        "backward_plan",
        bkn_rows(),
        {
            "product": "U00-000080",
            "forecast_id": "0000023181",
            "demand_end": "2026-05-31",
            "demand_qty": 3000,
            "substitute_enabled": False,
        },
    )

    assert result["business_date"] == "2026-08-25"
    assert result["max_delay_days"] == 176


def test_forecast_mode_needs_no_agent_copied_product_quantity_or_due_date():
    from managed_execution import execute_from_bkn_rows

    result = execute_from_bkn_rows(
        "backward_plan",
        bkn_rows(),
        {"forecast_id": "0000023181", "substitute_enabled": False},
    )

    assert result["product_code"] == "U00-000080"
    assert result["demand_qty"] == 3000
    assert result["demand_end"] == "2026-05-31"


def test_managed_execution_runs_bom_list_from_internal_bkn_rows():
    from managed_execution import execute_from_bkn_rows

    result = execute_from_bkn_rows(
        "bom_list",
        bkn_rows(),
        {"product": "382-000005", "depth": 1, "include_substitute": False},
    )

    assert result["product_code"] == "382-000005"
    assert result["l1_main_count"] == 9


def test_shared_contention_rejects_string_demands_before_querying_bkn():
    from managed_execution import load_bkn_rows

    def must_not_query(**_kwargs):
        raise AssertionError("invalid demands must not trigger a BKN query")

    with pytest.raises(ValueError, match="demands"):
        load_bkn_rows(
            "shared_contention",
            must_not_query,
            {
                "demands": ["382-000005:50", "P61-000351:60"],
                "substitute_enabled": False,
            },
        )


def test_backward_plan_rejects_missing_product_before_querying_bkn():
    from managed_execution import load_bkn_rows

    def must_not_query(**_kwargs):
        raise AssertionError("invalid backward plan must not trigger a BKN query")

    with pytest.raises(ValueError, match="product"):
        load_bkn_rows(
            "backward_plan",
            must_not_query,
            {
                "demand_qty": 3000,
                "demand_end": "2026-05-31",
                "substitute_enabled": False,
            },
        )
