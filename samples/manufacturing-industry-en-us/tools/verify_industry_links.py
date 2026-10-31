#!/usr/bin/env python3
"""Verify BKN links and the bookkeeping that every manufacturing record must obey.

The checks hold for any data that follows the business rules (links resolve, material and finished
goods balance to the transactions, shipments come from accepted lots), not for particular IDs.
"""
import csv
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODES = {  # displayed status (zh-CN or en-US) -> code
    '已接受': 'accepted', '已拒绝': 'rejected', '已拒收': 'rejected', '待检': 'pending_inspection', '待处理': 'pending',
    '已完成': 'completed', '已阻塞': 'blocked', '已下达': 'released', '生产中': 'in_production', '进行中': 'in_progress', '未开始': 'not_started',
    '已发料': 'issued', '部分发料': 'partial', '待发料': 'awaiting_issue', '通过': 'pass', '不通过': 'fail', '已发运': 'shipped',
    '已冻结': 'frozen', '草稿': 'draft', '已停用': 'obsolete', '原料库': 'raw_material', '待检区': 'quality_hold', '成品库': 'finished_goods',
}
BUSINESS_DATE = '2027-02-28'


def rows(name):
    with (ROOT / 'data' / f'{name}.csv').open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def code(value):
    return CODES.get(value, value)


def num(value):
    return float(value) if value != '' else 0.0


relation_count = 0
for path in sorted((ROOT / 'kn/relation_types').glob('*.bkn')):
    text = path.read_text(encoding='utf-8')
    identifier = re.search(r'(?m)^id: ([a-z][a-z0-9_]*)$', text)
    display_name = re.search(r'(?m)^name: (.+)$', text)
    assert identifier and display_name, f'Missing relation identifier or name: {path.name}'
    assert path.stem == identifier.group(1), f'Relation filename and id differ: {path.name}'
    assert len(identifier.group(1)) <= 128 and len(display_name.group(1)) <= 128, f'Relation API length limit exceeded: {path.name}'
    endpoint = re.search(r'\| ([a-z_]+) \| ([a-z_]+) \| direct \|', text)
    mapping = re.search(r'\| ([a-z_]+) \| ([a-z_]+) \|\s*$', text.split('### Mapping Rules', 1)[1], re.M)
    assert endpoint and mapping, f'Invalid relation declaration: {path.name}'
    source, target = endpoint.groups()
    source_field, target_field = mapping.groups()
    target_ids = {row[target_field] for row in rows(target)}
    assert all(row[source_field] in target_ids for row in rows(source) if row[source_field]), f'{source}.{source_field} has an unresolved BKN link'
    relation_count += 1

orders = {r['production_order_id']: r for r in rows('production_orders')}
versions = {r['bom_version_id']: r for r in rows('product_bom_versions')}
components = {r['bom_component_id']: r for r in rows('bom_components')}
receipts = {r['goods_receipt_id']: r for r in rows('goods_receipts')}
lots = {r['inspection_lot_id']: r for r in rows('quality_inspection_lots')}
fg = {r['finished_goods_receipt_id']: r for r in rows('finished_goods_receipts')}
sol = {r['sales_order_line_id']: r for r in rows('sales_order_lines')}

# work orders follow their BOM version, and each requirement is the BOM quantity with scrap rounded up
for order in orders.values():
    assert versions[order['bom_version_id']]['product_id'] == order['product_id'] == sol[order['sales_order_line_id']]['product_id']
issued_by_requirement = defaultdict(float)
for issue in rows('material_issue_transactions'):
    issued_by_requirement[issue['material_requirement_id']] += num(issue['issued_quantity'])
for req in rows('production_order_material_requirements'):
    comp = components[req['bom_component_id']]
    order = orders[req['production_order_id']]
    assert comp['bom_version_id'] == order['bom_version_id'] and comp['component_product_id'] == req['product_id']
    assert num(req['required_quantity']) == math.ceil(round(num(order['requested_quantity']) * num(comp['quantity_per']) * (1 + num(comp['scrap_factor'])), 6))
    assert num(req['issued_quantity']) == issued_by_requirement[req['material_requirement_id']]
    expected = 'issued' if num(req['issued_quantity']) >= num(req['required_quantity']) else ('partial' if num(req['issued_quantity']) > 0 else 'awaiting_issue')
    assert code(req['status']) == expected, req

# material and finished goods balance to receipts, issues and shipments as of the business date
issued_from = defaultdict(float)
on_hand = defaultdict(float)
for r in receipts.values():
    assert r['received_date'] <= BUSINESS_DATE
    if code(r['inspection_status']) in ('accepted', 'pending_inspection'):
        on_hand[(r['inventory_location_id'], r['product_id'])] += num(r['received_quantity'])
for issue in rows('material_issue_transactions'):
    r = receipts[issue['goods_receipt_id']]
    assert code(r['inspection_status']) != 'rejected' and issue['inventory_location_id'] == r['inventory_location_id'] and issue['issue_date'] <= BUSINESS_DATE
    issued_from[r['goods_receipt_id']] += num(issue['issued_quantity'])
    on_hand[(r['inventory_location_id'], r['product_id'])] -= num(issue['issued_quantity'])
assert all(issued_from[k] <= num(r['received_quantity']) for k, r in receipts.items())
shipped_from = defaultdict(float)
for receipt in fg.values():
    assert code(lots[receipt['inspection_lot_id']]['status']) == 'accepted' and lots[receipt['inspection_lot_id']]['production_order_id'] == receipt['production_order_id']
    on_hand[(receipt['inventory_location_id'], orders[receipt['production_order_id']]['product_id'])] += num(receipt['received_quantity'])
for shipment in rows('shipments'):
    receipt = fg[shipment['finished_goods_receipt_id']]
    assert receipt['production_order_id'] == shipment['production_order_id'] and orders[shipment['production_order_id']]['sales_order_line_id'] == shipment['sales_order_line_id']
    assert shipment['shipment_date'] <= BUSINESS_DATE and receipt['receipt_date'] <= shipment['shipment_date']
    shipped_from[receipt['finished_goods_receipt_id']] += num(shipment['shipped_quantity'])
    on_hand[(receipt['inventory_location_id'], orders[receipt['production_order_id']]['product_id'])] -= num(shipment['shipped_quantity'])
assert all(shipped_from[k] <= num(r['received_quantity']) for k, r in fg.items())
balances = rows('inventory_balances')
for balance in balances:
    key = (balance['inventory_location_id'], balance['product_id'])
    assert abs(num(balance['on_hand_quantity']) - on_hand.pop(key, 0.0)) < 1e-6, balance
    assert num(balance['available_quantity']) == num(balance['on_hand_quantity']) - num(balance['allocated_quantity']) >= 0
    assert balance['as_of_date'] == BUSINESS_DATE
assert all(abs(v) < 1e-6 for v in on_hand.values()), on_hand

# execution quantities: each operation passes on the good quantity of the one before
steps = {r['process_step_id']: r for r in rows('process_steps')}
operations = {r['operation_id']: r for r in rows('manufacturing_operations')}
for e in rows('production_execution_records'):
    if code(e['status']) == 'completed':
        assert e['started_date'] <= e['completed_date'] <= BUSINESS_DATE
        assert num(e['good_quantity']) + num(e['scrap_quantity']) <= num(orders[operations[steps[e['process_step_id']]['operation_id']]['production_order_id']]['requested_quantity'])
print(f'Validated {relation_count} BKN relations across the operational model.')
print('Validated requirements, transaction-derived stock, finished goods and shipment gates as of the business date.')
