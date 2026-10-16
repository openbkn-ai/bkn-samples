#!/usr/bin/env python3
"""制造业场景数据的确定性验收检查。"""
import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((Path(__file__).with_name('expected-results.json')).read_text())
QUESTION_BANK = json.loads((Path(__file__).with_name('questions.json')).read_text())
STATUS = {'completed': '已完成', 'qualified': '合格', 'assigned': '已安排', 'blocked': '已阻塞', 'rejected': '已拒绝', 'fail': '不通过', 'released': '已下达'}


def rows(name):
    with (ROOT / 'data' / f'{name}.csv').open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


order = rows('production_orders')[0]
material = rows('production_order_material_requirements')[0]
executions = [row for row in rows('production_execution_records') if row['execution_record_id'] in {'EXE-001', 'EXE-002'}]
steps = {row['process_step_id']: row for row in rows('process_steps') if row['process_step_id'] in {'STEP-1001-10-A', 'STEP-1001-20-A'}}
machine_caps = {(row['machine_id'], row['capability_id']) for row in rows('machine_capability_assignments') if row['qualification_status'] == STATUS['qualified']}
operator_caps = {(row['operator_id'], row['capability_id']) for row in rows('operator_qualifications') if row['qualification_status'] == STATUS['qualified']}
lot, result = rows('quality_inspection_lots')[0], rows('quality_inspection_results')[0]
balance, maintenance = rows('inventory_balances')[1], rows('maintenance_work_orders')[0]
operations = {row['operation_id']: row for row in rows('manufacturing_operations')}
shift_assignments = [row for row in rows('operator_shift_assignments') if row['operator_id'] == 'OPR-001' and row['assignment_status'] == STATUS['assigned']]
shifts = {row['shift_id']: row for row in rows('shifts')}

assert order['sales_order_line_id'] == EXPECTED['MFG-01']['sales_order_line_id'] and order['requested_quantity'] == EXPECTED['MFG-01']['quantity']
assert material['required_quantity'] == EXPECTED['MFG-02']['required_quantity'] and material['issued_quantity'] == EXPECTED['MFG-02']['issued_quantity']
assert len(executions) == EXPECTED['MFG-03']['completed_steps'] and all(row['status'] == STATUS['completed'] for row in executions)
assert sum((row['machine_id'], steps[row['process_step_id']]['required_capability_id']) in machine_caps for row in executions) == EXPECTED['MFG-04']['capability_matches']
assert sum((row['operator_id'], steps[row['process_step_id']]['required_capability_id']) in operator_caps for row in executions) == EXPECTED['MFG-05']['qualified_executions']
assert sum(
    any(
        assignment['work_center_id'] == operations[steps[row['process_step_id']]['operation_id']]['work_center_id']
        and date.fromisoformat(shifts[assignment['shift_id']]['starts_date']) <= date.fromisoformat(row['started_date']) <= date.fromisoformat(shifts[assignment['shift_id']]['ends_date'])
        for assignment in shift_assignments
    )
    for row in executions
) == EXPECTED['MFG-06']['shift_date_consistent_executions']
assert lot['status'] == EXPECTED['MFG-07']['inspection_status'] and result['result_status'] == EXPECTED['MFG-07']['result_status']
assert float(result['lower_limit']) <= float(result['measured_value']) <= float(result['upper_limit'])
assert balance['on_hand_quantity'] == EXPECTED['MFG-08']['on_hand_quantity'] and balance['allocated_quantity'] == EXPECTED['MFG-08']['allocated_quantity'] and balance['available_quantity'] == EXPECTED['MFG-08']['available_quantity'] and balance['as_of_date'] == EXPECTED['MFG-08']['as_of_date']
assert maintenance['maintenance_work_order_id'] == EXPECTED['MFG-09']['maintenance_work_order_id'] and maintenance['status'] == EXPECTED['MFG-09']['status']
assert len(list((ROOT / 'iof-reference' / 'data').glob('*.csv'))) == EXPECTED['MFG-10']['reference_class_count']
operational_tables = list((ROOT / 'data').glob('*.csv'))
operational_record_counts = [len(rows(path.stem)) for path in operational_tables]
assert len(operational_tables) == EXPECTED['MFG-11']['operational_table_count']
assert min(operational_record_counts) == EXPECTED['MFG-11']['minimum_records_per_table']
assert sum(operational_record_counts) == EXPECTED['MFG-11']['total_operational_records']
forecast_periods = sorted({row['forecast_period'] for row in rows('demand_forecasts')})
due_dates = sorted(row['due_date'] for row in rows('production_orders'))
assert forecast_periods[0] == EXPECTED['MFG-16']['forecast_start'] and forecast_periods[-1] == EXPECTED['MFG-16']['forecast_end']
assert due_dates[-1] == EXPECTED['MFG-16']['latest_due_date']
material_branch = next(row for row in rows('production_order_material_requirements') if row['production_order_id'] == 'WO-1001-MAT')
quality_branch_lot = next(row for row in rows('quality_inspection_lots') if row['production_order_id'] == 'WO-1001-QFAIL')
quality_branch_result = next(row for row in rows('quality_inspection_results') if row['inspection_lot_id'] == quality_branch_lot['inspection_lot_id'])
accepted_lots = [row for row in rows('quality_inspection_lots') if row['status'] == EXPECTED['MFG-07']['inspection_status']]
material_branches = [
    row for row in rows('production_order_material_requirements')
    if row['production_order_id'].startswith('WO-1001-MAT')
    or (row['production_order_id'].startswith('WO-1001-B0') and 21 <= int(row['production_order_id'][-3:]) <= 30)
]
quality_failure_lots = [row for row in rows('quality_inspection_lots') if row['status'] == STATUS['rejected']]
quality_failure_results = [row for row in rows('quality_inspection_results') if row['result_status'] == STATUS['fail']]
in_production_orders = [row for row in rows('production_orders') if row['status'] == STATUS['released']]
in_production_order_ids = {row['production_order_id'] for row in in_production_orders}
in_production_lots = [row for row in rows('quality_inspection_lots') if row['production_order_id'] in in_production_order_ids]
assert len(accepted_lots) == EXPECTED['MFG-12']['normal_completion_batches']
assert len(material_branches) == EXPECTED['MFG-13']['material_shortage_batches']
assert material_branch['issued_quantity'] == EXPECTED['MFG-13']['issued_quantity'] and material_branch['required_quantity'] == EXPECTED['MFG-13']['required_quantity']
assert all(row['issued_quantity'] == EXPECTED['MFG-13']['issued_quantity'] and row['required_quantity'] == EXPECTED['MFG-13']['required_quantity'] for row in material_branches)
assert len(quality_failure_lots) == EXPECTED['MFG-14']['quality_failure_batches'] and len(quality_failure_results) == EXPECTED['MFG-14']['quality_failure_batches']
assert quality_branch_lot['status'] == STATUS['rejected'] and quality_branch_result['result_status'] == STATUS['fail']
assert all(row['measured_value'] == EXPECTED['MFG-14']['measured_value'] and row['upper_limit'] == EXPECTED['MFG-14']['upper_limit'] for row in quality_failure_results)
assert len(in_production_orders) == EXPECTED['MFG-15']['in_production_batches']
assert len(in_production_lots) == EXPECTED['MFG-15']['in_production_batches'] and all(row['status'] == EXPECTED['MFG-15']['quality_status'] for row in in_production_lots)
shipments = rows('shipments')
assert sum(row['delivery_status'] == STATUS['completed'] for row in shipments) == EXPECTED['MFG-17']['shipment_complete_batches']
assert sum(row['delivery_status'] == STATUS['blocked'] for row in shipments) == EXPECTED['MFG-17']['material_blocked_shipments']
assert sum(row['delivery_status'] == STATUS['rejected'] for row in shipments) == EXPECTED['MFG-17']['quality_rejected_shipments']
assert sum(row['delivery_status'] == EXPECTED['MFG-15']['quality_status'] for row in shipments) == EXPECTED['MFG-17']['in_production_pending_shipments']
plans = rows('production_plans')
plan_lines = rows('production_plan_lines')
assert all(row['snapshot_date'] == EXPECTED['MFG-18']['plan_snapshot_date'] and row['planning_start_date'] == EXPECTED['MFG-18']['planning_start'] and row['planning_end_date'] == EXPECTED['MFG-18']['planning_end'] for row in plans)
assert all(row['scenario_as_of_date'] == EXPECTED['MFG-18']['plan_snapshot_date'] for row in plan_lines)
completed_shipments = [row for row in shipments if row['delivery_status'] == STATUS['completed']]
fg_by_id = {row['finished_goods_receipt_id']: row for row in rows('finished_goods_receipts')}
lots_by_order = {row['production_order_id']: row for row in rows('quality_inspection_lots')}
assert len([row for row in shipments if row['shipped_quantity'] == '0' and row['delivery_status'] in {STATUS['blocked'], STATUS['rejected'], EXPECTED['MFG-15']['quality_status']}]) + len(completed_shipments) == EXPECTED['MFG-18']['validated_shipment_gates']
assert all(fg_by_id[row['finished_goods_receipt_id']]['production_order_id'] == row['production_order_id'] and lots_by_order[row['production_order_id']]['status'] == '已接受' for row in completed_shipments)

assert len(QUESTION_BANK) == 100 and len({item['id'] for item in QUESTION_BANK}) == 100
assert {item['level'] for item in QUESTION_BANK} == {'easy_basic', 'intermediate', 'hard_complex'}
assert {level: sum(item['level'] == level for item in QUESTION_BANK) for level in {'easy_basic', 'intermediate', 'hard_complex'}} == {'easy_basic': 30, 'intermediate': 40, 'hard_complex': 30}
assert all(item['expected_answer'] for item in QUESTION_BANK)
print('MFG-01 至 MFG-18 已通过。')
print('100 题中英对照题库结构检查已通过。')
print('数据规模、计划时间跨度、物料发放、质量、成品入库、发运和业务分支的确定性检查已通过。')
