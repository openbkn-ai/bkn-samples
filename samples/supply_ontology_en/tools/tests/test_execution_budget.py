"""Acquisition must not spend trace operations on unusable supply facts."""
import pytest
from managed_execution import load_bkn_rows, execute_from_bkn_rows
from support_bkn_rows import bkn_rows

def matches(row, condition):
    if not condition:
        return True
    if condition['operation'] == 'and':
        return all(matches(row, c) for c in condition['sub_conditions'])
    v = row.get(condition['field'])
    if condition['operation'] == 'in':
        return v in condition['value']
    if condition['operation'] == '==':
        return v == condition['value']
    if condition['operation'] == '!=':
        return v != condition['value']
    raise AssertionError(condition)

@pytest.mark.parametrize('operation,params', [
    ('kitting_net_demand', {'product':'P61-000351','qty':60}),
    ('shared_contention', {'demands':[{'product':'382-000005','qty':50},{'product':'P61-000351','qty':60}]}),
])
def test_inventory_only_functions_never_query_purchase_orders(operation, params):
    params.update(substitute_enabled=False, warehouse_scope='all')
    calls=[]
    def query(**args):
        calls.append(args)
        assert not args['ot_id'].endswith('_po'), 'inventory-only computation queried POs'
        return {'datas':[]}
    load_bkn_rows(operation, query, params)
    assert calls

def test_filtered_reads_preserve_actual_shared_allocation_result():
    source=bkn_rows();calls=[]
    def query(**args):
        calls.append(args)
        dataset={'supply_ontology_en_bom':'bom','supply_ontology_en_inventory':'inventory','supply_ontology_en_po':'purchase_order'}[args['ot_id']]
        rows=[r for r in source[dataset] if matches(r,args.get('condition'))]
        offset=args.get('offset',0)
        return {'datas':rows[offset:offset+args['limit']]}
    params={'demands':[{'product':'382-000005','qty':50},{'product':'P61-000351','qty':60}],'warehouse_scope':'all','substitute_enabled':False}
    rows=load_bkn_rows('shared_contention',query,params)
    actual=execute_from_bkn_rows('shared_contention',rows,params)
    expected=execute_from_bkn_rows('shared_contention',source,params)
    assert actual['allocations']==expected['allocations']
    assert not any(c['ot_id'].endswith('_po') for c in calls)
