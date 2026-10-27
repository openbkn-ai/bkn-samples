#!/usr/bin/env python3
"""Verify BKN links and manufacturing decision constraints for every business branch."""
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMAL = {'已接受':'accepted','已拒绝':'rejected','已完成':'completed','已阻塞':'blocked','待处理':'pending','已下达':'released','已发料':'issued','部分发料':'partial','通过':'pass','失败':'fail'}
def rows(name):
    with (ROOT/'data'/f'{name}.csv').open(encoding='utf-8', newline='') as f: return list(csv.DictReader(f))
def state(value): return NORMAL.get(value, value)
def num(value): return float(value)

relation_count = 0
for path in sorted((ROOT/'kn/relation_types').glob('*.bkn')):
    text = path.read_text(encoding='utf-8')
    identifier = re.search(r'(?m)^id: ([a-z][a-z0-9_]*)$', text)
    display_name = re.search(r'(?m)^name: (.+)$', text)
    assert identifier and display_name, f'Missing relation identifier or name: {path.name}'
    assert path.stem == identifier.group(1), f'Relation filename and id differ: {path.name}'
    assert len(identifier.group(1)) <= 128 and len(display_name.group(1)) <= 128, f'Relation API length limit exceeded: {path.name}'
    endpoint = re.search(r'\| ([a-z_]+) \| ([a-z_]+) \| direct \|', text)
    mapping = re.search(r'\| ([a-z_]+) \| ([a-z_]+) \|\s*$', text.split('### Mapping Rules',1)[1], re.M)
    assert endpoint and mapping, f'Invalid relation declaration: {path.name}'
    source, target = endpoint.groups(); source_field, target_field = mapping.groups()
    target_ids = {row[target_field] for row in rows(target)}
    assert all(row[source_field] in target_ids for row in rows(source)), f'{source}.{source_field} has an unresolved BKN link'
    relation_count += 1

orders = {r['production_order_id']:r for r in rows('production_orders')}
plans = {r['production_plan_id']:r for r in rows('production_plans')}
plan_lines = {r['production_order_id']:r for r in rows('production_plan_lines')}
versions = {r['bom_version_id']:r for r in rows('product_bom_versions')}
components = {r['bom_component_id']:r for r in rows('bom_components')}
requirements = {r['production_order_id']:r for r in rows('production_order_material_requirements')}
lots = {r['production_order_id']:r for r in rows('quality_inspection_lots')}
results = {r['inspection_lot_id']:r for r in rows('quality_inspection_results')}
specs = {r['quality_specification_id']:r for r in rows('quality_specifications')}
fg = {r['finished_goods_receipt_id']:r for r in rows('finished_goods_receipts')}

for order_id, order in orders.items():
    plan_line = plan_lines[order_id]; plan = plans[plan_line['production_plan_id']]
    requirement = requirements[order_id]; component = components[requirement['bom_component_id']]
    assert plan['snapshot_date'] == '2026-10-20' and plan['planning_start_date'] == '2026-11-01' and plan['planning_end_date'] == '2027-03-31'
    assert state(plan_line['status']) == 'released' and plan_line['scenario_as_of_date'] == plan['snapshot_date']
    assert plan_line['product_id'] == order['product_id'] == versions[order['bom_version_id']]['product_id']
    assert component['bom_version_id'] == order['bom_version_id'] and component['component_product_id'] == requirement['product_id']

issues_by_location = defaultdict(float); receipts_by_location = defaultdict(float)
for r in rows('material_issue_transactions'): issues_by_location[r['inventory_location_id']] += num(r['issued_quantity'])
for r in rows('goods_receipts'): receipts_by_location[r['inventory_location_id']] += num(r['received_quantity'])
fg_in = defaultdict(float); fg_out = defaultdict(float)
for r in fg.values(): fg_in[r['inventory_location_id']] += num(r['received_quantity'])
for r in rows('shipments'): fg_out[fg[r['finished_goods_receipt_id']]['inventory_location_id']] += num(r['shipped_quantity'])
for balance in rows('inventory_balances'):
    loc = balance['inventory_location_id']
    expected = receipts_by_location[loc] - issues_by_location[loc] if balance['inventory_balance_id'].startswith('IB-RAW') else fg_in[loc] - fg_out[loc]
    assert num(balance['on_hand_quantity']) == expected
    assert num(balance['available_quantity']) == num(balance['on_hand_quantity']) - num(balance['allocated_quantity']) >= 0
    assert balance['as_of_date'] == '2027-03-31'

for shipment in rows('shipments'):
    order = orders[shipment['production_order_id']]; receipt = fg[shipment['finished_goods_receipt_id']]
    lot = lots[shipment['production_order_id']]; result = results[lot['inspection_lot_id']]
    delivery = state(shipment['delivery_status'])
    assert receipt['production_order_id'] == shipment['production_order_id']
    assert shipment['sales_order_line_id'] == order['sales_order_line_id']
    assert num(shipment['shipped_quantity']) <= num(receipt['received_quantity']) <= num(order['requested_quantity'])
    if delivery == 'completed':
        spec = specs[result['quality_specification_id']]
        assert state(receipt['status']) == state(lot['status']) == 'accepted'
        assert state(result['result_status']) == 'pass' and num(spec['lower_limit']) <= num(result['measured_value']) <= num(spec['upper_limit'])
        assert num(shipment['shipped_quantity']) > 0
    else:
        assert delivery in {'blocked','rejected','pending'} and num(shipment['shipped_quantity']) == 0

for order_id, requirement in requirements.items():
    if state(requirement['status']) == 'partial':
        raw = next(r for r in rows('inventory_balances') if r['product_id'] == requirement['product_id'])
        assert num(requirement['issued_quantity']) < num(requirement['required_quantity']) and num(raw['available_quantity']) == 0

print(f'Validated {relation_count} BKN relations across the operational model.')
print('Validated plan/BOM provenance, transaction-derived inventory snapshots, and every shipment quality-and-receipt gate.')
