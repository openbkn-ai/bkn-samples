"""Deterministic, read-only synthetic demand-response calculations."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZERO = Decimal('0')
OPS = {'flexibility_assessment', 'dispatch_plan', 'settlement_assessment'}


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result >= 0 else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def fmt(value, money=False):
    return None if value is None else format(value.quantize(Decimal('.01' if money else '.000001'), rounding=ROUND_HALF_UP), 'f')


def validate(operation, scope):
    if operation not in OPS or not isinstance(scope, dict):
        raise ValueError('Invalid operation or scope')
    ids = scope.get('event_ids')
    if not isinstance(ids, list) or not 1 <= len(ids) <= 20 or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('event_ids must contain 1..20 distinct nonempty strings')
    for key in ('as_of_date', 'knowledge_date'):
        value = scope.get(key)
        try:
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(key + ' must be YYYY-MM-DD') from None


class View:
    def __init__(self, tables, contract, scope):
        self.tables, self.contract, self.scope = tables, contract, scope
        self.evidence = defaultdict(set)
        self.issues = []
        self.partial = False
        self.trace = []

    def rows(self, table):
        return [r for r in self.tables.get(table, []) if not r.get('known_date') or r['known_date'] <= self.scope['knowledge_date']]

    def use(self, table, rows):
        key = self.contract['object_types'][table]['primary_key']
        ids = [r[key] for r in rows if key in r]
        self.evidence[table].update(ids)
        self.trace.extend((table, item) for item in ids)
        return ids

    def issue(self, code, events, ids=(), partial=True):
        item = {'code': code, 'source_ids': sorted(set(ids)), 'event_ids': sorted(set(events))}
        if item not in self.issues:
            self.issues.append(item)
        self.partial |= partial

    def latest(self, table, filters, events):
        rows = [r for r in self.rows(table) if all(r.get(k) == v for k, v in filters.items())]
        if not rows:
            return None
        try:
            rev = max(int(r.get('revision', 0)) for r in rows)
            selected = [r for r in rows if int(r.get('revision', 0)) == rev]
        except (ValueError, TypeError):
            self.issue('invalid_revision', events, self.use(table, rows))
            return None
        ids = self.use(table, selected)
        pk = self.contract['object_types'][table]['primary_key']
        payloads = {tuple(sorted((k, v) for k, v in r.items() if k not in {pk, 'known_date'} and k not in {'name', 'quality', 'status', 'reason'})) for r in selected}
        if len(payloads) > 1:
            self.issue('version_conflict', events, ids)
            return None
        return sorted(selected, key=lambda r: r.get(pk, ''))[0]

    def asset(self, table, key, value, events):
        matches = [r for r in self.rows(table) if r.get(key) == value]
        self.use(table, matches)
        if len(matches) != 1:
            self.issue('missing_or_duplicate_' + table, events, self.use(table, matches))
            return None
        return matches[0]

    def events(self):
        return [r for r in self.rows('response_events') if r.get('announced_date', '') <= self.scope['as_of_date']]

    def hours(self, event):
        hours = number(event.get('duration_hours'))
        canonical = number(self.contract['block_durations'].get(event.get('block_code')))
        if hours is None or hours != canonical or hours == 0:
            self.issue('invalid_block_duration', [event['event_id']], self.use('response_events', [event]))
            return None
        return hours

    def offer(self, event, device):
        offer = self.latest('flexibility_offers', {'event_id': event['event_id'], 'device_id': device}, [event['event_id']])
        if offer and (offer.get('status_code') != 'active' or not offer.get('valid_from', '') <= event['response_date'] <= offer.get('valid_to', '')):
            return None
        return offer

    def eligible(self, event):
        eid = event['event_id']
        devices = sorted({r['device_id'] for r in self.rows('flexibility_offers') if r.get('event_id') == eid})
        result = []
        for did in devices:
            trace_start = len(self.trace)
            offer = self.latest('flexibility_offers', {'event_id': eid, 'device_id': did}, [eid])
            row = {'event_id': eid, 'device_id': did, 'site_id': None, '_kw': None, '_cost': None, 'reason_codes': [], '_trace_start': trace_start}
            result.append(row)
            known_devices = [d for d in self.rows('devices') if d.get('device_id') == did]
            if len(known_devices) == 1:
                row['site_id'] = known_devices[0].get('site_id')
                self.use('devices', known_devices)
            if offer is None:
                row['reason_codes'] = ['version_conflict']
                continue
            if offer.get('status_code') != 'active' or not offer.get('valid_from', '') <= event['response_date'] <= offer.get('valid_to', ''):
                row.update(_kw=ZERO, reason_codes=['offer_inactive_or_expired'])
                continue
            device = self.asset('devices', 'device_id', did, [eid])
            if not device:
                row['reason_codes'] = ['missing_device']
                continue
            row['site_id'] = device['site_id']
            constraints = [r for r in self.rows('device_constraints') if r.get('device_id') == did and r.get('block_code') in {event['block_code'], '*', 'all'} and r.get('effective_from', '') <= event['response_date'] <= r.get('effective_to', '')]
            self.use('device_constraints', constraints)
            if device.get('status_code') != 'active' or any(r.get('constraint_type_code') in {'block', 'blocked', 'opt_out', 'maintenance'} for r in constraints):
                row.update(_kw=ZERO, reason_codes=['device_unavailable' if device.get('status_code') != 'active' else 'constraint_block'])
                continue
            forecast = self.latest('load_forecasts', {'device_id': did, 'response_date': event['response_date'], 'block_code': event['block_code']}, [eid])
            baseline = self.latest('baselines', {'device_id': did, 'response_date': event['response_date'], 'block_code': event['block_code']}, [eid])
            values = [number(offer.get('offered_kw')), number(device.get('max_reduction_kw')), number(device.get('min_service_kw')), number(forecast.get('forecast_kw')) if forecast else None, number(baseline.get('baseline_kw')) if baseline else None]
            caps = [number(r.get('cap_kw')) for r in constraints if r.get('constraint_type_code') == 'cap']
            if any(v is None for v in values + caps) or not forecast or forecast.get('quality_code') != 'valid' or not baseline or baseline.get('quality_code') != 'approved':
                self.issue('unknown_eligibility', [eid], [offer['offer_id'], did])
                row['reason_codes'] = ['missing_invalid_or_conflicting_capacity']
            else:
                offered, maximum, minimum, predicted, base = values
                row['_kw'] = min([offered, maximum, max(ZERO, min(predicted, base) - minimum)] + caps)
                row['reason_codes'] = ['eligible']
            row['_cost'] = number(offer.get('cost_cny_kwh'))
            row['status_code'] = 'unknown' if row['_kw'] is None else 'assessed'
        for index, row in enumerate(result):
            stop = result[index + 1]['_trace_start'] if index + 1 < len(result) else len(self.trace)
            evidence = defaultdict(set)
            for table, source_id in self.trace[row['_trace_start']:stop]:
                evidence[table].add(source_id)
            row['evidence'] = {table: sorted(ids) for table, ids in sorted(evidence.items())}
        for row in result:
            row.pop('_trace_start')
        return result


def assessment(v, events):
    rows, details = [], []
    for e in events:
        eid = e['event_id']
        v.use('response_events', [e])
        if e.get('status_code') != 'active':
            rows.append({'event_id': eid, 'status_code': 'cancelled', 'eligible_kw': None, 'target_kw': fmt(number(e.get('target_kw'))), 'shortfall_kw': None})
            continue
        ds = v.eligible(e)
        details.extend(ds)
        sites = defaultdict(list)
        for d in ds:
            if d['_kw'] != ZERO:
                sites[d['site_id']].append(d['_kw'])
        total = ZERO
        for sid, capacities in sites.items():
            site = v.asset('sites', 'site_id', sid, [eid])
            cap = number(site.get('response_cap_kw')) if site else None
            if cap is None or any(x is None for x in capacities):
                total = None
                v.issue('unknown_site_capacity', [eid], [sid] if sid else [])
                continue
            if total is not None:
                total += min(sum(capacities, ZERO), cap)
        target = number(e.get('target_kw'))
        if target is None:
            v.issue('invalid_target', [eid], [eid])
        rows.append({'event_id': eid, 'status_code': 'unknown' if total is None else 'assessed', 'eligible_kw': fmt(total), 'target_kw': fmt(target), 'shortfall_kw': fmt(max(ZERO, target-total)) if target is not None and total is not None else None})
    for d in details:
        d['eligible_kw'] = fmt(d.pop('_kw'))
        d.pop('_cost')
        d.setdefault('status_code', 'unknown' if d['eligible_kw'] is None else 'assessed')
    return rows, details


def committed(v, events):
    ids = {e['event_id'] for e in events}
    rows = [r for r in v.rows('dispatch_allocations') if r.get('event_id') in ids and r.get('status_code') == 'committed']
    v.use('dispatch_allocations', rows)
    return rows


def planning(v, pool):
    rows, allocations = [], []
    blocks = defaultdict(list)
    for e in pool:
        if e.get('status_code') == 'active':
            blocks[(e['response_date'], e['block_code'])].append(e)
    for block_events in blocks.values():
        event_ids = [e['event_id'] for e in block_events]
        v.use('response_events', block_events)
        eligible = {e['event_id']: v.eligible(e) for e in block_events}
        reserved = committed(v, block_events)
        device_used, site_used, event_used, own = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
        seen = set()
        unknown_commitment = set()
        bad = any(d['_kw'] is None for ds in eligible.values() for d in ds)
        for a in reserved:
            eid, did = a['event_id'], a['device_id']
            amount = number(a.get('committed_kw'))
            d = v.asset('devices', 'device_id', did, event_ids)
            match = next((x for x in eligible[eid] if x['device_id'] == did), None)
            invalid = amount is None or not d or (eid, did) in seen or match is None or match['_kw'] is None or (amount is not None and match['_kw'] is not None and amount > match['_kw'])
            seen.add((eid, did))
            if invalid:
                bad = True
                v.issue('invalid_commitment', event_ids, [a['allocation_id']])
            if amount is None:
                unknown_commitment.add(eid)
            else:
                event_used[eid] += amount
            if amount is not None and d:
                device_used[did] += amount
                site_used[d['site_id']] += amount
                own[(eid, did)] += amount
            allocations.append({'event_id': eid, 'device_id': did, 'allocation_id': a['allocation_id'], 'site_id': d['site_id'] if d else None, 'kind': 'existing', 'allocated_kw': fmt(amount), 'cost_cny_kwh': fmt(match['_cost']) if match else None, 'status_code': 'committed'})
        for did, amount in device_used.items():
            d = v.asset('devices', 'device_id', did, event_ids)
            cap = number(d.get('max_reduction_kw')) if d else None
            if cap is None or amount > cap:
                bad = True
                v.issue('device_over_reserved', event_ids, [did])
        site_remaining = {}
        for sid in {d['site_id'] for ds in eligible.values() for d in ds if d['_kw'] != ZERO} | set(site_used):
            s = v.asset('sites', 'site_id', sid, event_ids)
            cap = number(s.get('response_cap_kw')) if s else None
            if cap is None or site_used[sid] > cap:
                bad = True
                v.issue('site_over_reserved_or_unknown', event_ids, [sid] if sid else [])
            site_remaining[sid] = cap-site_used[sid] if cap is not None else ZERO
        priorities = {}
        for e in block_events:
            try:
                priority = int(e.get('priority', ''))
                if str(priority) != str(e.get('priority')) or priority < 0:
                    raise ValueError()
                priorities[e['event_id']] = priority
            except (ValueError, TypeError):
                priorities[e['event_id']] = 0
                bad = True
                v.issue('invalid_priority', event_ids, [e['event_id']])
            if number(e.get('target_kw')) is None or v.hours(e) is None:
                bad = True
            if any(d['_cost'] is None and d['_kw'] != ZERO for d in eligible[e['event_id']]):
                bad = True
                v.issue('missing_offer_cost', event_ids, [e['event_id']])
        if bad:
            v.issue('block_plan_unknown', event_ids)
        for e in sorted(block_events, key=lambda x: (priorities[x['event_id']], x['event_id'])):
            eid = e['event_id']
            target, hours = number(e.get('target_kw')), v.hours(e)
            new, cost = ZERO, ZERO
            if not bad:
                for d in sorted(eligible[eid], key=lambda x: (x['_cost'] if x['_cost'] is not None else ZERO, x['site_id'] or '', x['device_id'])):
                    did, sid = d['device_id'], d['site_id']
                    if d['_kw'] == ZERO:
                        continue
                    device = v.asset('devices', 'device_id', did, [eid])
                    amount = max(ZERO, min(d['_kw']-own[(eid, did)], number(device['max_reduction_kw'])-device_used[did], site_remaining[sid], target-event_used[eid]-new))
                    if amount:
                        new += amount
                        device_used[did] += amount
                        site_remaining[sid] -= amount
                        allocations.append({'event_id': eid, 'device_id': did, 'allocation_id': None, 'site_id': sid, 'kind': 'new', 'allocated_kw': fmt(amount), 'cost_cny_kwh': fmt(d['_cost']), 'status_code': 'proposed'})
                    cost += (own[(eid, did)] + amount)*hours*d['_cost']
            rows.append({'event_id': eid, 'status_code': 'unknown' if bad else 'planned', 'target_kw': fmt(target), 'committed_kw': None if eid in unknown_commitment else fmt(event_used[eid]), 'new_kw': None if bad else fmt(new), 'total_kw': None if bad else fmt(event_used[eid]+new), 'shortfall_kw': None if bad else fmt(max(ZERO, target-event_used[eid]-new)), 'estimated_cost_cny': None if bad else fmt(cost, True)})
    return rows, allocations


def settling(v, pool):
    active = [e for e in pool if e.get('status_code') == 'active' and e['response_date'] <= v.scope['as_of_date']]
    events = {e['event_id']: e for e in active}
    amounts, delivered, costs = defaultdict(Decimal), defaultdict(Decimal), defaultdict(Decimal)
    unknown_delivery, unknown_cost, unknown_commitment = set(), set(), set()
    groups = defaultdict(list)
    seen = set()
    for a in committed(v, active):
        eid, did, aid = a['event_id'], a['device_id'], a['allocation_id']
        e = events[eid]
        kw, hours = number(a.get('committed_kw')), v.hours(e)
        if kw is None or hours is None or (eid, did) in seen:
            unknown_commitment.add(eid)
            unknown_delivery.add(eid)
            unknown_cost.add(eid)
            v.issue('invalid_commitment', [eid], [aid])
            continue
        seen.add((eid, did))
        energy = kw*hours
        amounts[eid] += energy
        if energy == ZERO:
            continue
        receipt = v.latest('execution_logs', {'allocation_id': aid}, [eid])
        if not receipt or receipt.get('response_date') != e['response_date'] or receipt.get('status_code') not in {'completed', 'failed', 'declined'}:
            unknown_delivery.add(eid)
            unknown_cost.add(eid)
            v.issue('unresolved_execution', [eid], [aid])
            continue
        if receipt['status_code'] != 'completed':
            v.issue('execution_' + receipt['status_code'], [eid], [aid, receipt['execution_id']], partial=False)
            continue
        meters = [r for r in v.rows('meters') if r.get('device_id') == did]
        v.use('meters', meters)
        if len(meters) != 1 or meters[0].get('unit_code') not in {'kWh', 'kwh'} or sum(r.get('meter_id') == meters[0]['meter_id'] for r in v.rows('meters')) != 1:
            unknown_delivery.add(eid)
            unknown_cost.add(eid)
            v.issue('missing_or_invalid_device_meter', [eid], [did])
            continue
        groups[(meters[0]['meter_id'], e['response_date'], e['block_code'])].append((a, energy, hours))
    for (mid, day, block), members in groups.items():
        eids = [a['event_id'] for a, _, _ in members]
        did = members[0][0]['device_id']
        baseline = v.latest('baselines', {'device_id': did, 'response_date': day, 'block_code': block}, eids)
        reading = v.latest('meter_readings', {'meter_id': mid, 'response_date': day, 'block_code': block}, eids)
        base = number(baseline.get('baseline_kw')) if baseline else None
        actual = number(reading.get('actual_kwh')) if reading else None
        hours = members[0][2]
        if base is None or actual is None or not baseline or baseline.get('quality_code') != 'approved' or not reading or reading.get('quality_code') != 'valid' or number(reading.get('duration_hours')) != hours:
            unknown_delivery.update(eids)
            unknown_cost.update(eids)
            v.issue('unknown_shared_measurement', eids, [a['allocation_id'] for a, _, _ in members])
            continue
        total = sum((energy for _, energy, _ in members), ZERO)
        observed = min(max(ZERO, base*hours-actual), total)
        for a, energy, _ in members:
            eid = a['event_id']
            share = observed*energy/total
            delivered[eid] += share
            offer = v.offer(events[eid], a['device_id'])
            price = number(offer.get('cost_cny_kwh')) if offer else None
            if price is None:
                unknown_cost.add(eid)
                v.issue('missing_offer_cost', [eid], [a['allocation_id']])
            else:
                costs[eid] += share*price
    result = []
    fields = ('committed_kwh', 'verified_kwh', 'delivery_ratio', 'revenue_cny', 'cost_cny', 'net_cny', 'recorded_revenue_cny', 'revenue_difference_cny')
    for e in pool:
        eid = e['event_id']
        v.use('response_events', [e])
        row = dict.fromkeys(fields)
        row['event_id'] = eid
        if e.get('status_code') != 'active' or e['response_date'] > v.scope['as_of_date']:
            row['status_code'] = 'cancelled' if e.get('status_code') != 'active' else 'not_due'
            result.append(row)
            continue
        verified = None if eid in unknown_delivery else delivered[eid]
        ratio = verified/amounts[eid] if verified is not None and amounts[eid] > 0 else None
        reward, threshold = number(e.get('reward_cny_kwh')), number(e.get('minimum_ratio'))
        if amounts[eid] == ZERO and eid not in unknown_delivery:
            revenue = ZERO
            if number(e.get('target_kw')) is None or number(e.get('target_kw')) > ZERO:
                v.issue('target_shortage', [eid], [eid], partial=False)
        elif verified is None or reward is None or threshold is None:
            revenue = None
            if reward is None or threshold is None:
                v.issue('invalid_settlement_terms', [eid], [eid])
        else:
            revenue = verified*reward if ratio >= threshold else ZERO
            if ratio < threshold:
                v.issue('below_payment_threshold', [eid], [eid], partial=False)
        cost = None if eid in unknown_cost else costs[eid]
        revenue_s, cost_s = fmt(revenue, True), fmt(cost, True)
        net = Decimal(revenue_s)-Decimal(cost_s) if revenue_s is not None and cost_s is not None else None
        recorded = difference = None
        ledgers = [r for r in v.rows('settlements') if r.get('event_id') == eid and r.get('status_code') == 'posted' and r.get('posted_date', '') <= v.scope['as_of_date']]
        if ledgers:
            day = max(r['posted_date'] for r in ledgers)
            latest = [r for r in ledgers if r['posted_date'] == day]
            ids = v.use('settlements', latest)
            payloads = {(r.get('revenue_cny'), r.get('cost_cny'), r.get('net_cny')) for r in latest}
            if len(payloads) != 1:
                v.issue('settlement_conflict', [eid], ids)
            else:
                recorded = number(latest[0].get('revenue_cny'))
                if recorded is None:
                    v.issue('invalid_recorded_revenue', [eid], ids)
                if recorded is not None and revenue_s is not None:
                    difference = Decimal(revenue_s)-Decimal(fmt(recorded, True))
        row.update(status_code='unknown' if verified is None or revenue is None or cost is None else 'settled', committed_kwh=fmt(amounts[eid]) if eid not in unknown_commitment else None, verified_kwh=fmt(verified), delivery_ratio=fmt(ratio), revenue_cny=revenue_s, cost_cny=cost_s, net_cny=fmt(net, True), recorded_revenue_cny=fmt(recorded, True), revenue_difference_cny=fmt(difference, True))
        result.append(row)
    return result


def execute(operation, tables, contract, scope):
    """Validate the request before inspecting tables; return JSON-safe results."""
    validate(operation, scope)
    v = View(tables, contract, scope)
    visible = v.events()
    requested = [e for e in visible if e.get('event_id') in scope['event_ids']]
    missing = set(scope['event_ids']) - {e['event_id'] for e in requested}
    blocks = {(e['response_date'], e['block_code']) for e in requested}
    pool = [e for e in visible if (e['response_date'], e['block_code']) in blocks]
    result = {'scope': {k: scope[k] for k in ('event_ids', 'as_of_date', 'knowledge_date')}, 'rows': [], 'issues': v.issues, 'evidence': {}, 'completeness': 'complete', 'units': {'power': 'kW', 'energy': 'kWh', 'duration': 'h', 'rate': 'CNY/kWh', 'money': 'CNY', 'ratio': '1'}}
    if operation == 'flexibility_assessment':
        result['rows'], result['device_rows'] = assessment(v, requested)
    elif operation == 'dispatch_plan':
        result['rows'], result['allocation_rows'] = planning(v, pool)
        for e in requested:
            if e.get('status_code') != 'active':
                result['rows'].append({'event_id': e['event_id'], 'status_code': 'cancelled', **dict.fromkeys(('target_kw', 'committed_kw', 'new_kw', 'total_kw', 'shortfall_kw', 'estimated_cost_cny'))})
    else:
        result['rows'] = settling(v, pool)
    for eid in sorted(missing):
        v.issue('event_unavailable', [eid])
        result['rows'].append({'event_id': eid, 'status_code': 'unknown'})
    result['rows'] = sorted([r for r in result['rows'] if r['event_id'] in scope['event_ids']], key=lambda r: scope['event_ids'].index(r['event_id']))
    if 'allocation_rows' in result:
        result['allocation_rows'] = [r for r in result['allocation_rows'] if r['event_id'] in scope['event_ids']]
    result['evidence'] = {k: sorted(ids) for k, ids in sorted(v.evidence.items()) if ids}
    result['issues'] = sorted(v.issues, key=lambda i: (i['code'], i['event_ids'], i['source_ids']))
    result['completeness'] = 'partial' if v.partial else 'complete'
    return result
