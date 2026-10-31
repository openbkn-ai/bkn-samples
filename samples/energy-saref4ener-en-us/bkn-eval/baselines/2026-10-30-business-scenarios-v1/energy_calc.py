"""Independent demand-response calculations written from the business contract; they never import the sample engine."""
import csv
from collections import defaultdict
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

PAYLOAD_SKIP = {'known_date'}


class Energy:
    def __init__(self, data_dir):
        self.t = {p.stem: list(csv.DictReader(p.open(encoding='utf-8'))) for p in Path(data_dir).glob('*.csv')}
        self.devices = {r['device_id']: r for r in self.t['devices']}
        self.sites = {r['site_id']: r for r in self.t['sites']}
        self.meters = {r['device_id']: r for r in self.t['meters']}
        self.events_all = {r['event_id']: r for r in self.t['response_events']}

    # ---- visibility and versions
    def events(self, a, k):
        return {i: e for i, e in self.events_all.items() if e['announced_date'] <= a and e['known_date'] <= k}

    @staticmethod
    def payload(r, id_field):
        return tuple(sorted((key, v) for key, v in r.items() if key not in PAYLOAD_SKIP and key != id_field))

    def latest(self, table, key_fields, id_field, k):
        groups = defaultdict(list)
        for r in self.t[table]:
            if r['known_date'] <= k:
                groups[tuple(r[f] for f in key_fields)].append(r)
        out = {}
        for key, rows in groups.items():
            top = max(int(r['revision']) for r in rows)
            cand = [r for r in rows if int(r['revision']) == top]
            payloads = {self.payload(r, id_field) for r in cand}
            out[key] = ('conflict', cand) if len(payloads) > 1 else ('ok', cand[0])
        return out

    # ---- flexibility (contract function 1)
    def flexibility(self, event_id, a, k):
        ev = self.events(a, k).get(event_id)
        if ev is None:
            return None
        if ev['status_code'] == 'cancelled':
            return dict(event=ev, eligible=None, device_rows=[], status='cancelled')
        d, b = ev['response_date'], ev['block_code']
        offers = self.latest('flexibility_offers', ('event_id', 'device_id'), 'offer_id', k)
        fc = self.latest('load_forecasts', ('device_id', 'response_date', 'block_code'), 'forecast_id', k)
        bl = self.latest('baselines', ('device_id', 'response_date', 'block_code'), 'baseline_id', k)
        cons = [c for c in self.t['device_constraints'] if c['known_date'] <= k and c['effective_from'] <= d <= c['effective_to'] and c['block_code'] == b]
        rows = []
        for (eid, dev), (st, off) in sorted(offers.items()):
            if eid != event_id:
                continue
            device = self.devices[dev]
            row = dict(device_id=dev, site_id=device['site_id'], eligible=None, reasons=[])
            if st == 'conflict':
                row['reasons'].append('offer_conflict'); rows.append(row); continue
            if off['status_code'] != 'active' or not (off['valid_from'] <= d <= off['valid_to']):
                row['eligible'] = D(0); row['reasons'].append('offer_not_active'); rows.append(row); continue
            if device['status_code'] != 'active':
                row['eligible'] = D(0); row['reasons'].append('device_inactive'); rows.append(row); continue
            mine = [c for c in cons if c['device_id'] == dev]
            if any(c['constraint_type_code'] == 'block' for c in mine):
                row['eligible'] = D(0); row['reasons'].append('blocked'); rows.append(row); continue
            caps = [c['cap_kw'] for c in mine if c['constraint_type_code'] == 'cap']
            if any(c == '' for c in caps):
                row['reasons'].append('cap_missing'); rows.append(row); continue
            f, g = fc.get((dev, d, b)), bl.get((dev, d, b))
            if f is None or g is None or f[0] == 'conflict' or g[0] == 'conflict':
                row['reasons'].append('source_missing_or_conflict'); rows.append(row); continue
            if f[1]['quality_code'] != 'valid' or g[1]['quality_code'] != 'approved':
                row['reasons'].append('source_quality'); rows.append(row); continue
            vals = [D(off['offered_kw']), D(device['max_reduction_kw']),
                    max(D(0), min(D(f[1]['forecast_kw']), D(g[1]['baseline_kw'])) - D(device['min_service_kw']))] + [D(c) for c in caps]
            row['eligible'] = min(vals); rows.append(row)
        by_site = defaultdict(list)
        for r in rows:
            by_site[r['site_id']].append(r)
        total = D(0); unknown = False
        for sid, rs in by_site.items():
            if any(r['eligible'] is None for r in rs):
                unknown = True; continue
            total += min(sum((r['eligible'] for r in rs), D(0)), D(self.sites[sid]['response_cap_kw']))
        return dict(event=ev, eligible=None if unknown else total, device_rows=rows)

    # ---- settlement (contract function 3)
    def settlement(self, event_id, a, k):
        evs = self.events(a, k); ev = evs.get(event_id)
        if ev is None:
            return None
        if ev['status_code'] == 'cancelled':
            return dict(event=ev, status='cancelled')
        d, b, h = ev['response_date'], ev['block_code'], D(ev['duration_hours'])
        if d > a:
            return dict(event=ev, status='not_due')
        allocs = [r for r in self.t['dispatch_allocations'] if r['known_date'] <= k and r['status_code'] == 'committed']
        execs = self.latest('execution_logs', ('allocation_id',), 'execution_id', k)
        bl = self.latest('baselines', ('device_id', 'response_date', 'block_code'), 'baseline_id', k)
        rd = self.latest('meter_readings', ('meter_id', 'response_date', 'block_code'), 'reading_id', k)
        offers = self.latest('flexibility_offers', ('event_id', 'device_id'), 'offer_id', k)
        pool = {i for i, e in evs.items() if e['status_code'] == 'active' and e['response_date'] == d and e['block_code'] == b}
        pool_allocs = [r for r in allocs if r['event_id'] in pool]

        def receipt(alloc):
            x = execs.get((alloc['allocation_id'],))
            if x is None or x[0] == 'conflict':
                return None
            return x[1]['status_code']

        def observed(dev):
            g = bl.get((dev, d, b)); m = self.meters[dev]['meter_id']; r = rd.get((m, d, b))
            if g is None or r is None or g[0] == 'conflict' or r[0] == 'conflict':
                return None
            g, r = g[1], r[1]
            if g['quality_code'] != 'approved' or r['quality_code'] != 'valid' or D(r['duration_hours']) != h or D(r['actual_kwh']) < 0:
                return None
            return max(D(0), D(g['baseline_kw']) * h - D(r['actual_kwh']))

        mine = [r for r in pool_allocs if r['event_id'] == event_id]
        committed = sum((D(r['committed_kw']) * h for r in mine), D(0))
        verified, cost, unknown, cost_unknown = D(0), D(0), False, False
        for al in mine:
            rc = receipt(al)
            if rc is None:
                unknown = True; continue
            if rc != 'completed':
                continue
            dev = al['device_id']; obs = observed(dev)
            if obs is None:
                unknown = True; continue
            same = [r for r in pool_allocs if r['device_id'] == dev and receipt(r) == 'completed']
            tot = sum((D(r['committed_kw']) * h for r in same), D(0))
            share = min(obs, tot) * D(al['committed_kw']) * h / tot if tot > 0 else D(0)
            verified += share
            o = offers.get((event_id, dev))
            if o is None or o[0] == 'conflict' or o[1]['status_code'] != 'active' or not (o[1]['valid_from'] <= d <= o[1]['valid_to']) or D(o[1]['cost_cny_kwh']) < 0:
                cost_unknown = True
            else:
                cost += share * D(o[1]['cost_cny_kwh'])
        ratio = None if unknown or committed == 0 else verified / committed
        revenue = None if unknown else (verified * D(ev['reward_cny_kwh']) if ratio is not None and ratio >= D(ev['minimum_ratio']) else D(0))
        cost_r = None if unknown or cost_unknown else q2(cost)
        rev_r = None if revenue is None else q2(revenue)
        ledger = [s for s in self.t['settlements'] if s['event_id'] == event_id and s['status_code'] == 'posted' and s['posted_date'] <= a and s['known_date'] <= k]
        recorded = None
        if ledger:
            top = max(s['posted_date'] for s in ledger); same = {s['revenue_cny'] for s in ledger if s['posted_date'] == top}
            recorded = D(same.pop()) if len(same) == 1 else 'conflict'
        return dict(event=ev, status='settled', committed_kwh=committed, verified_kwh=None if unknown else verified, delivery_ratio=ratio,
                    revenue=rev_r, cost=cost_r, net=None if rev_r is None or cost_r is None else rev_r - cost_r, recorded=recorded)


def q2(x):
    return D(x).quantize(D('0.01'), ROUND_HALF_UP)


def q6(x):
    return None if x is None else D(x).quantize(D('0.000001'), ROUND_HALF_UP)


def dispatch(E, event_id, a, k):
    """Contract function 2: read-only proposal over the whole same-date/block pool of active events."""
    evs = E.events(a, k); ev = evs.get(event_id)
    if ev is None:
        return None
    if ev['status_code'] == 'cancelled':
        return dict(status='cancelled')
    d, b = ev['response_date'], ev['block_code']
    pool = sorted((e for e in evs.values() if e['status_code'] == 'active' and e['response_date'] == d and e['block_code'] == b),
                  key=lambda e: (int(e['priority']), e['event_id']))
    ids = {e['event_id'] for e in pool}
    allocs = [r for r in E.t['dispatch_allocations'] if r['known_date'] <= k and r['status_code'] == 'committed' and r['event_id'] in ids]
    dev_left = {i: D(r['max_reduction_kw']) for i, r in E.devices.items()}
    site_left = {i: D(r['response_cap_kw']) for i, r in E.sites.items()}
    issues = []
    seen = set()
    for r in allocs:
        kw = D(r['committed_kw'])
        if kw < 0 or (r['event_id'], r['device_id']) in seen:
            issues.append(('bad_commitment', r['allocation_id']))
        seen.add((r['event_id'], r['device_id']))
        dev_left[r['device_id']] -= kw
        site_left[E.devices[r['device_id']]['site_id']] -= kw
    for i, v in dev_left.items():
        if v < 0: issues.append(('overreserved_device', i))
    for i, v in site_left.items():
        if v < 0: issues.append(('overreserved_site', i))
    flex = {e['event_id']: E.flexibility(e['event_id'], a, k) for e in pool}
    # A commitment outside its event's current eligible limit makes the shared block plan unknown.
    for r in allocs:
        elig = {x['device_id']: x['eligible'] for x in flex[r['event_id']]['device_rows']}
        if elig.get(r['device_id']) is None or D(r['committed_kw']) > elig[r['device_id']]:
            issues.append(('commitment_outside_eligibility', r['allocation_id']))
    out = {}
    for e in pool:
        eid = e['event_id']; f = flex[eid]
        own = [r for r in allocs if r['event_id'] == eid]
        committed = sum((D(r['committed_kw']) for r in own), D(0))
        elig = {r['device_id']: r['eligible'] for r in f['device_rows']}
        unknown = any(x['eligible'] is None for x in flex.values()) or bool(issues)  # unknown capacity anywhere in the block
        residual = D(e['target_kw']) - committed
        new = []
        if not unknown:
            offers = E.latest('flexibility_offers', ('event_id', 'device_id'), 'offer_id', k)
            cands = []
            for dev, kw in elig.items():
                if kw and kw > 0:
                    cost = D(offers[(eid, dev)][1]['cost_cny_kwh'])
                    cands.append((cost, E.devices[dev]['site_id'], dev, kw))
            for cost, site, dev, kw in sorted(cands):
                if residual <= 0: break
                own_dev = sum((D(r['committed_kw']) for r in own if r['device_id'] == dev), D(0))
                take = min(kw - own_dev, dev_left[dev], site_left[site], residual)
                if take > 0:
                    new.append(dict(device_id=dev, site_id=site, kw=take, cost=cost))
                    dev_left[dev] -= take; site_left[site] -= take; residual -= take
        h = D(e['duration_hours'])
        out[eid] = dict(target=D(e['target_kw']), committed=committed, unknown=unknown,
                        new=None if unknown else sum((n['kw'] for n in new), D(0)),
                        total=None if unknown else committed + sum((n['kw'] for n in new), D(0)),
                        shortfall=None if unknown else max(D(0), residual),
                        cost=None if unknown else q2(sum((n['kw'] * h * n['cost'] for n in new), D(0))
                                                     + sum((D(r['committed_kw']) * h * D(E.latest('flexibility_offers', ('event_id', 'device_id'), 'offer_id', k)[(eid, r['device_id'])][1]['cost_cny_kwh']) for r in own), D(0))),
                        rows=new)
    return out
