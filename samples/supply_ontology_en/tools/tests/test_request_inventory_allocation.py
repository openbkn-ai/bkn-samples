"""Independent small counterexamples for hierarchical shared-stock allocation."""
import pytest

from fn.allocation import net_requirements
from fn.capacity import theoretical_build, total_sellable
from fn.contention import shared_contention
from fn.errors import CannotCompute
from fn.kitting import kitting_net_demand
from fn.snapshot import build_snapshot, load_csv_snapshot


def row(product, parent, code, usage=1, *, group='', alternative=False):
    return {'bom_material_code': product, 'parent_material_code': parent,
            'material_code': code, 'bom_level': 1, 'standard_usage': usage,
            'alt_group_no': group, 'alt_priority': 1 if alternative else 0,
            'alt_method': 'Alternate' if group or alternative else ''}


def snapshot(rows, stock, po=None):
    return build_snapshot({'bom': rows, 'inventory': [
        {'material_code': code, 'warehouse': 'OTHER', 'available_inventory_qty': qty,
         'stock_status': 'Available'} for code, qty in stock.items()], 'po': po or []})


def test_component_units_expand_after_own_stock_without_dividing_usage():
    s = snapshot([row('P', 'P', 'C', 2), row('P', 'C', 'L', 3)], {'C': 4, 'L': 18})
    net = net_requirements(s, 'P', 5)
    assert [(x['material_code'], x['gross_requirement'], x['net_requirement'])
            for x in net['lines']] == [('C', 10, 6), ('L', 18, 0)]
    assert net['feasible'] is True
    assert theoretical_build(s, 'P')['theoretical_build_qty'] == 5
    assert kitting_net_demand(s, 'P', 5)['kitting_ok'] is True


def test_candidate_usage_and_single_candidate_contract():
    s = snapshot([row('P', 'P', 'MAIN', group='G'),
                  row('P', 'P', 'ALT', 2, group='G', alternative=True)], {'MAIN': 0, 'ALT': 20})
    kit = kitting_net_demand(s, 'P', 15, substitute_enabled=True)
    assert kit['gaps'][0]['material_code'] == 'ALT'
    assert kit['gaps'][0]['gross_requirement'] == 30
    assert kit['gaps'][0]['net_requirement'] == 10
    assert theoretical_build(s, 'P', substitute_enabled=True)['theoretical_build_qty'] == 10


def test_component_and_leaf_shared_between_bom_positions_not_reused():
    s = snapshot([row('P', 'P', 'A'), row('P', 'P', 'B'),
                  row('P', 'A', 'L'), row('P', 'B', 'L')], {'L': 7})
    assert theoretical_build(s, 'P')['theoretical_build_qty'] == 3
    net = net_requirements(s, 'P', 4)
    leaf = [x for x in net['lines'] if x['is_leaf']]
    assert [x['allocated_qty'] for x in leaf] == [4, 3]
    assert [x['net_requirement'] for x in leaf] == [0, 1]


def test_competing_demands_reselect_alternative_using_remaining_stock():
    s = snapshot([row('P', 'P', 'M', group='G'),
                  row('P', 'P', 'A', group='G', alternative=True)], {'M': 5, 'A': 5})
    result = shared_contention(s, [{'product': 'P', 'qty': 5}, {'product': 'P', 'qty': 5}],
                               substitute_enabled=True, report_grain='full')
    assert result['all_satisfied'] is True
    assert [a['lines'][0]['material_code'] for a in result['allocations']] == ['M', 'A']
    assert result['remaining'] == {'P': 0, 'M': 0, 'A': 0}


def test_competing_demands_share_finished_goods_and_ignore_purchase_orders():
    s = snapshot([row('P', 'P', 'L')], {'P': 3, 'L': 4},
                 po=[{'material_number': 'L', 'qty': 100, 'actqty': 0}])
    result = shared_contention(s, [{'product': 'P', 'qty': 5}, {'product': 'P', 'qty': 5}], report_grain='full')
    assert [a['satisfied'] for a in result['allocations']] == [True, False]
    assert result['allocations'][1]['lines'][-1]['shortage'] == 3
    assert result['include_in_transit'] is False


def test_fractional_usage_does_not_make_inventory_sum_an_upper_bound():
    s = snapshot([row('P', 'P', 'L', 0.001)], {'L': 1})
    assert theoretical_build(s, 'P')['theoretical_build_qty'] == 1000


def test_all_warehouse_default_and_explicit_filter():
    s = snapshot([row('P', 'P', 'L')], {'P': 3, 'L': 4})
    assert total_sellable(s, 'P')['total_sellable_qty'] == 7
    assert total_sellable(s, 'P', production_scope=['missing'], finished_goods_scope=['missing'])['total_sellable_qty'] == 0
    assert net_requirements(s, 'P', 3, scope=None, include_finished_goods=True)['root_net_demand'] == 0


@pytest.mark.parametrize('qty', [float('nan'), float('inf'), -1])
def test_nonfinite_or_negative_demands_rejected(qty):
    s = snapshot([row('P', 'P', 'L')], {'L': 1})
    with pytest.raises(CannotCompute):
        kitting_net_demand(s, 'P', qty)
    with pytest.raises(CannotCompute):
        shared_contention(s, [{'product': 'P', 'qty': qty}, {'product': 'P', 'qty': 1}])


def test_invalid_bom_and_cycles_rejected_even_with_finished_goods():
    s = snapshot([row('P', 'P', 'C'), row('P', 'C', 'P')], {'P': 100})
    with pytest.raises(CannotCompute, match='cycle'):
        net_requirements(s, 'P', 1, include_finished_goods=True)
    with pytest.raises(CannotCompute, match='BOM'):
        theoretical_build(s, 'UNKNOWN')
    s = snapshot([row('P', 'P', 'L', float('nan'))], {'L': 1})
    with pytest.raises(CannotCompute):
        theoretical_build(s, 'P')


def test_real_sample_packaging_counterexample_from_inventory_and_bom():
    # This is the review's data-based counterexample, not the eval answer set.
    s = load_csv_snapshot()
    total = total_sellable(s, '623-000034')
    assert (total['fg_qty'], total['theoretical_build_qty'], total['total_sellable_qty']) == (17, 26, 43)
    kit = kitting_net_demand(s, '623-000034', 60)
    assert kit['root_net_demand'] == 43
    assert {x['material_code']: x['net_requirement'] for x in kit['gaps']} == {
        '468-000282': 17, '606-000129': 17}


def test_priority_zero_remains_main_even_when_group_method_is_substitute():
    main = row('P', 'P', 'M', group='G')
    main['alt_method'] = 'Alternate'
    s = snapshot([main, row('P', 'P', 'A', group='G', alternative=True)], {'M': 3, 'A': 8})
    assert theoretical_build(s, 'P')['theoretical_build_qty'] == 3
    assert theoretical_build(s, 'P', substitute_enabled=True)['theoretical_build_qty'] == 8


def test_repeated_parent_subtree_is_template_once_but_parent_positions_remain():
    a = row('P', 'P', 'C')
    b = row('P', 'P', 'C')
    l1 = row('P', 'C', 'L', 2); l1['bom_level'] = 2
    l2 = dict(l1)
    s = snapshot([a, b, l1, l2], {'L': 8})
    net = net_requirements(s, 'P', 2)
    assert [x['gross_requirement'] for x in net['lines'] if x['material_code'] == 'L'] == [4, 4]
    assert net['feasible'] is True
    assert theoretical_build(s, 'P')['theoretical_build_qty'] == 2


def test_group_key_includes_parent_and_candidate_original_order_wins_ties():
    s = snapshot([row('P', 'P', 'C'), row('P', 'C', 'M', group='G'),
                  row('P', 'C', 'Z', group='G', alternative=True),
                  row('P', 'C', 'A', group='G', alternative=True),
                  row('P', 'P', 'N', group='G'),
                  row('P', 'P', 'ALT', group='G', alternative=True)],
                 {'M': 0, 'Z': 3, 'A': 3, 'N': 0, 'ALT': 3})
    chosen = net_requirements(s, 'P', 3, substitute_enabled=True)['lines']
    assert [x['material_code'] for x in chosen] == ['C', 'Z', 'ALT']


def test_both_candidates_cover_demand_choose_main_even_when_alt_has_more_stock():
    from fn.bom import is_main_row, is_substitute_row
    main = row('P', 'P', 'M', 2, group='G')
    main['alt_method'] = 'Alternate'
    alternative = row('P', 'P', 'A', group='G', alternative=True)
    assert is_main_row(main) and not is_substitute_row(main)
    assert not is_main_row(alternative) and is_substitute_row(alternative)
    s = snapshot([main, alternative], {'M': 6, 'A': 100})
    net = net_requirements(s, 'P', 3, substitute_enabled=True)
    assert net['lines'][0]['material_code'] == 'M'
    assert net['lines'][0]['allocated_qty'] == 6
    assert net['remaining']['A'] == 100
    # When main cannot cover all parent units, select the higher coverage alt.
    assert net_requirements(s, 'P', 4, substitute_enabled=True)['lines'][0]['material_code'] == 'A'


def test_managed_loader_primary_group_inventory_matches_complete_snapshot():
    """Exercise actual acquisition filters/pages, not unfiltered injected rows."""
    from managed_execution import load_bkn_rows, execute_from_bkn_rows, _OBJECT_TYPES
    full = load_csv_snapshot()
    datasets = {'bom': full.bom, 'inventory': full.inventory, 'purchase_order': full.po}
    reverse = {value: key for key, value in _OBJECT_TYPES.items()}
    calls = []
    def matches(row, condition):
        if not condition:
            return True
        if condition.get('operation') == 'and':
            return all(matches(row, c) for c in condition['sub_conditions'])
        actual = row.get(condition['field'])
        operation, expected = condition['operation'], condition['value']
        return (actual == expected if operation == '==' else
                actual != expected if operation == '!=' else actual in expected)
    def query(**kwargs):
        calls.append(kwargs)
        selected = [r for r in datasets[reverse[kwargs['ot_id']]] if matches(r, kwargs.get('condition'))]
        offset = kwargs.get('offset', 0)
        return {'datas': selected[offset:offset + kwargs['limit']]}
    params = {'product': '382-000005', 'warehouse_scope': 'production_available', 'substitute_enabled': False}
    loaded = load_bkn_rows('theoretical_build', query, params)
    assert len(loaded['bom']) == 507
    assert any(r['material_code'] == '588-000620' for r in loaded['inventory'])
    assert execute_from_bkn_rows('theoretical_build', loaded, params)['theoretical_build_qty'] == 34
    params = {'product': 'P61-000351', 'qty': 60, 'warehouse_scope': 'all', 'substitute_enabled': False}
    loaded = load_bkn_rows('kitting_net_demand', query, params)
    assert len(loaded['bom']) == 603
    result = execute_from_bkn_rows('kitting_net_demand', loaded, params)
    assert {g['material_code']: g['net_requirement'] for g in result['gaps']} == {
        '606-000069': 41, '606-000071': 30, '994-000645': 20}
    assert any(c['ot_id'] == 'supply_ontology_en_bom' and c.get('offset') == 500 for c in calls)
