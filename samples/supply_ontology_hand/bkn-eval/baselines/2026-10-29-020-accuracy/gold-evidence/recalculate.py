#!/usr/bin/env python3
"""Independent raw-CSV oracle. Does not import or call evaluated functions.

BOM fixtures are breadth-first expanded trees, including alternative branches.
Repeated occurrences of one parent carry repeated identical child sequences.
Validate and partition those sequences before traversing a selected branch.
All arithmetic is Decimal; each candidate uses its own standard_usage.
"""
import csv
import os
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SAMPLE = BASE.parents[2]
DATA = Path(os.environ.get('SUPPLY_DATA_DIR', str(SAMPLE / 'data')))
D = Decimal
P = '382-000005'
Q = 'P61-000351'
U = 'U00-000151'
V = 'U00-000080'
FG = ['苏州成品仓', '乌鲁木齐成品仓', '哈尔滨成品仓']
PRODUCTION = ['苏州半成品仓', '苏州成品仓', '苏州电子原料仓',
              '苏州无人机原料仓', '苏州装配原料仓', '乌鲁木齐成品仓', '哈尔滨成品仓']
FILES = ['hd_product_view', 'erp_material', 'erp_supplier', 'sales_order',
         'erp_real_time_inventory', 'erp_mds_forecast', 'erp_material_bom', 'erp_purchase_order']
RAW = {name: list(csv.DictReader((DATA / (name + '.csv')).open(encoding='utf-8-sig')))
       for name in FILES}
BOM = RAW['erp_material_bom']
MAT = {r['material_code']: r for r in RAW['erp_material']}

def number(x):
    return int(x) if D(x) == D(x).to_integral_value() else float(x)

def main(row):
    return int(row['alt_priority'] or 0) == 0

def structure(product, level=None):
    return [r for r in BOM if r['bom_material_code'] == product and main(r)
            and int(r['bom_level']) > 0 and (level is None or int(r['bom_level']) == level)]

def codes(product, level=None):
    return sorted({r['material_code'] for r in structure(product, level)})

def pool(scope='production_available', include_po=False):
    result = defaultdict(D)
    warehouses = None if scope == 'all' else (PRODUCTION if scope == 'production_available' else FG)
    for r in RAW['erp_real_time_inventory']:
        if r['stock_status'] == '可用' and (warehouses is None or r['warehouse'] in warehouses):
            result[r['material_code']] += D(r['available_inventory_qty'] or 0)
    if include_po:
        for row in RAW['erp_purchase_order']:
            if row['rowclosestatus_title'] != '已关闭':
                result[row['material_number']] += max(D(0), D(row['qty'] or 0)-D(row['actqty'] or 0))
    return result

TEMPLATES = {}
REPEATED = []
for product in (P, Q, U, V):
    rows = [r for r in BOM if r['bom_material_code'] == product]
    occurrences = Counter((int(r['bom_level']), r['material_code']) for r in rows)
    groups = defaultdict(list)
    for r in rows:
        if int(r['bom_level']) > 0:
            groups[int(r['bom_level']), r['parent_material_code']].append(r)
    for (level, parent), children in groups.items():
        n = occurrences[level - 1, parent]
        assert n > 0 and len(children) % n == 0, (product, level, parent)
        size = len(children) // n
        signature = lambda xs: [(x['material_code'], x['standard_usage'], x['alt_group_no'],
                                  x['alt_priority'], x['alt_part']) for x in xs]
        assert all(signature(children[i*size:(i+1)*size]) == signature(children[:size])
                   for i in range(n)), (product, level, parent, 'inconsistent child occurrences')
        TEMPLATES[product, level-1, parent] = children[:size]
        if n > 1:
            REPEATED.append(dict(product=product, parent=parent, child_level=level,
                                 occurrences=n, raw_child_rows=len(children), rows_per_occurrence=size))

def positions(product, level, parent, alternatives):
    rows = TEMPLATES.get((product, level, parent), [])
    result = []
    for row in rows:
        if not main(row):
            continue
        candidates = [row]
        group = row['alt_group_no']
        if alternatives and group not in ('', '0'):
            candidates = [r for r in rows if r['alt_group_no'] == group]
        result.append(candidates)
    return result

def allocate(product, qty, stocks=None, alternatives=False, scope='production_available', finished=False, include_po=False):
    stocks = pool(scope, include_po) if stocks is None else stocks
    gaps = defaultdict(D)
    trace = []
    qty = D(qty)
    fg = min(qty, max(D(0), stocks[product])) if finished else D(0)
    if finished:
        stocks[product] -= fg
    def children(parent, count, level, path):
        for candidates in positions(product, level, parent, alternatives):
            # Current on-hand coverage; do not mix candidates or look into future PO.
            row = max(candidates, key=lambda r: (min(count, max(D(0), stocks[r['material_code']]) / D(r['standard_usage'])),
                                                 main(r), -int(r['seq_no'])))
            code = row['material_code']
            required = count * D(row['standard_usage'])
            used = min(required, max(D(0), stocks[code]))
            stocks[code] -= used
            net = required - used
            has_children = bool(positions(product, level+1, code, alternatives))
            item = dict(path=path + [int(row['seq_no'])], parent=parent, material_code=code,
                        usage=number(D(row['standard_usage'])), required=number(required),
                        allocated=number(used), remaining=number(stocks[code]),
                        net_to_expand=number(net), leaf=not has_children)
            trace.append(item)
            if net > 0:
                if has_children:
                    children(code, net, level+1, item['path'])
                else:
                    gaps[code] += net
    if qty > fg:
        children(product, qty-fg, 0, [])
    return dict(product_code=product, demand_qty=number(qty), fg_allocated=number(fg),
                manufacturing_qty=number(qty-fg), inventory_covers=not gaps,
                shortage_material_count=len(gaps),
                leaf_shortages={k: number(v) for k, v in sorted(gaps.items())}, trace=trace)

def capacity(product, scope='production_available', alternatives=False):
    low, high = 0, 1
    while allocate(product, high, alternatives=alternatives, scope=scope, finished=False)['inventory_covers']:
        low, high = high, high * 2
        assert high < 100000000, 'unbounded or missing BOM'
    while low + 1 < high:
        mid = (low+high)//2
        if allocate(product, mid, alternatives=alternatives, scope=scope, finished=False)['inventory_covers']:
            low = mid
        else:
            high = mid
    fg = number(pool(scope)[product])
    # These delivered fixtures have independent finite upper bounds. This proves
    # the maximum rather than relying only on monotonicity of a binary search.
    if product == U:
        certificate = dict(material_code='606-000065', inventory_qty=number(pool(scope)['606-000065']),
                           usage=D('0.1'), reason='mandatory non-substitutable top-level leaf')
        upper = int(pool(scope)['606-000065'] / D('0.1'))
    elif alternatives:
        certificate = dict(material_code='606-000989', inventory_qty=number(pool(scope)['606-000989']),
                           usage=D(1), reason='mandatory non-substitutable top-level leaf')
        upper = int(pool(scope)['606-000989'])
    else:
        assert pool(scope)['165-003886'] == 0
        certificate = dict(material_code='528-000036', inventory_qty=number(pool(scope)['528-000036']),
                           usage=D(1), reason='missing mandatory child 165-003886 prevents further manufacture',
                           child_inventory_qty=0, child_usage=2)
        upper = int(pool(scope)['528-000036'])
    assert low == upper and allocate(product, upper, alternatives=alternatives, scope=scope, finished=False)['inventory_covers']
    certificate['usage'] = number(certificate['usage'])
    certificate['upper_bound_qty'] = upper
    return dict(fg_qty=fg, theoretical_build_qty=low, total_sellable_qty=fg+low,
                maximum_certificate=certificate,
                boundary_ok=allocate(product, low, alternatives=alternatives, scope=scope, finished=False),
                boundary_fail=allocate(product, low+1, alternatives=alternatives, scope=scope, finished=False))


def recalculate():
    forecasts=[r for r in RAW['erp_mds_forecast'] if r['closestatus_title'] != '已关闭']
    facts={
      'input_csv_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob('*.csv'))},
      'master_data': {
        'products':len({r['material_code'] for r in RAW['hd_product_view']}),
        'materials':len({r['material_code'] for r in RAW['erp_material']}),
        'suppliers':len({r['supplier_code'] for r in RAW['erp_supplier']}),
        'sales_orders':len({r['sales_order_id'] for r in RAW['sales_order']}),
        'warehouses':len({r['warehouse'] for r in RAW['erp_real_time_inventory']}),
        'executing_sales_orders':len({r['sales_order_id'] for r in RAW['sales_order'] if r['order_status']=='执行中'}),
        'sales_382':{k:number(sum((D(r[k]) for r in RAW['sales_order'] if r['product_code']==P),D(0))) for k in ['signing_quantity','shipping_quantity']},
        'purchased_materials':len({r['material_code'] for r in RAW['erp_material'] if r['materialattr']=='外购'}),
        'self_made_materials':len({r['material_code'] for r in RAW['erp_material'] if r['materialattr']=='自制'}),
        'buyer_suppliers':len({r['supplier_code'] for r in RAW['erp_supplier'] if r['purchaserid_name']=='杨强云'}),
      },
      'forecasts':{'open_records':len(forecasts),'billnos':len({r['billno'] for r in forecasts}),
                   'qty':number(sum((D(r['qty']) for r in forecasts),D(0))),
                   'by_product':{p:{'records':len([r for r in forecasts if r['material_number']==p]),
                                   'qty':number(sum((D(r['qty']) for r in forecasts if r['material_number']==p),D(0)))} for p in [P,V]}},
      'structure':{p:{'primary_codes':codes(p),'l1_codes':codes(p,1),
                       'primary_rows':len(structure(p))} for p in [P,Q,U,V]},
      'intersections':{'+'.join(ps):sorted(set.intersection(*(set(codes(p)) for p in ps)))
                       for ps in [[P,Q],[P,Q,U],[Q,U]]},
      'capacity':{P:capacity(P),U:capacity(U),P+'+alternates':capacity(P,alternatives=True)},
      'production_kitting':{p:allocate(p,q,include_po=True) for p,q in [(P,50),(Q,60)]},
      'fulfillment':{p:allocate(p,q,finished=True,include_po=True) for p,q in [(P,50),(Q,60)]},
      'F14_structural_primary_nodes':1+len(structure(V)),
    }
    for label,ds,finished in [('F11',[(P,50),(Q,60)],True),('S04',[(P,50),(Q,60)],True),('S11',[(Q,60),(U,50)],True)]:
        stocks=pool(include_po=True)
        facts[label]=[allocate(p,q,stocks=stocks,finished=finished) for p,q in ds]
    (HERE/'facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'forecasts':facts['forecasts'],
                      'capacities':{p:r['total_sellable_qty'] for p,r in facts['capacity'].items()},
                      'production_gaps':{p:r['leaf_shortages'] for p,r in facts['production_kitting'].items()}},ensure_ascii=False))

if __name__=='__main__':
    recalculate()
