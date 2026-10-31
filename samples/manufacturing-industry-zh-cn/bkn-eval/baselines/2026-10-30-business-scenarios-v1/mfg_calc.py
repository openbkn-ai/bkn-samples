"""Business rules of the manufacturing PRD, computed from the delivered CSV files only.

Written from docs/PRD.md without importing the data generator; status texts are mapped from the
zh-CN or en-US display values to the same codes so both packages give the same results.
"""
import csv
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

TODAY = '2027-02-28'
CODES = {
    '已接受': 'accepted', '已拒绝': 'rejected', '已拒收': 'rejected', '待检': 'pending_inspection', '待处理': 'pending',
    '已完成': 'completed', '已阻塞': 'blocked', '已下达': 'released', '生产中': 'in_production', '进行中': 'in_progress',
    '未开始': 'not_started', '已发料': 'issued', '部分发料': 'partial', '待发料': 'awaiting_issue', '通过': 'pass', '不通过': 'fail',
    '已发运': 'shipped', '已冻结': 'frozen', '草稿': 'draft', '已停用': 'obsolete', '生效': 'active', '已作废': 'superseded',
    '可用': 'available', '维修中': 'under_repair', '合格': 'qualified', '暂停': 'suspended', '培训中': 'in_training',
    '在职': 'active', '离职': 'left', '已安排': 'assigned', '已计划': 'planned', '已取消': 'cancelled', '已确认': 'confirmed',
    '部分发货': 'partially_shipped', '已收货': 'received', '部分收货': 'partially_received', '启用': 'active',
}


def c(value):
    return CODES.get(value, value)


def f(value):
    return float(value) if value not in ('', None) else 0.0


class Mfg:
    def __init__(self, data_dir):
        self.t = {}
        for path in Path(data_dir).glob('*.csv'):
            with path.open(encoding='utf-8', newline='') as h:
                self.t[path.stem] = list(csv.DictReader(h))
        T = self.t
        self.wo = {r['production_order_id']: r for r in T['production_orders']}
        self.sol = {r['sales_order_line_id']: r for r in T['sales_order_lines']}
        self.so = {r['sales_order_id']: r for r in T['sales_orders']}
        self.prod = {r['product_id']: r for r in T['products']}
        self.ops = {r['operation_id']: r for r in T['manufacturing_operations']}
        self.steps = {r['process_step_id']: r for r in T['process_steps']}
        self.machines = {r['machine_id']: r for r in T['production_machines']}
        self.shifts = {r['shift_id']: r for r in T['shifts']}
        self.specs = {r['quality_specification_id']: r for r in T['quality_specifications']}
        self.lots = {r['inspection_lot_id']: r for r in T['quality_inspection_lots']}
        self.receipts = {r['goods_receipt_id']: r for r in T['goods_receipts']}
        self.pol = {r['purchase_order_line_id']: r for r in T['purchase_order_lines']}
        self.po = {r['purchase_order_id']: r for r in T['purchase_orders']}
        self.bomv = {r['bom_version_id']: r for r in T['product_bom_versions']}
        self.fgr = {r['finished_goods_receipt_id']: r for r in T['finished_goods_receipts']}

    # --- orders and delivery -------------------------------------------------------------------
    def shipments_of(self, sol_id):
        return sorted((s for s in self.t['shipments'] if s['sales_order_line_id'] == sol_id), key=lambda s: s['shipment_date'])

    def requested(self, sol_id):
        return self.so[self.sol[sol_id]['sales_order_id']]['requested_delivery_date']

    def line(self, sol_id):
        ordered = f(self.sol[sol_id]['ordered_quantity'])
        ships = self.shipments_of(sol_id)
        shipped = sum(f(s['shipped_quantity']) for s in ships)
        req = self.requested(sol_id)
        backlog = max(0.0, ordered - shipped)
        last = ships[-1]['shipment_date'] if ships else None
        if backlog == 0:
            late_days = max(0, (date.fromisoformat(last) - date.fromisoformat(req)).days)
        elif req < TODAY:
            late_days = (date.fromisoformat(TODAY) - date.fromisoformat(req)).days
        else:
            late_days = 0
        return dict(ordered=ordered, shipped=shipped, backlog=backlog, requested=req, last=last, late=late_days > 0, late_days=late_days,
                    complete=backlog == 0, shipments=[s['shipment_id'] for s in ships])

    def wos_of_line(self, sol_id):
        return sorted(w for w, r in self.wo.items() if r['sales_order_line_id'] == sol_id)

    # --- material -------------------------------------------------------------------------------
    def requirements(self, wo_id):
        return [r for r in self.t['production_order_material_requirements'] if r['production_order_id'] == wo_id]

    def required_by_rule(self, wo_id, req):
        comp = next(b for b in self.t['bom_components'] if b['bom_component_id'] == req['bom_component_id'])
        return math.ceil(round(f(self.wo[wo_id]['requested_quantity']) * f(comp['quantity_per']) * (1 + f(comp['scrap_factor'])), 6))

    def issued(self, req_id):
        return sum(f(i['issued_quantity']) for i in self.t['material_issue_transactions'] if i['material_requirement_id'] == req_id)

    def shortages(self, wo_id):
        out = {}
        for r in self.requirements(wo_id):
            need, got = self.required_by_rule(wo_id, r), self.issued(r['material_requirement_id'])
            if got < need:
                out[r['product_id']] = need - got
        return out

    def blocked_reasons(self, wo_id):
        reasons = []
        if c(self.bomv[self.wo[wo_id]['bom_version_id']]['status']) != 'frozen':
            reasons.append('bom_not_frozen')
        start = next(l['planned_start_date'] for l in self.t['production_plan_lines'] if l['production_order_id'] == wo_id)
        if start <= TODAY and self.shortages(wo_id):
            reasons.append('material_short')
        return reasons

    def improper_issues(self):
        return sorted(i['material_issue_transaction_id'] for i in self.t['material_issue_transactions']
                      if c(self.receipts[i['goods_receipt_id']]['inspection_status']) != 'accepted')

    # --- purchasing -----------------------------------------------------------------------------
    def po_accepted(self, po_id):
        lines = [l for l in self.t['purchase_order_lines'] if l['purchase_order_id'] == po_id]
        got = sum(f(r['received_quantity']) for r in self.t['goods_receipts'] if r['purchase_order_line_id'] in {l['purchase_order_line_id'] for l in lines} and c(r['inspection_status']) == 'accepted')
        return got, sum(f(l['ordered_quantity']) for l in lines)

    def overdue_pos(self):
        out = []
        for po_id, po in self.po.items():
            got, ordered = self.po_accepted(po_id)
            if po['expected_receipt_date'] < TODAY and got < ordered:
                out.append(po_id)
        return sorted(out)

    def late_receipts(self):
        out = []
        for r in self.t['goods_receipts']:
            po = self.po[self.pol[r['purchase_order_line_id']]['purchase_order_id']]
            if c(r['inspection_status']) != 'rejected' and r['received_date'] > po['expected_receipt_date']:
                out.append((r['goods_receipt_id'], po['purchase_order_id'], po['supplier_id'], (date.fromisoformat(r['received_date']) - date.fromisoformat(po['expected_receipt_date'])).days))
        return out

    # --- execution ------------------------------------------------------------------------------
    def executions(self, wo_id=None):
        out = []
        for e in self.t['production_execution_records']:
            step = self.steps[e['process_step_id']]
            op = self.ops[step['operation_id']]
            if wo_id is None or op['production_order_id'] == wo_id:
                out.append(dict(e, wo=op['production_order_id'], cap=step['required_capability_id'], wc=op['work_center_id'], seq=int(op['sequence_number'])))
        return out

    def compliance(self, e):
        reasons = []
        start = e['started_date']
        if not any(a['machine_id'] == e['machine_id'] and a['capability_id'] == e['cap'] and c(a['qualification_status']) == 'qualified'
                   for a in self.t['machine_capability_assignments']):
            reasons.append('machine_capability')
        if any(m['machine_id'] == e['machine_id'] and m['planned_date'] == start and c(m['status']) != 'cancelled' for m in self.t['maintenance_work_orders']):
            reasons.append('maintenance_same_day')
        if not any(q['operator_id'] == e['operator_id'] and q['capability_id'] == e['cap'] and c(q['qualification_status']) == 'qualified' and q['valid_to'] >= start
                   for q in self.t['operator_qualifications']):
            reasons.append('operator_qualification')
        if not any(a['operator_id'] == e['operator_id'] and a['work_center_id'] == e['wc'] and c(a['assignment_status']) == 'assigned'
                   and self.shifts[a['shift_id']]['starts_date'] <= start <= self.shifts[a['shift_id']]['ends_date']
                   for a in self.t['operator_shift_assignments']):
            reasons.append('shift_assignment')
        return reasons

    def noncompliant(self):
        return {e['execution_record_id']: (e['wo'], self.compliance(e)) for e in self.executions() if self.compliance(e)}

    # --- output ---------------------------------------------------------------------------------
    def completed_qty(self, wo_id):
        ex = [e for e in self.executions(wo_id) if c(e['status']) == 'completed']
        ops = [o for o in self.ops.values() if o['production_order_id'] == wo_id]
        if len(ex) < len(ops):
            return None
        return f(max(ex, key=lambda e: e['seq'])['good_quantity'])

    def scrap(self, wo_id):
        return sum(f(e['scrap_quantity']) for e in self.executions(wo_id))

    # --- quality --------------------------------------------------------------------------------
    def lot_of(self, wo_id):
        return next((l for l in self.t['quality_inspection_lots'] if l['production_order_id'] == wo_id), None)

    def results(self, lot_id):
        return [r for r in self.t['quality_inspection_results'] if r['inspection_lot_id'] == lot_id]

    def out_of_spec(self, lot_id):
        bad = []
        for r in self.results(lot_id):
            s = self.specs[r['quality_specification_id']]
            if c(r['result_status']) != 'pending' and not (f(s['lower_limit']) <= f(r['measured_value']) <= f(s['upper_limit'])):
                bad.append(r)
        return bad

    def quality_ok(self, wo_id):
        lot = self.lot_of(wo_id)
        if lot is None or c(lot['status']) == 'pending':
            return None
        return c(lot['status']) == 'accepted' and not self.out_of_spec(lot['inspection_lot_id'])

    def escapes(self):
        """Lots released although a result marked pass is outside its specification."""
        return sorted(l['production_order_id'] for l in self.t['quality_inspection_lots']
                      if c(l['status']) == 'accepted' and any(c(r['result_status']) == 'pass' for r in self.out_of_spec(l['inspection_lot_id'])))

    # --- stock, maintenance, plan -----------------------------------------------------------------
    def balance(self, product_id, location_type=None):
        rows = [b for b in self.t['inventory_balances'] if b['product_id'] == product_id]
        return dict(on_hand=sum(f(b['on_hand_quantity']) for b in rows), allocated=sum(f(b['allocated_quantity']) for b in rows),
                    available=sum(f(b['available_quantity']) for b in rows))

    def overdue_maintenance(self):
        return sorted(m['maintenance_work_order_id'] for m in self.t['maintenance_work_orders'] if m['planned_date'] < TODAY and c(m['status']) != 'completed')

    def plan_vs_forecast(self):
        planned = defaultdict(float)
        for l in self.t['production_plan_lines']:
            month = self.wo[l['production_order_id']]['due_date'][:7]
            planned[(l['product_id'], month)] += f(l['planned_quantity'])
        out = {}
        for fc in self.t['demand_forecasts']:
            key = (fc['product_id'], fc['forecast_period'])
            out[key] = dict(forecast=f(fc['forecast_quantity']), planned=planned.get(key, 0.0))
        return out
