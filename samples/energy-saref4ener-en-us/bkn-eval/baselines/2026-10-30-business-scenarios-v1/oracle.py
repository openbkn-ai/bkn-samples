#!/usr/bin/env python3
"""Independent oracle for the energy demand-response business-scenario question set.

Reads only this package's delivered CSV files. Flexibility, dispatch and settlement are
recomputed by energy_calc.py, written from the business contract without importing the
sample's engine. The files are identical in the zh-CN and en-US packages: their data differ
only in translated text, so expected values match except for names.

Writes question-set-v1.yaml (no answers) and answer-set-v1.yaml next to this file.
"""
import sys
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from energy_calc import Energy, dispatch, q2, q6  # noqa: E402

LANG = 'zh' if ROOT.name.endswith('zh-cn') else 'en'
TODAY = '2027-02-28'
E = Energy(ROOT / 'data')
T = E.t
EV = E.events(TODAY, TODAY)


def num(x):
    if x is None:
        return None
    x = q6(x)
    return int(x) if x == x.to_integral_value() else float(x.normalize())


def money(x):
    return None if x is None else float(q2(x))


QUESTIONS = []
ROLE = {'OP': ('聚合商运营负责人', 'Aggregator operations lead'), 'EM': ('企业能源经理', 'Site energy manager'),
        'DO': ('响应值班员', 'Response duty officer'), 'SC': ('结算专员', 'Settlement clerk')}
LEVEL = {'basic': ('基础', 'basic'), 'medium': ('中等', 'medium'), 'complex': ('复杂', 'complex')}


def q(qid, scenario, level, role, zh, en, expected, contract_zh, contract_en):
    i = 0 if LANG == 'zh' else 1
    QUESTIONS.append(dict(id=qid, scenario=scenario, difficulty=LEVEL[level][i], role=ROLE[role][i],
                          question=(zh, en)[i], output_contract=(contract_zh, contract_en)[i], expected=expected))


def settle(event_id, a=TODAY, k=TODAY):
    return E.settlement(event_id, a, k)


def flex(event_id, a=TODAY, k=TODAY):
    return E.flexibility(event_id, a, k)


# S01 assets
q('Q-01', 'S01', 'basic', 'OP', '我们签约了多少家企业客户、多少个场所、多少台可调设备？三类设备各多少台？',
  'How many enterprise customers, sites and controllable devices do we have under contract, and how many of each device type?',
  dict(customers=len(T['customers']), sites=len(T['sites']), devices=len(T['devices']),
       by_type=dict(sorted(Counter(d['device_type_code'] for d in T['devices']).items()))), '客户数、场所数、设备数、各类设备数', 'customers, sites, devices, devices by type')
s1 = E.sites['SIT-001']
q('Q-02', 'S01', 'basic', 'EM', 'SIT-001 这个场所最多能响应多少千瓦？场所里有哪些设备？', 'What is the most SIT-001 can respond in kW, and which devices does it have?',
  dict(response_cap_kw=num(D(s1['response_cap_kw'])), devices=sorted(d['device_id'] for d in T['devices'] if d['site_id'] == 'SIT-001')),
  '场所响应上限、设备清单', 'site response cap, device ids')
q('Q-03', 'S01', 'basic', 'EM', '现在有哪些设备是停用状态？', 'Which devices are currently inactive?',
  dict(devices=sorted(d['device_id'] for d in T['devices'] if d['status_code'] != 'active')), '设备清单', 'device ids')
d1 = E.devices['DEV-001']
q('Q-04', 'S01', 'basic', 'EM', 'DEV-001 每次最多能削减多少千瓦？至少要保留多少千瓦保障运行？用哪块电表计量？',
  'How much can DEV-001 reduce at most, how much load must it keep for safe operation, and which meter measures it?',
  dict(max_reduction_kw=num(D(d1['max_reduction_kw'])), min_service_kw=num(D(d1['min_service_kw'])), meter_id=E.meters['DEV-001']['meter_id']),
  '最大削减、最低保障负荷、电表编号', 'max reduction, minimum service load, meter id')

# S02 forecasts and plans
fut = [e for e in EV.values() if e['response_date'] > TODAY]
q('Q-05', 'S02', 'basic', 'OP', '三月份还安排了多少场响应事件？有没有已经取消的？', 'How many response events are scheduled for March, and have any been cancelled?',
  dict(active=sum(e['status_code'] == 'active' for e in fut), cancelled=sorted(e['event_id'] for e in fut if e['status_code'] == 'cancelled')),
  '有效事件数、已取消事件清单', 'active event count, cancelled event ids')
e61 = EV['EVT-061']
q('Q-06', 'S02', 'basic', 'OP', 'EVT-061 是哪天、哪个时段？要削减多少千瓦、持续几小时？每千瓦时奖励多少？达标要求多少？',
  'When is EVT-061 and in which block? What reduction is targeted, for how many hours, at what reward per kWh, and what delivery ratio is required?',
  dict(response_date=e61['response_date'], block=e61['block_code'], target_kw=num(D(e61['target_kw'])), hours=num(D(e61['duration_hours'])),
       reward_cny_kwh=num(D(e61['reward_cny_kwh'])), minimum_ratio=num(D(e61['minimum_ratio']))), '日期、时段、目标、小时数、奖励单价、最低交付比例',
  'date, block, target, hours, reward rate, minimum delivery ratio')
fc46 = E.latest('load_forecasts', ('device_id', 'response_date', 'block_code'), 'forecast_id', TODAY)[('DEV-046', '2026-11-25', 'peak_b')][1]
q('Q-07', 'S02', 'medium', 'EM', 'DEV-046 在 2026-11-25 那个时段的负荷预测，最新一版能用吗？', 'Can the latest load forecast for DEV-046 on 2026-11-25 be used?',
  dict(usable=False, forecast_id=fc46['forecast_id'], revision=int(fc46['revision']), quality=fc46['quality_code']), '能否使用、最新预测编号、版本、质量', 'usable or not, latest forecast id, revision, quality')
peak = Counter(e['response_date'] for e in fut if e['status_code'] == 'active')
q('Q-08', 'S02', 'medium', 'OP', '三月份按日期看，哪几天的响应目标合计最大？合计多少千瓦？', 'Which March date has the largest total response target, and how many kW?',
  dict(**(lambda best: dict(date=best, target_kw=num(sum((D(e['target_kw']) for e in fut if e['status_code'] == 'active' and e['response_date'] == best), D(0)))))(
      max(peak, key=lambda d: (sum((D(e['target_kw']) for e in fut if e['status_code'] == 'active' and e['response_date'] == d), D(0)), d)))),
  '日期、目标合计', 'date, total target')

# S03 eligibility
f1 = flex('EVT-001')
q('Q-09', 'S03', 'medium', 'OP', 'EVT-001 现在申报的设备里，按负荷和设备约束一共能承诺多少千瓦？', 'Of the devices offered for EVT-001, how many kW can be committed under load and device constraints?',
  dict(eligible_kw=num(f1['eligible'])), '可承诺千瓦', 'eligible kW')
blocked1 = sorted(r['device_id'] for r in f1['device_rows'] if 'blocked' in r['reasons'])
q('Q-10', 'S03', 'medium', 'EM', 'EVT-001 有哪些设备因为检修等原因被禁止响应？', 'Which devices are barred from EVT-001 because of maintenance or similar constraints?',
  dict(devices=blocked1), '设备清单', 'device ids')
q('Q-11', 'S03', 'complex', 'OP', 'EVT-013 的可承诺容量为什么算不出来？是哪台设备、什么原因？', 'Why can EVT-013\'s eligible capacity not be calculated? Which device and what reason?',
  dict(devices=[r['device_id'] for r in flex('EVT-013')['device_rows'] if r['eligible'] is None], reason='latest_forecast_invalid'),
  '设备、原因', 'device, reason')
q('Q-12', 'S03', 'complex', 'EM', 'DEV-061 在 2027-02-10 有一条限额约束没填上限，影响哪些事件？这些事件的可承诺容量还能算吗？',
  'DEV-061 has a cap constraint on 2027-02-10 with no cap value. Which events does it affect, and can their eligible capacity still be calculated?',
  dict(events=sorted(i for i in EV if EV[i]['response_date'] == '2027-02-10' and flex(i) and flex(i)['eligible'] is None), calculable=False, constraint='CON-076'),
  '受影响事件、能否计算、约束编号', 'affected events, calculable or not, constraint id')
offers_now = E.latest('flexibility_offers', ('event_id', 'device_id'), 'offer_id', TODAY)
withdrawn = [v[1] for v in offers_now.values() if v[0] == 'ok' and v[1]['status_code'] == 'withdrawn']
q('Q-13', 'S03', 'medium', 'EM', '现在有多少份设备申报处于撤回状态？涉及多少个事件？', 'How many device offers are currently withdrawn, and across how many events?',
  dict(offers=len(withdrawn), events=len({o['event_id'] for o in withdrawn})), '撤回申报数、涉及事件数', 'withdrawn offer count, event count')

# S04 site cap and no double count
def site_capped(event_id):
    f = flex(event_id); out = {}
    for r in f['device_rows']:
        if r['eligible'] is not None:
            out.setdefault(r['site_id'], D(0)); out[r['site_id']] += r['eligible']
    return {s: v for s, v in out.items() if v > D(E.sites[s]['response_cap_kw'])}
cap1 = site_capped('EVT-001')
q('Q-14', 'S04', 'complex', 'EM', 'EVT-001 里，哪些场所的设备可承诺量加起来超过了场所响应上限？各被压到多少？',
  'In EVT-001, which sites have device eligibility that adds up to more than the site response cap, and what are they limited to?',
  dict(sites={s: dict(devices_kw=num(v), capped_kw=num(D(E.sites[s]['response_cap_kw']))) for s, v in sorted(cap1.items())}),
  '场所、设备合计、场所上限', 'site, device total, site cap')
q('Q-15', 'S04', 'basic', 'EM', '每台设备有几块电表？场所总表会不会和设备电表重复计量？', 'How many meters does each device have, and is a site meter added on top of device meters?',
  dict(meters_per_device=max(Counter(m['device_id'] for m in T['meters']).values()), site_meter_added=False), '每台设备电表数、是否叠加场所电表', 'meters per device, site meter added or not')

# S05 shared commitments and priorities
pool24 = sorted(i for i in EV if EV[i]['response_date'] == '2027-02-24' and EV[i]['block_code'] == 'peak_a')
over = [r for r in T['dispatch_allocations'] if r['allocation_id'] == 'ALL-0499'][0]
q('Q-16', 'S05', 'complex', 'OP', '2027-02-24 那个时段有哪几个事件？已承诺的分配有没有超出设备能削减的上限？超的是哪台设备、哪条分配？',
  'Which events share the 2027-02-24 block? Do existing commitments exceed what a device can reduce, and if so on which device and allocation?',
  dict(events=pool24, overreserved_device=over['device_id'], allocation=over['allocation_id']), '事件清单、超额设备、分配编号', 'event ids, over-reserved device, allocation id')
d16 = dispatch(E, 'EVT-057', TODAY, TODAY)
q('Q-17', 'S05', 'complex', 'OP', '2027-02-24 那个时段的事件现在还能给出完整的新增分配方案吗？为什么？', 'Can a complete new allocation plan still be produced for the events in the 2027-02-24 block, and why?',
  dict(complete_plan=False, events_with_unknown_plan=sorted(i for i, v in d16.items() if v['unknown'])), '能否给出、计划未知的事件', 'complete or not, events with an unknown plan')
pool04 = sorted(i for i in EV if EV[i]['response_date'] == '2026-11-04' and EV[i]['block_code'] == 'peak_a')
shared = sorted({r['event_id'] for r in T['dispatch_allocations'] if r['device_id'] == 'DEV-016' and r['status_code'] == 'committed' and r['event_id'] in pool04})
q('Q-18', 'S05', 'medium', 'DO', '2026-11-04 午后那个时段，DEV-016 同时承诺给了哪几个事件？', 'In the 2026-11-04 peak_a block, which events was DEV-016 committed to at the same time?',
  dict(events=shared), '事件清单', 'event ids')
p61 = dispatch(E, 'EVT-061', TODAY, TODAY)
q('Q-19', 'S05', 'complex', 'OP', 'EVT-061 所在时段几个事件按优先级先后排，各自已承诺多少、还能新安排多少、缺口多少？',
  'In EVT-061\'s block, with events served by priority, how much has each committed, how much more can be scheduled, and what is each shortfall?',
  dict(events={i: dict(committed_kw=num(v['committed']), new_kw=num(v['new']), shortfall_kw=num(v['shortfall'])) for i, v in sorted(p61.items())}),
  '各事件已承诺、新增、缺口', 'per event committed, new, shortfall')

# S06 cost-ordered allocation
v61 = p61['EVT-061']
q('Q-20', 'S06', 'complex', 'OP', 'EVT-061 按成本从低到高安排，新增的设备有哪些、各多少千瓦？整个方案预计成本多少？',
  'Scheduling EVT-061 from the cheapest offer up, which devices are added and how many kW each? What is the estimated cost of the whole plan?',
  dict(new_devices={n['device_id']: num(n['kw']) for n in v61['rows']}, estimated_cost_cny=money(v61['cost'])), '新增设备及千瓦、预计成本', 'added devices and kW, estimated cost')
q('Q-21', 'S06', 'medium', 'OP', 'EVT-061 按现在的方案能凑够目标吗？还差多少千瓦？', 'Can EVT-061 reach its target with the current plan, and how many kW short is it?',
  dict(target_met=v61['shortfall'] == 0, shortfall_kw=num(v61['shortfall'])), '能否达标、缺口', 'target met or not, shortfall')
p74 = dispatch(E, 'EVT-074', TODAY, TODAY)['EVT-074']
q('Q-22', 'S06', 'medium', 'OP', 'EVT-074 已经承诺了多少千瓦？再新安排多少就能凑够？预计总成本多少？', 'How many kW has EVT-074 committed, how many more must be scheduled to reach its target, and what is the estimated total cost?',
  dict(committed_kw=num(p74['committed']), new_kw=num(p74['new']), shortfall_kw=num(p74['shortfall']), estimated_cost_cny=money(p74['cost'])), '已承诺、新增、缺口、预计成本', 'committed, new, shortfall, estimated cost')

# S07 execution and measured delivery
ex = Counter(x['status_code'] for x in T['execution_logs'])
q('Q-23', 'S07', 'basic', 'DO', '执行回执里，有多少条执行完成、多少条失败、多少条客户临时退出？', 'In the execution receipts, how many completed, how many failed and how many were declined by the customer?',
  dict(completed=ex['completed'], failed=ex['failed'], declined=ex['declined']), '完成、失败、退出条数', 'completed, failed, declined counts')
s1v = settle('EVT-001')
q('Q-24', 'S07', 'medium', 'DO', 'EVT-001 实际核实的削减电量是多少千瓦时？交付比例多少？达标了吗？', 'How many kWh of reduction were verified for EVT-001, what is the delivery ratio, and did it meet the threshold?',
  dict(committed_kwh=num(s1v['committed_kwh']), verified_kwh=num(s1v['verified_kwh']), delivery_ratio=num(s1v['delivery_ratio']),
       met=s1v['delivery_ratio'] >= D(EV['EVT-001']['minimum_ratio'])), '承诺电量、核实电量、交付比例、是否达标', 'committed kWh, verified kWh, delivery ratio, met or not')
q('Q-25', 'S07', 'complex', 'DO', 'EVT-033 有一条分配没有执行回执，会影响什么？', 'EVT-033 has an allocation with no execution receipt. What does that affect?',
  dict(allocation='ALL-0283', settlement_known=settle('EVT-033')['verified_kwh'] is not None, committed_kwh=num(settle('EVT-033')['committed_kwh'])),
  '分配编号、结算能否确定、承诺电量', 'allocation id, settlement determinable or not, committed kWh')
below = sorted(i for i in EV if (s := settle(i)) and s.get('status') == 'settled' and s['delivery_ratio'] is not None and s['delivery_ratio'] < D(EV[i]['minimum_ratio']))
q('Q-26', 'S07', 'complex', 'DO', '已经发生的事件里，哪些没有达到最低交付比例？', 'Which past events fell short of their minimum delivery ratio?',
  dict(events=below), '事件清单', 'event ids')
fx = [x for x in T['execution_logs'] if x['status_code'] != 'completed']
q('Q-27', 'S07', 'medium', 'DO', '执行失败或客户退出的分配，各是什么原因？分别有几条？', 'For allocations that failed or were declined, what were the reasons and how many of each?',
  dict(reasons=dict(sorted(Counter(x['reason'] for x in fx).items()))), '原因及条数', 'reasons and counts')

# S08 late, corrected and conflicting records
ev_jan6 = sorted(i for i in EV if EV[i]['response_date'] == '2027-01-06')
def verified_with_dev136(k):
    out = {}
    for i in ev_jan6:
        if any(r['device_id'] == 'DEV-136' and r['event_id'] == i and r['status_code'] == 'committed' for r in T['dispatch_allocations']):
            out[i] = num(settle(i, TODAY, k)['verified_kwh'])
    return out
q('Q-28', 'S08', 'complex', 'DO', 'DEV-136 在 2027-01-06 的电表读数后来更正过。按 1 月 10 日掌握的信息和按今天的信息，用到这台设备的事件核实电量各是多少？',
  'DEV-136\'s meter reading for 2027-01-06 was corrected later. Based on what was known on January 10 and based on today, what verified energy do the events using this device have?',
  dict(jan10=verified_with_dev136('2027-01-10'), today=verified_with_dev136(TODAY), corrected_reading='REA-10-136-R2'), '1 月 10 日口径、今天口径的核实电量，更正读数编号', 'verified energy as known on Jan 10 and today, corrected reading id')
s57a, s57b = settle('EVT-057'), settle('EVT-057', TODAY, '2027-03-05')
q('Q-29', 'S08', 'complex', 'SC', 'DEV-061 在 2027-02-24 的基线 3 月 3 日被重新核定了。按 3 月 5 日掌握的信息，EVT-057 的核实电量和应收收入会怎么变？',
  'DEV-061\'s 2027-02-24 baseline was restated on March 3. Based on what was known on March 5, how do EVT-057\'s verified energy and revenue change?',
  dict(today=dict(verified_kwh=num(s57a['verified_kwh']), revenue_cny=money(s57a['revenue'])), march5=dict(verified_kwh=num(s57b['verified_kwh']), revenue_cny=money(s57b['revenue']))),
  '今天口径与 3 月 5 日口径的核实电量和收入', 'verified energy and revenue as known today and on March 5')
q('Q-30', 'S08', 'medium', 'DO', 'DEV-076 在 2026-12-09 的基线有两条同版本记录内容不一致，影响哪个事件的结算？', 'DEV-076 has two same-revision baselines that disagree for 2026-12-09. Which event\'s settlement does that affect?',
  dict(events=sorted(i for i in EV if EV[i]['response_date'] == '2026-12-09' and (s := settle(i)) and s.get('status') == 'settled' and s['verified_kwh'] is None)),
  '事件清单', 'event ids')
q('Q-31', 'S08', 'medium', 'DO', 'DEV-136 在 2026-12-30 的读数提交了两次，会被算两次吗？', 'DEV-136\'s 2026-12-30 reading was submitted twice. Is it counted twice?',
  dict(counted_twice=False, readings=['REA-09-136', 'REA-09-136-RETRY']), '是否重复计算、读数编号', 'counted twice or not, reading ids')
q('Q-32', 'S08', 'medium', 'DO', 'DEV-106 在 2026-12-23 缺电表读数，影响哪个事件的结算？', 'DEV-106 has no meter reading for 2026-12-23. Which event\'s settlement does that affect?',
  dict(events=sorted(i for i in EV if EV[i]['response_date'] == '2026-12-23' and (s := settle(i)) and s.get('status') == 'settled' and s['verified_kwh'] is None)),
  '事件清单', 'event ids')

# S09 settlement and ledger
led = Counter(s['status_code'] for s in T['settlements'])
q('Q-33', 'S09', 'basic', 'SC', '结算台账里已经入账的有多少笔？还在待入账的有多少笔？', 'How many settlements are posted in the ledger, and how many are still pending?',
  dict(posted=led['posted'], pending=led['pending']), '已入账、待入账笔数', 'posted, pending counts')
s3 = settle('EVT-003')
q('Q-34', 'S09', 'medium', 'SC', 'EVT-003 没有达标，平台能拿到多少奖励？还要付给客户多少补偿？净额多少？', 'EVT-003 missed its threshold. How much reward does the aggregator get, how much compensation is owed to customers, and what is the net?',
  dict(revenue_cny=money(s3['revenue']), cost_cny=money(s3['cost']), net_cny=money(s3['net'])), '奖励收入、客户补偿、净额', 'revenue, customer compensation, net')
s25 = settle('EVT-025')
q('Q-35', 'S09', 'medium', 'SC', 'EVT-025 按核实电量算出来的收入和账上已入账的收入差多少？', 'How much does EVT-025\'s revenue from verified energy differ from the revenue posted in the ledger?',
  dict(recomputed_revenue_cny=money(s25['revenue']), posted_revenue_cny=money(s25['recorded']), difference_cny=money(s25['revenue'] - s25['recorded'])),
  '重算收入、已入账收入、差额（重算减入账）', 'recomputed revenue, posted revenue, difference (recomputed minus posted)')
q('Q-36', 'S09', 'complex', 'SC', 'EVT-041 的账目能核对吗？为什么？', 'Can EVT-041\'s ledger be reconciled, and why?',
  dict(reconcilable=False, settlements=sorted(s['settlement_id'] for s in T['settlements'] if s['event_id'] == 'EVT-041'), recomputed_revenue_cny=money(settle('EVT-041')['revenue'])),
  '能否核对、冲突入账编号、重算收入', 'reconcilable or not, conflicting settlement ids, recomputed revenue')
neg = sorted(i for i in EV if (s := settle(i)) and s.get('status') == 'settled' and s['net'] is not None and s['net'] < 0)
q('Q-37', 'S09', 'complex', 'SC', '已经发生的事件里，哪些是净亏损的（补偿比收入多）？', 'Which past events ran at a net loss, with compensation above revenue?',
  dict(events=neg), '事件清单', 'event ids')
s5 = settle('EVT-005')
q('Q-38', 'S09', 'complex', 'SC', 'EVT-005 的交付比例为什么是空的？收入和补偿是多少？', 'Why is EVT-005\'s delivery ratio empty, and what are its revenue and compensation?',
  dict(committed_kwh=num(s5['committed_kwh']), delivery_ratio=None, revenue_cny=money(s5['revenue']), cost_cny=money(s5['cost'])), '承诺电量、交付比例、收入、补偿', 'committed kWh, delivery ratio, revenue, compensation')
tot = [settle(i) for i in EV if EV[i]['response_date'] <= TODAY]
done = [s for s in tot if s and s.get('status') == 'settled' and s['revenue'] is not None]
q('Q-39', 'S09', 'complex', 'SC', '到今天为止，结算结果能确定的已发生事件，奖励收入和客户补偿合计各是多少？净额多少？涉及多少个事件？',
  'Up to today, for past events whose settlement can be determined, what are total revenue and total customer compensation, the net, and how many events are included?',
  dict(events=len(done), revenue_cny=money(sum((s['revenue'] for s in done), D(0))), cost_cny=money(sum((s['cost'] for s in done), D(0))),
       net_cny=money(sum((s['net'] for s in done), D(0)))), '事件数、收入合计、补偿合计、净额', 'event count, revenue, compensation, net')

# S10 plan vs actual, snapshots, investigation
q('Q-40', 'S10', 'basic', 'OP', '容量快照里有几条被标记为无效？是哪些事件？', 'How many capacity snapshots are marked invalid, and for which events?',
  dict(events=sorted(s['event_id'] for s in T['capacity_snapshots'] if s['quality_code'] != 'valid')), '事件清单', 'event ids')
snap17 = [s for s in T['capacity_snapshots'] if s['event_id'] == 'EVT-017'][0]
q('Q-41', 'S10', 'medium', 'OP', 'EVT-017 的容量快照记录的可承诺量，和按现在的数据重算的相比差多少？', 'How does the eligible capacity recorded in EVT-017\'s snapshot compare with a recalculation from current data?',
  dict(snapshot_kw=num(D(snap17['eligible_kw'])), recomputed_kw=num(flex('EVT-017')['eligible']), difference_kw=num(D(snap17['eligible_kw']) - flex('EVT-017')['eligible'])),
  '快照值、重算值、差额（快照减重算）', 'snapshot, recomputed, difference (snapshot minus recomputed)')
drift = sorted(s['event_id'] for s in T['capacity_snapshots'] if s['quality_code'] == 'valid' and (f := flex(s['event_id'])) and f.get('eligible') is not None and q6(f['eligible']) != D(s['eligible_kw']))
q('Q-42', 'S10', 'complex', 'OP', '标为有效的容量快照里，哪些和按现在数据重算的结果对不上？', 'Among capacity snapshots marked valid, which disagree with a recalculation from current data?',
  dict(events=drift), '事件清单', 'event ids')
q('Q-43', 'S10', 'basic', 'SC', 'EVT-061 现在能结算吗？', 'Can EVT-061 be settled now?',
  dict(can_settle=False, response_date=EV['EVT-061']['response_date']), '能否结算、响应日期', 'settle now or not, response date')
q('Q-44', 'S10', 'basic', 'OP', '有哪些响应事件已经取消了？', 'Which response events have been cancelled?',
  dict(events=sorted(i for i, e in EV.items() if e['status_code'] == 'cancelled')), '事件清单', 'event ids')
d73 = dispatch(E, 'EVT-074', TODAY, '2027-03-05')
q('Q-45', 'S10', 'complex', 'OP', 'EVT-073 的一份申报 3 月 5 日撤回了。按 3 月 5 日掌握的信息，2027-03-12 那个时段的计划还能完整给出吗？EVT-073 原来已承诺的量还算数吗？',
  'One of EVT-073\'s offers was withdrawn on March 5. Based on what was known on March 5, can the plan for the 2027-03-12 block still be given in full, and does EVT-073\'s existing commitment still stand?',
  dict(complete_plan=not any(v['unknown'] for v in d73.values()), evt073_committed_kw=num(d73['EVT-073']['committed']), offer='OFF-2161'),
  '计划能否完整、EVT-073 已承诺量、撤回的申报', 'plan complete or not, EVT-073 committed kW, withdrawn offer')
ssv = [x for x in T['settlement_snapshots'] if x['quality_code'] == 'valid' and x['revenue_cny'] != '']
rev_mis = sorted(x['event_id'] for x in ssv if settle(x['event_id'])['revenue'] is None or q2(settle(x['event_id'])['revenue']) != D(x['revenue_cny']))
q('Q-46', 'S10', 'medium', 'SC', '标为有效的结算快照里，哪些事件记录的收入和按现在数据重算的不一致？各差多少？',
  'Among settlement snapshots marked valid, which events record revenue that differs from a recalculation from current data, and by how much?',
  dict(events={i: dict(snapshot_cny=money(D([x for x in ssv if x['event_id'] == i][0]['revenue_cny'])), recomputed_cny=money(settle(i)['revenue'])) for i in rev_mis}),
  '事件、快照收入、重算收入', 'event, snapshot revenue, recomputed revenue')
q('Q-47', 'S03', 'medium', 'OP', 'EVT-061 的申报设备现在一共能承诺多少千瓦？比目标差多少？', 'How many kW can EVT-061\'s offered devices commit now, and how far is that from the target?',
  dict(eligible_kw=num(flex('EVT-061')['eligible']), target_kw=num(D(EV['EVT-061']['target_kw'])),
       gap_kw=num(max(D(0), D(EV['EVT-061']['target_kw']) - flex('EVT-061')['eligible']))), '可承诺、目标、差额', 'eligible, target, gap')
s1rev = settle('EVT-001')
q('Q-48', 'S09', 'medium', 'SC', 'EVT-001 能拿到多少奖励？付给客户多少补偿？和账上一致吗？', 'How much reward does EVT-001 earn, how much compensation goes to customers, and does it match the ledger?',
  dict(revenue_cny=money(s1rev['revenue']), cost_cny=money(s1rev['cost']), matches_ledger=s1rev['recorded'] == s1rev['revenue']), '收入、补偿、是否与台账一致', 'revenue, compensation, matches ledger or not')
cust = E.sites[E.devices['DEV-016']['site_id']]['customer_id']
q('Q-49', 'S01', 'medium', 'EM', 'DEV-016 属于哪个场所、哪家客户？这个场所最多能响应多少千瓦？', 'Which site and customer does DEV-016 belong to, and what is that site\'s response cap?',
  dict(site_id=E.devices['DEV-016']['site_id'], customer_id=cust, response_cap_kw=num(D(E.sites[E.devices['DEV-016']['site_id']]['response_cap_kw']))),
  '场所、客户、场所上限', 'site, customer, site cap')
open_issue = sorted(i for i in EV if EV[i]['response_date'] <= TODAY and (s := settle(i)) and s.get('status') == 'settled' and s['verified_kwh'] is None)
q('Q-50', 'S10', 'complex', 'SC', '已经发生的事件里，哪些的结算结果现在还确定不了？各卡在哪里？', 'Which past events cannot have their settlement determined yet, and what is blocking each?',
  dict(events=open_issue), '事件清单及原因', 'event ids and reasons')


def main():
    assert len(QUESTIONS) == 50 and len({x['id'] for x in QUESTIONS}) == 50
    meta = dict(schema_version='1.0', set_id='energy-business-scenarios-v1', business_date=TODAY, prd='docs/PRD.md')
    dump = lambda data: yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)
    questions = [{k: v for k, v in x.items() if k != 'expected'} for x in QUESTIONS]
    answers = [dict(id=x['id'], question=x['question'], expected=x['expected']) for x in sorted(QUESTIONS, key=lambda x: x['id'])]
    questions.sort(key=lambda x: x['id'])
    (HERE / 'question-set-v1.yaml').write_text(dump(dict(meta, audience='evaluated_agent', answer_set_access='forbidden', questions=questions)), encoding='utf-8')
    (HERE / 'answer-set-v1.yaml').write_text(dump(dict(meta, generation_method='independent CSV oracle (oracle.py + energy_calc.py)', answers=answers)), encoding='utf-8')
    print(len(QUESTIONS), Counter(x['difficulty'] for x in QUESTIONS), Counter(x['role'] for x in QUESTIONS), Counter(x['scenario'] for x in QUESTIONS))


if __name__ == '__main__':
    main()
