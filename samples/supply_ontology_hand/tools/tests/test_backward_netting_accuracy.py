"""Business regressions exposed by the frozen 020 blind trial; no gold edits."""
from datetime import date

import pytest
from fn import backward_plan, kitting_net_demand, load_csv_snapshot
from fn.snapshot import build_snapshot
from fn.supply_status import supply_status
from test_backward_plan import (PRODUCT, TODAY, bom_row, inventory, material, mrp,
                                node, po, rows, run_plan)


def test_csv_backward_leaf_gaps_match_independent_net_requirements():
    snap = load_csv_snapshot()
    result = backward_plan(snap, 'P61-000351', demand_qty=60,
                           demand_end='2026-09-05', business_date='2026-08-25',
                           substitute_enabled=False, report_grain='full_tree')
    kit = kitting_net_demand(snap, 'P61-000351', 60)
    assert {g['material_code']: g['shortage_qty'] for g in result['gaps']} == {
        g['material_code']: g['net_requirement'] for g in kit['gaps']
    } == {'994-000645': 40}
    assert result['can_deliver_on_time'] is False
    assert result['customer_earliest_lower_bound'].startswith('2026-')


def test_partial_finished_goods_and_semifinished_stock_reduce_child_demand():
    snap = build_snapshot(rows(
        bom=[bom_row('SUB'), bom_row('LEAF', parent='SUB', level=2, usage=2)],
        materials=[material(PRODUCT, attr='自制', production_lt=1),
                   material('SUB', attr='自制', production_lt=2), material('LEAF', purchase_lt=30)],
        inventories=[inventory(PRODUCT,4,warehouse='苏州成品仓'),inventory('SUB',3),inventory('LEAF',6)]))
    result = run_plan(snap)
    assert result['root_net_demand'] == 6
    assert node(result,'SUB')['gross_requirement'] == 6
    assert node(result,'LEAF')['gross_requirement'] == 6
    assert result['gaps'] == []
    assert result['node_count_total'] == 3


def test_covered_subtree_stays_in_full_tree_without_affecting_risk_or_dates():
    snap = build_snapshot(rows(
        bom=[bom_row('SUB'),bom_row('LEAF',parent='SUB',level=2)],
        materials=[material(PRODUCT,attr='自制',production_lt=1),
                   material('SUB',attr='自制',production_lt=2),material('LEAF',purchase_lt=999)],
        inventories=[inventory('SUB',10)],
        purchase_orders=[po('LEAF',qty=10,deliverdate='2027-09-21')]))
    result=run_plan(snap)
    assert node(result,'LEAF')['gross_requirement']==0
    assert result['node_count_total']==3
    assert result['gaps']==[]
    assert result['can_deliver_on_time'] is True
    assert result['delay_b']==[]
    assert result['customer_earliest_available_date'].startswith('2026-')


def test_repeated_material_positions_share_one_inventory_pool():
    snap=build_snapshot(rows(
        forecasts=[],bom=[bom_row('A'),bom_row('B'),bom_row('M',parent='A',level=2),bom_row('M',parent='B',level=2)],
        materials=[material(PRODUCT,attr='自制',production_lt=1),material('A',attr='自制',production_lt=1),
                   material('B',attr='自制',production_lt=1),material('M',purchase_lt=2)],inventories=[inventory('M',1)]))
    result=run_plan(snap,forecast_id=None,demand_qty=1)
    assert sum(g['shortage_qty'] for g in result['gaps'] if g['material_code']=='M')==1
    assert [x['available_qty'] for x in result['nodes'] if x['material_code']=='M']==[1,0]


def test_all_required_po_receipts_not_only_the_first_determine_readiness():
    snap=build_snapshot(rows(purchase_orders=[po('RM-001',qty=1,deliverdate='2026-08-20'),
                                             po('RM-001',qty=9,deliverdate='2026-09-20')]))
    result=run_plan(snap)
    assert result['customer_earliest_available_date'] >= '2026-09-20'
    assert result['can_deliver_on_time'] is False


def test_unused_late_purchase_order_does_not_delay_on_hand_stock():
    result=run_plan(build_snapshot(rows(inventories=[inventory('RM-001',10)],
                                       purchase_orders=[po('RM-001',qty=10,deliverdate='2027-09-21')])))
    assert result['can_deliver_on_time'] is True
    assert result['delay_b']==[]


def test_unreceived_overdue_po_does_not_become_a_confirmed_arrival():
    result=run_plan(build_snapshot(rows(purchase_orders=[po('RM-001',qty=10,deliverdate='2026-08-01')],
                                       mrps=[mrp('RM-001')])))
    assert result['can_deliver_on_time'] is None
    assert result['customer_earliest_available_date'] is None
    assert result['uncertain_supply_items']


def test_finished_goods_today_cannot_retroactively_meet_a_past_due_date():
    result=run_plan(build_snapshot(rows(inventories=[inventory(PRODUCT,10,warehouse='苏州成品仓')])),
                    forecast_id=None,demand_end='2026-08-10')
    assert result['can_deliver_on_time'] is False
    assert result['customer_late_days']==4


def test_dated_supply_status_does_not_treat_late_po_as_on_time_inventory():
    snap=build_snapshot(rows(purchase_orders=[po('RM-001',qty=10,deliverdate='2026-09-20')],
                             mrps=[mrp('RM-001')]))
    result=supply_status(snap,'RM-001',gross_requirement=10,due_date='2026-08-31',today=TODAY)
    assert result['status']=='deadline_risk'


def test_backward_respects_confirmed_substitute_selection():
    main={**bom_row('MAIN'),'alt_group_no':'G'}
    alt={**bom_row('ALT'),'alt_group_no':'G','alt_priority':1,'alt_method':'替代'}
    snap=build_snapshot(rows(bom=[main,alt],materials=[material(PRODUCT,attr='自制',production_lt=1),
        material('MAIN',purchase_lt=30),material('ALT',purchase_lt=5)],inventories=[inventory('ALT',10)]))
    result=run_plan(snap,substitute_enabled=True)
    assert node(result,'ALT')['gross_requirement']==10
    assert result['gaps']==[]
    assert result['can_deliver_on_time'] is True


def test_unusable_finished_goods_are_not_shipped():
    bad={**inventory(PRODUCT,10,warehouse='苏州成品仓'),'stock_status':'不良'}
    result=run_plan(build_snapshot(rows(inventories=[bad])))
    assert result['finished_goods_qty']==0
    assert result['production_plan_required'] is True
