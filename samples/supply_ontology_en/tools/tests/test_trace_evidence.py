"""The sample owns business meaning; platform evidence content is opaque."""

import pytest

from fn import bom_shared_list, load_csv_snapshot
from fn.trace_evidence import bom_intersection_evidence


def test_bom_declaration_matches_real_result_and_zero_is_valid():
    result = bom_shared_list(load_csv_snapshot(), ["382-000005", "P61-000351"])
    evidence = bom_intersection_evidence(result)
    assert evidence["claim_type"] == "bom.structure_intersection/v1"
    assert evidence["complete"] is True
    assert evidence["content"]["shared_count"] == 38
    assert evidence["content"]["shared_codes"] == result["shared_codes"]
    assert "details" not in evidence["content"]
    result.update(shared_codes=[], shared_count=0)
    assert bom_intersection_evidence(result)["content"]["shared_count"] == 0


@pytest.mark.parametrize("patch", [
    {"shared_count": None}, {"shared_count": True}, {"shared_count": 1},
    {"include_substitute": None}, {"shared_codes": ["M", "M"]},
    {"shared_codes": ["Z", "A"], "shared_count": 2}, {"products": ["P", "P"]},
    {"truncated": True}, {"partial": True}, {"caliber": "stock_available"},
])
def test_invalid_business_result_has_no_declaration(patch):
    result = dict(products=["P1", "P2"], include_substitute=False, depth=None,
                  shared_codes=[], shared_count=0, caliber="structure_intersect_only")
    result.update(patch)
    assert bom_intersection_evidence(result) is None
