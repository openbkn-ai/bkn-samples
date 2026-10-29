"""Business regressions independent of historical answer/function agreement."""
import pytest
from fn import bom_shared_list, kitting_net_demand, theoretical_build, load_csv_snapshot
from fn.snapshot import build_snapshot
from managed_execution import load_bkn_rows


def test_priority_zero_remains_primary_inside_alternate_group():
    snap = build_snapshot({'bom': [
        {'bom_material_code': p, 'parent_material_code': p, 'bom_level': 1,
         'material_code': 'M', 'standard_usage': 1, 'alt_priority': 0,
         'alt_method': '替代', 'alt_group_no': 'G'} for p in ['P', 'Q']]})
    assert bom_shared_list(snap, ['P', 'Q'])['shared_codes'] == ['M']


@pytest.mark.parametrize('product,expected', [('382-000005',34), ('U00-000151',120)])
def test_capacity_matches_independent_csv_boundary(product, expected):
    # Independent oracle certificates are frozen in the 020 reproduction evidence.
    assert theoretical_build(load_csv_snapshot(), product)['theoretical_build_qty'] == expected


def _assembly():
    return build_snapshot({'bom': [
        {'id':'1','bom_material_code':'P','parent_material_code':'P','bom_level':1,
         'material_code':'S','standard_usage':1,'alt_priority':0},
        {'id':'2','bom_material_code':'P','parent_material_code':'S','bom_level':2,
         'material_code':'M','standard_usage':2,'alt_priority':0}],
        'inventory':[{'material_code':'S','warehouse':'苏州半成品仓',
                      'stock_status':'可用','available_inventory_qty':3},
                     {'material_code':'M','warehouse':'苏州半成品仓',
                      'stock_status':'可用','available_inventory_qty':2}]})


def test_kitting_consumes_intermediate_stock_before_raw_material():
    # 4 assemblies: 3 already stocked; only 1 needs manufacturing, using 2 M.
    assert kitting_net_demand(_assembly(), 'P', 4)['kitting_ok'] is True
    assert kitting_net_demand(_assembly(), 'P', 5)['kitting_ok'] is False


@pytest.mark.parametrize('stored_id', ['0000023181', '23181'])
def test_forecast_exact_id_first_with_bounded_numeric_fallback(stored_id):
    queries = []
    def query(**kwargs):
        queries.append(kwargs)
        if kwargs['ot_id'].endswith('_forecast'):
            if kwargs['condition']['value'] == stored_id:
                return {'datas':[{'id':stored_id,'material_number':'P'}]}
        return {'datas':[]}
    rows = load_bkn_rows('backward_plan', query,
                         {'forecast_id':'0000023181','substitute_enabled':False})
    assert queries[0]['condition']['value'] == '0000023181'
    assert len(rows['forecast']) == 1
    assert sum(q['ot_id'].endswith('_forecast') for q in queries) == (1 if stored_id.startswith('0') else 2)


def test_missing_forecast_stops_before_bom_scan_even_if_product_given():
    queries=[]
    def query(**kwargs):
        queries.append(kwargs)
        return {'datas':[]}
    with pytest.raises(ValueError, match='预测单不存在'):
        load_bkn_rows('backward_plan', query,
                     {'forecast_id':'0000023181','product':'P','substitute_enabled':False})
    assert len(queries) == 2
    assert all(q['ot_id'].endswith('_forecast') for q in queries)


def test_shared_component_stock_and_po_are_consumed_once_across_demands():
    from fn import shared_contention
    snap = build_snapshot({'bom': [
        {'id':p,'bom_material_code':p,'parent_material_code':p,'bom_level':1,
         'material_code':'M','standard_usage':2,'alt_priority':0} for p in ['P','Q']],
        'inventory':[{'material_code':'M','warehouse':'苏州半成品仓',
                      'stock_status':'可用','available_inventory_qty':1}],
        'purchase_order':[{'material_number':'M','qty':2,'actqty':1,'rowclosestatus_title':'正常'}]})
    out = shared_contention(snap,[{'product':'P','qty':1},{'product':'Q','qty':1}],report_grain='full')
    assert [a['satisfied'] for a in out['allocations']] == [True,False]
    assert out['allocations'][1]['lines'][0]['shortage'] == 2


def test_zero_priority_is_not_reported_as_substitute():
    from fn.bom import is_substitute_row
    assert is_substitute_row({'alt_priority':0,'alt_method':'替代'}) is False


def test_fulfillment_and_production_have_explicit_different_finished_goods_policy():
    snap = _assembly()
    snap.inv_by_material['P']=[{'material_code':'P','warehouse':'苏州成品仓',
                              'stock_status':'可用','available_inventory_qty':5}]
    assert kitting_net_demand(snap,'P',5)['kitting_ok'] is False
    out=kitting_net_demand(snap,'P',5,demand_mode='fulfillment')
    assert out['kitting_ok'] is True
    assert out['root_net_demand'] == 0
    assert out['finished_goods_allocated_qty'] == 5


def test_fulfillment_finished_goods_are_shared_across_repeated_product_demands():
    from fn import shared_contention
    snap = _assembly()
    snap.inv_by_material['P']=[{'material_code':'P','warehouse':'苏州成品仓',
                              'stock_status':'可用','available_inventory_qty':2}]
    out=shared_contention(snap,[{'product':'P','qty':2},{'product':'P','qty':5}],demand_mode='fulfillment')
    assert [a['satisfied'] for a in out['allocations']] == [True,False]


def test_gap_count_is_distinct_materials_not_bom_positions():
    snap=build_snapshot({'bom':[
      {'bom_material_code':'P','parent_material_code':'P','bom_level':1,
       'material_code':'M','standard_usage':1,'alt_priority':0},
      {'bom_material_code':'P','parent_material_code':'P','bom_level':1,
       'material_code':'M','standard_usage':2,'alt_priority':0}]})
    out=kitting_net_demand(snap,'P',1)
    assert out['gap_count']==1
    assert out['gaps'][0]['net_requirement']==3


def test_nonusable_inventory_cannot_cover_new_manufacturing():
    snap=build_snapshot({'bom':[
        {'bom_material_code':'P','parent_material_code':'P','bom_level':1,
         'material_code':'M','standard_usage':1,'alt_priority':0}],
        'inventory':[{'material_code':'M','warehouse':'苏州电子原料仓',
                      'stock_status':'不良','available_inventory_qty':10}]})
    assert kitting_net_demand(snap,'P',10)['kitting_ok'] is False
    assert theoretical_build(snap,'P')['theoretical_build_qty']==0


@pytest.mark.parametrize('product', ['734-000001','734-000003'])
def test_disabled_alternate_branch_does_not_block_main_product_calculation(product):
    # These exports have inconsistent subtrees only under an unused alternate.
    assert theoretical_build(load_csv_snapshot(),product,substitute_enabled=False)['theoretical_build_qty'] >= 0
