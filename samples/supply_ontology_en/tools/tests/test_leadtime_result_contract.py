"""Regression coverage for issue #63: selected field and business provenance."""

import pytest

from fn.leadtime import leadtime_days
from fn.snapshot import build_snapshot
from managed_execution import execute_from_bkn_rows


@pytest.mark.parametrize("attribute,days,caliber,field", [
    ('Purchased', 14, "purchase", "purchase_fixedleadtime"),
    ('Subcontracted', 14, "purchase", "purchase_fixedleadtime"),
    ('Manufactured', 1, "production", "product_fixedleadtime"),
    (None, 1, "production", "product_fixedleadtime"),
])
def test_leadtime_result_declares_the_field_actually_used(attribute, days, caliber, field):
    rows = {"material": [{"material_code": "MAT-1", "materialattr": attribute,
                          "purchase_fixedleadtime": 14, "product_fixedleadtime": 1}]}
    result = execute_from_bkn_rows("leadtime_days", rows, {"material_code": "MAT-1"})
    assert result["material_code"] == "MAT-1"
    assert result["leadtime_days"] == leadtime_days(build_snapshot(rows), "MAT-1") == days
    assert result["caliber"] == caliber
    assert result["source_field"] == field
    assert result["material_attribute"] == attribute
    assert result["attribute_missing"] is (attribute is None)
    assert result["object_type_id"] == "supply_ontology_en_material"
    assert result["unit"] == "day"
