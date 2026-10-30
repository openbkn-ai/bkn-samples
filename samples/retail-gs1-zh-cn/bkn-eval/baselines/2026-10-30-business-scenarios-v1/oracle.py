#!/usr/bin/env python3
"""Independent oracle for the retail business-scenario question set.

Reads only this package's delivered CSV files. Inventory replay, FEFO allocation,
replenishment and recall closure come from the evaluator-only reference in
tools/retail_eval/oracle.py, which implements the PRD rules from source facts and does
not import the sample's functions. The file is identical in the zh-CN and en-US
packages: their data differ only in translated text, so expected values match
except for names and labels.

Writes question-set-v1.yaml (no answers) and answer-set-v1.yaml next to this file.
"""
import sys
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[4] / 'tools' / 'retail_eval'))
from oracle import Reference, ZERO, number  # noqa: E402

LANG = 'zh' if ROOT.name.endswith('zh-cn') else 'en'
TODAY = '2027-02-28'
R = Reference(ROOT / 'data')
T = R.tables
INV, DIAG, EVENTS = R.inventory(TODAY, TODAY)
PRODUCTS = sorted(R.products)
ALLOC = R.allocation(PRODUCTS, TODAY, TODAY)
PLAN = R.plan(PRODUCTS, TODAY, TODAY)
LOC = {r['location_id']: r for r in T['locations']}
ORG = {r['organization_id']: r for r in T['organizations']}


def num(x):
    if x is None:
        return None
    x = D(x).quantize(D('0.000001'))
    return int(x) if x == x.to_integral_value() else float(x.normalize())


def total(rows, key):
    return sum((r[key] for r in rows if r[key] is not None), ZERO)


QUESTIONS = []
ROLE = {'QA': ('质量负责人', 'Quality lead'), 'WH': ('仓配负责人', 'Warehouse and distribution lead'), 'ST': ('门店店长', 'Store manager')}
LEVEL = {'basic': ('基础', 'basic'), 'medium': ('中等', 'medium'), 'complex': ('复杂', 'complex')}


def q(qid, scenario, level, role, zh, en, expected, contract_zh, contract_en):
    i = 0 if LANG == 'zh' else 1
    QUESTIONS.append(dict(id=qid, scenario=scenario, difficulty=LEVEL[level][i], role=ROLE[role][i],
                          question=(zh, en)[i], output_contract=(contract_zh, contract_en)[i], expected=expected))


def cells(**match):
    return [r for r in INV if all(r[k] == v for k, v in match.items())]


# S01 master data
q('Q-01', 'S01', 'basic', 'WH', '我们一共经营多少个商品？分在几个品类？', 'How many products do we carry, and in how many categories?',
  dict(products=len(T['products']), categories=len({p['category'] for p in T['products']})), '商品数、品类数', 'product count, category count')
p1 = R.products['PRD-001']
q('Q-02', 'S01', 'basic', 'WH', 'PRD-001 是哪家供应商供货？一箱几件？发货时至少要留几天保质期？',
  'Who supplies PRD-001, how many units are in a case, and how many days of shelf life must remain when it ships?',
  dict(supplier_id=p1['supplier_id'], supplier=ORG[p1['supplier_id']]['name'], pack_multiplier=num(p1['pack_multiplier']), min_shelf_days=num(p1['min_shelf_days'])),
  '供应商编号与名称、每箱件数、最少剩余保质天数', 'supplier id and name, units per case, minimum remaining shelf-life days')
q('Q-03', 'S01', 'basic', 'WH', '我们有多少个仓库、多少家门店？', 'How many warehouses and how many stores do we have?',
  dict(warehouses=sum(r['location_type_code'] == 'warehouse' for r in T['locations']), stores=sum(r['location_type_code'] == 'store' for r in T['locations'])),
  '仓库数、门店数', 'warehouse count, store count')
src = sorted({m['source_location_id'] for m in EVENTS if m['event_type_code'] == 'dispatch' and m['destination_location_id'] == 'STORE-001'})
q('Q-04', 'S03', 'medium', 'ST', 'STORE-001 的货是从哪个仓库调过来的？', 'Which warehouse supplies STORE-001 by transfer?',
  dict(warehouses=src), '仓库编号清单', 'warehouse ids')

# S02 receiving and inspection
status = {l: R.inspection(l, TODAY, TODAY) for l in sorted(R.lots)}
q('Q-05', 'S02', 'basic', 'QA', '现在有哪些批次质检不合格？哪些还没检完？', 'Which lots have failed inspection, and which are still awaiting inspection?',
  dict(failed=[l for l, s in status.items() if s == 'failed'], pending=[l for l, s in status.items() if s == 'pending']), '不合格批次清单、待检批次清单', 'failed lots, pending lots')
bad_lots = [l for l, s in status.items() if s == 'failed']
bad_cells = sorted((r for r in INV if r['lot_id'] in bad_lots and r['on_hand'] and r['on_hand'] > 0), key=lambda r: (r['lot_id'], r['location_id']))
q('Q-06', 'S02', 'medium', 'QA', '质检不合格的批次现在还在哪些地方有货？各多少件？', 'Where is stock of the lots that failed inspection still held, and how much at each place?',
  dict(stock=[dict(lot_id=r['lot_id'], location_id=r['location_id'], on_hand=num(r['on_hand'])) for r in bad_cells]), '批次、地点、在库数量清单', 'list of lot, location, on-hand quantity')
feb_recv = {m['lot_id'] for m in EVENTS if m['event_type_code'] == 'receive' and m['event_date'][:7] == '2027-02'}
q('Q-07', 'S02', 'basic', 'WH', '二月份一共收进了多少个批次的货？', 'How many lots did we receive in February?',
  dict(lots=len(feb_recv)), '批次数', 'lot count')
pend = cells(lot_id='LOT-013-D')
q('Q-08', 'S02', 'medium', 'ST', 'LOT-013-D 还没检完，现在能卖吗？各地点能用的库存是多少？', 'LOT-013-D is still awaiting inspection. Can it be sold now, and how much is available at each location?',
  dict(can_sell=False, available={r['location_id']: num(r['available']) for r in pend}), '能否销售、各地点可用量', 'can sell or not, available per location')

# S04 stock and in-transit
w1 = cells(product_id='PRD-001', location_id='WH-001')
q('Q-09', 'S04', 'basic', 'WH', 'PRD-001 现在在 WH-001 能用的库存有多少件？', 'How many units of PRD-001 are available at WH-001 now?',
  dict(available=num(total(w1, 'available'))), '可用件数', 'available units')
q('Q-10', 'S04', 'medium', 'WH', '现在已经发出、还没到货的在途货一共有多少件？', 'How many units are currently in transit, dispatched but not yet arrived?',
  dict(in_transit=num(total(INV, 'in_transit'))), '在途件数', 'units in transit')
qcells = [r for r in INV if r['quarantined'] and r['quarantined'] > 0]
q('Q-11', 'S04', 'medium', 'QA', '现在被隔离、不能用的库存一共多少件？分布在多少个批次库位？', 'How many units are quarantined now, and across how many lot-location positions?',
  dict(quarantined=num(total(qcells, 'quarantined')), positions=len(qcells)), '隔离件数、批次库位数', 'quarantined units, lot-location count')
q('Q-12', 'S04', 'complex', 'WH', 'PRD-001 在 WH-001 在库不少，为什么能用的只有这么些？按批次说明。',
  'PRD-001 has plenty on hand at WH-001. Why is so little available? Explain by lot.',
  dict(on_hand=num(total(w1, 'on_hand')), available=num(total(w1, 'available')),
       lots={r['lot_id']: dict(on_hand=num(r['on_hand']), expired=r['expired'], quarantined=num(r['quarantined']), recall_blocked=num(r['recall_blocked']),
                               reserved=num(r['reserved']), available=num(r['available'])) for r in sorted(w1, key=lambda r: r['lot_id'])}),
  '在库合计、可用合计、各批次在库/是否过期/隔离/召回封存/预留/可用', 'on-hand and available totals; per lot on-hand, expired, quarantined, recall-blocked, reserved, available')
st1 = [r for r in cells(location_id='STORE-001') if r['available'] and r['available'] > 0]
q('Q-13', 'S04', 'basic', 'ST', 'STORE-001 现在能卖的货有多少件？分在几个批次？', 'How many units can STORE-001 sell now, and in how many lots?',
  dict(available=num(total(st1, 'available')), lots=len(st1)), '可用件数、批次数', 'available units, lot count')
best = max((p for p in ['WH-001', 'STORE-001']), key=lambda l: total(cells(product_id='PRD-001', location_id=l), 'available'))

# S05 expiry
exp = [r for r in INV if r['expired'] and r['on_hand'] and r['on_hand'] > 0]
q('Q-14', 'S05', 'medium', 'QA', '现在有多少个批次库位的货已经过期但还在库？合计多少件？', 'How many lot-location positions hold expired stock that is still on hand, and how many units in total?',
  dict(positions=len(exp), units=num(total(exp, 'on_hand'))), '批次库位数、件数', 'position count, units')
near1 = sorted(r['lot_id'] for r in cells(location_id='STORE-001') if r['near_expiry'] and r['on_hand'] and r['on_hand'] > 0)
q('Q-15', 'S05', 'medium', 'ST', 'STORE-001 有哪些批次两周内到期、还有货？', 'Which lots at STORE-001 expire within two weeks and still have stock?',
  dict(lots=near1), '批次清单', 'lot ids')
exp_lot = sorted(r['lot_id'] for r in cells(location_id='STORE-001') if r['expired'] and r['on_hand'] and r['on_hand'] > 0)
q('Q-16', 'S05', 'basic', 'ST', 'STORE-001 有哪些批次已经过期但还在架上？', 'Which lots at STORE-001 have expired but are still on hand?',
  dict(lots=exp_lot), '批次清单', 'lot ids')

# S06 order fulfilment
open_orders = [o for o in T['orders'] if o['status_code'] == 'open']
q('Q-17', 'S06', 'basic', 'WH', '现在还有多少张订单没完成？其中有没有已经过了交期的？', 'How many orders are still open, and are any of them past their due date?',
  dict(open_orders=len(open_orders), overdue=sorted(o['order_id'] for o in open_orders if o['due_date'] < TODAY)), '未完成订单数、逾期订单清单', 'open order count, overdue order ids')
st = Counter(r['allocation_status_code'] for r in ALLOC)
q('Q-18', 'S06', 'complex', 'WH', '按优先级和交期用现有可用库存给未完成的订单行配货，能全部满足、部分满足和一件都配不到的各有多少行？',
  'Allocating available stock to open order lines by priority and due date, how many lines are fully covered, partly covered, and get nothing?',
  dict(full=st['full'], partial=st['partial'], none=st['shortage'], unknown=st['unknown']), '全部满足、部分满足、配不到、无法判断的行数', 'full, partial, none and unknown line counts')
a1 = [r for r in ALLOC if r['order_id'] == 'ORD-001-A'][0]
q('Q-19', 'S06', 'complex', 'WH', 'ORD-001-A 能全部发出吗？用哪些批次、各多少件？', 'Can ORD-001-A ship in full? Which lots and how many units of each?',
  dict(requested=num(a1['requested_quantity']), allocated=num(a1['allocated_quantity']), lots={x['lot_id']: num(x['quantity']) for x in a1['allocations']}),
  '订购数、可配数、批次及件数', 'ordered, allocated, lots and units')
a49 = [r for r in ALLOC if r['order_id'] == 'ORD-049-A'][0]
q('Q-20', 'S06', 'complex', 'WH', 'ORD-049-A 已经过了交期还没发，按要求保质期它还能配到多少件？用哪个批次？',
  'ORD-049-A is past its due date and not shipped. With its required shelf life, how many units can it still get, and from which lot?',
  dict(requested=num(a49['requested_quantity']), allocated=num(a49['allocated_quantity']), lots={x['lot_id']: num(x['quantity']) for x in a49['allocations']}),
  '订购数、可配数、批次及件数', 'ordered, allocated, lots and units')
zero = sorted((r for r in ALLOC if r['allocation_status_code'] == 'shortage'), key=lambda r: r['order_id'])
q('Q-21', 'S06', 'complex', 'WH', '哪些订单行一件都配不到？各缺多少件？', 'Which order lines cannot get a single unit, and how much is each short?',
  dict(lines={r['order_id']: num(r['shortage_quantity']) for r in zero}), '订单号及缺货件数', 'order ids and units short')
over = [r for r in ALLOC if r['allocation_status_code'] in ('partial', 'shortage')]
q('Q-22', 'S06', 'complex', 'WH', '按现有库存配货后，未完成订单一共还缺多少件？', 'After allocating current stock, how many units are the open orders short in total?',
  dict(shortage=num(sum((r['shortage_quantity'] for r in ALLOC if r['shortage_quantity'] is not None), ZERO))), '缺货件数', 'units short')

# S07 replenishment
fc1 = [r for r in T['demand_forecasts'] if r['product_id'] == 'PRD-001' and r['location_id'] == 'WH-001']
q('Q-23', 'S07', 'basic', 'WH', 'PRD-001 在 WH-001 三月份的需求预测一共多少件？', 'What is the March demand forecast for PRD-001 at WH-001 in total?',
  dict(forecast=num(sum((number(r['quantity']) for r in fc1), ZERO))), '预测件数', 'forecast units')
plan1 = [r for r in PLAN if r['product_id'] == 'PRD-001' and r['location_id'] == 'WH-001']
q('Q-24', 'S07', 'complex', 'WH', '按三月预测，PRD-001 在 WH-001 三月份需要补多少件？分别从哪次需求开始缺？',
  'Against the March forecast, how many units of PRD-001 must WH-001 replenish in March, and from which demand does it start to fall short?',
  dict(replenish=num(sum((r['recommended_quantity'] for r in plan1), ZERO)), shortages={r['demand_date']: num(r['shortage_quantity']) for r in plan1 if r['shortage_quantity'] > 0}),
  '补货件数、各需求日期的缺口', 'units to replenish, shortfall by demand date')
g = defaultdict(lambda: ZERO)
for r in PLAN:
    g[(r['product_id'], r['location_id'])] += r['recommended_quantity'] or ZERO
top = max(g, key=lambda k: (g[k], k))
q('Q-25', 'S07', 'complex', 'WH', '三月份补货缺口最大的是哪个商品、在哪个仓？要补多少件？', 'Which product at which warehouse has the largest March replenishment gap, and how many units?',
  dict(product_id=top[0], location_id=top[1], replenish=num(g[top])), '商品、仓库、补货件数', 'product, warehouse, units')
q('Q-26', 'S07', 'complex', 'WH', '三月份所有商品按预测一共需要补多少件？涉及多少个商品仓库组合？', 'Across all products, how many units must be replenished in March, and for how many product-warehouse pairs?',
  dict(replenish=num(sum(g.values(), ZERO)), pairs=sum(1 for v in g.values() if v > 0)), '补货件数、组合数', 'units, pair count')
p15 = [r for r in plan1 if r['demand_date'] == '2027-03-15'][0]
q('Q-27', 'S07', 'complex', 'WH', 'PRD-001 在 WH-001 3 月 15 日那次需求为什么只能满足一部分？那时能用的货有多少、缺多少？',
  'Why can the March 15 demand for PRD-001 at WH-001 be met only in part? How much usable stock is there then, and how much is short?',
  dict(demand=num(p15['demand_quantity']), usable_supply=num(p15['eligible_supply_quantity']), shortage=num(p15['shortage_quantity'])),
  '需求件数、可用供应、缺口', 'demand, usable supply, shortfall')

# S08 recall reach
recs = Counter(r['status_code'] for r in T['recalls'])
q('Q-28', 'S08', 'basic', 'QA', '现在有多少个召回在进行？有没有已经关闭的？', 'How many recalls are in progress, and are any closed?',
  dict(open=recs['open'], closed=sorted(r['recall_id'] for r in T['recalls'] if r['status_code'] == 'closed')), '进行中召回数、已关闭召回清单', 'open recall count, closed recall ids')
c1 = sorted(R.closure('LOT-001-B', TODAY, TODAY))
q('Q-29', 'S08', 'medium', 'QA', 'REC-001 涉及哪些批次？包括拆分出去的。', 'Which lots does REC-001 cover, including lots split from it?',
  dict(lots=c1), '批次清单', 'lot ids')
r1 = R.recall('REC-001', TODAY, TODAY)
q('Q-30', 'S08', 'medium', 'QA', 'REC-001 的问题货现在在哪些地方？各有多少件在库？', 'Where is REC-001 stock now, and how many units are on hand at each place?',
  dict(locations={r['location_id']: num(r['on_hand']) for r in r1}), '地点及在库件数', 'locations and on-hand units')
q('Q-31', 'S08', 'medium', 'ST', 'REC-001 的问题货已经卖出去、没退回来的有多少件？在哪家门店卖的？', 'How many units of REC-001 stock were sold and not returned, and at which store?',
  dict(sold=num(total(r1, 'sold')), stores=sorted(r['location_id'] for r in r1 if r['sold'] and r['sold'] > 0)), '已售未退件数、门店', 'units sold and not returned, stores')
r48 = R.recall('REC-048', TODAY, TODAY)
q('Q-32', 'S08', 'complex', 'QA', 'REC-048 会牵连到哪些批次和商品？为什么会涉及别的商品？', 'Which lots and products does REC-048 reach, and why does it involve another product?',
  dict(lots=sorted(R.closure('LOT-048-B', TODAY, TODAY)), products=sorted({r['product_id'] for r in r48}), via_link=[l['link_id'] for l in T['lot_links'] if l['link_type_code'] == 'transform']),
  '批次清单、商品清单、牵连原因（商品转换记录）', 'lots, products, reason (product transformation link)')
q('Q-33', 'S08', 'complex', 'ST', 'REC-001 影响哪些订单？', 'Which orders does REC-001 affect?',
  dict(orders=sorted({o for r in r1 for o in r['affected_order_ids']})), '订单号清单', 'order ids')

# S09 recall control
snap1 = [r for r in T['recall_snapshots'] if r['recall_id'] == 'REC-001'][0]
q('Q-34', 'S09', 'basic', 'QA', 'REC-001 截至今天已经控制住多少件？可控制的一共多少件？控制比例多少？', 'For REC-001 as of today, how many units are controlled, how many are controllable, and what is the coverage?',
  dict(controlled=num(snap1['controlled_quantity']), controllable=num(snap1['controllable_quantity']), coverage=num(snap1['coverage_ratio'])), '已控制、可控制、比例', 'controlled, controllable, coverage')
w = [r for r in r1 if r['location_id'] == 'WH-001'][0]
q('Q-35', 'S09', 'medium', 'QA', 'REC-001 在 WH-001 的控制比例是多少？', 'What is REC-001\'s coverage at WH-001?',
  dict(controlled=num(w['controlled_quantity']), controllable=num(w['controllable_quantity']), coverage=num(w['coverage_ratio'])), '已控制、可控制、比例', 'controlled, controllable, coverage')
s1 = [r for r in r1 if r['location_id'] == 'STORE-001'][0]
q('Q-36', 'S09', 'medium', 'ST', 'REC-001 在 STORE-001 还有多少件没控制住？', 'How many units of REC-001 at STORE-001 are not yet under control?',
  dict(pending=num(s1['pending_control_quantity'])), '未控制件数', 'units not controlled')
snaps = [r for r in T['recall_snapshots'] if r['coverage_ratio'] != '']
low = min(D(r['coverage_ratio']) for r in snaps)
q('Q-37', 'S09', 'medium', 'QA', '哪些召回的控制比例最低？是多少？', 'Which recalls have the lowest coverage, and what is it?',
  dict(recalls=sorted(r['recall_id'] for r in snaps if D(r['coverage_ratio']) == low), coverage=num(low)), '召回清单、比例', 'recall ids, coverage')
q('Q-38', 'S09', 'medium', 'QA', 'REC-050 已经关闭，现在还要按召回去封存它的批次吗？', 'REC-050 is closed. Should its lots still be blocked as a recall now?',
  dict(still_blocked=False, assessment_rows=len(R.recall('REC-050', TODAY, TODAY))), '是否仍需封存', 'still blocked or not')
nocov = sorted(r['recall_id'] for r in T['recall_snapshots'] if r['coverage_ratio'] == '')
q('Q-39', 'S09', 'complex', 'QA', '有没有召回的控制比例算不出来？为什么？', 'Is there a recall whose coverage cannot be calculated, and why?',
  dict(recalls=nocov), '召回清单及原因', 'recall ids and reason')
q('Q-40', 'S09', 'complex', 'QA', 'REC-001 在 WH-001 被召回封存的库存里，有多少件同时还被预隔离了？', 'Of REC-001 stock at WH-001, how much is already quarantined and how much is blocked only by the recall?',
  dict(quarantined=num(total([r for r in INV if r['lot_id'] in c1 and r['location_id'] == 'WH-001'], 'quarantined')),
       recall_blocked=num(total([r for r in INV if r['lot_id'] in c1 and r['location_id'] == 'WH-001'], 'recall_blocked'))),
  '已隔离件数、仅召回封存件数', 'quarantined units, recall-blocked units')

# S10 data trust and look-back
unk = sorted((r['lot_id'], r['location_id']) for r in INV if r['available'] is None)
q('Q-41', 'S10', 'complex', 'WH', '现在有哪些批次库位的库存算不清楚？各是什么原因？', 'Which lot-location positions have stock that cannot be determined now, and why?',
  dict(positions={f'{a}@{b}': sorted({d['code'] for d in DIAG if d.get('lot_id') == a and d.get('location_id') == b}
                                     | {'conflicting_event' for d in DIAG if d['code'] == 'conflicting_event'
                                        and any(m['event_id'] == d['event_id'] and m['lot_id'] == a for m in T['movements'])}) for a, b in unk}),
  '批次@地点及原因代码', 'lot@location with reason codes')
dup = [d for d in DIAG if d['code'] == 'duplicate_event']
q('Q-42', 'S10', 'medium', 'WH', '有没有被重复记录的出入库事件？涉及哪个批次？会不会被算两次？',
  'Is any stock movement recorded twice? Which lot does it involve, and is it counted twice?',
  dict(events=[d['event_id'] for d in dup], lots=sorted({m['lot_id'] for m in T['movements'] if m['event_id'] in {d['event_id'] for d in dup}}), counted_twice=False),
  '事件编号、批次、是否重复计算', 'event ids, lots, counted twice or not')
miss = sorted(d['transfer_id'] for d in DIAG if d['code'] == 'missing_or_insufficient_dispatch')
q('Q-43', 'S10', 'medium', 'WH', '有没有到货了却找不到发货记录的调拨？', 'Are there transfers that arrived without a matching dispatch?',
  dict(transfers=miss), '调拨编号清单', 'transfer ids')
overres = sorted(f"{d['lot_id']}@{d['location_id']}" for d in DIAG if d['code'] == 'overreservation')
q('Q-44', 'S10', 'medium', 'WH', '哪些预留超过了能用的库存？', 'Which reservations exceed the stock that can be used?',
  dict(positions=overres), '批次@地点清单', 'lot@location list')
rev = [m for m in T['movements'] if m['event_type_code'] == 'reversal'][0]
c44 = cells(lot_id='LOT-044-C', location_id='STORE-019')[0]
q('Q-45', 'S10', 'complex', 'ST', 'LOT-044-C 在 STORE-019 有一笔销售被冲正了。冲正后这家店卖出了多少件、还剩多少件在库？',
  'A sale of LOT-044-C at STORE-019 was reversed. After the reversal, how many units has the store sold and how many are on hand?',
  dict(reversed_event=rev['reversal_of'], sold=num(c44['sold']), on_hand=num(c44['on_hand'])), '被冲正事件、已售件数、在库件数', 'reversed event, units sold, units on hand')
late_inv, _, _ = R.inventory(TODAY, '2027-03-05')
before = cells(lot_id='LOT-041-C', location_id='STORE-016')[0]
after = [r for r in late_inv if r['lot_id'] == 'LOT-041-C' and r['location_id'] == 'STORE-016'][0]
q('Q-46', 'S10', 'complex', 'ST', 'LOT-041-C 在 STORE-016 有一笔 2 月 26 日的销售 3 月 2 日才补录。按今天掌握的信息和按 3 月 5 日掌握的信息，这家店的在库分别是多少？',
  'A February 26 sale of LOT-041-C at STORE-016 was only recorded on March 2. What is the store\'s on-hand quantity based on what is known today, and based on what is known on March 5?',
  dict(known_today=num(before['on_hand']), known_march_5=num(after['on_hand'])), '今天口径在库、3 月 5 日口径在库', 'on hand as known today, on hand as known on March 5')
early_inv, _, _ = R.inventory('2027-02-20', '2027-02-20')
e1 = [r for r in early_inv if r['product_id'] == 'PRD-001' and r['location_id'] == 'WH-001']
q('Q-47', 'S10', 'complex', 'WH', '回到 2 月 20 日，按当时掌握的信息，PRD-001 在 WH-001 能用的库存是多少？和今天比差多少？',
  'Back on February 20, based on what was known then, how many units of PRD-001 were available at WH-001, and how does that compare with today?',
  dict(feb20=num(total(e1, 'available')), today=num(total(w1, 'available')), change=num(total(w1, 'available') - total(e1, 'available'))),
  '2 月 20 日可用、今天可用、变化', 'available on Feb 20, available today, change')
q('Q-48', 'S03', 'medium', 'QA', 'LOT-001-B 收货以后都去了哪里？按事件说明数量。', 'Where did LOT-001-B go after it was received? Give the quantities by event.',
  dict(events=[dict(event=m['event_type_code'], source=m['source_location_id'] or None, destination=m['destination_location_id'] or None, quantity=num(number(m['quantity'])), date=m['event_date'])
               for m in EVENTS if m['lot_id'] == 'LOT-001-B']), '事件类型、来源、去向、数量、日期清单', 'list of event type, source, destination, quantity, date')
q('Q-49', 'S03', 'medium', 'QA', 'LOT-001-B 拆出了哪个子批次？拆了多少件？', 'Which child lot was split from LOT-001-B, and how many units?',
  dict(children={l['child_lot_id']: num(number(l['child_quantity'])) for l in T['lot_links'] if l['parent_lot_id'] == 'LOT-001-B'}), '子批次及件数', 'child lot and units')
reach = sorted({m['destination_location_id'] for m in EVENTS if m['lot_id'] in set(c1) and m['event_type_code'] in ('dispatch', 'arrive') and m['destination_location_id']}
               | {m['destination_location_id'] for m in EVENTS if m['lot_id'] in set(c1) and m['event_type_code'] == 'receive'})
q('Q-50', 'S03', 'medium', 'QA', 'REC-001 的问题批次一共到过哪些地点？', 'Which locations has REC-001 stock been to?',
  dict(locations=reach), '地点清单', 'location ids')


def main():
    assert len(QUESTIONS) == 50 and len({x['id'] for x in QUESTIONS}) == 50
    meta = dict(schema_version='1.0', set_id='retail-business-scenarios-v1', business_date=TODAY,
                prd='docs/PRD.zh-CN.md' if LANG == 'zh' else 'docs/PRD.en-US.md')
    dump = lambda data: yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)
    questions = [{k: v for k, v in x.items() if k != 'expected'} for x in QUESTIONS]
    answers = [dict(id=x['id'], question=x['question'], expected=x['expected']) for x in QUESTIONS]
    (HERE / 'question-set-v1.yaml').write_text(dump(dict(meta, audience='evaluated_agent', answer_set_access='forbidden', questions=questions)), encoding='utf-8')
    (HERE / 'answer-set-v1.yaml').write_text(dump(dict(meta, generation_method='independent CSV oracle (oracle.py with tools/retail_eval reference)', answers=answers)), encoding='utf-8')
    print(len(QUESTIONS), Counter(x['difficulty'] for x in QUESTIONS), Counter(x['role'] for x in QUESTIONS), Counter(x['scenario'] for x in QUESTIONS))


if __name__ == '__main__':
    main()
