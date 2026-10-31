#!/usr/bin/env python3
"""Independent oracle for the manufacturing business-scenario question set.

Reads only this package's delivered CSV files through mfg_calc.py, which implements the PRD rules
without importing the data generator. The files are identical in the zh-CN and en-US packages:
their data differ only in translated text, so expected values match except for names.

Writes question-set-v1.yaml (no answers) and answer-set-v1.yaml next to this file.
"""
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from mfg_calc import TODAY, Mfg, c, f  # noqa: E402

LANG = 'zh' if ROOT.name.endswith('zh-cn') else 'en'
M = Mfg(ROOT / 'data')
T = M.t


def num(x):
    if x is None:
        return None
    x = round(float(x), 4)
    return int(x) if x == int(x) else x


QUESTIONS = []
ROLE = {'OD': ('订单交付经理', 'Order fulfilment manager'), 'PR': ('生产主管', 'Production lead'),
        'QM': ('质量经理', 'Quality manager'), 'PM': ('采购与物料经理', 'Purchasing and materials manager')}
LEVEL = {'basic': ('基础', 'basic'), 'medium': ('中等', 'medium'), 'complex': ('复杂', 'complex')}


def q(qid, scenario, level, role, zh, en, expected, contract_zh, contract_en):
    i = 0 if LANG == 'zh' else 1
    QUESTIONS.append(dict(id=qid, scenario=scenario, difficulty=LEVEL[level][i], role=ROLE[role][i],
                          question=(zh, en)[i], output_contract=(contract_zh, contract_en)[i], expected=expected))


def rows(table, **match):
    return [r for r in T[table] if all(r[k] == v for k, v in match.items())]


lines = {s: M.line(s) for s in M.sol}
due_lines = {s: v for s, v in lines.items() if v['requested'] <= TODAY}
executions = M.executions()
noncompliant = M.noncompliant()

# --- S01 products and capacity -----------------------------------------------------------------
q('Q-01', 'S01', 'basic', 'PR', '我们有几个工厂、几个工作中心、多少台生产设备？每个工厂各有多少台设备？',
  'How many plants, work centres and production machines do we have, and how many machines does each plant have?',
  dict(sites=len(T['manufacturing_sites']), work_centers=len(T['work_centers']), machines=len(T['production_machines']),
       machines_by_site=dict(Counter(m['site_id'] for m in T['production_machines']))),
  '工厂数、工作中心数、设备数、各工厂设备数', 'plants, work centres, machines, machines per plant')
ph200 = next(v for v in T['product_bom_versions'] if v['product_id'] == 'FG-PH200' and c(v['status']) == 'frozen')
q('Q-02', 'S01', 'basic', 'PM', 'PH200 高压泵壳现在用哪个 BOM 版本？每件要用哪些物料、各多少？',
  'Which BOM version does the PH200 high-pressure pump housing use now, and which materials go into each unit, in what quantity?',
  dict(bom_version=ph200['bom_version_id'], components={b['component_product_id']: num(b['quantity_per']) for b in rows('bom_components', bom_version_id=ph200['bom_version_id'])}),
  'BOM 版本、物料及单耗', 'BOM version, materials and quantity per unit')
route = sorted(rows('routing_operations', routing_id='ROUTE-VB080'), key=lambda r: int(r['sequence_number']))
q('Q-03', 'S01', 'basic', 'PR', 'VB080 阀体要经过哪几道工序？按顺序各在哪个工作中心做？',
  'Which operations does the VB080 valve body go through, and in which work centre is each done, in order?',
  dict(work_centers=[r['work_center_id'] for r in route]), '工序及工作中心（按顺序）', 'operations and work centres in order')
milling = sorted({x['operator_id'] for x in rows('operator_qualifications', capability_id='CAP-MILL') if c(x['qualification_status']) == 'qualified'
                  and x['valid_to'] >= TODAY and c(next(o for o in T['operators'] if o['operator_id'] == x['operator_id'])['employment_status']) == 'active'})
q('Q-04', 'S01', 'medium', 'PR', '现在有哪些操作员可以上五轴铣削？', 'Which operators can run 5-axis milling now?',
  dict(operators=milling), '操作员清单', 'operator ids')
cap_ok = {a['machine_id'] for a in T['machine_capability_assignments'] if c(a['qualification_status']) == 'qualified'}
unusable = sorted(m['machine_id'] for m in T['production_machines'] if c(m['status']) != 'available' or m['machine_id'] not in cap_ok)
q('Q-05', 'S01', 'medium', 'PR', '现在哪些设备不能安排生产？各是什么原因？', 'Which machines cannot be scheduled for production now, and why?',
  dict(machines=unusable), '设备及原因', 'machines and reasons')

# --- S02 orders and delivery -------------------------------------------------------------------
open_due = {s: v for s, v in due_lines.items() if v['backlog'] > 0}
q('Q-06', 'S02', 'basic', 'OD', '交期已经到了的订单行里，有多少行还没发完？一共还欠客户多少件？',
  'Among order lines whose requested date has arrived, how many are not fully shipped, and how many units do we still owe customers in total?',
  dict(lines=len(open_due), units=num(sum(v['backlog'] for v in open_due.values()))), '订单行数、欠交件数', 'order lines, units owed')
late_done = {s: v['late_days'] for s, v in lines.items() if v['complete'] and v['late']}
q('Q-07', 'S02', 'medium', 'OD', '已经发完的订单行里，哪些是延误交付的？各晚了几天？', 'Among fully shipped order lines, which were delivered late, and by how many days?',
  dict(lines=late_done), '订单行及延误天数', 'order lines and days late')
sol5 = 'SOL-2611-04-1'
q('Q-08', 'S02', 'medium', 'OD', 'SO-2611-04 是怎么发货的？分了几批、每批多少件、哪天发的？算不算延误？',
  'How was SO-2611-04 shipped: in how many shipments, how many units each and on which dates, and was it late?',
  dict(shipments={s['shipment_id']: dict(quantity=num(s['shipped_quantity']), date=s['shipment_date']) for s in M.shipments_of(sol5)},
       late_days=lines[sol5]['late_days']), '各批发运数量与日期、延误天数', 'quantity and date per shipment, days late')
sol6 = 'SOL-2610-06-1'
first, repl = M.wos_of_line(sol6)
bad = M.out_of_spec(M.lot_of(first)['inspection_lot_id'])[0]
q('Q-09', 'S02', 'complex', 'OD', '华中智能流体 SO-2610-06 那批泵壳为什么晚交了？最后是怎么交上的？',
  'Why was the pump housing order SO-2610-06 for Central China Smart Fluids delivered late, and how was it finally delivered?',
  dict(rejected_work_order=first, characteristic=bad['characteristic_name'], measured=num(bad['measured_value']), replacement_work_order=repl,
       shipped=num(lines[sol6]['shipped']), late_days=lines[sol6]['late_days']),
  '原工单、超限项与测量值、补做工单、发运数量、延误天数', 'original work order, failed characteristic and value, replacement work order, shipped units, days late')
q('Q-10', 'S02', 'complex', 'OD', '交期已过还没发完的订单行各差多少件？各卡在哪里？',
  'For each order line past its requested date and not fully shipped, how many units are missing and what is holding it up?',
  dict(lines={s: num(v['backlog']) for s, v in open_due.items()}), '订单行、欠交件数及原因', 'order line, units owed and cause')
owed = defaultdict(float)
for s, v in open_due.items():
    owed[M.so[M.sol[s]['sales_order_id']]['customer_id']] += v['backlog']
top = max(owed, key=owed.get)
q('Q-11', 'S02', 'complex', 'OD', '按客户看，交期已过还欠多少件？欠得最多的是哪家客户？',
  'By customer, how many units past their requested date are still owed, and which customer is owed the most?',
  dict(customers={k: num(v) for k, v in sorted(owed.items())}, top_customer=top), '各客户欠交件数、欠得最多的客户', 'units owed per customer, customer owed most')

# --- S03 forecast and plan ---------------------------------------------------------------------
pv = M.plan_vs_forecast()
q('Q-12', 'S03', 'basic', 'OD', '三月份计划生产多少件 PH100？三月 PH100 的需求预测是多少？', 'How many PH100 units are planned for March, and what is the March forecast for PH100?',
  dict(planned=num(pv[('FG-PH100', '2027-03')]['planned']), forecast=num(pv[('FG-PH100', '2027-03')]['forecast'])), '计划数量、预测数量', 'planned, forecast')
feb = {p: num(round(v['planned'] / v['forecast'], 2)) for (p, m), v in pv.items() if m == '2027-02' and v['planned'] < v['forecast']}
q('Q-13', 'S03', 'medium', 'OD', '2027 年 2 月哪些产品的生产计划没有覆盖需求预测？覆盖率各是多少？',
  'In February 2027, which products have a production plan below their forecast, and what is each coverage ratio?',
  dict(products=feb), '产品及覆盖率', 'products and coverage ratio')
gap = defaultdict(float)
for (p, m), v in pv.items():
    gap[p] += v['forecast'] - v['planned']
worst = max(gap, key=gap.get)
q('Q-14', 'S03', 'medium', 'OD', '十一月到三月合计，哪个产品的计划比预测少得最多？少多少件？', 'Over November to March, which product\'s plan falls furthest below its forecast, and by how many units?',
  dict(product=worst, shortfall=num(gap[worst])), '产品、差额', 'product, shortfall')
blocked = {w: M.blocked_reasons(w) for w in M.wo if M.blocked_reasons(w)}
mar_exec = defaultdict(float)
for l in T['production_plan_lines']:
    if M.wo[l['production_order_id']]['due_date'][:7] == '2027-03' and l['production_order_id'] not in blocked:
        mar_exec[l['product_id']] += f(l['planned_quantity'])
mar_short = {p: num(v['forecast'] - mar_exec[p]) for (p, m), v in pv.items() if m == '2027-03' and mar_exec[p] < v['forecast']}
q('Q-15', 'S03', 'complex', 'OD', '三月的计划里去掉已经阻塞的工单，哪些产品的可执行计划低于预测？各差多少件？',
  'Taking blocked work orders out of the March plan, which products have an executable plan below forecast, and by how many units?',
  dict(products=mar_short), '产品及差额', 'products and shortfall')

# --- S04 material availability -------------------------------------------------------------------
r23 = next(r for r in M.requirements('WO-2702-03') if r['product_id'] == 'RM-SS316')
need23 = M.required_by_rule('WO-2702-03', r23)
q('Q-16', 'S04', 'basic', 'PM', 'WO-2702-03 需要多少 316L 不锈钢棒料？已经发了多少？还差多少？', 'How much 316L stainless bar does WO-2702-03 need, how much has been issued, and how much is still missing?',
  dict(required=num(need23), issued=num(M.issued(r23['material_requirement_id'])), missing=num(need23 - M.issued(r23['material_requirement_id']))),
  '需求、已发、缺口（千克）', 'required, issued, missing (kg)')
q('Q-17', 'S04', 'complex', 'PM', '现在哪些工单被阻塞了？各是因为什么？', 'Which work orders are blocked now, and why?',
  dict(work_orders=sorted(blocked)), '工单及阻塞原因', 'work orders and reasons')
q('Q-18', 'S04', 'medium', 'PM', 'WO-2703-01 每种物料各需要多少？', 'How much of each material does WO-2703-01 need?',
  dict(materials={r['product_id']: num(M.required_by_rule('WO-2703-01', r)) for r in M.requirements('WO-2703-01')}), '物料及需求量', 'materials and required quantity')
a_comp = next(b for b in T['bom_components'] if b['bom_version_id'] == 'BOMV-FL150-A')
need_a = M.required_by_rule('WO-2703-02', dict(bom_component_id=a_comp['bom_component_id']))
avail_al = M.balance('RM-AL6061')['available']
q('Q-19', 'S04', 'complex', 'PM', 'WO-2703-02 为什么开不了工？如果改用已冻结的 A 版 BOM，现有铝合金方坯够吗？',
  'Why can WO-2703-02 not start, and if it switched to the frozen BOM revision A, would current aluminium billet stock be enough?',
  dict(bom_version=M.wo['WO-2703-02']['bom_version_id'], required_with_a=num(need_a), available=num(avail_al), enough=avail_al >= need_a, missing=num(max(0, need_a - avail_al))),
  'BOM 版本原因、A 版需求、可用库存、是否够、缺口', 'BOM reason, revision A requirement, available stock, enough or not, shortfall')
starts = {l['production_order_id']: l['planned_start_date'] for l in T['production_plan_lines']}
waiting = [w for w in M.wo if c(M.wo[w]['status']) == 'released']
need_ci = sum(M.required_by_rule(w, r) - M.issued(r['material_requirement_id']) for w in waiting for r in M.requirements(w) if r['product_id'] == 'RM-CI250')
avail_ci = M.balance('RM-CI250')['available']
q('Q-20', 'S04', 'complex', 'PM', '三月已下达、还没开工的工单一共还需要多少灰铸铁泵壳毛坯？现在可用库存够吗？差多少？',
  'How many grey iron housing castings do the released March work orders that have not started still need, is available stock enough, and how far short is it?',
  dict(work_orders=sorted(w for w in waiting if any(r['product_id'] == 'RM-CI250' for r in M.requirements(w))), required=num(need_ci), available=num(avail_ci), missing=num(max(0, need_ci - avail_ci))),
  '涉及工单、需求、可用、缺口', 'work orders, required, available, shortfall')

# --- S05 purchasing and receipts ---------------------------------------------------------------
overdue = M.overdue_pos()
q('Q-21', 'S05', 'medium', 'PM', '现在有哪些采购订单逾期未到？', 'Which purchase orders are overdue now?', dict(purchase_orders=overdue), '采购订单清单', 'purchase order ids')
rej = [r for r in T['goods_receipts'] if c(r['inspection_status']) == 'rejected']
rej_wo = sorted(w for w in blocked if any(r['product_id'] in M.shortages(w) for r in rej))
q('Q-22', 'S05', 'medium', 'PM', '哪些来料被拒收了？影响了哪个工单？', 'Which incoming receipts were rejected, and which work order did that affect?',
  dict(receipts=[r['goods_receipt_id'] for r in rej], work_orders=rej_wo), '拒收来料、受影响工单', 'rejected receipts, affected work orders')
bad_issue = M.improper_issues()
mi = next(i for i in T['material_issue_transactions'] if i['material_issue_transaction_id'] == bad_issue[0])
q('Q-23', 'S05', 'complex', 'PM', '有没有从还没检验放行的来料里发料？发给了哪个工单、多少？那个工单后来做完发货了吗？',
  'Was any material issued from a receipt that had not passed incoming inspection? To which work order and how much, and was that order later completed and shipped?',
  dict(issue=mi['material_issue_transaction_id'], receipt=mi['goods_receipt_id'], work_order=mi['production_order_id'], quantity=num(mi['issued_quantity']),
       shipped=num(sum(f(s['shipped_quantity']) for s in rows('shipments', production_order_id=mi['production_order_id'])))),
  '发料记录、来料、工单、数量、发运数量', 'issue, receipt, work order, quantity, shipped units')
late_sup = defaultdict(list)
for gr, po, sup, days in M.late_receipts():
    late_sup[sup].append(days)
q('Q-24', 'S05', 'medium', 'PM', '哪些供应商有延迟到货？各晚了几天？', 'Which suppliers delivered late, and by how many days?',
  dict(suppliers=sorted(late_sup)), '供应商及延迟天数', 'suppliers and days late')
sup2 = {}
for po_id in overdue:
    if M.po[po_id]['supplier_id'] == 'SUP-02':
        got, ordered = M.po_accepted(po_id)
        sup2[po_id] = num(ordered - got)
q('Q-25', 'S05', 'complex', 'PM', '宝联特钢现在有哪些采购没有交齐？各还差多少千克？分别是给哪些工单买的？',
  'Which purchase orders from Baolian Special Steel are not fully delivered, how many kg is each short, and which work orders were they bought for?',
  dict(purchase_orders=sup2), '采购订单、缺少数量、对应工单', 'purchase orders, missing kg, work orders')

# --- S06 progress and output -------------------------------------------------------------------
q('Q-26', 'S06', 'basic', 'PR', '现在各种状态的工单各有多少张？', 'How many work orders are in each status now?',
  dict(statuses=dict(Counter(M.wo[w]['status'] for w in M.wo))), '各状态工单数', 'work orders per status')
ex5 = sorted(M.executions('WO-2702-05'), key=lambda e: e['seq'])
q('Q-27', 'S06', 'medium', 'PR', 'WO-2702-05 做到哪一步了？', 'How far has WO-2702-05 progressed?',
  dict(completed_operations=sum(c(e['status']) == 'completed' for e in ex5), current_step=next(e['process_step_id'] for e in ex5 if c(e['status']) != 'completed'),
       good_so_far=num(max(f(e['good_quantity']) for e in ex5))), '已完成工序数、当前步骤、已产出合格数', 'operations completed, current step, good units so far')
scrap = {}
for e in executions:
    if f(e['scrap_quantity']) > 0:
        scrap[e['wo']] = dict(step=e['process_step_id'], scrap=num(e['scrap_quantity']))
q('Q-28', 'S06', 'medium', 'PR', '哪些工单有报废？报废在哪一步、多少件？', 'Which work orders had scrap, at which step, and how many units?',
  dict(work_orders=scrap), '工单、步骤、报废数', 'work order, step, scrap units')
done6 = M.completed_qty('WO-2611-06')
q('Q-29', 'S06', 'complex', 'PR', 'WO-2611-06 的良率是多少？少做的件数对客户交付有什么影响？', 'What is the yield of WO-2611-06, and how did the missing units affect the customer delivery?',
  dict(completed=num(done6), yield_ratio=num(round(done6 / f(M.wo['WO-2611-06']['requested_quantity']), 4)), sales_order_line=M.wo['WO-2611-06']['sales_order_line_id'],
       backlog=num(lines[M.wo['WO-2611-06']['sales_order_line_id']]['backlog'])), '完成数量、良率、订单行、欠交件数', 'completed units, yield, order line, units owed')
jan = 0.0
for w in M.wo:
    ex = [e for e in M.executions(w) if c(e['status']) == 'completed']
    if M.completed_qty(w) is not None and max(e['completed_date'] for e in ex)[:7] == '2027-01':
        jan += M.completed_qty(w)
q('Q-30', 'S06', 'medium', 'PR', '2027 年 1 月做完的工单一共产出多少件合格品？', 'How many good units did the work orders finished in January 2027 produce in total?',
  dict(good_units=num(jan)), '合格品件数', 'good units')

# --- S07 execution compliance ------------------------------------------------------------------
q5 = next(x for x in T['operator_qualifications'] if x['operator_id'] == 'OPR-05' and x['capability_id'] == 'CAP-MILL')
q('Q-31', 'S07', 'basic', 'PR', '孙浩的五轴铣削资质什么时候到期？', 'When does Sun Hao\'s 5-axis milling qualification expire?', dict(valid_to=q5['valid_to']), '到期日', 'expiry date')
op_bad = sorted(x for x, (w, rs) in noncompliant.items() if 'operator_qualification' in rs)
q('Q-32', 'S07', 'complex', 'PR', '有哪些执行是由资质不合格或资质已过期的操作员做的？', 'Which executions were done by an operator who was not qualified or whose qualification had expired?',
  dict(executions=op_bad), '执行记录、操作员、原因', 'executions, operators, reasons')
m4 = sorted(e['execution_record_id'] for e in executions if e['machine_id'] == 'MACH-MILL-04')
q('Q-33', 'S07', 'medium', 'PR', 'MACH-MILL-04 做过哪些活？这些执行合规吗？', 'What work has MACH-MILL-04 done, and were those executions compliant?',
  dict(executions=m4, compliant=not any(x in noncompliant for x in m4)), '执行记录、是否合规及原因', 'executions, compliant or not, reason')
q('Q-34', 'S07', 'complex', 'PR', '已经完成的执行里，哪些不合规？各是什么原因？', 'Among completed executions, which are non-compliant, and why?',
  dict(executions={x: w for x, (w, rs) in sorted(noncompliant.items()) if c(next(e for e in executions if e['execution_record_id'] == x)['status']) == 'completed'}),
  '执行记录、工单、原因', 'execution, work order, reason')
nc_wos = sorted({w for w, rs in noncompliant.values()})
shipped_nc = sorted(w for w in nc_wos if rows('shipments', production_order_id=w))
q('Q-35', 'S07', 'complex', 'PR', '有不合规执行的工单里，哪些已经发货给客户了？发给了哪些客户？', 'Among work orders with a non-compliant execution, which have already been shipped, and to which customers?',
  dict(work_orders=shipped_nc, customers=sorted({M.so[M.sol[M.wo[w]['sales_order_line_id']]['sales_order_id']]['customer_id'] for w in shipped_nc})),
  '工单、客户', 'work orders, customers')
e9 = next(e for e in executions if e['wo'] == 'WO-2701-09' and e['seq'] == 10)
wk = [a for a in T['operator_shift_assignments'] if a['operator_id'] == e9['operator_id'] and M.shifts[a['shift_id']]['starts_date'] <= e9['started_date'] <= M.shifts[a['shift_id']]['ends_date']]
q('Q-36', 'S07', 'medium', 'PR', 'WO-2701-09 的精铣是谁做的？他那一周被安排在哪个工作中心？', 'Who did the finish milling on WO-2701-09, and which work centre was that operator assigned to that week?',
  dict(operator=e9['operator_id'], assigned_work_center=wk[0]['work_center_id'], operation_work_center=e9['wc']), '操作员、排班工作中心、工序工作中心', 'operator, assigned work centre, operation work centre')

# --- S08 quality release -----------------------------------------------------------------------
rejected_lots = sorted(l['inspection_lot_id'] for l in T['quality_inspection_lots'] if c(l['status']) == 'rejected')
q('Q-37', 'S08', 'basic', 'QM', '有哪些最终检验批被拒收了？', 'Which final inspection lots were rejected?', dict(lots=rejected_lots), '检验批清单', 'inspection lot ids')
bore = {s['status']: s for s in T['quality_specifications'] if s['product_id'] == 'FG-PH100' and s['quality_specification_id'].startswith('QS-PH100-BORE')}
cur = next(s for s in bore.values() if c(s['status']) == 'active')
old = next(s for s in bore.values() if c(s['status']) != 'active')
q('Q-38', 'S08', 'medium', 'QM', 'PH100 关键孔径现在的规格上下限是多少？和上一版有什么不同？', 'What are the current limits for the PH100 critical bore, and how do they differ from the previous revision?',
  dict(current=dict(lower=num(cur['lower_limit']), upper=num(cur['upper_limit']), effective=cur['effective_date']), previous=dict(lower=num(old['lower_limit']), upper=num(old['upper_limit']))),
  '现行上下限与生效日期、上一版上下限', 'current limits and effective date, previous limits')
esc = M.escapes()[0]
esc_r = next(r for r in M.out_of_spec(M.lot_of(esc)['inspection_lot_id']))
q('Q-39', 'S08', 'complex', 'QM', '有没有检验记成通过、测量值却超出规格的批次？这批货发出去了吗？',
  'Is there a lot whose result was recorded as pass although the measured value is outside the specification, and was it shipped?',
  dict(work_order=esc, lot=M.lot_of(esc)['inspection_lot_id'], measured=num(esc_r['measured_value']), upper_limit=num(M.specs[esc_r['quality_specification_id']]['upper_limit']),
       shipped=num(sum(f(s['shipped_quantity']) for s in rows('shipments', production_order_id=esc)))),
  '工单、检验批、测量值、上限、发运数量', 'work order, lot, measured value, upper limit, shipped units')
r10 = M.out_of_spec(M.lot_of('WO-2701-10')['inspection_lot_id'])[0]
q('Q-40', 'S08', 'medium', 'QM', 'WO-2701-10 的检验为什么没过？超了多少？', 'Why did WO-2701-10 fail inspection, and by how much?',
  dict(characteristic=r10['characteristic_name'], measured=num(r10['measured_value']), upper_limit=num(r10['upper_limit']), exceeded_by=num(f(r10['measured_value']) - f(r10['upper_limit']))),
  '超限项、测量值、上限、超出量', 'characteristic, measured value, upper limit, excess')
pending = sorted(l['inspection_lot_id'] for l in T['quality_inspection_lots'] if c(l['status']) == 'pending')
q('Q-41', 'S08', 'medium', 'QM', '现在还有哪些检验批没出结论？', 'Which inspection lots have no decision yet?', dict(lots=pending), '检验批清单', 'inspection lot ids')
hit = defaultdict(float)
for w in sorted({M.lots[l]['production_order_id'] for l in rejected_lots} | set(M.escapes())):
    hit[M.so[M.sol[M.wo[w]['sales_order_line_id']]['sales_order_id']]['customer_id']] += f(M.lot_of(w)['lot_quantity'])
q('Q-42', 'S08', 'complex', 'QM', '被拒收和漏检的批次一共涉及多少件？分别影响了哪些客户、各多少件？',
  'How many units do the rejected lots and the lot released despite an out-of-spec result involve, and which customers are affected, by how many units each?',
  dict(units=num(sum(hit.values())), customers={k: num(v) for k, v in sorted(hit.items())}), '总件数、各客户件数', 'total units, units per customer')

# --- S09 maintenance ---------------------------------------------------------------------------
od = M.overdue_maintenance()
q('Q-43', 'S09', 'basic', 'PR', '哪些设备维护工单逾期了？', 'Which maintenance work orders are overdue?', dict(maintenance_orders=od), '维护工单清单', 'maintenance work order ids')
q('Q-46', 'S09', 'basic', 'PR', '现在有几台设备在维修？是哪几台？', 'How many machines are under repair now, and which?',
  dict(machines=sorted(m['machine_id'] for m in T['production_machines'] if c(m['status']) == 'under_repair')), '设备清单', 'machine ids')
turn_mwo = next(m for m in T['maintenance_work_orders'] if m['machine_id'] == 'MACH-TURN-01' and m['planned_date'][:7] == '2027-01')
clash = sorted(e['execution_record_id'] for e in executions if e['machine_id'] == 'MACH-TURN-01' and e['started_date'] == turn_mwo['planned_date'])
q('Q-44', 'S09', 'medium', 'PR', '数控车床 1 号一月份保养那天有没有排生产？', 'Was CNC Lathe 1 used for production on the day of its January service?',
  dict(maintenance_order=turn_mwo['maintenance_work_order_id'], date=turn_mwo['planned_date'], executions=clash), '维护工单、日期、同日执行', 'maintenance order, date, same-day executions')
pt = next(m for m in T['maintenance_work_orders'] if m['maintenance_work_order_id'] in od and m['machine_id'] == 'MACH-PT-01')
after = sorted(e['execution_record_id'] for e in executions if e['machine_id'] == 'MACH-PT-01' and e['started_date'] > pt['planned_date'])
q('Q-45', 'S09', 'complex', 'PR', '压力测试台 1 号的保养逾期多久了？逾期以后它又做了哪些压力测试？',
  'How long has Pressure Rig 1\'s service been overdue, and which pressure tests has it run since?',
  dict(maintenance_order=pt['maintenance_work_order_id'], planned=pt['planned_date'], days_overdue=(date.fromisoformat(TODAY) - date.fromisoformat(pt['planned_date'])).days, executions=after),
  '维护工单、计划日期、逾期天数、之后的执行', 'maintenance order, planned date, days overdue, later executions')

# --- S10 end-to-end trace ----------------------------------------------------------------------
w6 = 'WO-2701-06'
q('Q-47', 'S10', 'complex', 'OD', '把 SO-2612-05 从下单到发运的过程讲一下：哪个工单做的、发了什么料、谁在哪台设备上做的、检验和入库怎样、哪天发的货？',
  'Trace SO-2612-05 from order to shipment: which work order made it, what material was issued, who did the work on which machine, how inspection and receipt went, and when it shipped.',
  dict(work_order=w6, issue=rows('material_issue_transactions', production_order_id=w6)[0]['material_issue_transaction_id'],
       machines=sorted({e['machine_id'] for e in M.executions(w6)}), operators=sorted({e['operator_id'] for e in M.executions(w6)}),
       lot=M.lot_of(w6)['inspection_lot_id'], receipt=rows('finished_goods_receipts', production_order_id=w6)[0]['finished_goods_receipt_id'],
       shipment=rows('shipments', production_order_id=w6)[0]['shipment_id'], shipped=num(lines[M.wo[w6]['sales_order_line_id']]['shipped']),
       late_days=lines[M.wo[w6]['sales_order_line_id']]['late_days']),
  '工单、发料、设备、操作员、检验批、入库、发运、延误天数', 'work order, issue, machines, operators, lot, receipt, shipment, days late')
seal = M.balance('PC-SEAL')
q('Q-48', 'S10', 'basic', 'PM', '密封圈套件现在在手多少、已分配多少、可用多少？', 'How many FKM seal kits are on hand, allocated and available now?',
  dict(on_hand=num(seal['on_hand']), allocated=num(seal['allocated']), available=num(seal['available'])), '在手、已分配、可用', 'on hand, allocated, available')
fg_stock = {b['product_id']: num(b['on_hand_quantity']) for b in T['inventory_balances'] if b['inventory_location_id'].endswith('-FG') and f(b['on_hand_quantity']) > 0}
q('Q-49', 'S10', 'medium', 'PM', '成品库里现在有哪些成品？各多少件？', 'Which finished goods are in stock now, and how many units of each?',
  dict(products=fg_stock), '成品及数量', 'products and units')
w31 = 'WO-2703-01'
fg31 = rows('finished_goods_receipts', production_order_id=w31)[0]
q('Q-50', 'S10', 'complex', 'OD', 'WO-2703-01 做完了吗？质量放行了吗？成品放在哪个库？客户要求哪天交货？',
  'Is WO-2703-01 finished and released by quality, where are the finished goods stored, and when does the customer want them?',
  dict(completed=num(M.completed_qty(w31)), quality_ok=M.quality_ok(w31), location=fg31['inventory_location_id'], requested=M.requested(M.wo[w31]['sales_order_line_id']), shipped=num(lines[M.wo[w31]['sales_order_line_id']]['shipped'])),
  '完成数量、是否放行、库位、要求交期、已发数量', 'completed units, released or not, location, requested date, shipped units')


def main():
    assert len(QUESTIONS) == 50 and len({x['id'] for x in QUESTIONS}) == 50
    meta = dict(schema_version='1.0', set_id='manufacturing-business-scenarios-v1', business_date=TODAY, prd='docs/PRD.md')
    dump = lambda data: yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)
    questions = sorted(({k: v for k, v in x.items() if k != 'expected'} for x in QUESTIONS), key=lambda x: x['id'])
    answers = [dict(id=x['id'], question=x['question'], expected=x['expected']) for x in sorted(QUESTIONS, key=lambda x: x['id'])]
    (HERE / 'question-set-v1.yaml').write_text(dump(dict(meta, audience='evaluated_agent', answer_set_access='forbidden', questions=questions)), encoding='utf-8')
    (HERE / 'answer-set-v1.yaml').write_text(dump(dict(meta, generation_method='independent CSV oracle (oracle.py + mfg_calc.py)', answers=answers)), encoding='utf-8')
    print(len(QUESTIONS), Counter(x['difficulty'] for x in QUESTIONS), Counter(x['role'] for x in QUESTIONS), Counter(x['scenario'] for x in QUESTIONS))


if __name__ == '__main__':
    main()
