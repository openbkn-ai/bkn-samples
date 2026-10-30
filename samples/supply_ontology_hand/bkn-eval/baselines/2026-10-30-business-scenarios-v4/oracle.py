#!/usr/bin/env python3
"""Independent raw-CSV oracle for the v4 business-scenario question set.

Reads only the delivered CSV fixtures. Does not import or call the sample's
functions, skills or earlier answer sets. Business rules follow docs/PRD.zh-CN.md
("业务口径"); every expected value is recomputed here with Decimal arithmetic.

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
FG = ['苏州成品仓', '乌鲁木齐成品仓', '哈尔滨成品仓']
PRODUCTION = ['苏州半成品仓', '苏州成品仓', '苏州电子原料仓',
              '苏州无人机原料仓', '苏州装配原料仓', '乌鲁木齐成品仓', '哈尔滨成品仓']


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


# ---- business facts (PRD 业务口径) -------------------------------------------

def unshipped(r):
    return int(r['signing_quantity']) - int(r['shipping_quantity'])


BACKLOG_ORDERS = sorted((r for r in SALES if unshipped(r) > 0),
                        key=lambda r: (r['promised_delivery_date'], r['sales_order_id']))
BACKLOG = defaultdict(int)
for r in BACKLOG_ORDERS:
    BACKLOG[r['product_code']] += unshipped(r)

OPEN_FORECASTS = [r for r in FORECASTS if r['closestatus_title'] != '已关闭']
OPEN_PO = [r for r in PO if r['rowclosestatus_title'] == '正常' and r['rowterminatestatus_title'] == '正常'
           and D(r['qty']) - D(r['actqty']) > 0]


def open_qty(r):
    return D(r['qty']) - D(r['actqty'])


OVERDUE_PO = [r for r in OPEN_PO if r['deliverdate'] < BUSINESS_DATE]


def pool(scope='all'):
    result = defaultdict(D)
    for r in INVENTORY:
        if r['stock_status'] == '可用' and (scope == 'all' or r['warehouse'] in scope):
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
    """可承诺量: finished goods + manufacturable quantity, net of this product's signed backlog."""
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


on_sale = [p for p in PRODUCTS if MAT[p]['product_status'] == '已上架']
q('Q-01', 'S01', '基础', 'PMC', '我们现在在售（已上架）的成品型号有几个？分在几条产品线？',
  dict(on_sale_models=len(on_sale), product_lines=len({PRODUCTS[p]['huid_productline_name'] for p in on_sale})),
  '型号数、产品线数')
q('Q-02', 'S01', '基础', '采购', '外购件 606-000989 的标准采购提前期是几天？',
  dict(purchase_lead_days=num(MAT['606-000989']['purchase_fixedleadtime'])), '天数')
level1 = structure('U00-000080', 1)
q('Q-03', 'S04', '基础', 'PMC', '车载终端 U00-000080 总装时直接投入的一级物料有几种？列出物料编码。',
  dict(count=len(level1), material_codes=level1), '种数与完整编码清单')
q('Q-04', 'S05', '基础', 'PMC', '382-000005 北斗导航农机驾驶仪在三个成品仓里还有多少可用库存？',
  dict(qty=num(pool(FG)['382-000005'])), '数量（套）')
q('Q-05', 'S02', '基础', 'PMC', '现在还有多少张销售订单没发完货？一共还欠客户多少套？',
  dict(orders=len(BACKLOG_ORDERS), unshipped_qty=sum(BACKLOG.values())), '订单数、欠交套数')
q('Q-06', 'S03', '基础', 'PMC', '手上还挂着多少张没关闭的需求预测？合计多少套？',
  dict(count=len(OPEN_FORECASTS), qty=num(sum((D(r['qty']) for r in OPEN_FORECASTS), D(0)))), '张数、套数')
q('Q-07', 'S08', '基础', '采购', '现在还有多少条采购订单行没收完货？已关闭、已终止的不算。',
  dict(lines=len(OPEN_PO)), '行数')
q('Q-08', 'S10', '基础', 'PMC', 'MRP 算出来但还没投放的计划订单有多少张？',
  dict(count=sum(r['dropstatus_title'] == '未投放' for r in MRP.values())), '张数')

oldest = BACKLOG_ORDERS[0]
q('Q-09', 'S02', '中等', 'PMC', '欠货的订单里有多少张已经过了承诺交期？拖得最久的是哪张单，拖了多少天？',
  dict(overdue_orders=sum(r['promised_delivery_date'] < BUSINESS_DATE for r in BACKLOG_ORDERS),
       oldest_order=oldest['sales_order_id'],
       days_late=(date.fromisoformat(BUSINESS_DATE) - date.fromisoformat(oldest['promised_delivery_date'])).days),
  '逾期单数、最久订单号、逾期天数')
customer = '武汉农兴农业科技有限公司'
mine = [r for r in BACKLOG_ORDERS if r['customer_name'] == customer]
q('Q-10', 'S02', '中等', 'PMC', f'{customer}还有哪些订单没发完？一共欠他们多少套？',
  dict(orders=sorted(r['sales_order_id'] for r in mine), unshipped_qty=sum(unshipped(r) for r in mine)),
  '完整订单号清单、欠交套数')
q('Q-11', 'S08', '中等', '采购', '已经过了交期还没到齐的采购行有多少？涉及多少家供应商？',
  dict(lines=len(OVERDUE_PO), suppliers=len({r['supplier_number'] for r in OVERDUE_PO})), '行数、供应商数')
top_supplier, top_lines = Counter(r['supplier_number'] for r in OVERDUE_PO).most_common(1)[0]
q('Q-12', 'S08', '中等', '采购', '逾期没到货的采购行最多的是哪家供应商？共多少行、还欠我们多少数量？',
  dict(supplier=SUPPLIERS[top_supplier]['supplier_name'], lines=top_lines,
       open_qty=num(sum((open_qty(r) for r in OVERDUE_PO if r['supplier_number'] == top_supplier), D(0)))),
  '供应商名称、行数、未到数量')
buyer = '杨强云'
buyer_suppliers = {s['supplier_code'] for s in SUPPLIERS.values() if s['purchaserid_name'] == buyer}
q('Q-13', 'S08', '中等', '采购', f'{buyer}负责的供应商里，有几家现在有逾期未到的采购行？',
  dict(suppliers=len(buyer_suppliers), with_overdue=len(buyer_suppliers & {r['supplier_number'] for r in OVERDUE_PO})),
  '负责供应商总数、其中有逾期的家数')
q('Q-14', 'S04', '中等', 'PMC', '密封圈 165-002537 用在哪些成品上？',
  dict(product_codes=where_used('165-002537')), '完整成品编码清单')
common = sorted(set(structure('367-000130')) & set(structure('367-000131')))
q('Q-15', 'S04', '中等', 'PMC', '两款 YN580 农业无人飞机（367-000130、367-000131）有多少种主料是通用的？',
  dict(shared_count=len(common)), '通用物料种数（全层级主料，不含替代料）')
bad = [r for r in INVENTORY if r['stock_status'] == '不良']
q('Q-16', 'S05', '中等', 'PMC', '有哪些库存被判为不良、不能投产？合计多少数量？',
  dict(material_codes=sorted({r['material_code'] for r in bad}),
       qty=num(sum((D(r['inventory_qty']) for r in bad), D(0)))), '完整物料编码清单、合计数量')
open_wo = [r for r in WORK_ORDERS if r['taskstatus_title'] != '完工']
q('Q-17', 'S10', '中等', 'PMC', '还没完工的生产工单有多少张？合计还有多少套没入库？',
  dict(work_orders=len(open_wo),
       remaining_qty=num(sum((D(r['qty']) - D(r['xkquainwaqty']) for r in open_wo), D(0)))), '工单数、未入库套数')
fc_by = defaultdict(D)
for r in OPEN_FORECASTS:
    fc_by[r['material_number']] += D(r['qty'])
top_fc = max(fc_by, key=fc_by.get)
q('Q-18', 'S03', '中等', 'PMC', '没关闭的预测里，哪个产品的预测量最大？是它现有成品库存的多少倍？',
  dict(product_code=top_fc, forecast_qty=num(fc_by[top_fc]), fg_qty=num(pool()[top_fc]),
       ratio=round(float(fc_by[top_fc] / pool()[top_fc]), 1)), '产品编码、预测量、成品库存、倍数（保留1位小数）')
window = [r for r in OPEN_PO if BUSINESS_DATE < r['deliverdate'] <= days_after(BUSINESS_DATE, 30)]
q('Q-19', 'S08', '中等', '采购', '接下来 30 天内按交期应到货的采购行有几行？来自几家供应商？',
  dict(lines=len(window), suppliers=len({r['supplier_number'] for r in window})), '行数、供应商数')
q('Q-20', 'S09', '中等', '采购', '贴片无源晶振 527-000017 今天下单的话，最早哪天能到？',
  dict(arrival_date=days_after(BUSINESS_DATE, MAT['527-000017']['purchase_fixedleadtime'])), '日期')
fg382 = pool()['382-000005']
q('Q-21', 'S06', '中等', 'PMC', '客户要 50 套 382-000005，能直接从成品库发吗？发完以后还能再承诺多少套现货？',
  dict(can_ship=fg382 - BACKLOG['382-000005'] >= 50,
       remaining_promisable_fg=num(fg382 - BACKLOG['382-000005'] - 50)), '能否、剩余可承诺现货')
in_plant = capacity('382-000005', lambda: pool(PRODUCTION))
company = capacity('382-000005', pool)
q('Q-22', 'S06', '中等', 'PMC', '只用苏州工厂生产七仓的料，最多能做多少套 382-000005？比用全公司库存少做多少？',
  dict(plant_buildable=in_plant, company_buildable=company, difference=company - in_plant), '工厂可做、全公司可做、差额')

fg = pool()
short = {p: BACKLOG[p] - num(fg[p]) for p in sorted(BACKLOG) if BACKLOG[p] > fg[p]}
q('Q-23', 'S02', '复杂', 'PMC', '哪些产品的欠货已经超过了成品现货？各差多少套？',
  dict(products=short), '完整产品清单及差额')
stuck = {}
for p, gap in short.items():
    build = capacity(p, pool)
    if build < gap:
        stuck[p] = gap - build
q('Q-24', 'S02', '复杂', 'PMC', '现货补完欠货后还不够的产品里，哪些靠现有库存也生产不出来？还差多少套？',
  dict(products=stuck), '完整产品清单及最终差额')
result, items = blockers('367-000097', BACKLOG['367-000097'])
q('Q-25', 'S06', '复杂', 'PMC', '625 农业无人飞机 367-000097 的欠单还差几套补不上？卡在哪些料？哪些可以催在途，哪些得新下单、最早哪天到？',
  dict(short_sets=num(result['make']),
       blocking_materials={i['material_code']: i['shortage_qty'] for i in items},
       chase_open_po=sorted(i['material_code'] for i in items if i['open_po_qty'] >= i['shortage_qty']),
       new_order_needed=sorted(i['material_code'] for i in items if i['open_po_qty'] < i['shortage_qty']),
       earliest_new_order_arrival=max(i['new_order_arrival'] for i in items if i['open_po_qty'] < i['shortage_qty'])),
  '缺口套数、卡料清单及缺量、可催在途料、需新下单料、最早齐料日期')
result, items = blockers('367-000130', BACKLOG['367-000130'])
no_po = [i for i in items if not i['open_po']]
longest = max(no_po, key=lambda i: (i['purchase_lead_days'], i['material_code']))
q('Q-26', 'S08', '复杂', '采购', '要补齐 YN580 农业无人飞机 367-000130 的欠单，哪些缺料完全没有在途、必须马上下单？其中最慢的是哪颗料、最早哪天到？',
  dict(no_open_po=sorted(i['material_code'] for i in no_po), slowest_material=longest['material_code'],
       arrival_date=longest['new_order_arrival']), '完整物料清单、最慢物料、到货日期')
orders = [r for r in BACKLOG_ORDERS if r['product_code'] == '526-000006']
left, unmet = fg['526-000006'], []
for r in orders:
    take = min(left, D(unshipped(r)))
    left -= take
    if take < unshipped(r):
        unmet.append(r['sales_order_id'])
remaining = BACKLOG['526-000006'] - num(fg['526-000006'])
q('Q-27', 'S07', '复杂', 'PMC', '526-000006 的欠单按承诺交期先后用现货补发，哪几张单补不上？差的部分能不能用现有库存生产出来？',
  dict(unmet_orders=unmet, remaining_qty=remaining,
       can_build=capacity('526-000006', pool) >= remaining), '补不上的订单号清单、差额、能否生产补足')
q('Q-28', 'S06', '复杂', 'PMC', '客户想再订 30 套 526-000006，现在最多能接多少套？',
  dict(accept_qty=min(30, atp('526-000006')['available_to_promise']), **atp('526-000006')), '可接套数')
plain, alt = atp('382-000005'), atp('382-000005', alternatives=True)
q('Q-29', 'S06', '复杂', 'PMC', '客户要 900 套 382-000005，现货加上用现有库存生产能满足吗？如果允许用替代料呢？',
  dict(without_substitutes=dict(can_accept=plain['available_to_promise'] >= 900, promisable=plain['available_to_promise']),
       with_substitutes=dict(can_accept=alt['available_to_promise'] >= 900, promisable=alt['available_to_promise'])),
  '不替代与允许替代两种情况的能否、可承诺量')
p61 = atp('P61-000351')
p61_fc = num(fc_by['P61-000351'])
q('Q-30', 'S03', '复杂', 'PMC', 'P61-000351 没关闭的预测有多少套？先保已签单的欠货，现有库存还能支撑多少套预测？缺口多少？',
  dict(forecast_qty=p61_fc, backlog_qty=p61['backlog_qty'], supported_qty=p61['available_to_promise'],
       gap_qty=p61_fc - p61['available_to_promise']), '预测量、欠交量、可支撑量、缺口')
stocks = stocks_after_backlog({'P61-000351', 'U00-000151'})
first = allocate('P61-000351', 60, stocks)
second = allocate('U00-000151', 50, stocks)
q('Q-31', 'S07', '复杂', 'PMC', '两个新单一起来：P61-000351 要 60 套、U00-000151 要 50 套。先保这两个产品的欠货，现有库存能同时接下吗？缺什么料、各缺多少？',
  dict(P61_000351=dict(covered=first['covered'], shortages={k: num(v) for k, v in first['gaps'].items()}),
       U00_000151=dict(covered=second['covered'], shortages={k: num(v) for k, v in second['gaps'].items()})),
  '两单各自能否满足及完整缺料清单')
users = where_used('527-000017')
q('Q-32', 'S04', '复杂', 'PMC', '贴片无源晶振 527-000017 用在哪些成品上？这些成品里，哪些的欠货光靠现货补不齐、必须生产，会被这颗料直接影响？各要生产多少套？',
  dict(product_codes=users,
       must_build={p: BACKLOG[p] - num(fg[p]) for p in users if BACKLOG[p] > fg[p]}),
  '完整成品清单、需生产补欠货的产品及套数')
q('Q-33', 'S09', '复杂', '采购', '382-000005 允许用替代料时最多还能做多少套？是哪颗料卡住的？这颗料有没有在途？',
  dict(buildable_qty=capacity('382-000005', pool, alternatives=True), limiting_material='606-000989',
       limiting_stock=num(pool()['606-000989']), has_open_po=bool(po_lines('606-000989'))),
  '可做套数、卡脖子物料、其库存、是否有在途')
need = allocate('367-000131', 100, pool(), finished=False)
q('Q-34', 'S10', '复杂', 'PMC', '下周想再排一张 100 套的 YN580 367-000131 生产工单，现有库存够不够？不够的话缺几种料、缺得最多的是哪颗？',
  dict(covered=need['covered'], shortage_material_count=len(need['gaps']),
       largest_shortage=max(need['gaps'], key=lambda k: (need['gaps'][k], k)) if need['gaps'] else None),
  '能否开工、缺料种数、缺量最大的物料')
trace_po, trace_material = '02-KSHA-CGDD-260402-012958', '849-000904'
po_row = next(r for r in PO if r['billno'] == trace_po and r['material_number'] == trace_material)
# Purchase request lines link to PO lines by line ID and material, as the knowledge network relation does.
pr_row = next(r for r in PR_LINES if r['entry_id'] == po_row['srcbillentryid'] and r['material_number'] == trace_material)
mrp_row = MRP[pr_row['srcbillnumber']]
fc_rows = [r for r in FORECASTS if r['billno'] == mrp_row['rootdemandbillno']]
q('Q-35', 'S10', '复杂', '采购', f'采购订单 {trace_po} 里 {trace_material} 这一行是从哪张请购单来的？请购又是哪张 MRP 计划订单生成的？最终是为哪张需求预测、哪个产品备的料？',
  dict(purchase_request=pr_row['billno'], mrp_plan_order=mrp_row['billno'],
       forecast=mrp_row['rootdemandbillno'], product_codes=sorted({r['material_number'] for r in fc_rows})),
  '请购单号、MRP计划单号、预测单号、产品编码')


q('Q-36', 'S01', '基础', '采购', '我们现在一共有多少家供应商建了档？',
  dict(suppliers=len(SUPPLIERS)), '家数')
rows382 = [r for r in SALES if r['product_code'] == '382-000005']
q('Q-37', 'S02', '基础', 'PMC', '382-000005 到现在一共签了多少套、发了多少套、还欠多少套？',
  dict(signed=sum(int(r['signing_quantity']) for r in rows382), shipped=sum(int(r['shipping_quantity']) for r in rows382),
       unshipped=BACKLOG['382-000005']), '签约、已发、欠交套数')
q('Q-38', 'S05', '基础', '采购', '物料 321-000569 现在全公司还有多少可用库存？',
  dict(qty=num(pool()['321-000569'])), '数量')
q('Q-39', 'S02', '基础', 'PMC', '现在还在执行中的销售订单有几张？',
  dict(orders=sum(r['order_status'] == '执行中' for r in SALES)), '张数')

today = [r for r in OPEN_PO if r['deliverdate'] == BUSINESS_DATE]
q('Q-40', 'S08', '中等', '采购', '今天按交期应该到货的采购有哪些？是哪家供应商、什么料、还差多少没到？',
  dict(lines=[dict(po=r['billno'], supplier=r['supplier_name'], material_code=r['material_number'],
                   open_qty=num(open_qty(r))) for r in today]), '完整采购行清单')
september = [r for r in OPEN_PO if r['deliverdate'][:7] == '2026-09']
q('Q-41', 'S08', '中等', '采购', '9 月份按交期要到货的采购行有多少行？来自几家供应商？',
  dict(lines=len(september), suppliers=len({r['supplier_number'] for r in september})), '行数、供应商数')
top3 = sorted(BACKLOG, key=lambda p: (-BACKLOG[p], p))[:3]
q('Q-42', 'S02', '中等', 'PMC', '欠货最多的三个产品是哪几个？各欠多少套？',
  dict(products={p: BACKLOG[p] for p in top3}), '产品编码及欠交套数，按欠交从多到少')
seller = '路霞'
theirs = [r for r in BACKLOG_ORDERS if r['salesperson'] == seller]
q('Q-43', 'S02', '中等', 'PMC', f'销售员{seller}手上还有多少张单没发完？一共欠多少套？其中多少张已经逾期？',
  dict(orders=len(theirs), unshipped_qty=sum(unshipped(r) for r in theirs),
       overdue=sum(r['promised_delivery_date'] < BUSINESS_DATE for r in theirs)), '单数、欠交套数、逾期单数')
q('Q-44', 'S08', '中等', '采购', '纸护角 606-001059 还有哪些采购没到？哪些已经逾期？',
  dict(lines=sorted(po_lines('606-001059'), key=lambda x: x['deliver_date'])), '完整采购行清单（订单号、未到数量、交期、是否逾期）')
zero = sorted(p for p in fc_by if pool()[p] == 0)
q('Q-45', 'S03', '中等', 'PMC', '有未关闭预测的产品里，哪些现在一套成品库存都没有？',
  dict(product_codes=zero), '完整产品编码清单')

stock_only = capacity('U00-000080', pool)
chased = capacity('U00-000080', lambda: pool_with_po(chase_overdue=True))
first_gap = allocate('U00-000080', stock_only + 1, pool(), finished=False)['gaps']
q('Q-46', 'S09', '复杂', 'PMC', 'U00-000080 车载终端用现有库存最多还能做多少套？再多做一套卡在哪颗料？如果逾期没到的采购都能催回来，最多能做多少套？',
  dict(stock_only_buildable=stock_only, first_blocking_materials=sorted(first_gap),
       with_overdue_po_chased=chased), '现有库存可做、卡住的物料、催回逾期在途后可做')
stocks = pool_with_po(chase_overdue=True)
for r in BACKLOG_ORDERS:
    if r['product_code'] == 'P61-000351':
        allocate('P61-000351', unshipped(r), stocks)
p61_new = allocate('P61-000351', 60, stocks)
q('Q-47', 'S07', '复杂', '采购', 'P61-000351 新来 60 套的单。先保它的欠货，如果所有没到的采购（包括逾期的）都能催回来，料够不够？还缺什么、缺多少？',
  dict(covered=p61_new['covered'], shortages={k: num(v) for k, v in p61_new['gaps'].items()}), '能否满足、完整缺料清单')
amp = '972-000677'
def enough(need, by):
    have = pool_with_po(need_by=by)[amp]
    return dict(available=num(have), covered=have >= need, short=num(max(D(0), D(need) - have)))
q('Q-48', 'S09', '复杂', 'PMC', f'D 类音频功放 {amp}，9 月 5 日前要投 500 个、9 月 15 日前累计要投 5000 个。库存加上按期到货的在途，两个时间点分别够不够？',
  dict(by_2026_09_05=enough(500, '2026-09-05'), by_2026_09_15=enough(5000, '2026-09-15')),
  '两个时间点各自的可用量、能否满足、缺口')
gain = {p: capacity(p, lambda: pool_with_po(need_by='2026-09-30')) - capacity(p, pool) for p in sorted(stuck)}
q('Q-49', 'S06', '复杂', 'PMC', '9 月底前按期到货的在途采购，能让欠货补不上的那几个产品各多做出几套？',
  dict(extra_buildable=gain), '每个产品可多做的套数')
result, items = blockers('367-000130', BACKLOG['367-000130'])
with_po = [i for i in items if i['open_po']]
q('Q-50', 'S08', '复杂', '采购', 'YN580 367-000130 欠单的缺料里，哪些有没到的采购可以催？把这些采购全催回来，够不够补上缺口？',
  dict(materials={i['material_code']: dict(shortage_qty=i['shortage_qty'], open_po_qty=i['open_po_qty'],
                                           enough=i['open_po_qty'] >= i['shortage_qty']) for i in with_po},
       other_materials_still_short=len(items) - len(with_po)),
  '可催物料清单（缺量、在途量、是否够）、仍需新下单的物料种数')


def main():
    meta = dict(schema_version='4.0', set_id='supply-business-scenarios-v4', business_date=BUSINESS_DATE,
                source_snapshot_date='2026-08-13', prd='docs/PRD.zh-CN.md')
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
