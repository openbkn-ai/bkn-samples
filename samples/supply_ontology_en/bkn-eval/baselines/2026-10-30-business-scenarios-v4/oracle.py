#!/usr/bin/env python3
"""Independent raw-CSV oracle for the v4 business-scenario question set.

Reads only the delivered CSV fixtures. Does not import or call the sample's
functions, skills or earlier answer sets. Business rules follow docs/PRD.en-US.md
("Business rules"); every expected value is recomputed here with Decimal arithmetic.

Writes question-set-v4.yaml (no answers) and answer-set-v4.yaml next to this file.
"""
import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[2] / 'data'
BUSINESS_DATE = '2026-08-25'
FG = ['Suzhou Finished Goods', 'Urumqi Finished Goods', 'Harbin Finished Goods']
PRODUCTION = ['Suzhou Subassemblies', 'Suzhou Finished Goods', 'Suzhou Electronics',
              'Suzhou Drone Materials', 'Suzhou Assembly', 'Urumqi Finished Goods', 'Harbin Finished Goods']


def load(name):
    return list(csv.DictReader((DATA / (name + '.csv')).open(encoding='utf-8-sig')))


PRODUCTS = {r['material_code']: r for r in load('hd_product_view')}
MAT = {r['material_code']: r for r in load('erp_material')}
SUPPLIERS = {r['supplier_code']: r for r in load('erp_supplier')}
BOM = load('erp_material_bom')
INVENTORY = load('erp_real_time_inventory')
SALES = load('sales_order')
FORECASTS = load('erp_mds_forecast')
PO = load('erp_purchase_order')
PR_LINES = load('erp_purchase_request')
MRP = {r['billno']: r for r in load('erp_mrp_plan_order')}
WORK_ORDERS = load('erp_production_work_order')


def num(x):
    x = D(x)
    return int(x) if x == x.to_integral_value() else float(round(x, 6))


def days_after(day, n):
    return (date.fromisoformat(day) + timedelta(days=int(D(n)))).isoformat()


# ---- business facts (PRD business rules) -------------------------------------------

def unshipped(r):
    return int(r['signing_quantity']) - int(r['shipping_quantity'])


BACKLOG_ORDERS = sorted((r for r in SALES if unshipped(r) > 0),
                        key=lambda r: (r['promised_delivery_date'], r['sales_order_id']))
BACKLOG = defaultdict(int)
for r in BACKLOG_ORDERS:
    BACKLOG[r['product_code']] += unshipped(r)

OPEN_FORECASTS = [r for r in FORECASTS if r['closestatus_title'] != 'Closed']
OPEN_PO = [r for r in PO if r['rowclosestatus_title'] == 'Open' and r['rowterminatestatus_title'] == 'Open'
           and D(r['qty']) - D(r['actqty']) > 0]


def open_qty(r):
    return D(r['qty']) - D(r['actqty'])


OVERDUE_PO = [r for r in OPEN_PO if r['deliverdate'] < BUSINESS_DATE]


def pool(scope='all'):
    result = defaultdict(D)
    for r in INVENTORY:
        if r['stock_status'] == 'Available' and (scope == 'all' or r['warehouse'] in scope):
            result[r['material_code']] += D(r['available_inventory_qty'] or 0)
    return result


def pool_with_po(need_by=None, chase_overdue=False):
    """Stock plus in-transit: lines due from today to `need_by`, and overdue lines only when chased back."""
    result = pool()
    for r in OPEN_PO:
        due = r['deliverdate'] >= BUSINESS_DATE and (need_by is None or r['deliverdate'] <= need_by)
        if due or (chase_overdue and r['deliverdate'] < BUSINESS_DATE):
            result[r['material_number']] += open_qty(r)
    return result


# ---- BOM netting (same rules as the v3 oracle, generalised to every product) --

def main_row(r):
    return int(r['alt_priority'] or 0) == 0 and r['alt_part'] != '√'


TEMPLATES = {}
for product in PRODUCTS:
    rows = [r for r in BOM if r['bom_material_code'] == product]
    occurrences = Counter((int(r['bom_level']), r['material_code']) for r in rows)
    groups = defaultdict(list)
    for r in rows:
        if int(r['bom_level']) > 0:
            groups[int(r['bom_level']), r['parent_material_code']].append(r)
    for (level, parent), children in groups.items():
        size = len(children) // occurrences[level - 1, parent]
        TEMPLATES[product, level - 1, parent] = children[:size]


def structure(product, level=None):
    return sorted({r['material_code'] for r in BOM if r['bom_material_code'] == product and main_row(r)
                   and int(r['bom_level']) > 0 and (level is None or int(r['bom_level']) == level)})


def where_used(material):
    return sorted({r['bom_material_code'] for r in BOM if r['material_code'] == material and main_row(r)
                   and int(r['bom_level']) > 0})


def positions(product, level, parent, alternatives):
    rows = TEMPLATES.get((product, level, parent), [])
    result = []
    for row in rows:
        if not main_row(row):
            continue
        candidates = [row]
        if alternatives and row['alt_group_no'] not in ('', '0'):
            candidates = [r for r in rows if r['alt_group_no'] == row['alt_group_no']]
        result.append(candidates)
    return result


def allocate(product, qty, stocks, alternatives=False, finished=True):
    """Finished goods first, then each BOM level's stock before expanding the net shortage."""
    gaps = defaultdict(D)
    qty = D(qty)
    fg = min(qty, max(D(0), stocks[product])) if finished else D(0)
    stocks[product] -= fg

    def children(parent, count, level):
        for candidates in positions(product, level, parent, alternatives):
            row = max(candidates, key=lambda r: (min(count, max(D(0), stocks[r['material_code']]) / D(r['standard_usage'])),
                                                 main_row(r), -int(r['seq_no'])))
            code = row['material_code']
            required = count * D(row['standard_usage'])
            used = min(required, max(D(0), stocks[code]))
            stocks[code] -= used
            if required > used:
                if positions(product, level + 1, code, alternatives):
                    children(code, required - used, level + 1)
                else:
                    gaps[code] += required - used

    if qty > fg:
        children(product, qty - fg, 0)
    return dict(fg=fg, make=qty - fg, covered=not gaps, gaps=dict(sorted(gaps.items())))


def capacity(product, stocks_factory, alternatives=False):
    """Largest quantity current stock can still manufacture (finished goods excluded)."""
    def ok(n):
        return allocate(product, n, stocks_factory(), alternatives, finished=False)['covered']
    low, high = 0, 1
    while ok(high):
        low, high = high, high * 2
    while low + 1 < high:
        mid = (low + high) // 2
        low, high = (mid, high) if ok(mid) else (low, mid)
    return low


def stocks_after_backlog(products, scope='all'):
    """Shared pool after the signed backlog of `products` (due-date order) has been reserved."""
    stocks = pool(scope)
    for r in BACKLOG_ORDERS:
        if r['product_code'] in products:
            allocate(r['product_code'], unshipped(r), stocks)
    return stocks


def atp(product, alternatives=False):
    """Available to promise: finished goods + manufacturable quantity, net of this product's signed backlog."""
    fg = pool()[product]
    build = capacity(product, pool, alternatives)
    return dict(fg_qty=num(fg), buildable_qty=build, backlog_qty=BACKLOG[product],
                available_to_promise=num(max(D(0), fg + build - BACKLOG[product])))


def po_lines(material):
    return [dict(po=r['billno'], supplier=r['supplier_name'], open_qty=num(open_qty(r)),
                 deliver_date=r['deliverdate'], overdue=r['deliverdate'] < BUSINESS_DATE)
            for r in OPEN_PO if r['material_number'] == material]


def blockers(product, qty):
    """Leaf shortages for `qty` after FG, with open PO and new-order arrival for each."""
    result = allocate(product, qty, pool())
    items = []
    for code, gap in result['gaps'].items():
        lines = po_lines(code)
        items.append(dict(material_code=code, material_name=MAT[code]['material_name'], shortage_qty=num(gap),
                          open_po_qty=num(sum((D(x['open_qty']) for x in lines), D(0))),
                          open_po=lines, purchase_lead_days=num(MAT[code]['purchase_fixedleadtime']),
                          new_order_arrival=days_after(BUSINESS_DATE, MAT[code]['purchase_fixedleadtime'])))
    return result, items


# ---- questions --------------------------------------------------------------

QUESTIONS = []


def q(qid, scenario, level, role, question, expected, contract):
    QUESTIONS.append(dict(id=qid, scenario=scenario, difficulty=level, role=role, question=question,
                          output_contract=contract, expected=expected))


on_sale = [p for p in PRODUCTS if MAT[p]['product_status'] == 'Listed']
q('Q-01', 'S01', 'basic', 'PMC', 'How many finished-goods models do we currently sell (listed), and across how many product lines?',
  dict(on_sale_models=len(on_sale), product_lines=len({PRODUCTS[p]['huid_productline_name'] for p in on_sale})),
  'model count, product line count')
q('Q-02', 'S01', 'basic', 'Purchasing', 'What is the standard purchasing lead time for bought-in part 606-000989, in days?',
  dict(purchase_lead_days=num(MAT['606-000989']['purchase_fixedleadtime'])), 'days')
level1 = structure('U00-000080', 1)
q('Q-03', 'S04', 'basic', 'PMC', 'How many first-level materials go straight into final assembly of vehicle terminal U00-000080? List the material codes.',
  dict(count=len(level1), material_codes=level1), 'count and full list of codes')
q('Q-04', 'S05', 'basic', 'PMC', 'How much available stock of 382-000005, the BeiDou navigation farm autopilot, is left in the three finished-goods warehouses?',
  dict(qty=num(pool(FG)['382-000005'])), 'quantity (units)')
q('Q-05', 'S02', 'basic', 'PMC', 'How many sales orders are not fully shipped yet, and how many units do we still owe customers in total?',
  dict(orders=len(BACKLOG_ORDERS), unshipped_qty=sum(BACKLOG.values())), 'order count, units owed')
q('Q-06', 'S03', 'basic', 'PMC', 'How many demand forecasts are still open, and how many units do they add up to?',
  dict(count=len(OPEN_FORECASTS), qty=num(sum((D(r['qty']) for r in OPEN_FORECASTS), D(0)))), 'forecast count, units')
q('Q-07', 'S08', 'basic', 'Purchasing', "How many purchase order lines are still waiting for goods? Closed and terminated lines don't count.",
  dict(lines=len(OPEN_PO)), 'line count')
q('Q-08', 'S10', 'basic', 'PMC', 'How many MRP planned orders have been calculated but not released yet?',
  dict(count=sum(r['dropstatus_title'] == 'Not Released' for r in MRP.values())), 'order count')

oldest = BACKLOG_ORDERS[0]
q('Q-09', 'S02', 'medium', 'PMC', 'Among the orders we still owe, how many are past their promised date? Which one is the most overdue, and by how many days?',
  dict(overdue_orders=sum(r['promised_delivery_date'] < BUSINESS_DATE for r in BACKLOG_ORDERS),
       oldest_order=oldest['sales_order_id'],
       days_late=(date.fromisoformat(BUSINESS_DATE) - date.fromisoformat(oldest['promised_delivery_date'])).days),
  'overdue order count, most overdue order, days overdue')
customer = 'Cypressridge Agri'
mine = [r for r in BACKLOG_ORDERS if r['customer_name'] == customer]
q('Q-10', 'S02', 'medium', 'PMC', "Which of Cypressridge Agri's orders are not fully shipped yet, and how many units do we owe them in total?",
  dict(orders=sorted(r['sales_order_id'] for r in mine), unshipped_qty=sum(unshipped(r) for r in mine)),
  'full list of order numbers, units owed')
q('Q-11', 'S08', 'medium', 'Purchasing', 'How many purchase lines are past their due date and still not fully received? How many suppliers do they involve?',
  dict(lines=len(OVERDUE_PO), suppliers=len({r['supplier_number'] for r in OVERDUE_PO})), 'line count, supplier count')
top_supplier, top_lines = Counter(r['supplier_number'] for r in OVERDUE_PO).most_common(1)[0]
q('Q-12', 'S08', 'medium', 'Purchasing', 'Which supplier has the most overdue purchase lines? How many lines, and how much do they still owe us?',
  dict(supplier=SUPPLIERS[top_supplier]['supplier_name'], lines=top_lines,
       open_qty=num(sum((open_qty(r) for r in OVERDUE_PO if r['supplier_number'] == top_supplier), D(0)))),
  'supplier name, line count, open quantity')
buyer = 'Alex Reed'
buyer_suppliers = {s['supplier_code'] for s in SUPPLIERS.values() if s['purchaserid_name'] == buyer}
q('Q-13', 'S08', 'medium', 'Purchasing', 'Of the suppliers Alex Reed is responsible for, how many currently have overdue purchase lines?',
  dict(suppliers=len(buyer_suppliers), with_overdue=len(buyer_suppliers & {r['supplier_number'] for r in OVERDUE_PO})),
  'suppliers handled, of which with overdue lines')
q('Q-14', 'S04', 'medium', 'PMC', 'Which finished products use seal ring 165-002537?',
  dict(product_codes=where_used('165-002537')), 'full list of product codes')
common = sorted(set(structure('367-000130')) & set(structure('367-000131')))
q('Q-15', 'S04', 'medium', 'PMC', 'How many main-part materials do the two YN580 agricultural drones (367-000130 and 367-000131) have in common?',
  dict(shared_count=len(common)), 'shared material count (main parts at all levels, no alternates)')
bad = [r for r in INVENTORY if r['stock_status'] == 'Defective']
q('Q-16', 'S05', 'medium', 'PMC', 'Which stock has been judged defective and cannot go into production? What is the total quantity?',
  dict(material_codes=sorted({r['material_code'] for r in bad}),
       qty=num(sum((D(r['inventory_qty']) for r in bad), D(0)))), 'full list of material codes, total quantity')
open_wo = [r for r in WORK_ORDERS if r['taskstatus_title'] != 'Complete']
q('Q-17', 'S10', 'medium', 'PMC', 'How many production work orders are not complete yet, and how many units have not been received into stock?',
  dict(work_orders=len(open_wo),
       remaining_qty=num(sum((D(r['qty']) - D(r['xkquainwaqty']) for r in open_wo), D(0)))), 'work order count, units not received')
fc_by = defaultdict(D)
for r in OPEN_FORECASTS:
    fc_by[r['material_number']] += D(r['qty'])
top_fc = max(fc_by, key=fc_by.get)
q('Q-18', 'S03', 'medium', 'PMC', 'Among the open forecasts, which product has the largest forecast quantity? How many times its current finished-goods stock is that?',
  dict(product_code=top_fc, forecast_qty=num(fc_by[top_fc]), fg_qty=num(pool()[top_fc]),
       ratio=round(float(fc_by[top_fc] / pool()[top_fc]), 1)), 'product code, forecast quantity, finished-goods stock, ratio (1 decimal)')
window = [r for r in OPEN_PO if BUSINESS_DATE < r['deliverdate'] <= days_after(BUSINESS_DATE, 30)]
q('Q-19', 'S08', 'medium', 'Purchasing', 'How many purchase lines are due to arrive in the next 30 days, and from how many suppliers?',
  dict(lines=len(window), suppliers=len({r['supplier_number'] for r in window})), 'line count, supplier count')
q('Q-20', 'S09', 'medium', 'Purchasing', 'If we order SMD crystal 527-000017 today, what is the earliest date it can arrive?',
  dict(arrival_date=days_after(BUSINESS_DATE, MAT['527-000017']['purchase_fixedleadtime'])), 'date')
fg382 = pool()['382-000005']
q('Q-21', 'S06', 'medium', 'PMC', 'A customer wants 50 units of 382-000005. Can we ship them straight from finished goods? After that, how many more units of stock on hand can we still promise?',
  dict(can_ship=fg382 - BACKLOG['382-000005'] >= 50,
       remaining_promisable_fg=num(fg382 - BACKLOG['382-000005'] - 50)), 'yes/no, remaining promisable stock on hand')
in_plant = capacity('382-000005', lambda: pool(PRODUCTION))
company = capacity('382-000005', pool)
q('Q-22', 'S06', 'medium', 'PMC', 'Using only materials in the seven Suzhou plant production warehouses, how many units of 382-000005 can we build at most? How many fewer is that than using stock across the company?',
  dict(plant_buildable=in_plant, company_buildable=company, difference=company - in_plant), 'plant buildable, company buildable, difference')

fg = pool()
short = {p: BACKLOG[p] - num(fg[p]) for p in sorted(BACKLOG) if BACKLOG[p] > fg[p]}
q('Q-23', 'S02', 'complex', 'PMC', 'Which products already owe customers more than we have in finished-goods stock? By how many units each?',
  dict(products=short), 'full product list with gaps')
stuck = {}
for p, gap in short.items():
    build = capacity(p, pool)
    if build < gap:
        stuck[p] = gap - build
q('Q-24', 'S02', 'complex', 'PMC', "Of the products where finished goods can't cover the backlog, which can't be built from current stock either? How many units short is each?",
  dict(products=stuck), 'full product list with final gaps')
result, items = blockers('367-000097', BACKLOG['367-000097'])
q('Q-25', 'S06', 'complex', 'PMC', "For the 625 agricultural drone 367-000097, how many backlog units can't be covered? Which materials block it? Which can we expedite from open purchase orders, which need a new order, and what is the earliest date everything is in?",
  dict(short_sets=num(result['make']),
       blocking_materials={i['material_code']: i['shortage_qty'] for i in items},
       chase_open_po=sorted(i['material_code'] for i in items if i['open_po_qty'] >= i['shortage_qty']),
       new_order_needed=sorted(i['material_code'] for i in items if i['open_po_qty'] < i['shortage_qty']),
       earliest_new_order_arrival=max(i['new_order_arrival'] for i in items if i['open_po_qty'] < i['shortage_qty'])),
  'units short, blocking materials and quantities, materials to expedite, materials to order, earliest complete date')
result, items = blockers('367-000130', BACKLOG['367-000130'])
no_po = [i for i in items if not i['open_po']]
longest = max(no_po, key=lambda i: (i['purchase_lead_days'], i['material_code']))
q('Q-26', 'S08', 'complex', 'Purchasing', 'To clear the backlog for the YN580 agricultural drone 367-000130, which short materials have no open purchase order at all and must be ordered right away? Which is the slowest, and when is the earliest it can arrive?',
  dict(no_open_po=sorted(i['material_code'] for i in no_po), slowest_material=longest['material_code'],
       arrival_date=longest['new_order_arrival']), 'full material list, slowest material, arrival date')
orders = [r for r in BACKLOG_ORDERS if r['product_code'] == '526-000006']
left, unmet = fg['526-000006'], []
for r in orders:
    take = min(left, D(unshipped(r)))
    left -= take
    if take < unshipped(r):
        unmet.append(r['sales_order_id'])
remaining = BACKLOG['526-000006'] - num(fg['526-000006'])
q('Q-27', 'S07', 'complex', 'PMC', "If we ship the 526-000006 backlog from stock on hand in promised-date order, which orders can't be filled? Can the shortfall be built from current stock?",
  dict(unmet_orders=unmet, remaining_qty=remaining,
       can_build=capacity('526-000006', pool) >= remaining), 'unfilled order numbers, shortfall, whether it can be built')
q('Q-28', 'S06', 'complex', 'PMC', 'A customer wants another 30 units of 526-000006. How many can we accept right now?',
  dict(accept_qty=min(30, atp('526-000006')['available_to_promise']), **atp('526-000006')), 'units accepted')
plain, alt = atp('382-000005'), atp('382-000005', alternatives=True)
q('Q-29', 'S06', 'complex', 'PMC', 'A customer wants 900 units of 382-000005. Can stock on hand plus what we can build from current stock cover it? What if alternates are allowed?',
  dict(without_substitutes=dict(can_accept=plain['available_to_promise'] >= 900, promisable=plain['available_to_promise']),
       with_substitutes=dict(can_accept=alt['available_to_promise'] >= 900, promisable=alt['available_to_promise'])),
  'yes/no and promisable quantity without and with alternates')
p61 = atp('P61-000351')
p61_fc = num(fc_by['P61-000351'])
q('Q-30', 'S03', 'complex', 'PMC', 'How many units of open forecast does P61-000351 have? After protecting the signed backlog, how much of that forecast can current stock support, and what is the gap?',
  dict(forecast_qty=p61_fc, backlog_qty=p61['backlog_qty'], supported_qty=p61['available_to_promise'],
       gap_qty=p61_fc - p61['available_to_promise']), 'forecast quantity, backlog, supported quantity, gap')
stocks = stocks_after_backlog({'P61-000351', 'U00-000151'})
first = allocate('P61-000351', 60, stocks)
second = allocate('U00-000151', 50, stocks)
q('Q-31', 'S07', 'complex', 'PMC', "Two new orders arrive together: 60 units of P61-000351 and 50 units of U00-000151. Protecting both products' backlog first, can current stock take both? What is short, and by how much?",
  dict(P61_000351=dict(covered=first['covered'], shortages={k: num(v) for k, v in first['gaps'].items()}),
       U00_000151=dict(covered=second['covered'], shortages={k: num(v) for k, v in second['gaps'].items()})),
  'coverage per order and full shortage list')
users = where_used('527-000017')
q('Q-32', 'S04', 'complex', 'PMC', "Which finished products use SMD crystal 527-000017? Among them, which have backlog that finished goods can't cover, so they must be built and are directly affected by this part? How many units must each build?",
  dict(product_codes=users,
       must_build={p: BACKLOG[p] - num(fg[p]) for p in users if BACKLOG[p] > fg[p]}),
  'full product list, products that must build and units')
q('Q-33', 'S09', 'complex', 'Purchasing', 'With alternates allowed, how many more units of 382-000005 can we build at most? Which material is the bottleneck, and does it have any open purchase order?',
  dict(buildable_qty=capacity('382-000005', pool, alternatives=True), limiting_material='606-000989',
       limiting_stock=num(pool()['606-000989']), has_open_po=bool(po_lines('606-000989'))),
  'buildable units, bottleneck material, its stock, open purchase order or not')
need = allocate('367-000131', 100, pool(), finished=False)
q('Q-34', 'S10', 'complex', 'PMC', 'Next week we want to schedule another work order for 100 units of YN580 367-000131. Is current stock enough? If not, how many materials are short, and which is short the most?',
  dict(covered=need['covered'], shortage_material_count=len(need['gaps']),
       largest_shortage=max(need['gaps'], key=lambda k: (need['gaps'][k], k)) if need['gaps'] else None),
  'can it start, short material count, largest shortage')
trace_po, trace_material = '02-KSHA-CGDD-260402-012958', '849-000904'
po_row = next(r for r in PO if r['billno'] == trace_po and r['material_number'] == trace_material)
# Purchase request lines link to PO lines by line ID and material, as the knowledge network relation does.
pr_row = next(r for r in PR_LINES if r['entry_id'] == po_row['srcbillentryid'] and r['material_number'] == trace_material)
mrp_row = MRP[pr_row['srcbillnumber']]
fc_rows = [r for r in FORECASTS if r['billno'] == mrp_row['rootdemandbillno']]
q('Q-35', 'S10', 'complex', 'Purchasing', 'Purchase order 02-KSHA-CGDD-260402-012958, line 849-000904: which purchase requisition did it come from? Which MRP planned order generated that requisition? In the end, which forecast and which product was the material bought for?',
  dict(purchase_request=pr_row['billno'], mrp_plan_order=mrp_row['billno'],
       forecast=mrp_row['rootdemandbillno'], product_codes=sorted({r['material_number'] for r in fc_rows})),
  'requisition number, MRP order number, forecast number, product codes')


q('Q-36', 'S01', 'basic', 'Purchasing', 'How many suppliers do we have on file in total?',
  dict(suppliers=len(SUPPLIERS)), 'supplier count')
rows382 = [r for r in SALES if r['product_code'] == '382-000005']
q('Q-37', 'S02', 'basic', 'PMC', 'For 382-000005, how many units have been signed, shipped and are still owed to date?',
  dict(signed=sum(int(r['signing_quantity']) for r in rows382), shipped=sum(int(r['shipping_quantity']) for r in rows382),
       unshipped=BACKLOG['382-000005']), 'signed, shipped, owed units')
q('Q-38', 'S05', 'basic', 'Purchasing', 'How much available stock of material 321-000569 is there across the company right now?',
  dict(qty=num(pool()['321-000569'])), 'quantity')
q('Q-39', 'S02', 'basic', 'PMC', 'How many sales orders are still in progress?',
  dict(orders=sum(r['order_status'] == 'In Progress' for r in SALES)), 'order count')

today = [r for r in OPEN_PO if r['deliverdate'] == BUSINESS_DATE]
q('Q-40', 'S08', 'medium', 'Purchasing', 'Which purchases are due to arrive today? From which supplier, which material, and how much is still outstanding?',
  dict(lines=[dict(po=r['billno'], supplier=r['supplier_name'], material_code=r['material_number'],
                   open_qty=num(open_qty(r))) for r in today]), 'full list of purchase lines')
september = [r for r in OPEN_PO if r['deliverdate'][:7] == '2026-09']
q('Q-41', 'S08', 'medium', 'Purchasing', 'How many purchase lines are due to arrive in September, and from how many suppliers?',
  dict(lines=len(september), suppliers=len({r['supplier_number'] for r in september})), 'line count, supplier count')
top3 = sorted(BACKLOG, key=lambda p: (-BACKLOG[p], p))[:3]
q('Q-42', 'S02', 'medium', 'PMC', 'Which three products have the biggest backlog, and how many units does each owe?',
  dict(products={p: BACKLOG[p] for p in top3}), 'product codes and units owed, largest first')
seller = 'Joel Hayes'
theirs = [r for r in BACKLOG_ORDERS if r['salesperson'] == seller]
q('Q-43', 'S02', 'medium', 'PMC', 'How many orders does salesperson Joel Hayes still have not fully shipped? How many units are owed, and how many of those orders are overdue?',
  dict(orders=len(theirs), unshipped_qty=sum(unshipped(r) for r in theirs),
       overdue=sum(r['promised_delivery_date'] < BUSINESS_DATE for r in theirs)), 'order count, units owed, overdue order count')
q('Q-44', 'S08', 'medium', 'Purchasing', "Which purchases of cardboard corner protector 606-001059 haven't arrived yet? Which of them are overdue?",
  dict(lines=sorted(po_lines('606-001059'), key=lambda x: x['deliver_date'])), 'full list of purchase lines (order number, open quantity, due date, overdue or not)')
zero = sorted(p for p in fc_by if pool()[p] == 0)
q('Q-45', 'S03', 'medium', 'PMC', 'Among products with open forecasts, which have no finished-goods stock at all right now?',
  dict(product_codes=zero), 'full list of product codes')

stock_only = capacity('U00-000080', pool)
chased = capacity('U00-000080', lambda: pool_with_po(chase_overdue=True))
first_gap = allocate('U00-000080', stock_only + 1, pool(), finished=False)['gaps']
q('Q-46', 'S09', 'complex', 'PMC', 'How many more units of vehicle terminal U00-000080 can current stock build at most? Which material blocks one more unit? If every overdue purchase could be chased in, how many could we build?',
  dict(stock_only_buildable=stock_only, first_blocking_materials=sorted(first_gap),
       with_overdue_po_chased=chased), 'buildable from stock, blocking material, buildable with overdue purchases chased')
stocks = pool_with_po(chase_overdue=True)
for r in BACKLOG_ORDERS:
    if r['product_code'] == 'P61-000351':
        allocate('P61-000351', unshipped(r), stocks)
p61_new = allocate('P61-000351', 60, stocks)
q('Q-47', 'S07', 'complex', 'Purchasing', 'A new order for 60 units of P61-000351 has come in. Protecting its backlog first, if every open purchase (overdue ones included) could be chased in, would materials be enough? What would still be short, and by how much?',
  dict(covered=p61_new['covered'], shortages={k: num(v) for k, v in p61_new['gaps'].items()}), 'covered or not, full shortage list')
amp = '972-000677'
def enough(need, by):
    have = pool_with_po(need_by=by)[amp]
    return dict(available=num(have), covered=have >= need, short=num(max(D(0), D(need) - have)))
q('Q-48', 'S09', 'complex', 'PMC', 'For class-D audio amplifier 972-000677, we need to issue 500 to production by September 5 and 5,000 cumulative by September 15. With stock plus purchases arriving on schedule, is there enough at each point?',
  dict(by_2026_09_05=enough(500, '2026-09-05'), by_2026_09_15=enough(5000, '2026-09-15')),
  'available quantity, coverage and gap at each date')
gain = {p: capacity(p, lambda: pool_with_po(need_by='2026-09-30')) - capacity(p, pool) for p in sorted(stuck)}
q('Q-49', 'S06', 'complex', 'PMC', "For the products whose backlog can't be covered, how many more units would purchases arriving on schedule before the end of September let each of them build?",
  dict(extra_buildable=gain), 'extra units per product')
result, items = blockers('367-000130', BACKLOG['367-000130'])
with_po = [i for i in items if i['open_po']]
q('Q-50', 'S08', 'complex', 'Purchasing', 'Among the short materials for the YN580 367-000130 backlog, which have open purchases we can expedite? If all of those purchases came in, would it close the gap?',
  dict(materials={i['material_code']: dict(shortage_qty=i['shortage_qty'], open_po_qty=i['open_po_qty'],
                                           enough=i['open_po_qty'] >= i['shortage_qty']) for i in with_po},
       # chasing every open line also refills upstream assemblies, so the remaining gaps come from netting again
       still_short_after_chasing=sorted(allocate('367-000130', BACKLOG['367-000130'], pool_with_po(chase_overdue=True))['gaps'])),
  'expeditable materials (shortage, open quantity, enough or not), materials still short after chasing everything')


def main():
    meta = dict(schema_version='4.0', set_id='supply-business-scenarios-v4', business_date=BUSINESS_DATE,
                source_snapshot_date='2026-08-13', prd='docs/PRD.en-US.md')
    questions = [{k: v for k, v in x.items() if k != 'expected'} for x in QUESTIONS]
    answers = [dict(id=x['id'], question=x['question'], expected=x['expected'],
                    answer=json.dumps(x['expected'], ensure_ascii=False, default=str)) for x in QUESTIONS]
    dump = lambda data: yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)
    (HERE / 'question-set-v4.yaml').write_text(
        dump(dict(meta, audience='evaluated_agent', answer_set_access='forbidden', questions=questions)), encoding='utf-8')
    (HERE / 'answer-set-v4.yaml').write_text(
        dump(dict(meta, generation_method='independent raw CSV Decimal oracle (oracle.py)', answers=answers)), encoding='utf-8')
    print(f'{len(QUESTIONS)} questions:', Counter(x['difficulty'] for x in QUESTIONS))


if __name__ == '__main__':
    main()
