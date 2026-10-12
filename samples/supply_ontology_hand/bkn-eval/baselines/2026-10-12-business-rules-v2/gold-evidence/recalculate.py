#!/usr/bin/env python3
"""Independent raw-CSV oracle. Does not import or call evaluated functions.

BOM fixtures are breadth-first expanded trees, including alternative branches.
Repeated occurrences of one parent carry repeated identical child sequences.
Validate and partition those sequences before traversing a selected branch.
All arithmetic is Decimal; each candidate uses its own standard_usage.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SAMPLE = BASE.parents[2]
DATA = SAMPLE / 'data'
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
    return int(row['alt_priority'] or 0) == 0 and row['alt_part'] != '√'

def structure(product, level=None):
    return [r for r in BOM if r['bom_material_code'] == product and main(r)
            and int(r['bom_level']) > 0 and (level is None or int(r['bom_level']) == level)]

def codes(product, level=None):
    return sorted({r['material_code'] for r in structure(product, level)})

def pool(scope='all'):
    result = defaultdict(D)
    warehouses = None if scope == 'all' else (PRODUCTION if scope == 'production_available' else FG)
    for r in RAW['erp_real_time_inventory']:
        if r['stock_status'] == '可用' and (warehouses is None or r['warehouse'] in warehouses):
            result[r['material_code']] += D(r['available_inventory_qty'] or 0)
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

def allocate(product, qty, stocks=None, alternatives=False, scope='all', finished=True):
    stocks = pool(scope) if stocks is None else stocks
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

def capacity(product, scope='all', alternatives=False):
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

def sequence(demands):
    stocks = pool()
    results = [allocate(product, quantity, stocks=stocks) for product, quantity in demands]
    return dict(all_covered=all(r['inventory_covers'] for r in results), demands=results)

def compact(value):
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items() if k not in ('trace', 'boundary_ok', 'boundary_fail', 'maximum_certificate')}
    if isinstance(value, list):
        return [compact(x) for x in value]
    return value

def calculate():
    questions = yaml.safe_load((BASE / 'question-set-v3.yaml').read_text())['questions']
    answers, facts = [], {}
    def add(qid, expected, inputs=None):
        facts[qid] = expected
        answers.append(dict(id=qid, inputs=inputs or {}, expected=compact(expected),
                            answer=json.dumps(compact(expected), ensure_ascii=False),
                            evidence_ref='gold-evidence/facts.json#' + qid))
    open_fc = [r for r in RAW['erp_mds_forecast'] if r['closestatus_title'] != '已关闭']
    for qid, value in [('M-01',len({r['material_code'] for r in RAW['hd_product_view']})),
                       ('M-02',len({r['material_code'] for r in RAW['erp_material']})),
                       ('M-03',len({r['supplier_code'] for r in RAW['erp_supplier']})),
                       ('M-04',len({r['sales_order_id'] for r in RAW['sales_order']})),
                       ('M-05',len({r['warehouse'] for r in RAW['erp_real_time_inventory']})),
                       ('M-06',number(pool('finished_goods')[P])),
                       ('M-07',number(sum((D(r['qty']) for r in open_fc),D(0)))),
                       ('M-08',len(open_fc)),
                       ('M-09',sum(r['order_status']=='执行中' for r in RAW['sales_order']))]:
        add(qid, dict(value=value), dict(product_code=P, scope='finished_goods') if qid=='M-06' else {})
    sales = [r for r in RAW['sales_order'] if r['product_code']==P]
    signed=sum(D(r['signing_quantity']) for r in sales)
    shipped=sum(D(r['shipping_quantity']) for r in sales)
    add('M-10',dict(signing_qty=number(signed),shipping_qty=number(shipped),unshipped_qty=number(signed-shipped)),dict(product_code=P))
    for qid,product in [('M-11',P),('M-12',V)]:
        rows=[r for r in open_fc if r['material_number']==product]
        add(qid,dict(count=len(rows),qty=number(sum((D(r['qty']) for r in rows),D(0)))),dict(product_code=product))
    add('M-13',dict(value=sum(r['materialattr']=='外购' for r in RAW['erp_material'])))
    add('M-14',dict(value=sum(r['materialattr']=='自制' for r in RAW['erp_material'])))
    add('M-15',dict(value=sum(r['purchaserid_name']=='杨强云' for r in RAW['erp_supplier'])),dict(purchaser='杨强云'))
    add('F-01',dict(material_codes=codes(P,1),count=len(codes(P,1))),dict(product_code=P,depth=1,include_substitutes=False))
    def shared(qid, products):
        common=sorted(set.intersection(*(set(codes(p)) for p in products)))
        add(qid,dict(shared_count=len(common),material_codes=common),dict(product_codes=products,include_substitutes=False,include_root=False))
    shared('F-02',[P,Q]);shared('F-03',[P,Q,U]);shared('F-12',[Q,U])
    capacities={}
    for qid,product,scope,alts in [('F-04',P,'all',False),('F-05',U,'all',False),
                                ('F-08',P,'production_available',False),('F-09',U,'production_available',False),
                                ('F-13',P,'production_available',False),('F-15',P,'all',True)]:
        result=capacity(product,scope,alts);capacities[qid]=result
        add(qid,result,dict(product_code=product,scope=scope,substitute_enabled=alts,include_in_transit=False))
    simpleP=allocate(P,50);simpleQ=allocate(Q,60);twoPQ=sequence([(P,50),(Q,60)])
    for qid,result,demands in [('F-06',simpleP,[(P,50)]),('F-10',simpleQ,[(Q,60)]),('F-11',twoPQ,[(P,50),(Q,60)]),
                             ('S-01',simpleQ,[(Q,60)]),('S-03',simpleP,[(P,50)]),('S-04',twoPQ,[(P,50),(Q,60)]),
                             ('S-11',sequence([(Q,60),(U,50)]),[(Q,60),(U,50)])]:
        add(qid,result,dict(demands=[dict(product_code=p,qty=n) for p,n in demands],scope='all',substitute_enabled=False,include_in_transit=False))
    add('F-07',dict(leadtime_days=number(D(MAT['606-000989']['purchase_fixedleadtime'])),materialattr=MAT['606-000989']['materialattr']),dict(material_code='606-000989'))
    add('F-14',dict(non_root_line_count=len(structure(V)),node_count=len(structure(V))+1),dict(product_code=V,include_substitutes=False,grain='full_structure'))
    for qid,product,level in [('R-01',Q,1),('R-02',V,1),('R-03',V,None),('R-04',P,None)]:
        add(qid,dict(count=len(codes(product,level)),material_codes=codes(product,level)),dict(product_code=product,depth=level or 'all',include_root=False,include_substitutes=False))
    for qid,code in [('R-05','321-000569'),('R-06','606-000989'),('R-07','725-000226')]:
        products=sorted({r['bom_material_code'] for r in BOM if r['material_code']==code and int(r['bom_level'])>0})
        add(qid,dict(count=len(products),product_codes=products),dict(material_code=code,include_substitute_occurrences=True))
    common=sorted(set(codes(P,1)) & set(codes('382-000006',1)))
    add('R-08',dict(count=len(common),material_codes=common),dict(product_codes=[P,'382-000006'],depth=1,include_substitutes=False))
    group=[r for r in BOM if r['bom_material_code']==P and r['parent_material_code']=='588-000620' and r['alt_group_no']=='12']
    substitutes=[dict(material_code=r['material_code'],available_qty=number(pool()[r['material_code']]),usage=number(D(r['standard_usage']))) for r in group if not main(r)]
    add('R-09',dict(main_material_code='356-000061',substitutes=substitutes),dict(product_code=P,parent_material_code='588-000620',alt_group_no='12',scope='all'))
    add('S-02',dict(**compact(capacities['F-05']),delivery_promise=False),dict(product_code=U,scope='all',substitute_enabled=False,include_in_transit=False))
    add('S-05',dict(**twoPQ,shared_count=len(set(codes(P)) & set(codes(Q)))),dict(demands=[dict(product_code=P,qty=50),dict(product_code=Q,qty=60)],scope='all',substitute_enabled=False,include_in_transit=False))
    gap=simpleQ['leaf_shortages'].get('321-000569',0)
    add('S-06',dict(material_code='321-000569',net_shortage=gap,recommended_replenishment_qty=gap),dict(product_code=Q,demand_qty=60,scope='all',substitute_enabled=False,include_in_transit=False))
    fg=number(pool()[P]);add('S-07',dict(fg_qty=fg,on_time=fg>=50,ship_date='2026-08-25',remaining_qty=fg-50),dict(product_code=P,demand_qty=50,scope='all',substitute_enabled=True,business_date='2026-08-25',demand_end='2026-09-05'))
    code='321-000569';eligible=[];excluded=[]
    for r in RAW['erp_purchase_order']:
        if r['material_number']!=code:continue
        net=max(D(0),D(r['qty'])-D(r['actqty'] or 0))
        date=r['deliverdate'][:10]
        reason='closed' if r['rowclosestatus_title']=='已关闭' else ('zero_net' if net==0 else ('overdue' if date and date<='2026-08-25' else ('undated' if not date else ('late' if date>'2026-09-08' else 'eligible'))))
        item=dict(entry_id=r['entry_id'],deliverdate=date,qty=number(D(r['qty'])),received_qty=number(D(r['actqty'] or 0)),net_qty=number(net),reason=reason)
        (eligible if reason=='eligible' else excluded).append(item)
    po=sum((D(x['net_qty']) for x in eligible),D(0));inv=pool()[code];supply=inv+po
    add('S-08',dict(inventory_qty=number(inv),on_time_po_qty=number(po),confirmed_supply_qty=number(supply),shortage_qty=number(max(D(0),D(240)-supply)),covers=supply>=240,eligible_po=eligible,excluded_po=excluded),dict(material_code=code,gross_demand_qty=240,scope='all',business_date='2026-08-25',need_by='2026-09-08',include_in_transit=True))
    for qid,quantity in [('S-09',3850),('S-10',3851)]:
        cap=compact(capacities['F-05']);add(qid,dict(**cap,covers=cap['total_sellable_qty']>=quantity,capacity_shortfall=max(0,quantity-cap['total_sellable_qty'])),dict(product_code=U,demand_qty=quantity,scope='all',substitute_enabled=False,include_in_transit=False))
    byid={a['id']:a for a in answers}
    assert len(byid)==50 and set(byid)=={q['id'] for q in questions}
    # Grade only the outputs asked for. Complete independent computations stay
    # in facts.json; evidence fields must not become extra answer obligations.
    required = {
        'F-01':['material_codes'], 'F-02':['shared_count'], 'F-03':['shared_count'],
        'F-06':['inventory_covers'], 'F-07':['leadtime_days'],
        'F-08':['theoretical_build_qty'], 'F-09':['theoretical_build_qty'],
        'F-10':['inventory_covers','shortage_material_count'],
        'F-11':['demands'], 'F-12':['shared_count'], 'F-13':['theoretical_build_qty'],
        'R-01':['count'], 'R-02':['count'], 'R-03':['count'], 'R-04':['count'],
        'R-05':['product_codes'], 'R-06':['product_codes'], 'R-07':['count'],
        'R-08':['material_codes'], 'R-09':['substitutes'],
        'S-01':['inventory_covers','leaf_shortages'],
        'S-03':['inventory_covers','leaf_shortages'],
        'S-04':['all_covered','demands'], 'S-05':['shared_count','demands'],
        'S-06':['net_shortage','recommended_replenishment_qty'],
        'S-07':['fg_qty','on_time','remaining_qty'],
        'S-08':['inventory_qty','on_time_po_qty','confirmed_supply_qty','shortage_qty','covers'],
        'S-09':['covers'], 'S-10':['covers','capacity_shortfall'], 'S-11':['demands'],
    }
    for qid, keys in required.items():
        expected={key:byid[qid]['expected'][key] for key in keys}
        if 'demands' in expected:
            demand_keys=['product_code','inventory_covers']
            if qid != 'F-11': demand_keys.append('leaf_shortages')
            expected['demands']=[{key:row[key] for key in demand_keys} for row in expected['demands']]
        byid[qid]['expected']=expected
        byid[qid]['answer']=json.dumps(expected,ensure_ascii=False)
    ordered=[dict(byid[q['id']],question=q['question']) for q in questions]
    metadata=dict(schema_version='2.0',set_id='supply-business-rules-v3',baseline_id='supply-business-rules-v3-deterministic',snapshot_kind='repository_fixture_freeze',snapshot_date='2026-10-12',source_snapshot_date='2026-08-13',business_date='2026-08-25',generation_method='independent raw CSV Decimal oracle; no evaluated function imports or calls',scope_presets=dict(finished_goods=FG,production_available=PRODUCTION),answers=ordered)
    (BASE/'answer-set-v3.yaml').write_text(yaml.safe_dump(metadata,allow_unicode=True,sort_keys=False),encoding='utf-8')
    (HERE/'facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={name:dict(path=str(DATA/(name+'.csv')),rows=len(RAW[name]),sha256=hashlib.sha256((DATA/(name+'.csv')).read_bytes()).hexdigest()) for name in FILES}
    (HERE/'provenance.json').write_text(json.dumps(dict(source_manifest=manifest,repeated_parent_validation=REPEATED,question_set_sha256=hashlib.sha256((BASE/'question-set-v3.yaml').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({a['id']:a['expected'] for a in ordered},ensure_ascii=False,indent=2))

if __name__=='__main__':
    calculate()
