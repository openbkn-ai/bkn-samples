"""Project shipped calculation results onto recovered historical question contracts."""
from decimal import Decimal


def operation(fields):
    if any(k in fields for k in ('delivery_ratio','verified_kwh','committed_kwh','revenue_cny','cost_cny','net_cny','recorded_revenue_cny','recomputed_delivery_ratio','status_code')):
        return 'settlement_assessment'
    if any(k in fields for k in ('committed_kw','new_kw','total_kw','allocated_kw')):
        return 'dispatch_plan'
    return 'flexibility_assessment'


def project(execute,tables,contract,question,scope=None):
    scope=scope or question['scope'];fields=question['output_contract']['fields']
    op=operation(fields);result=execute(op,tables,contract,scope)
    if 'snapshot_id' in fields:
        power='recorded_eligible_kw' in fields
        table='capacity_snapshots' if power else 'settlement_snapshots'
        prop='eligible_kw' if power else 'delivery_ratio';kind='kw' if power else 'ratio'
        actual={r['event_id']:r.get(prop) for r in result['rows']};rows=[]
        for source in tables[table]:
            if source['event_id'] not in scope['event_ids'] or source['as_of_date']!=scope['as_of_date'] or source['knowledge_date']!=scope['knowledge_date']:continue
            recorded=source[prop] or None;computed=actual.get(source['event_id'])
            delta=None if recorded is None or computed is None else format((Decimal(computed)-Decimal(recorded)).quantize(Decimal('.000001')),'f')
            rows.append({'event_id':source['event_id'],'snapshot_id':source['snapshot_id'],'recorded_'+prop:recorded,'recomputed_'+prop:computed,'difference_'+kind:delta})
    elif 'customer_id' in fields:
        devices={r['device_id']:r for r in tables['devices']};sites={r['site_id']:r for r in tables['sites']};rows=[]
        for r in result['device_rows']:
            device=devices[r['device_id']];site=sites[device['site_id']]
            meters=[m for m in tables['meters'] if m['device_id']==r['device_id'] and m.get('known_date','')<=scope['knowledge_date']]
            rows.append({**r,'customer_id':site['customer_id'],'meter_ids':sorted(m['meter_id'] for m in meters),'meter_units':sorted({m['unit_code'] for m in meters}),'device_type_code':device['device_type_code']})
    elif 'allocated_kw' in fields:rows=result['allocation_rows']
    elif 'device_id' in fields:rows=result['device_rows']
    else:rows=result['rows']
    selected=[{k:r.get(k) for k in fields} for r in rows if all(r.get(k)==v for k,v in question['output_contract'].get('filter',{}).items())]
    return selected,result
