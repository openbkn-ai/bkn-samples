"""The discovery surface must explain executable IDs and result completeness."""
from function_catalog import FUNCTION_CATALOG
from register_native_function_toolbox import _operation_inputs

def test_discovered_functions_explain_exact_id_and_exit_status_contract():
    for spec in FUNCTION_CATALOG.values():
        text=spec['use_rule']
        assert 'toolbox_id=owner_id' in text
        assert 'tool_id=capability_id' in text
        assert 'exit_code' in text
        assert '01a17' not in text

def test_coverage_summary_already_has_complete_shortage_quantities():
    text=FUNCTION_CATALOG['kitting_net_demand']['description']
    assert 'summary' in text and 'gaps' in text and 'net_requirement' in text
    assert 'lines' in text and 'full' in text
    grain=next(x for x in _operation_inputs('kitting_net_demand') if x['name']=='report_grain')['description']
    assert 'gaps' in grain and 'quantities' in grain

def test_position_alternatives_are_targeted_and_never_character_truncated():
    text=FUNCTION_CATALOG['substitute_status']['description']
    assert 'material_code' in text and 'prefer' in text
    assert 'parent' in text and 'available_qty' in text
    assert 'truncate' in text

def test_shared_allocation_description_exposes_complete_summary_and_object_input():
    text=FUNCTION_CATALOG['shared_contention']['description']
    assert 'summary' in text and 'shortages' in text
    assert '{product, qty}' in text
    assert 'independent' in text
