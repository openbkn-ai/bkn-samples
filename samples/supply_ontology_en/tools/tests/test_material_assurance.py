import copy
import json
import sys
import types
from pathlib import Path

import pytest

from fn.errors import CannotCompute
from fn.material_assurance import material_coverage, replenishment_draft
from fn.snapshot import build_snapshot, load_csv_snapshot

PRODUCT = '623-000034'
GAPS = {'468-000282', '606-000129'}


@pytest.mark.parametrize('purpose,covered,shortage', [('customer_delivery',43,17),('new_production',26,34)])
def test_locked_baseline_has_explicit_demand_purpose(purpose,covered,shortage):
    snapshot=load_csv_snapshot()
    original=copy.deepcopy(snapshot.bom_by_product[PRODUCT])
    result=material_coverage(snapshot,PRODUCT,60,demand_purpose=purpose)
    assert result['covered_qty']==covered
    assert result['uncovered_qty']==60-covered
    assert {g['material_code']:g['shortage_qty'] for g in result['gaps']}=={code:shortage for code in GAPS}
    assert result['provenance']['bom_row_count']==549
    assert result['provenance']['bom_primary_row_count']==439
    assert result['provenance']['bom_version']=='2026-08-05'
    assert snapshot.bom_by_product[PRODUCT]==original
    assert result['substitute_enabled'] is False and result['include_in_transit'] is False


@pytest.mark.parametrize('purpose,manual,tray,expected',[
    ('customer_delivery',0,0,43),('new_production',0,0,26),
    ('customer_delivery',17,0,43),('new_production',17,0,26),
    ('customer_delivery',17,17,60),('new_production',17,17,43),
    ('customer_delivery',34,34,60),('new_production',34,34,60),
])
def test_new_design_based_replay_cases_not_historical_receipts(purpose,manual,tray,expected):
    snapshot=load_csv_snapshot()
    for code,extra in [('468-000282',manual),('606-000129',tray)]:
        row=next(r for r in snapshot.inv_by_material[code] if float(r.get('available_inventory_qty') or 0)>0)
        row['available_inventory_qty']=str(float(row['available_inventory_qty'])+extra)
    result=material_coverage(snapshot,PRODUCT,60,demand_purpose=purpose)
    assert result['covered_qty']==expected


@pytest.mark.parametrize('qty,purpose',[(True,'customer_delivery'),(float('nan'),'customer_delivery'),(float('inf'),'customer_delivery'),(-1,'customer_delivery'),(0,'customer_delivery'),(1.5,'customer_delivery'),(60,None),(60,[]),(60,'unknown')])
def test_invalid_parameters_fail_before_any_fact_read(qty,purpose):
    from managed_execution import load_bkn_rows
    def query(**kwargs):pytest.fail('invalid request attempted to read facts')
    with pytest.raises((CannotCompute,ValueError)):
        load_bkn_rows('material_coverage',query,{'product':PRODUCT,'qty':qty,'demand_purpose':purpose})


def test_missing_or_mixed_bom_version_is_not_silent_success():
    snapshot=load_csv_snapshot()
    snapshot.bom_by_product[PRODUCT][0]['bom_version']='other-version'
    with pytest.raises(CannotCompute,match='one explicit source version'):
        material_coverage(snapshot,PRODUCT,60,demand_purpose='customer_delivery')


def test_shared_leaf_stock_is_not_reused_across_component_positions():
    rows=[{'bom_material_code':'P','bom_version':'v1','bom_level':1,'parent_material_code':'P','material_code':x,'standard_usage':1,'alt_priority':0} for x in ['A','B']]
    rows += [{'bom_material_code':'P','bom_version':'v1','bom_level':2,'parent_material_code':x,'material_code':'L','standard_usage':1,'alt_priority':0} for x in ['A','B']]
    # No available-stock status is needed: blank means the sample's default available state.
    snapshot=build_snapshot({'bom':rows,'inventory':[{'material_code':'L','warehouse':'W','available_inventory_qty':3}]})
    result=material_coverage(snapshot,'P',2,demand_purpose='new_production')
    assert result['covered_qty']==1
    assert result['gaps'][0]['shortage_qty']==1


def test_draft_is_deterministic_non_executable_and_does_not_mutate_coverage():
    result=material_coverage(load_csv_snapshot(),PRODUCT,60,demand_purpose='customer_delivery')
    original=copy.deepcopy(result)
    first=replenishment_draft(result)
    result['provenance']['data_collected_at']='a later read of identical facts'
    second=replenishment_draft(result)
    assert first['draft_id']==second['draft_id']
    assert first['status']=='draft' and first['persisted'] is False and first['executable'] is False
    assert first['items']==[{'material_code':code,'quantity':17} for code in sorted(GAPS)]
    result['provenance']['data_collected_at']=original['provenance']['data_collected_at']
    assert result==original


def test_generated_native_function_reads_full_bom_and_only_returns_draft(monkeypatch):
    import managed_execution
    from native_function_bundle import build_native_function_code
    from support_bkn_rows import bkn_rows
    raw=bkn_rows();calls=[]
    datasets={r.object_type_id:r.dataset for r in managed_execution.managed_query_plan('material_coverage').requirements}
    def matches(row,condition):
        if not condition:return True
        if condition['operation']=='and':return all(matches(row,c) for c in condition['sub_conditions'])
        value=row.get(condition['field'])
        if condition['operation']=='==':return str(value)==str(condition['value'])
        if condition['operation']=='in':return value in condition['value']
        raise AssertionError(condition)
    def query(**kwargs):
        calls.append(kwargs);rows=[r for r in raw[datasets[kwargs['ot_id']]] if matches(r,kwargs.get('condition'))]
        offset=kwargs.get('offset',0);return {'datas':rows[offset:offset+kwargs['limit']]}
    sdk=types.ModuleType('sandbox_sdk');sdk.tool=lambda f:f;sdk.bkn=types.SimpleNamespace(query_object_instance=query)
    monkeypatch.setitem(sys.modules,'sandbox_sdk',sdk)
    namespace={};exec(build_native_function_code(fixed_operation='material_coverage'),namespace)
    coverage=namespace['supply_function'](product=PRODUCT,qty=60,demand_purpose='customer_delivery')
    call_count=len(calls)
    sdk.bkn=types.SimpleNamespace(query_object_instance=lambda **kw:pytest.fail('draft action must not query BKN'))
    namespace={};exec(build_native_function_code(fixed_operation='replenishment_draft'),namespace)
    result=namespace['supply_function'](coverage=coverage)
    assert len(calls)==call_count
    assert result['basis_validation']=='structure_only_not_requeried'
    assert result['coverage']['covered_qty']==43
    assert result['coverage']['provenance']['bom_row_count']==549
    assert result['coverage']['provenance']['query_started_at']<=result['coverage']['provenance']['data_collected_at']
    assert len([q for q in calls if datasets[q['ot_id']]=='bom'])==2
    assert coverage['data_source']['loaded_datasets']==['bom','inventory']
    assert result['data_source']=={'kind':'supplied-coverage','requeried':False}
    assert result['persisted'] is False


def test_draft_action_binding_is_owned_conflict_checked_and_idempotent(monkeypatch):
    import bind_draft_action as binder
    import yaml
    manifest=yaml.safe_load((binder.ROOT/'sample.yaml').read_text());kn_id=manifest['spec']['knowledgeNetwork']['id']
    definition=next(a for a in json.loads((binder.ROOT/'kn'/(kn_id+'.json')).read_text())['action_types'] if a['id'].endswith('_act_replen_draft'))
    # Retain compatibility with deployed 0.2.1 builds whose import ID limit is 40.
    assert len(definition['id']) <= 40
    current=copy.deepcopy(definition);calls=[]
    tags=['bkn-samples','bkn-sample-'+manifest['metadata']['name']]
    monkeypatch.delenv('BKN_SAMPLE_OWNERSHIP_TAGS',raising=False)
    def call(args):
        calls.append(args)
        if args[:2]==['bkn','get']:return {'tags':tags}
        if args[:3]==['bkn','action-type','get']:
            assert args[3:]==[kn_id,definition['id']]
            return copy.deepcopy(current)
        assert args[0]=='call' and args[3]=='PUT'
        current.update(json.loads(args[5]));return {}
    binder.bind_draft_action(call,kn_id,'box','draft-tool')
    current['action_source'].update(mcp_id='',tool_name='')
    binder.bind_draft_action(call,kn_id,'box','draft-tool')
    assert len([c for c in calls if c[0]=='call'])==1
    current['action_source']['tool_id']='human-tool'
    with pytest.raises(ValueError,match='different tool'):binder.bind_draft_action(call,kn_id,'box','draft-tool')
    assert len([c for c in calls if c[0]=='call'])==1
    tags.clear()
    with pytest.raises(ValueError,match='ownership conflict'):binder.bind_draft_action(call,kn_id,'box','draft-tool')
    assert len([c for c in calls if c[0]=='call'])==1


def test_complete_reader_follows_short_pages_and_rejects_truncation():
    from fn.read_complete import read_complete
    pages=iter([{'datas':[{'id':1}],'search_after':['cursor-1'],'total_count':2}, {'datas':[{'id':2}],'total_count':2}])
    calls=[]
    def query(**kwargs):calls.append(kwargs);return next(pages)
    rows=read_complete(query,{'kn_id':'kn','ot_id':'ot'},lambda p:p['datas'])
    assert len(rows)==2 and calls[1]['search_after']==['cursor-1']
    for page in [{'datas':[],'total_count':2},{'datas':[{'id':1}],'total_count':2,'has_more':False},{'datas':[{'id':1}],'status':'partial'}]:
        with pytest.raises(ValueError):read_complete(lambda **kw:page,{},lambda p:p['datas'])


def test_complete_reader_rejects_repeated_rows_and_cursors():
    from fn.read_complete import read_complete
    with pytest.raises(ValueError,match='repeated object row'):
        read_complete(lambda **kw:{'datas':[{'id':1}],'search_after':['same']},{},lambda p:p['datas'])
    pages=iter([{'datas':[{'id':1}],'search_after':['same']},{'datas':[{'id':2}],'search_after':['same']}])
    with pytest.raises(ValueError,match='cursor repeated'):
        read_complete(lambda **kw:next(pages),{},lambda p:p['datas'])


@pytest.mark.parametrize('method,group,priority,kind',[
    ('','',0,'ordinary_main'), ('','0',0,'ordinary_main'),
    ('','G',0,'group_main'), ('主料','G',0,'group_main'), ('main component','',0,'ordinary_main'),
    ('替代','G',0,'group_main'), ('替代','G',1,'substitute'),
    ('Alternate','G',0,'group_main'), ('Alternate','G',2,'substitute'),
])
def test_method_group_and_priority_are_interpreted_together(method,group,priority,kind):
    from fn.bom import classify_bom_row
    assert classify_bom_row({'alt_method':method,'alt_group_no':group,'alt_priority':priority})==kind


@pytest.mark.parametrize('method,group,priority',[
    ('','',1), ('主料','G',1), ('替代','',0), ('替代','G',None),
    ('unknown','G',0), ('替代','G',-1), ('替代','G',0.5), ('替代','G',True),
])
def test_contradictory_or_ambiguous_replacement_rows_fail_closed(method,group,priority):
    from fn.bom import is_main_row
    with pytest.raises(CannotCompute):is_main_row({'alt_method':method,'alt_group_no':group,'alt_priority':priority})


def test_all_locked_bom_rows_have_consistent_combined_classification():
    from collections import Counter
    from fn.bom import classify_bom_row
    rows=load_csv_snapshot().bom
    assert Counter(classify_bom_row(row) for row in rows)=={'ordinary_main':21436,'group_main':4434,'substitute':5553}


@pytest.mark.parametrize('change', ['missing_provenance','duplicate_gap','bad_quantity','inconsistent_count'])
def test_draft_input_structure_is_validated_without_claiming_fact_verification(change):
    result=material_coverage(load_csv_snapshot(),PRODUCT,60,demand_purpose='customer_delivery')
    if change=='missing_provenance':result.pop('provenance')
    if change=='duplicate_gap':result['gaps'].append(copy.deepcopy(result['gaps'][0]))
    if change=='bad_quantity':result['gaps'][0]['shortage_qty']=float('nan')
    if change=='inconsistent_count':result['uncovered_qty']=0
    with pytest.raises(CannotCompute):replenishment_draft(result)


@pytest.mark.parametrize('method,group', [('Alternate',''), ('unknown','G'), ('替代','')])
def test_allocation_itself_rejects_invalid_priority_zero_combinations(method,group):
    # Call the common allocator directly: assurance's preflight must not hide
    # a different classification policy used by other Functions.
    from fn.allocation import net_requirements
    snapshot=build_snapshot({'bom':[{'bom_material_code':'P','bom_level':1,
        'parent_material_code':'P','material_code':'M','standard_usage':1,
        'alt_method':method,'alt_group_no':group,'alt_priority':0}],
        'inventory':[{'material_code':'M','warehouse':'W','available_inventory_qty':10}]})
    with pytest.raises(CannotCompute):net_requirements(snapshot,'P',1,substitute_enabled=False)
