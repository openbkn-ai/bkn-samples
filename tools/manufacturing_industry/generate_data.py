#!/usr/bin/env python3
"""Generates the manufacturing sample data (zh-CN and en-US) from one deterministic business story.

Two plants machine pump housings, valve bodies, impellers and flanges for ten customers from
November 2026 to March 2027; the business date is 2027-02-28. Products, machines, operators,
suppliers and stock are shared across orders, and the exceptions a planner, production lead,
quality lead or buyer must find are placed on purpose (listed in EXCEPTIONS). Table and column
layout is unchanged from the model contract.

Usage: generate_data.py [--check]   (--check compares with the committed CSV files)
"""
import csv
import datetime as dt
import hashlib
import io
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLES = {'zh': REPO / 'samples/manufacturing-industry-zh-cn', 'en': REPO / 'samples/manufacturing-industry-en-us'}
BUSINESS_DATE = dt.date(2027, 2, 28)
D = dt.date.fromisoformat


def day(value, delta=0):
    return (D(value) if isinstance(value, str) else value) + dt.timedelta(days=delta)


# --- vocabulary: code -> (zh, en) -------------------------------------------------------------
V = {
    'EA': ('件', 'EA'), 'KG': ('千克', 'KG'),
    'plant': ('工厂', 'plant'), 'machining': ('机加工', 'machining'), 'quality': ('质检', 'quality'), 'marking': ('标识', 'marking'),
    'inspection': ('检测', 'inspection'),
    'finished_good': ('成品', 'finished_good'), 'raw_material': ('原材料', 'raw_material'), 'purchased_part': ('外购件', 'purchased_part'),
    'raw_location': ('原料库', 'raw_material'), 'qi_location': ('待检区', 'quality_hold'), 'fg_location': ('成品库', 'finished_goods'),
    'frozen': ('已冻结', 'frozen'), 'draft': ('草稿', 'draft'), 'obsolete': ('已停用', 'obsolete'),
    'released': ('已下达', 'released'), 'active': ('生效', 'active'), 'superseded': ('已作废', 'superseded'),
    'available': ('可用', 'available'), 'under_repair': ('维修中', 'under_repair'),
    'qualified': ('合格', 'qualified'), 'suspended': ('暂停', 'suspended'), 'training': ('培训中', 'in_training'),
    'employed': ('在职', 'active'), 'left': ('离职', 'left'),
    'assigned': ('已安排', 'assigned'),
    'planned': ('已计划', 'planned'), 'in_progress': ('进行中', 'in_progress'), 'completed': ('已完成', 'completed'), 'not_started': ('未开始', 'not_started'),
    'blocked': ('已阻塞', 'blocked'), 'in_production': ('生产中', 'in_production'),
    'issued': ('已发料', 'issued'), 'partial': ('部分发料', 'partial'), 'awaiting_issue': ('待发料', 'awaiting_issue'),
    'accepted': ('已接受', 'accepted'), 'pending_inspection': ('待检', 'pending_inspection'), 'rejected': ('已拒收', 'rejected'),
    'lot_accepted': ('已接受', 'accepted'), 'lot_rejected': ('已拒绝', 'rejected'), 'lot_pending': ('待处理', 'pending'),
    'pass': ('通过', 'pass'), 'fail': ('不通过', 'fail'), 'pending': ('待处理', 'pending'),
    'confirmed': ('已确认', 'confirmed'), 'partially_shipped': ('部分发货', 'partially_shipped'), 'closed': ('已完成', 'completed'),
    'received': ('已收货', 'received'), 'partially_received': ('部分收货', 'partially_received'),
    'shipped': ('已发运', 'shipped'),
    'final': ('最终检验', 'final'),
    'pump_oem': ('泵业整机厂', 'pump_oem'), 'valve_oem': ('阀门整机厂', 'valve_oem'), 'project': ('工程项目', 'project'), 'distributor': ('分销商', 'distributor'),
    'casting': ('铸件', 'casting'), 'bar': ('棒料', 'bar_stock'), 'aluminium': ('铝材', 'aluminium'), 'seal': ('密封件', 'seals'), 'fastener': ('紧固件', 'fasteners'), 'label': ('标识件', 'labels'),
    'cast_iron': ('铸铁', 'CAST_IRON'), 'stainless': ('不锈钢', 'STAINLESS'), 'bronze': ('青铜', 'BRONZE'), 'aluminium_setup': ('铝材', 'ALUMINIUM'), 'inspect_setup': ('检验', 'INSPECTION'), 'mark_setup': ('打标', 'MARKING'),
    'CNC_MILL': ('五轴加工中心', 'CNC_MILL'), 'CNC_LATHE': ('数控车床', 'CNC_LATHE'), 'CMM': ('三坐标测量机', 'CMM'), 'PRESSURE_RIG': ('压力测试台', 'PRESSURE_RIG'), 'LASER': ('激光打标机', 'LASER_MARKER'),
    'active_plan': ('启用', 'active'),
}


def t(code, lang):
    return V[code][0 if lang == 'zh' else 1]


def n(pair, lang):
    return pair[0] if lang == 'zh' else pair[1]


# --- master data ------------------------------------------------------------------------------
SITES = [('SITE-SZ', ('深圳精密加工厂', 'Shenzhen Precision Machining Plant')), ('SITE-SU', ('苏州测试装配厂', 'Suzhou Test and Assembly Plant'))]
WORK_CENTERS = [
    ('WC-SZ-CNC', 'SITE-SZ', ('深圳五轴加工中心', 'Shenzhen 5-axis Machining Cell'), 'machining'),
    ('WC-SZ-TURN', 'SITE-SZ', ('深圳数控车削单元', 'Shenzhen CNC Turning Cell'), 'machining'),
    ('WC-SZ-QC', 'SITE-SZ', ('深圳计量室', 'Shenzhen Metrology Lab'), 'quality'),
    ('WC-SU-TEST', 'SITE-SU', ('苏州压力测试区', 'Suzhou Pressure Test Bay'), 'quality'),
    ('WC-SU-MARK', 'SITE-SU', ('苏州激光打标区', 'Suzhou Laser Marking Bay'), 'marking'),
]
CAPS = [
    ('CAP-MILL', ('五轴铣削', '5-axis milling'), 'machining'), ('CAP-TURN', ('数控车削', 'CNC turning'), 'machining'),
    ('CAP-CMM', ('三坐标检测', 'CMM inspection'), 'inspection'), ('CAP-PTEST', ('压力测试', 'Pressure testing'), 'inspection'),
    ('CAP-MARK', ('激光打标', 'Laser marking'), 'marking'),
]
MACHINES = [  # id, site, work centre, name, type, status, capability, assignment status
    ('MACH-MILL-01', 'SITE-SZ', 'WC-SZ-CNC', ('五轴加工中心 1 号', '5-axis Mill 1'), 'CNC_MILL', 'available', 'CAP-MILL', 'qualified'),
    ('MACH-MILL-02', 'SITE-SZ', 'WC-SZ-CNC', ('五轴加工中心 2 号', '5-axis Mill 2'), 'CNC_MILL', 'available', 'CAP-MILL', 'qualified'),
    ('MACH-MILL-03', 'SITE-SZ', 'WC-SZ-CNC', ('五轴加工中心 3 号', '5-axis Mill 3'), 'CNC_MILL', 'under_repair', 'CAP-MILL', 'qualified'),
    ('MACH-MILL-04', 'SITE-SZ', 'WC-SZ-CNC', ('五轴加工中心 4 号', '5-axis Mill 4'), 'CNC_MILL', 'available', 'CAP-MILL', 'suspended'),
    ('MACH-TURN-01', 'SITE-SZ', 'WC-SZ-TURN', ('数控车床 1 号', 'CNC Lathe 1'), 'CNC_LATHE', 'available', 'CAP-TURN', 'qualified'),
    ('MACH-TURN-02', 'SITE-SZ', 'WC-SZ-TURN', ('数控车床 2 号', 'CNC Lathe 2'), 'CNC_LATHE', 'available', 'CAP-TURN', 'qualified'),
    ('MACH-CMM-01', 'SITE-SZ', 'WC-SZ-QC', ('三坐标测量机 1 号', 'CMM 1'), 'CMM', 'available', 'CAP-CMM', 'qualified'),
    ('MACH-CMM-02', 'SITE-SZ', 'WC-SZ-QC', ('三坐标测量机 2 号', 'CMM 2'), 'CMM', 'available', 'CAP-CMM', 'qualified'),
    ('MACH-PT-01', 'SITE-SU', 'WC-SU-TEST', ('压力测试台 1 号', 'Pressure Rig 1'), 'PRESSURE_RIG', 'available', 'CAP-PTEST', 'qualified'),
    ('MACH-PT-02', 'SITE-SU', 'WC-SU-TEST', ('压力测试台 2 号', 'Pressure Rig 2'), 'PRESSURE_RIG', 'available', 'CAP-PTEST', 'qualified'),
    ('MACH-LSR-01', 'SITE-SU', 'WC-SU-MARK', ('激光打标机 1 号', 'Laser Marker 1'), 'LASER', 'available', 'CAP-MARK', 'qualified'),
]
# id, (zh, en) name, home site, employment, {capability: (status, valid_to)}
OPERATORS = [
    ('OPR-01', ('陈立', 'Chen Li'), 'SITE-SZ', 'employed', {'CAP-MILL': ('qualified', '2027-09-30'), 'CAP-CMM': ('qualified', '2027-09-30')}),
    ('OPR-02', ('王敏', 'Wang Min'), 'SITE-SZ', 'employed', {'CAP-MILL': ('qualified', '2027-06-30')}),
    ('OPR-03', ('刘洋', 'Liu Yang'), 'SITE-SZ', 'employed', {'CAP-TURN': ('qualified', '2027-08-31')}),
    ('OPR-04', ('赵静', 'Zhao Jing'), 'SITE-SZ', 'employed', {'CAP-TURN': ('qualified', '2027-05-31'), 'CAP-MILL': ('qualified', '2027-05-31')}),
    ('OPR-05', ('孙浩', 'Sun Hao'), 'SITE-SZ', 'employed', {'CAP-MILL': ('qualified', '2026-12-31')}),
    ('OPR-06', ('周婷', 'Zhou Ting'), 'SITE-SZ', 'employed', {'CAP-CMM': ('qualified', '2027-10-31')}),
    ('OPR-07', ('吴磊', 'Wu Lei'), 'SITE-SZ', 'employed', {'CAP-CMM': ('training', '2027-12-31')}),
    ('OPR-08', ('郑凯', 'Zheng Kai'), 'SITE-SU', 'employed', {'CAP-PTEST': ('qualified', '2027-07-31')}),
    ('OPR-09', ('冯雪', 'Feng Xue'), 'SITE-SU', 'employed', {'CAP-PTEST': ('qualified', '2027-04-30'), 'CAP-MARK': ('qualified', '2027-04-30')}),
    ('OPR-10', ('何军', 'He Jun'), 'SITE-SU', 'left', {'CAP-MARK': ('qualified', '2027-03-31')}),
    ('OPR-11', ('林峰', 'Lin Feng'), 'SITE-SZ', 'employed', {'CAP-MILL': ('qualified', '2027-11-30'), 'CAP-TURN': ('qualified', '2027-11-30')}),
    ('OPR-12', ('黄蕾', 'Huang Lei'), 'SITE-SU', 'employed', {'CAP-PTEST': ('qualified', '2027-08-31')}),
]
CUSTOMERS = [
    ('CUST-01', ('华东流体设备有限公司', 'East China Fluid Equipment Co.'), 'pump_oem'),
    ('CUST-02', ('南方泵业制造有限公司', 'Southern Pump Manufacturing Co.'), 'pump_oem'),
    ('CUST-03', ('海川阀门集团', 'Haichuan Valve Group'), 'valve_oem'),
    ('CUST-04', ('江北过程装备有限公司', 'Jiangbei Process Equipment Co.'), 'project'),
    ('CUST-05', ('东海能源设备有限公司', 'Donghai Energy Equipment Co.'), 'project'),
    ('CUST-06', ('华中智能流体有限公司', 'Central China Smart Fluids Co.'), 'pump_oem'),
    ('CUST-07', ('西部化工机械有限公司', 'Western Chemical Machinery Co.'), 'project'),
    ('CUST-08', ('北方工业品分销有限公司', 'Northern Industrial Distribution Co.'), 'distributor'),
    ('CUST-09', ('粤港水务工程有限公司', 'Yuegang Water Engineering Co.'), 'project'),
    ('CUST-10', ('长江阀业有限公司', 'Changjiang Valve Co.'), 'valve_oem'),
]
SUPPLIERS = [
    ('SUP-01', ('华南铸造有限公司', 'South China Foundry Co.'), 'casting'),
    ('SUP-02', ('宝联特钢有限公司', 'Baolian Special Steel Co.'), 'bar'),
    ('SUP-03', ('华东精铝有限公司', 'East China Fine Aluminium Co.'), 'aluminium'),
    ('SUP-04', ('恒密密封件有限公司', 'Hengmi Seals Co.'), 'seal'),
    ('SUP-05', ('申达紧固件有限公司', 'Shenda Fasteners Co.'), 'fastener'),
    ('SUP-06', ('江南精铸有限公司', 'Jiangnan Precision Casting Co.'), 'casting'),
]
# product id, code, (zh, en) name, type, unit, supplier (purchased items)
PRODUCTS = [
    ('FG-PH100', 'PH100', ('离心泵壳体 PH100（标准型）', 'Pump housing PH100 (standard)'), 'finished_good', 'EA', None),
    ('FG-PH200', 'PH200', ('离心泵壳体 PH200（高压型）', 'Pump housing PH200 (high pressure)'), 'finished_good', 'EA', None),
    ('FG-VB050', 'VB050', ('球阀阀体 VB050（DN50）', 'Ball valve body VB050 (DN50)'), 'finished_good', 'EA', None),
    ('FG-VB080', 'VB080', ('球阀阀体 VB080（DN80）', 'Ball valve body VB080 (DN80)'), 'finished_good', 'EA', None),
    ('FG-IMP300', 'IMP300', ('青铜叶轮 IMP300', 'Bronze impeller IMP300'), 'finished_good', 'EA', None),
    ('FG-FL150', 'FL150', ('铝合金法兰 FL150', 'Aluminium flange FL150'), 'finished_good', 'EA', None),
    ('RM-CI250', 'CI250', ('灰铸铁泵壳毛坯 HT250', 'Grey iron housing casting HT250'), 'raw_material', 'EA', 'SUP-01'),
    ('RM-SS316', 'SS316', ('316L 不锈钢棒料', '316L stainless bar'), 'raw_material', 'KG', 'SUP-02'),
    ('RM-AL6061', 'AL6061', ('6061-T6 铝合金方坯', '6061-T6 aluminium billet'), 'raw_material', 'EA', 'SUP-03'),
    ('RM-BRZ', 'BRZ', ('锡青铜叶轮铸件', 'Tin bronze impeller casting'), 'raw_material', 'EA', 'SUP-06'),
    ('PC-SEAL', 'SEAL', ('氟橡胶密封圈套件', 'FKM seal kit'), 'purchased_part', 'EA', 'SUP-04'),
    ('PC-BOLT', 'BOLT', ('不锈钢紧固件包', 'Stainless fastener pack'), 'purchased_part', 'EA', 'SUP-05'),
]
PRODUCT = {p[0]: p for p in PRODUCTS}
# BOM versions: id, product, version, status, effective_from, components [(product, qty per, scrap)]
BOM_VERSIONS = [
    ('BOMV-PH100-A', 'FG-PH100', 'A', 'frozen', '2026-06-01', [('RM-CI250', 1, 0.02), ('PC-SEAL', 1, 0)]),
    ('BOMV-PH200-A', 'FG-PH200', 'A', 'obsolete', '2026-03-01', [('RM-CI250', 1, 0.03), ('PC-SEAL', 1, 0)]),
    ('BOMV-PH200-B', 'FG-PH200', 'B', 'frozen', '2026-09-01', [('RM-CI250', 1, 0.03), ('PC-SEAL', 2, 0), ('PC-BOLT', 1, 0)]),
    ('BOMV-VB050-A', 'FG-VB050', 'A', 'frozen', '2026-05-01', [('RM-SS316', 1.6, 0.05), ('PC-SEAL', 2, 0), ('PC-BOLT', 1, 0)]),
    ('BOMV-VB080-A', 'FG-VB080', 'A', 'frozen', '2026-05-01', [('RM-SS316', 2.8, 0.05), ('PC-SEAL', 2, 0), ('PC-BOLT', 1, 0)]),
    ('BOMV-IMP300-A', 'FG-IMP300', 'A', 'frozen', '2026-04-01', [('RM-BRZ', 1, 0.04)]),
    ('BOMV-FL150-A', 'FG-FL150', 'A', 'frozen', '2026-04-01', [('RM-AL6061', 1, 0.02)]),
    ('BOMV-FL150-B', 'FG-FL150', 'B', 'draft', '2027-03-01', [('RM-AL6061', 1, 0.02), ('PC-BOLT', 1, 0)]),
]
BOMV = {b[0]: b for b in BOM_VERSIONS}
CURRENT_BOM = {'FG-PH100': 'BOMV-PH100-A', 'FG-PH200': 'BOMV-PH200-B', 'FG-VB050': 'BOMV-VB050-A', 'FG-VB080': 'BOMV-VB080-A',
               'FG-IMP300': 'BOMV-IMP300-A', 'FG-FL150': 'BOMV-FL150-A'}
OP = {  # op code -> work centre, capability, (zh, en) name, setup
    'MILL': ('WC-SZ-CNC', 'CAP-MILL', ('五轴精铣', '5-axis finish milling')),
    'TURN': ('WC-SZ-TURN', 'CAP-TURN', ('数控车削', 'CNC turning')),
    'CMM': ('WC-SZ-QC', 'CAP-CMM', ('三坐标尺寸检测', 'CMM dimensional inspection')),
    'PTEST': ('WC-SU-TEST', 'CAP-PTEST', ('壳体压力测试', 'Pressure test')),
    'MARK': ('WC-SU-MARK', 'CAP-MARK', ('激光打标', 'Laser marking')),
}
ROUTING = {'FG-PH100': ['MILL', 'CMM'], 'FG-PH200': ['MILL', 'CMM', 'PTEST'], 'FG-VB050': ['TURN', 'MILL', 'PTEST'],
           'FG-VB080': ['TURN', 'MILL', 'PTEST'], 'FG-IMP300': ['TURN', 'CMM'], 'FG-FL150': ['MILL', 'MARK']}
SETUP = {'FG-PH100': 'cast_iron', 'FG-PH200': 'cast_iron', 'FG-VB050': 'stainless', 'FG-VB080': 'stainless', 'FG-IMP300': 'bronze', 'FG-FL150': 'aluminium_setup'}
FG_SITE = {'FG-PH100': 'SITE-SZ', 'FG-PH200': 'SITE-SU', 'FG-VB050': 'SITE-SU', 'FG-VB080': 'SITE-SU', 'FG-IMP300': 'SITE-SZ', 'FG-FL150': 'SITE-SU'}
# quality specs: id, product, characteristic (zh, en), target, lower, upper, effective, status
SPECS = [
    ('QS-PH100-BORE-A', 'FG-PH100', ('关键孔径', 'Critical bore diameter'), 50.00, 49.94, 50.06, '2026-06-01', 'superseded'),
    ('QS-PH100-BORE-B', 'FG-PH100', ('关键孔径', 'Critical bore diameter'), 50.00, 49.95, 50.05, '2027-01-01', 'active'),
    ('QS-PH100-FLAT', 'FG-PH100', ('安装面平面度', 'Mounting face flatness'), 0.00, 0.00, 0.03, '2026-06-01', 'active'),
    ('QS-PH200-BORE', 'FG-PH200', ('关键孔径', 'Critical bore diameter'), 65.00, 64.96, 65.04, '2026-09-01', 'active'),
    ('QS-PH200-PRES', 'FG-PH200', ('保压泄漏量', 'Pressure-hold leakage'), 0.00, 0.00, 0.50, '2026-09-01', 'active'),
    ('QS-VB050-BORE', 'FG-VB050', ('通径', 'Flow bore diameter'), 50.00, 49.90, 50.10, '2026-05-01', 'active'),
    ('QS-VB050-RA', 'FG-VB050', ('阀座密封面粗糙度', 'Seat surface roughness'), 0.40, 0.00, 0.80, '2026-05-01', 'active'),
    ('QS-VB080-BORE', 'FG-VB080', ('通径', 'Flow bore diameter'), 80.00, 79.90, 80.10, '2026-05-01', 'active'),
    ('QS-VB080-RA', 'FG-VB080', ('阀座密封面粗糙度', 'Seat surface roughness'), 0.40, 0.00, 0.80, '2026-05-01', 'active'),
    ('QS-IMP300-OD', 'FG-IMP300', ('外径', 'Outer diameter'), 300.00, 299.90, 300.10, '2026-04-01', 'active'),
    ('QS-IMP300-BAL', 'FG-IMP300', ('动平衡残余量', 'Residual unbalance'), 0.00, 0.00, 25.00, '2026-04-01', 'active'),
    ('QS-FL150-PCD', 'FG-FL150', ('螺栓孔中心距', 'Bolt circle diameter'), 150.00, 149.90, 150.10, '2026-04-01', 'active'),
    ('QS-FL150-THK', 'FG-FL150', ('厚度', 'Thickness'), 20.00, 19.80, 20.20, '2026-04-01', 'active'),
]
SPEC_INDEX = defaultdict(list)
for _s in SPECS:
    SPEC_INDEX[_s[1]].append(_s)
NOMINAL = {  # in-spec measured value per spec
    'QS-PH100-BORE-A': 50.01, 'QS-PH100-BORE-B': 50.01, 'QS-PH100-FLAT': 0.02, 'QS-PH200-BORE': 65.01, 'QS-PH200-PRES': 0.20,
    'QS-VB050-BORE': 50.02, 'QS-VB050-RA': 0.50, 'QS-VB080-BORE': 80.03, 'QS-VB080-RA': 0.60, 'QS-IMP300-OD': 300.02,
    'QS-IMP300-BAL': 12.00, 'QS-FL150-PCD': 150.03, 'QS-FL150-THK': 20.05,
}

OUT_OF_SPEC = {'QS-PH100-BORE-A': 50.09, 'QS-IMP300-BAL': 31.5, 'QS-PH100-FLAT': 0.05}
RECORDED_PASS_VALUE = {'QS-PH100-FLAT': 0.04}

# --- orders: (wo, product, qty, due, customer); sales orders group lines by order number ------------
ORDERS = [
    # November 2026
    ('SO-2610-01', 'CUST-01', '2026-10-12', [('WO-2611-01', 'FG-PH100', 120, '2026-11-06'), ('WO-2611-02', 'FG-IMP300', 80, '2026-11-06')]),
    ('SO-2610-02', 'CUST-03', '2026-10-14', [('WO-2611-03', 'FG-VB050', 200, '2026-11-10')]),
    ('SO-2610-03', 'CUST-02', '2026-10-15', [('WO-2611-04', 'FG-PH200', 60, '2026-11-13')]),
    ('SO-2610-04', 'CUST-08', '2026-10-18', [('WO-2611-05', 'FG-FL150', 300, '2026-11-17'), ('WO-2611-06', 'FG-PH100', 90, '2026-11-17')]),
    ('SO-2610-05', 'CUST-04', '2026-10-21', [('WO-2611-07', 'FG-VB080', 70, '2026-11-20')]),
    ('SO-2610-06', 'CUST-06', '2026-10-25', [('WO-2611-08', 'FG-PH100', 150, '2026-11-24')]),
    ('SO-2610-07', 'CUST-10', '2026-10-28', [('WO-2611-09', 'FG-VB050', 160, '2026-11-27'), ('WO-2611-10', 'FG-VB080', 50, '2026-11-27')]),
    # December 2026
    ('SO-2611-01', 'CUST-05', '2026-11-02', [('WO-2612-01', 'FG-PH200', 80, '2026-12-03')]),
    ('SO-2611-02', 'CUST-01', '2026-11-05', [('WO-2612-02', 'FG-PH100', 140, '2026-12-04'), ('WO-2612-03', 'FG-IMP300', 100, '2026-12-04')]),
    ('SO-2611-03', 'CUST-07', '2026-11-08', [('WO-2612-04', 'FG-FL150', 240, '2026-12-08')]),
    ('SO-2611-04', 'CUST-03', '2026-11-10', [('WO-2612-05', 'FG-VB050', 180, '2026-12-10')]),
    ('SO-2611-05', 'CUST-09', '2026-11-12', [('WO-2612-06', 'FG-VB080', 90, '2026-12-14')]),
    ('SO-2611-06', 'CUST-02', '2026-11-16', [('WO-2612-07', 'FG-PH100', 110, '2026-12-16'), ('WO-2612-08', 'FG-PH200', 50, '2026-12-16')]),
    ('SO-2611-07', 'CUST-10', '2026-11-20', [('WO-2612-09', 'FG-VB080', 60, '2026-12-18')]),
    ('SO-2611-08', 'CUST-06', '2026-11-23', [('WO-2612-10', 'FG-PH100', 130, '2026-12-22')]),
    ('SO-2611-09', 'CUST-08', '2026-11-25', [('WO-2612-11', 'FG-IMP300', 120, '2026-12-23')]),
    # January 2027
    ('SO-2612-01', 'CUST-04', '2026-12-01', [('WO-2701-01', 'FG-VB050', 150, '2027-01-08')]),
    ('SO-2612-02', 'CUST-01', '2026-12-03', [('WO-2701-02', 'FG-PH100', 160, '2027-01-12')]),
    ('SO-2612-03', 'CUST-05', '2026-12-06', [('WO-2701-03', 'FG-IMP300', 90, '2027-01-14'), ('WO-2701-04', 'FG-VB080', 80, '2027-01-14')]),
    ('SO-2612-04', 'CUST-02', '2026-12-09', [('WO-2701-05', 'FG-PH200', 70, '2027-01-15')]),
    ('SO-2612-05', 'CUST-07', '2026-12-12', [('WO-2701-06', 'FG-FL150', 260, '2027-01-19')]),
    ('SO-2612-06', 'CUST-09', '2026-12-15', [('WO-2701-07', 'FG-PH100', 100, '2027-01-21')]),
    ('SO-2612-07', 'CUST-03', '2026-12-18', [('WO-2701-08', 'FG-VB050', 220, '2027-01-22')]),
    ('SO-2612-08', 'CUST-06', '2026-12-20', [('WO-2701-09', 'FG-PH100', 120, '2027-01-26'), ('WO-2701-10', 'FG-IMP300', 110, '2027-01-26')]),
    ('SO-2612-09', 'CUST-10', '2026-12-22', [('WO-2701-11', 'FG-VB080', 40, '2027-01-28')]),
    # February 2027
    ('SO-2701-01', 'CUST-01', '2027-01-05', [('WO-2702-01', 'FG-PH100', 150, '2027-02-03')]),
    ('SO-2701-02', 'CUST-08', '2027-01-07', [('WO-2702-02', 'FG-FL150', 280, '2027-02-05')]),
    ('SO-2701-03', 'CUST-03', '2027-01-09', [('WO-2702-03', 'FG-VB050', 190, '2027-02-09')]),
    ('SO-2701-04', 'CUST-05', '2027-01-12', [('WO-2702-04', 'FG-PH200', 90, '2027-02-11')]),
    ('SO-2701-05', 'CUST-04', '2027-01-15', [('WO-2702-05', 'FG-VB080', 100, '2027-02-26')]),
    ('SO-2701-06', 'CUST-02', '2027-01-18', [('WO-2702-06', 'FG-PH100', 130, '2027-02-17')]),
    ('SO-2701-07', 'CUST-06', '2027-01-20', [('WO-2702-07', 'FG-IMP300', 140, '2027-02-24')]),
    ('SO-2701-08', 'CUST-09', '2027-01-22', [('WO-2702-08', 'FG-VB050', 120, '2027-02-19')]),
    ('SO-2701-09', 'CUST-07', '2027-01-25', [('WO-2702-09', 'FG-FL150', 200, '2027-02-23'), ('WO-2702-10', 'FG-PH100', 80, '2027-02-23')]),
    ('SO-2701-10', 'CUST-10', '2027-01-27', [('WO-2702-11', 'FG-VB080', 60, '2027-02-25')]),
    # March 2027
    ('SO-2702-01', 'CUST-01', '2027-02-02', [('WO-2703-01', 'FG-PH100', 170, '2027-03-05')]),
    ('SO-2702-02', 'CUST-07', '2027-02-04', [('WO-2703-02', 'FG-FL150', 220, '2027-03-09')]),
    ('SO-2702-03', 'CUST-03', '2027-02-06', [('WO-2703-03', 'FG-VB050', 210, '2027-03-10'), ('WO-2703-04', 'FG-VB080', 90, '2027-03-10')]),
    ('SO-2702-04', 'CUST-02', '2027-02-09', [('WO-2703-05', 'FG-PH200', 80, '2027-03-12')]),
    ('SO-2702-05', 'CUST-05', '2027-02-11', [('WO-2703-06', 'FG-PH100', 140, '2027-03-08')]),
    ('SO-2702-06', 'CUST-06', '2027-02-13', [('WO-2703-07', 'FG-IMP300', 100, '2027-03-17')]),
    ('SO-2702-07', 'CUST-04', '2027-02-16', [('WO-2703-08', 'FG-VB080', 110, '2027-03-19')]),
    ('SO-2702-08', 'CUST-08', '2027-02-18', [('WO-2703-09', 'FG-PH100', 120, '2027-03-23')]),
    ('SO-2702-09', 'CUST-09', '2027-02-20', [('WO-2703-10', 'FG-VB050', 130, '2027-03-26')]),
    ('SO-2702-10', 'CUST-10', '2027-02-22', [('WO-2703-11', 'FG-PH200', 60, '2027-03-30')]),
]
# A replacement work order re-makes the rejected WO-2611-08 for the same sales order line.
REPLACEMENT = ('WO-2612-R1', 'WO-2611-08', '2026-12-11')

# --- deliberate exceptions ---------------------------------------------------------------------
EXCEPTIONS = {
    'late_shipment': {'WO-2611-03': 4, 'WO-2701-06': 6, 'WO-2612-R1': 0},          # days after the requested date
    'scrap': {('WO-2611-06', 'MILL'): 4, ('WO-2701-03', 'TURN'): 2, ('WO-2702-11', 'PTEST'): 3, ('WO-2612-06', 'TURN'): 5},
    'split_shipment': {'WO-2612-05': (110, 9)},                                    # first quantity, days until the rest
    'quality_reject': {'WO-2611-08': 'QS-PH100-BORE-A', 'WO-2701-10': 'QS-IMP300-BAL', 'WO-2702-10': 'QS-PH100-FLAT'},
    'recorded_pass_out_of_spec': {'WO-2612-10': 'QS-PH100-FLAT'},                  # shipped despite an out-of-limit value
    'suspended_machine': {('WO-2612-04', 'MILL'), ('WO-2701-07', 'MILL')},          # MACH-MILL-04
    'expired_operator': {('WO-2701-02', 'MILL'), ('WO-2701-05', 'MILL')},           # OPR-05, valid to 2026-12-31
    'training_operator': {('WO-2702-06', 'CMM')},                                   # OPR-07 still in training
    'maintenance_clash': {('WO-2701-04', 'TURN')},                                  # MACH-TURN-01 serviced that day
    'wrong_work_centre_shift': {('WO-2701-09', 'MILL')},                            # assigned to the turning cell that week
    'no_shift': {('WO-2702-08', 'MILL')},
    'issue_from_unreleased_receipt': {'WO-2612-09'},                                # stainless issued from a receipt still in inspection
    'short_issue': {'WO-2702-03': ('RM-SS316', 200.0)},                             # receipt short, only part issued
    'in_progress': {'WO-2702-05': 1, 'WO-2702-07': 'inspection'},                   # ops completed by the business date
    'fg_not_shipped': {'WO-2702-11'},
    'draft_bom': {'WO-2703-02': 'BOMV-FL150-B'},
    'late_po': {'WO-2703-04'},                                                      # stainless PO overdue, nothing received
    'rejected_receipt': {'WO-2703-06'},                                             # housing castings rejected at receipt
}


# --- generation ----------------------------------------------------------------------------------
def required_qty(qty, per, scrap):
    return math.ceil(round(qty * per * (1 + scrap), 6))


def build():
    out = defaultdict(list)  # table -> list of dicts with codes (language applied later)
    wos = []
    for so_id, cust, order_date, lines in ORDERS:
        req = max(D(w[3]) for w in lines)
        out['sales_orders'].append(dict(sales_order_id=so_id, customer_id=cust, order_date=order_date, requested_delivery_date=req.isoformat(), status=None))
        for i, (wo, prod, qty, due) in enumerate(lines, 1):
            sol = f'{so_id.replace("SO", "SOL")}-{i}'
            out['sales_order_lines'].append(dict(sales_order_line_id=sol, sales_order_id=so_id, product_id=prod, ordered_quantity=qty, unit=PRODUCT[prod][4]))
            wos.append(dict(wo=wo, sol=sol, prod=prod, qty=qty, due=D(due), requested=req))
    original = next(w for w in wos if w['wo'] == REPLACEMENT[1])
    wos.append(dict(wo=REPLACEMENT[0], sol=original['sol'], prod=original['prod'], qty=original['qty'], due=D(REPLACEMENT[2]), requested=original['requested']))
    wos.sort(key=lambda w: (w['due'], w['wo']))
    X = EXCEPTIONS

    # masters
    for sid, name in SITES:
        out['manufacturing_sites'].append(dict(site_id=sid, site_name=name, site_type='plant', country_code='CN'))
    for wc, sid, name, typ in WORK_CENTERS:
        out['work_centers'].append(dict(work_center_id=wc, site_id=sid, work_center_name=name, work_center_type=typ))
    for cid, name, cat in CAPS:
        out['equipment_capabilities'].append(dict(capability_id=cid, capability_name=name, capability_category=cat))
    for i, m in enumerate(MACHINES, 1):
        out['production_machines'].append(dict(machine_id=m[0], site_id=m[1], work_center_id=m[2], machine_name=m[3], machine_type=m[4], status=m[5]))
        out['machine_capability_assignments'].append(dict(machine_capability_assignment_id=f'MCA-{i:02d}', machine_id=m[0], capability_id=m[6], qualification_status=m[7]))
    q = 0
    for o in OPERATORS:
        out['operators'].append(dict(operator_id=o[0], operator_name=o[1], home_site_id=o[2], employment_status=o[3]))
        for cap, (status, valid_to) in o[4].items():
            q += 1
            out['operator_qualifications'].append(dict(operator_qualification_id=f'OQ-{q:02d}', operator_id=o[0], capability_id=cap, qualification_status=status, valid_to=valid_to))
    for c in CUSTOMERS:
        out['customers'].append(dict(customer_id=c[0], customer_name=c[1], customer_segment=c[2]))
    for s in SUPPLIERS:
        out['suppliers'].append(dict(supplier_id=s[0], supplier_name=s[1], supplier_category=s[2]))
    for p in PRODUCTS:
        out['products'].append(dict(product_id=p[0], product_code=p[1], product_name=p[2], product_type=p[3], base_unit=p[4]))
    comp_id = {}
    for b in BOM_VERSIONS:
        bom = b[0].replace('BOMV', 'BOM')
        out['product_bom_versions'].append(dict(bom_version_id=b[0], product_id=b[1], version_code=b[2], status=b[3], effective_from=b[4]))
        out['bill_of_materials'].append(dict(bom_id=bom, bom_version_id=b[0], bom_name=(f'{PRODUCT[b[1]][1]} 物料清单 {b[2]} 版', f'{PRODUCT[b[1]][1]} bill of materials rev {b[2]}'), quantity_basis=1))
        for k, (cp, per, scrap) in enumerate(b[5], 1):
            cid = f'{bom.replace("BOM", "BOMC")}-{k}'
            comp_id[(b[0], cp)] = cid
            out['bom_components'].append(dict(bom_component_id=cid, bom_version_id=b[0], bom_id=bom, component_product_id=cp, quantity_per=per, unit=PRODUCT[cp][4], scrap_factor=scrap))
    rop_id = {}
    for prod, ops in ROUTING.items():
        rid = f'ROUTE-{PRODUCT[prod][1]}'
        out['routings'].append(dict(routing_id=rid, product_id=prod, routing_name=(f'{PRODUCT[prod][1]} 加工路线', f'{PRODUCT[prod][1]} routing'), status='released'))
        for k, op in enumerate(ops, 1):
            r = f'ROP-{PRODUCT[prod][1]}-{k * 10}'
            rop_id[(prod, op)] = r
            out['routing_operations'].append(dict(routing_operation_id=r, routing_id=rid, operation_code=f'{k * 10:03d}', operation_name=OP[op][2], sequence_number=k * 10, work_center_id=OP[op][0], required_capability_id=OP[op][1]))
    for s in SPECS:
        out['quality_specifications'].append(dict(quality_specification_id=s[0], product_id=s[1], characteristic_name=s[2], target_value=s[3], lower_limit=s[4], upper_limit=s[5], effective_date=s[6], status=s[7]))
    out['inventory_locations'] += [
        dict(inventory_location_id='LOC-SZ-RAW', site_id='SITE-SZ', location_name=('深圳原料库', 'Shenzhen raw material store'), location_type='raw_location'),
        dict(inventory_location_id='LOC-SZ-QI', site_id='SITE-SZ', location_name=('深圳来料待检区', 'Shenzhen incoming inspection hold'), location_type='qi_location'),
        dict(inventory_location_id='LOC-SZ-FG', site_id='SITE-SZ', location_name=('深圳成品库', 'Shenzhen finished goods store'), location_type='fg_location'),
        dict(inventory_location_id='LOC-SU-FG', site_id='SITE-SU', location_name=('苏州成品库', 'Suzhou finished goods store'), location_type='fg_location'),
    ]

    # machines and operators per capability, rotated across work orders
    pool_m = {'CAP-MILL': ['MACH-MILL-01', 'MACH-MILL-02', 'MACH-MILL-03'], 'CAP-TURN': ['MACH-TURN-01', 'MACH-TURN-02'],
              'CAP-CMM': ['MACH-CMM-01', 'MACH-CMM-02'], 'CAP-PTEST': ['MACH-PT-01', 'MACH-PT-02'], 'CAP-MARK': ['MACH-LSR-01']}
    pool_o = {'CAP-MILL': ['OPR-01', 'OPR-02', 'OPR-11', 'OPR-04'], 'CAP-TURN': ['OPR-03', 'OPR-04', 'OPR-11'], 'CAP-CMM': ['OPR-06', 'OPR-01'],
              'CAP-PTEST': ['OPR-08', 'OPR-12', 'OPR-09'], 'CAP-MARK': ['OPR-09']}
    turn = defaultdict(int)

    def pick(pool, cap):
        v = pool[cap][turn[(id(pool), cap)] % len(pool[cap])]
        turn[(id(pool), cap)] += 1
        return v

    # purchasing: one purchase per raw material per month, received ahead of the month's issues
    issue_plan = []  # (wo, requirement id, product, qty required, issue date)
    exe_seq = defaultdict(int)
    shift_rows = {}
    assignments = {}
    mwo = []
    month_name = {}
    for w in wos:
        wo, prod, qty, due = w['wo'], w['prod'], w['qty'], w['due']
        bomv = X['draft_bom'].get(wo, CURRENT_BOM[prod])
        rid = f'ROUTE-{PRODUCT[prod][1]}'
        blocked = wo in X['draft_bom'] or wo in X['late_po'] or wo in X['rejected_receipt'] or wo in X['short_issue']
        w.update(bomv=bomv, blocked=blocked)
        issue_date = day(due, -12)
        w['issue_date'] = issue_date
        for cp, per, scrap in BOMV[bomv][5]:
            mr = f'MR-{wo[3:]}-{PRODUCT[cp][1]}'
            need = required_qty(qty, per, scrap)
            issue_plan.append(dict(wo=wo, mr=mr, prod=cp, need=need, date=issue_date, comp=comp_id[(bomv, cp)], unit=PRODUCT[cp][4]))
        ops = ROUTING[prod]
        w['ops'] = []
        good = qty
        for k, op in enumerate(ops, 1):
            wc, cap, opname = OP[op]
            op_id = f'OP-{wo[3:]}-{k * 10}'
            step_id = f'STEP-{wo[3:]}-{k * 10}'
            start = day(due, -10 + 2 * (k - 1))
            end = day(start, 1)
            scrap_q = X['scrap'].get((wo, op), 0)
            good -= scrap_q
            machine = pick(pool_m, cap)
            operator = pick(pool_o, cap)
            if (wo, op) in X['suspended_machine']:
                machine = 'MACH-MILL-04'
            if (wo, op) in X['expired_operator']:
                operator = 'OPR-05'
            if (wo, op) in X['training_operator']:
                operator = 'OPR-07'
            if (wo, op) in X['maintenance_clash']:
                machine = 'MACH-TURN-01'
            if machine == 'MACH-MILL-03' and start >= D('2027-02-20'):
                machine = 'MACH-MILL-01'
            status = 'completed' if end <= BUSINESS_DATE else ('in_progress' if start <= BUSINESS_DATE else 'not_started')
            if blocked:
                status = 'not_started'
            if wo in X['in_progress'] and isinstance(X['in_progress'][wo], int):
                status = 'completed' if k <= X['in_progress'][wo] else ('in_progress' if k == X['in_progress'][wo] + 1 else 'not_started')
            w['ops'].append(dict(op=op, op_id=op_id, step=step_id, wc=wc, cap=cap, name=opname, k=k, start=start, end=end, machine=machine,
                                 operator=operator, good=good if status == 'completed' else 0, scrap=scrap_q if status == 'completed' else 0, status=status))
            out['manufacturing_operations'].append(dict(operation_id=op_id, production_order_id=wo, routing_operation_id=rop_id[(prod, op)], work_center_id=wc,
                                                        operation_name=opname, sequence_number=k * 10, status=status))
            out['process_steps'].append(dict(process_step_id=step_id, operation_id=op_id, process_step_name=opname, sequence_number=10,
                                             required_capability_id=cap, setup_class=('inspect_setup' if op in ('CMM', 'PTEST') else ('mark_setup' if op == 'MARK' else SETUP[prod]))))
            if status == 'not_started':
                continue
            exe_seq[wo] += 1
            out['production_execution_records'].append(dict(
                execution_record_id=f'EXE-{wo[3:]}-{k * 10}', process_step_id=step_id, machine_id=machine, operator_id=operator,
                started_date=start.isoformat(), completed_date=end.isoformat() if status == 'completed' else '',
                good_quantity=good if status == 'completed' else 0, scrap_quantity=scrap_q if status == 'completed' else 0, status=status))
            site = next(s for c, s, *_ in WORK_CENTERS if c == wc)
            week = start - dt.timedelta(days=start.weekday())
            shift = f'SHIFT-{site[5:]}-{week:%Y%m%d}'
            shift_rows[shift] = dict(shift_id=shift, site_id=site, shift_name=(f'{week:%m-%d} 当周日班', f'Day shift week of {week:%b %d}'),
                                     starts_date=week.isoformat(), ends_date=day(week, 6).isoformat())
            if (wo, op) in X['no_shift']:
                continue
            assigned_wc = 'WC-SZ-TURN' if (wo, op) in X['wrong_work_centre_shift'] else wc
            assignments[(operator, shift, assigned_wc)] = True
            if (wo, op) in X['maintenance_clash']:
                mwo.append(('MACH-TURN-01', start, 'completed'))
        w['good'] = good
        w['complete'] = all(o['status'] == 'completed' for o in w['ops'])
        w['started'] = any(o['status'] != 'not_started' for o in w['ops'])
        status = 'completed' if w['complete'] else ('blocked' if blocked else ('in_production' if w['started'] else 'released'))
        out['production_orders'].append(dict(production_order_id=wo, sales_order_line_id=w['sol'], product_id=prod, bom_version_id=bomv, routing_id=rid,
                                             requested_quantity=qty, unit=PRODUCT[prod][4], due_date=due.isoformat(), status=status))
        w['status'] = status

    # purchase orders and receipts: per material and issue month; exception requirements get their own order
    def tag(it):
        if it['wo'] in X['late_po'] and it['prod'] == 'RM-SS316':
            return 'late'
        if it['wo'] in X['rejected_receipt'] and it['prod'] == 'RM-CI250':
            return 'rejected'
        if it['wo'] in X['short_issue'] and X['short_issue'][it['wo']][0] == it['prod']:
            return 'short'
        if it['wo'] in X['issue_from_unreleased_receipt'] and it['prod'] == 'RM-SS316':
            return 'hold'
        return ''
    by_order = defaultdict(list)
    for it in issue_plan:
        if it['wo'] in X['draft_bom']:
            continue
        it['tag'] = tag(it)
        by_order[(it['prod'], it['date'].strftime('%Y-%m'), it['tag'])].append(it)
    receipts = []
    for (prod, month, tg), items in sorted(by_order.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        po = f'PO-{month[2:4]}{month[5:]}-{PRODUCT[prod][1]}' + ('-B' if tg else '')
        first = min(i['date'] for i in items)
        expected = day(first, -5)
        need = sum(i['need'] for i in items)
        ordered = need if tg else (math.ceil(need * 1.05) if PRODUCT[prod][4] == 'EA' else int(round(need * 1.05 + 4.9, -1)))
        out['purchase_orders'].append(dict(purchase_order_id=po, supplier_id=PRODUCT[prod][5], order_date=day(expected, -21).isoformat(), expected_receipt_date=expected.isoformat(), status=None))
        pol = po.replace('PO', 'POL') + '-1'
        out['purchase_order_lines'].append(dict(purchase_order_line_id=pol, purchase_order_id=po, product_id=prod, ordered_quantity=ordered, unit=PRODUCT[prod][4]))
        for i in items:
            i['pol'] = pol
        gr = pol.replace('POL', 'GR')
        if tg == 'late':
            continue
        if tg == 'rejected':
            receipts.append(dict(id=gr, pol=pol, prod=prod, loc='LOC-SZ-QI', qty=ordered, date=day(expected, 1), status='rejected'))
        elif tg == 'short':
            receipts.append(dict(id=gr, pol=pol, prod=prod, loc='LOC-SZ-RAW', qty=sum(X['short_issue'][i['wo']][1] for i in items), date=day(expected, 3), status='accepted'))
        elif tg == 'hold':
            receipts.append(dict(id=gr, pol=pol, prod=prod, loc='LOC-SZ-QI', qty=ordered, date=day(expected, 2), status='pending_inspection'))
        else:
            late = 2 if prod == 'RM-BRZ' and month >= '2027-01' else 0
            if day(expected, late) <= BUSINESS_DATE:
                receipts.append(dict(id=gr, pol=pol, prod=prod, loc='LOC-SZ-RAW', qty=ordered, date=day(expected, late), status='accepted'))
    # issues: each requirement from its order's receipt; only material due by the business date is issued
    issue_n = 0
    issued = defaultdict(float)
    for it in sorted(issue_plan, key=lambda i: (i['date'], i['wo'], i['prod'])):
        qty_issued, source = 0, None
        if it['date'] <= BUSINESS_DATE and it['wo'] not in X['draft_bom']:
            cands = [r for r in receipts if r['pol'] == it['pol'] and r['status'] in ('accepted', 'pending_inspection')]
            if cands:
                source = cands[0]
                qty_issued = X['short_issue'][it['wo']][1] if it['tag'] == 'short' else it['need']
        status = 'issued' if qty_issued >= it['need'] else ('partial' if qty_issued > 0 else 'awaiting_issue')
        out['production_order_material_requirements'].append(dict(material_requirement_id=it['mr'], production_order_id=it['wo'], bom_component_id=it['comp'],
                                                                  product_id=it['prod'], required_quantity=it['need'], issued_quantity=qty_issued, unit=it['unit'], status=status))
        if source:
            issue_n += 1
            issued[source['id']] += qty_issued
            out['material_issue_transactions'].append(dict(material_issue_transaction_id=f'MIT-{issue_n:03d}', material_requirement_id=it['mr'], production_order_id=it['wo'],
                                                           goods_receipt_id=source['id'], inventory_location_id=source['loc'], issued_quantity=qty_issued,
                                                           issue_date=it['date'].isoformat(), status='completed'))
    for r in receipts:
        assert issued[r['id']] <= r['qty'], r
        out['goods_receipts'].append(dict(goods_receipt_id=r['id'], purchase_order_line_id=r['pol'], product_id=r['prod'], inventory_location_id=r['loc'],
                                          received_quantity=r['qty'], received_date=r['date'].isoformat(), inspection_status=r['status']))
    for po in out['purchase_orders']:
        pol = next(l for l in out['purchase_order_lines'] if l['purchase_order_id'] == po['purchase_order_id'])
        got = sum(r['qty'] for r in receipts if r['pol'] == pol['purchase_order_line_id'] and r['status'] == 'accepted')
        po['status'] = 'received' if got >= pol['ordered_quantity'] else ('partially_received' if got > 0 else 'confirmed')

    # quality, finished goods and shipments
    lot_n = res_n = fgr_n = shp_n = 0
    shipped_by_sol = defaultdict(float)
    fg_balance = defaultdict(float)
    for w in wos:
        wo, prod = w['wo'], w['prod']
        last = w['ops'][-1]
        inspecting = X['in_progress'].get(wo) == 'inspection'
        if not w['complete'] and not inspecting:
            continue
        lot_n += 1
        lot = f'QIL-{wo[3:]}'
        lot_qty = w['good'] if w['complete'] else w['qty']
        insp_date = day(last['end'], 1)
        specs = [s for s in SPEC_INDEX[prod] if s[7] == 'active' or (s[0] == 'QS-PH100-BORE-A' and insp_date < D('2027-01-01'))]
        specs = [s for s in specs if not (s[0] == 'QS-PH100-BORE-B' and insp_date < D('2027-01-01'))]
        lot_status = 'lot_accepted'
        for s in specs:
            res_n += 1
            value, rstat = NOMINAL[s[0]], 'pass'
            if inspecting:
                rstat = 'pending'
            elif X['quality_reject'].get(wo) == s[0]:
                value, rstat, lot_status = OUT_OF_SPEC[s[0]], 'fail', 'lot_rejected'
            elif X['recorded_pass_out_of_spec'].get(wo) == s[0]:
                value = RECORDED_PASS_VALUE[s[0]]
            out['quality_inspection_results'].append(dict(inspection_result_id=f'QIR-{wo[3:]}-{res_n:03d}', inspection_lot_id=lot, characteristic_name=s[2],
                                                          measured_value=value, target_value=s[3], lower_limit=s[4], upper_limit=s[5], result_status=rstat,
                                                          quality_specification_id=s[0]))
        if inspecting:
            lot_status = 'lot_pending'
        out['quality_inspection_lots'].append(dict(inspection_lot_id=lot, production_order_id=wo, product_id=prod, inspection_type='final', lot_quantity=lot_qty, status=lot_status))
        if lot_status != 'lot_accepted':
            continue
        fgr_n += 1
        fgr = f'FGR-{wo[3:]}'
        loc = 'LOC-SU-FG' if FG_SITE[prod] == 'SITE-SU' else 'LOC-SZ-FG'
        out['finished_goods_receipts'].append(dict(finished_goods_receipt_id=fgr, production_order_id=wo, inspection_lot_id=lot, inventory_location_id=loc,
                                                   received_quantity=w['good'], receipt_date=insp_date.isoformat(), status='accepted'))
        fg_balance[(loc, prod)] += w['good']
        if wo in X['fg_not_shipped']:
            continue
        ship_date = max(day(w['requested'], X['late_shipment'].get(wo, 0)), day(insp_date, 1))
        parts = [(w['good'], ship_date)]
        if wo in X['split_shipment']:
            first, gap = X['split_shipment'][wo]
            parts = [(first, ship_date), (w['good'] - first, day(ship_date, gap))]
        for qty, sdate in parts:
            if sdate > BUSINESS_DATE:
                continue
            shp_n += 1
            out['shipments'].append(dict(shipment_id=f'SHP-{shp_n:03d}', sales_order_line_id=w['sol'], production_order_id=wo, finished_goods_receipt_id=fgr,
                                         shipped_quantity=qty, shipment_date=sdate.isoformat(), delivery_status='shipped'))
            shipped_by_sol[w['sol']] += qty
            fg_balance[(loc, prod)] -= qty
    for so in out['sales_orders']:
        lines = [l for l in out['sales_order_lines'] if l['sales_order_id'] == so['sales_order_id']]
        shipped = [shipped_by_sol[l['sales_order_line_id']] for l in lines]
        full = all(s >= l['ordered_quantity'] for s, l in zip(shipped, lines))
        so['status'] = 'closed' if full else ('partially_shipped' if any(shipped) else 'confirmed')

    # inventory balances as of the business date; open requirements of released orders are allocated
    on_hand = defaultdict(float)
    for r in receipts:
        if r['status'] == 'accepted':
            on_hand[(r['loc'], r['prod'])] += r['qty']
        elif r['status'] == 'pending_inspection':
            on_hand[(r['loc'], r['prod'])] += r['qty']
    for m in out['material_issue_transactions']:
        prod = next(r['prod'] for r in receipts if r['id'] == m['goods_receipt_id'])
        on_hand[(m['inventory_location_id'], prod)] -= m['issued_quantity']
    open_need = defaultdict(float)
    for r in out['production_order_material_requirements']:
        wo = next(w for w in wos if w['wo'] == r['production_order_id'])
        if wo['status'] == 'released' and wo['issue_date'] <= day(BUSINESS_DATE, 7):
            open_need[r['product_id']] += r['required_quantity'] - r['issued_quantity']
    ib = []
    for (loc, prod), qty in sorted(on_hand.items()):
        if loc == 'LOC-SZ-QI':
            alloc = 0
        else:
            alloc = min(qty, open_need[prod])
        ib.append(dict(inventory_balance_id=f'IB-{loc[4:]}-{PRODUCT[prod][1]}', inventory_location_id=loc, product_id=prod, on_hand_quantity=_num(qty),
                       allocated_quantity=_num(alloc), available_quantity=_num(qty - alloc), unit=PRODUCT[prod][4], as_of_date=BUSINESS_DATE.isoformat()))
    for (loc, prod), qty in sorted(fg_balance.items()):
        ib.append(dict(inventory_balance_id=f'IB-{loc[4:]}-{PRODUCT[prod][1]}', inventory_location_id=loc, product_id=prod, on_hand_quantity=_num(qty),
                       allocated_quantity=0, available_quantity=_num(qty), unit=PRODUCT[prod][4], as_of_date=BUSINESS_DATE.isoformat()))
    out['inventory_balances'] = ib

    # planning: one plan per month (snapshot on the 20th of the month before), forecasts per product and month
    months = ['2026-11', '2026-12', '2027-01', '2027-02', '2027-03']
    forecast_qty = {
        'FG-PH100': [400, 420, 380, 400, 450], 'FG-PH200': [60, 120, 80, 100, 160], 'FG-VB050': [360, 200, 380, 320, 300],
        'FG-VB080': [120, 160, 120, 160, 200], 'FG-IMP300': [80, 220, 200, 140, 100], 'FG-FL150': [300, 240, 260, 480, 220],
    }
    for prod, qtys in forecast_qty.items():
        for m, fq in zip(months, qtys):
            out['demand_forecasts'].append(dict(forecast_id=f'FC-{m[2:4]}{m[5:]}-{PRODUCT[prod][1]}', product_id=prod, forecast_period=m, forecast_quantity=fq, unit='EA'))
    for m in months:
        y, mo = int(m[:4]), int(m[5:])
        start = dt.date(y, mo, 1)
        end = (dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1))
        snap = day(start, -12)
        out['production_plans'].append(dict(production_plan_id=f'PP-{m[2:4]}{m[5:]}', plan_version=f'{m}-v1', snapshot_date=snap.isoformat(),
                                            planning_start_date=start.isoformat(), planning_end_date=end.isoformat(), status='released'))
    for k, w in enumerate(wos, 1):
        m = w['due'].strftime('%Y-%m')
        out['production_plan_lines'].append(dict(
            production_plan_line_id=f'PPL-{w["wo"][3:]}', production_plan_id=f'PP-{m[2:4]}{m[5:]}', forecast_id=f'FC-{m[2:4]}{m[5:]}-{PRODUCT[w["prod"]][1]}',
            product_id=w['prod'], site_id=FG_SITE[w['prod']], production_order_id=w['wo'], planned_quantity=w['qty'],
            planned_start_date=day(w['due'], -10).isoformat(), planned_completion_date=w['due'].isoformat(),
            scenario_as_of_date=next(p['snapshot_date'] for p in out['production_plans'] if p['production_plan_id'] == f'PP-{m[2:4]}{m[5:]}'), status='released'))

    # maintenance: one plan per machine; monthly work orders; two overdue, one in progress, one clash
    for i, m in enumerate(MACHINES, 1):
        freq = 30 if m[4] in ('CNC_MILL', 'CNC_LATHE') else 60
        out['maintenance_plans'].append(dict(maintenance_plan_id=f'MP-{m[0][5:]}', machine_id=m[0], plan_name=((f'{m[3][0]}{"月度" if freq == 30 else "双月"}保养'), f'{m[3][1]} {"monthly" if freq == 30 else "bi-monthly"} service'),
                                             frequency_days=freq, status='active_plan'))
    mw = []
    for m in MACHINES:
        freq = 30 if m[4] in ('CNC_MILL', 'CNC_LATHE') else 60
        d0 = D('2026-11-07') + dt.timedelta(days=MACHINES.index(m) % 5)
        d = d0
        while d <= D('2027-03-31'):
            status = 'completed' if d < BUSINESS_DATE else 'planned'
            mw.append([m[0], d, status])
            d = day(d, freq)
    for machine, date, status in mwo:
        for row in mw:
            if row[0] == machine and abs((row[1] - date).days) < 15:
                row[1] = date
    for row in mw:
        if row[0] == 'MACH-MILL-02' and row[1].strftime('%Y-%m') == '2027-02':
            row[1], row[2] = D('2027-02-10'), 'planned'
        if row[0] == 'MACH-PT-01' and row[1].strftime('%Y-%m') in ('2027-01', '2027-02') and row[1] < BUSINESS_DATE:
            row[2] = 'planned'
        if row[0] == 'MACH-MILL-03' and row[1].strftime('%Y-%m') == '2027-02':
            row[1], row[2] = D('2027-02-24'), 'in_progress'
    busy = {(e['machine_id'], e['started_date']) for e in out['production_execution_records']}
    clash = {(m, d.isoformat()) for m, d, _ in mwo}
    for row in mw:  # routine service is planned on days the machine is idle, except the deliberate clash
        while (row[0], row[1].isoformat()) in busy and (row[0], row[1].isoformat()) not in clash:
            row[1] = day(row[1], 1)
    mw.sort(key=lambda r: (r[1], r[0]))
    for k, (machine, date, status) in enumerate(mw, 1):
        out['maintenance_work_orders'].append(dict(maintenance_work_order_id=f'MWO-{k:03d}', maintenance_plan_id=f'MP-{machine[5:]}', machine_id=machine,
                                                   planned_date=date.isoformat(), status=status))
    out['shifts'] = sorted(shift_rows.values(), key=lambda r: (r['starts_date'], r['site_id']))
    for k, (operator, shift, wc) in enumerate(sorted(assignments), 1):
        out['operator_shift_assignments'].append(dict(operator_shift_assignment_id=f'OSA-{k:03d}', operator_id=operator, shift_id=shift, work_center_id=wc, assignment_status='assigned'))
    return out


def _num(v):
    return int(v) if float(v) == int(v) else round(v, 1)


TRANSLATED = {  # columns holding vocabulary codes
    'site_type', 'work_center_type', 'capability_category', 'machine_type', 'status', 'qualification_status', 'employment_status', 'customer_segment',
    'supplier_category', 'product_type', 'base_unit', 'unit', 'location_type', 'inspection_status', 'inspection_type', 'result_status', 'delivery_status',
    'assignment_status', 'setup_class',
}


def render(out, lang, contract):
    files = {}
    for table, spec in contract['object_types'].items():
        fields = list(spec['fields'])
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator='\n')
        writer.writerow(fields)
        for row in out[table]:
            values = []
            for f in fields:
                v = row[f]
                if isinstance(v, tuple):
                    v = n(v, lang)
                elif f in TRANSLATED and v not in ('', None):
                    v = t(v, lang)
                elif isinstance(v, float):
                    v = f'{v:.2f}'.rstrip('0').rstrip('.') if v != int(v) else str(int(v))
                values.append('' if v is None else v)
            writer.writerow(values)
        files[table] = buf.getvalue()
    return files


def main():
    out = build()
    check = '--check' in sys.argv
    for lang, root in SAMPLES.items():
        contract_path = root / 'model-contract.json'
        contract = json.loads(contract_path.read_text(encoding='utf-8'))
        files = render(out, lang, contract)
        lock = {'files': {}}
        for table, text in files.items():
            path = root / 'data' / f'{table}.csv'
            if check:
                assert path.read_text(encoding='utf-8') == text, f'{path} differs from the generator'
            else:
                path.write_text(text, encoding='utf-8')
            lock['files'][path.name] = 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest()
            contract['object_types'][table]['row_count'] = len(out[table])
        if not check:
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            old = json.loads((root / 'dataset.lock').read_text(encoding='utf-8'))
            old['files'] = dict(sorted(lock['files'].items()))
            (root / 'dataset.lock').write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(lang, sum(len(v) for v in out.values()), 'records in', len(files), 'tables')


if __name__ == '__main__':
    main()
