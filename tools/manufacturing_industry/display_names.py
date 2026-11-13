"""Display names for the manufacturing samples: every property and relation, in Chinese and English.

`python3 -m tools.manufacturing_industry.display_names` rewrites the Display Name column of every
object type and the `name` of every relation type in both samples. Identifiers stay unchanged.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = {'zh': ROOT / 'samples' / 'manufacturing-industry-zh-cn', 'en': ROOT / 'samples' / 'manufacturing-industry-en-us'}

# property -> (Chinese, English)
PROPERTIES = {
    'bom_id': ('物料清单编号', 'BOM ID'),
    'bom_version_id': ('BOM 版本编号', 'BOM Version ID'),
    'bom_name': ('物料清单名称', 'BOM Name'),
    'quantity_basis': ('基准数量', 'Quantity Basis'),
    'bom_component_id': ('BOM 组件编号', 'BOM Component ID'),
    'component_product_id': ('组件物料编号', 'Component Product ID'),
    'quantity_per': ('单位用量', 'Quantity Per'),
    'unit': ('单位', 'Unit'),
    'scrap_factor': ('损耗系数', 'Scrap Factor'),
    'customer_id': ('客户编号', 'Customer ID'),
    'customer_name': ('客户名称', 'Customer Name'),
    'customer_segment': ('客户分层', 'Customer Segment'),
    'forecast_id': ('预测编号', 'Forecast ID'),
    'product_id': ('物料编号', 'Product ID'),
    'forecast_period': ('预测期间', 'Forecast Period'),
    'forecast_quantity': ('预测数量', 'Forecast Quantity'),
    'capability_id': ('能力编号', 'Capability ID'),
    'capability_name': ('能力名称', 'Capability Name'),
    'capability_category': ('能力类别', 'Capability Category'),
    'finished_goods_receipt_id': ('成品入库编号', 'Finished Goods Receipt ID'),
    'production_order_id': ('生产工单编号', 'Production Order ID'),
    'inspection_lot_id': ('检验批编号', 'Inspection Lot ID'),
    'inventory_location_id': ('库位编号', 'Inventory Location ID'),
    'received_quantity': ('入库数量', 'Received Quantity'),
    'receipt_date': ('入库日期', 'Receipt Date'),
    'status': ('状态', 'Status'),
    'goods_receipt_id': ('收货编号', 'Goods Receipt ID'),
    'purchase_order_line_id': ('采购订单行编号', 'Purchase Order Line ID'),
    'received_date': ('收货日期', 'Received Date'),
    'inspection_status': ('检验状态', 'Inspection Status'),
    'inventory_balance_id': ('库存余额编号', 'Inventory Balance ID'),
    'on_hand_quantity': ('现有数量', 'On-hand Quantity'),
    'available_quantity': ('可用数量', 'Available Quantity'),
    'allocated_quantity': ('已分配数量', 'Allocated Quantity'),
    'as_of_date': ('截至日期', 'As-of Date'),
    'site_id': ('工厂编号', 'Site ID'),
    'location_name': ('库位名称', 'Location Name'),
    'location_type': ('库位类型', 'Location Type'),
    'machine_capability_assignment_id': ('设备能力分配编号', 'Machine Capability Assignment ID'),
    'machine_id': ('设备编号', 'Machine ID'),
    'qualification_status': ('资质状态', 'Qualification Status'),
    'maintenance_plan_id': ('保养计划编号', 'Maintenance Plan ID'),
    'plan_name': ('计划名称', 'Plan Name'),
    'frequency_days': ('周期（天）', 'Frequency (Days)'),
    'maintenance_work_order_id': ('维修工单编号', 'Maintenance Work Order ID'),
    'planned_date': ('应保养日', 'Due Date'),
    'planned_start_date': ('计划开始日', 'Planned Start Date'),
    'planned_end_date': ('计划结束日', 'Planned End Date'),
    'operation_id': ('工序编号', 'Operation ID'),
    'routing_operation_id': ('工艺路线工序编号', 'Routing Operation ID'),
    'work_center_id': ('工作中心编号', 'Work Center ID'),
    'operation_name': ('工序名称', 'Operation Name'),
    'sequence_number': ('序号', 'Sequence Number'),
    'planned_machine_id': ('计划机台', 'Planned Machine'),
    'standard_duration_days': ('标准工期（天）', 'Standard Duration (Days)'),
    'predecessor_operation_id': ('前序工序', 'Predecessor Operation'),
    'site_name': ('工厂名称', 'Site Name'),
    'site_type': ('工厂类型', 'Site Type'),
    'country_code': ('国家代码', 'Country Code'),
    'material_issue_transaction_id': ('发料记录编号', 'Material Issue Transaction ID'),
    'material_requirement_id': ('用料需求编号', 'Material Requirement ID'),
    'issued_quantity': ('已发数量', 'Issued Quantity'),
    'issue_date': ('发料日期', 'Issue Date'),
    'operator_qualification_id': ('人员资质编号', 'Operator Qualification ID'),
    'operator_id': ('操作员编号', 'Operator ID'),
    'valid_to': ('有效期至', 'Valid To'),
    'operator_shift_assignment_id': ('排班编号', 'Shift Assignment ID'),
    'shift_id': ('班次编号', 'Shift ID'),
    'assignment_status': ('排班状态', 'Assignment Status'),
    'operator_name': ('操作员姓名', 'Operator Name'),
    'home_site_id': ('所属工厂编号', 'Home Site ID'),
    'employment_status': ('在职状态', 'Employment Status'),
    'process_step_id': ('工步编号', 'Process Step ID'),
    'process_step_name': ('工步名称', 'Process Step Name'),
    'required_capability_id': ('所需能力编号', 'Required Capability ID'),
    'setup_class': ('换型类别', 'Setup Class'),
    'version_code': ('版本号', 'Version Code'),
    'effective_from': ('生效日期', 'Effective From'),
    'execution_record_id': ('执行记录编号', 'Execution Record ID'),
    'started_date': ('开始日期', 'Started Date'),
    'completed_date': ('完成日期', 'Completed Date'),
    'good_quantity': ('合格数量', 'Good Quantity'),
    'scrap_quantity': ('报废数量', 'Scrap Quantity'),
    'machine_name': ('设备名称', 'Machine Name'),
    'machine_type': ('设备类型', 'Machine Type'),
    'required_quantity': ('需求数量', 'Required Quantity'),
    'sales_order_line_id': ('销售订单行编号', 'Sales Order Line ID'),
    'routing_id': ('工艺路线编号', 'Routing ID'),
    'requested_quantity': ('需求数量', 'Requested Quantity'),
    'due_date': ('交期', 'Due Date'),
    'production_plan_line_id': ('生产计划行编号', 'Production Plan Line ID'),
    'production_plan_id': ('生产计划编号', 'Production Plan ID'),
    'planned_quantity': ('计划数量', 'Planned Quantity'),
    'planned_completion_date': ('计划完成日', 'Planned Completion Date'),
    'scenario_as_of_date': ('情景基准日', 'Scenario As-of Date'),
    'plan_version': ('计划版本', 'Plan Version'),
    'snapshot_date': ('快照日期', 'Snapshot Date'),
    'planning_start_date': ('计划期开始日', 'Planning Start Date'),
    'planning_end_date': ('计划期结束日', 'Planning End Date'),
    'product_code': ('物料代码', 'Product Code'),
    'product_name': ('物料名称', 'Product Name'),
    'product_type': ('物料类型', 'Product Type'),
    'base_unit': ('基本单位', 'Base Unit'),
    'purchase_order_id': ('采购订单编号', 'Purchase Order ID'),
    'ordered_quantity': ('订购数量', 'Ordered Quantity'),
    'supplier_id': ('供应商编号', 'Supplier ID'),
    'order_date': ('下单日期', 'Order Date'),
    'expected_receipt_date': ('预计到货日', 'Expected Receipt Date'),
    'inspection_type': ('检验类型', 'Inspection Type'),
    'lot_quantity': ('批量', 'Lot Quantity'),
    'inspection_result_id': ('检验结果编号', 'Inspection Result ID'),
    'characteristic_name': ('检验特性', 'Characteristic'),
    'measured_value': ('实测值', 'Measured Value'),
    'target_value': ('目标值', 'Target Value'),
    'lower_limit': ('下限', 'Lower Limit'),
    'upper_limit': ('上限', 'Upper Limit'),
    'result_status': ('判定结果', 'Result Status'),
    'quality_specification_id': ('质量规格编号', 'Quality Specification ID'),
    'effective_date': ('生效日期', 'Effective Date'),
    'operation_code': ('工序代码', 'Operation Code'),
    'routing_name': ('工艺路线名称', 'Routing Name'),
    'sales_order_id': ('销售订单编号', 'Sales Order ID'),
    'requested_delivery_date': ('要求交货日', 'Requested Delivery Date'),
    'shift_name': ('班次名称', 'Shift Name'),
    'starts_date': ('开始日期', 'Start Date'),
    'ends_date': ('结束日期', 'End Date'),
    'shipment_id': ('发货编号', 'Shipment ID'),
    'shipped_quantity': ('发货数量', 'Shipped Quantity'),
    'shipment_date': ('发货日期', 'Shipment Date'),
    'delivery_status': ('交付状态', 'Delivery Status'),
    'supplier_name': ('供应商名称', 'Supplier Name'),
    'supplier_category': ('供应商类别', 'Supplier Category'),
    'work_center_name': ('工作中心名称', 'Work Center Name'),
    'work_center_type': ('工作中心类型', 'Work Center Type'),
}

# Relations are named after the field that links them: "<source object>的<target>" / "<Source object> → <target>".
# The target reads as the field's label without a trailing ID; these fields read better under another name.
RELATION_TARGETS = {
    'planned_machine_id': ('计划机台', 'Planned Machine'),
    'predecessor_operation_id': ('前序工序', 'Predecessor Operation'),
    'component_product_id': ('组件物料', 'Component Product'),
    'required_capability_id': ('所需能力', 'Required Capability'),
    'home_site_id': ('所属工厂', 'Home Site'),
}


def relation_target(field, language):
    if field in RELATION_TARGETS:
        return RELATION_TARGETS[field][language == 'en']
    label = PROPERTIES[field][language == 'en']
    return re.sub(r'编号$', '', label) if language == 'zh' else re.sub(r' ID$', '', label)


def relation_name(source_name, field, language):
    target = relation_target(field, language)
    return f'{source_name}的{target}' if language == 'zh' else f'{source_name} → {target}'


def _object_names(sample):
    return {p.stem: re.search(r'^name: (.*)$', p.read_text(encoding='utf-8'), re.M).group(1)
            for p in (sample / 'kn' / 'object_types').glob('*.bkn')}


ROW = re.compile(r'^\| (\w+) \| ([^|]+?) \| (\w+) \|', re.M)


def apply(language, sample):
    index = 0 if language == 'zh' else 1
    for path in sorted((sample / 'kn' / 'object_types').glob('*.bkn')):
        text = path.read_text(encoding='utf-8')
        new = ROW.sub(lambda m: m.group(0) if m.group(1) == 'Name' else
                      f'| {m.group(1)} | {PROPERTIES[m.group(1)][index]} | {m.group(3)} |', text)
        if new != text:
            path.write_text(new, encoding='utf-8')
    objects = _object_names(sample)
    for path in sorted((sample / 'kn' / 'relation_types').glob('*.bkn')):
        text = path.read_text(encoding='utf-8')
        source, target = re.search(r'^\| (\w+) \| (\w+) \| direct \|$', text, re.M).groups()
        fields = re.findall(r'^\| (\w+) \| (\w+) \|$', text.split('### Mapping Rules', 1)[1], re.M)
        fields = [f for f, _t in fields if f != 'Source Property']
        assert len(fields) == 1, (path, fields)
        name = relation_name(objects[source], fields[0], language)
        new = re.sub(r'^name: .*$', f'name: {name}', text, count=1, flags=re.M)
        new = re.sub(r'^## RelationType: .*$', f'## RelationType: {name}', new, count=1, flags=re.M)
        if new != text:
            path.write_text(new, encoding='utf-8')


if __name__ == '__main__':
    for language, sample in SAMPLES.items():
        apply(language, sample)
