"""Strict business-row comparator. No question-specific answer exceptions."""
import argparse, json, re
from decimal import Decimal, InvalidOperation
from pathlib import Path

NUMBER_FIELDS=set('quantity pack_multiplier min_shelf_days priority event_sequence parent_quantity child_quantity return_overlap_quantity on_hand in_transit quarantined recall_blocked reserved available sold returned controlled_quantity controllable_quantity pending_control_quantity coverage_ratio requested_quantity allocated_quantity shortage_quantity demand_quantity eligible_supply_quantity recommended_quantity base_quantity product_count physical_row_count payload_variant_count recorded_available reconstructed_available recorded_ratio reconstructed_ratio difference'.split())
DATE_FIELDS=set('produced_date expiry_date event_date recorded_date inspection_date known_date effective_from effective_to order_date due_date demand_date announced_date effective_date as_of_date knowledge_date'.split())
MIDNIGHT=re.compile(r'^(\d{4}-\d{2}-\d{2})T00:00:00(?:\.0+)?(?:Z|[+-]\d{2}:\d{2})$')

def canonical(value,field=None):
    if value is None:return ('null',)
    if isinstance(value,bool):return ('boolean',value)
    if field in NUMBER_FIELDS:
        if not isinstance(value,(str,int,float)):raise ValueError(f'{field}: quantity must be decimal')
        try:n=Decimal(str(value))
        except InvalidOperation:raise ValueError(f'{field}: invalid decimal')
        if not n.is_finite():raise ValueError(f'{field}: non-finite decimal')
        return ('number',str(n.normalize()))
    if field in DATE_FIELDS:
        if not isinstance(value,str):raise ValueError(f'{field}: date must be string')
        match=MIDNIGHT.fullmatch(value)
        return ('date',match.group(1) if match else value)
    if isinstance(value,dict):return ('object',tuple((k,canonical(v,k)) for k,v in sorted(value.items())))
    if isinstance(value,list):
        if field=='allocations':
            if any(not isinstance(r,dict) or set(r)!=set(('lot_id','quantity')) for r in value):raise ValueError('allocations require lot_id and quantity only')
            if len({r['lot_id'] for r in value})!=len(value):raise ValueError('duplicate allocation lot_id')
            return ('list',tuple(sorted(canonical(r) for r in value)))
        if field in ('affected_lot_ids','affected_order_ids'):
            if any(not isinstance(v,str) for v in value):raise ValueError(f'{field}: string IDs required')
            if len(value)!=len(set(value)):raise ValueError(f'{field}: duplicate identifiers')
            return ('identifiers',tuple(sorted(value)))
        return ('list',tuple(canonical(x) for x in value))
    if not isinstance(value,str):raise ValueError(f'{field}: string required')
    return ('string',value)

def unpack(actual):
    if not isinstance(actual,dict):raise ValueError('answer must be JSON object')
    if 'rows' in actual:
        if not isinstance(actual['rows'],list):raise ValueError('rows must be array')
        return actual['rows']
    if set(('columns','data'))<=set(actual):
        columns=actual['columns'];data=actual['data']
        if not isinstance(columns,list) or len(set(columns))!=len(columns) or not all(isinstance(c,str) for c in columns):raise ValueError('unique string columns required')
        if not isinstance(data,list) or any(not isinstance(r,list) or len(r)!=len(columns) for r in data):raise ValueError('complete compact rows required')
        return [dict(zip(columns,r)) for r in data]
    raise ValueError('rows or columns/data required')

def sort_key(row,fields):
    """Contract-declared ascending order, with numerical rather than lexical quantities."""
    result=[]
    for field in fields:
        value=row[field]
        if value is None:result.append((0,''));continue
        if field in NUMBER_FIELDS:
            if isinstance(value,bool):raise ValueError('boolean is not a numeric sort value')
            decimal=Decimal(str(value))
            if not decimal.is_finite():raise ValueError('non-finite sort value')
            result.append((1,decimal))
        elif field in DATE_FIELDS:
            match=MIDNIGHT.fullmatch(value);result.append((1,match.group(1) if match else value))
        else:result.append((1,str(value)))
    return tuple(result)

def grade(actual,expected,contract=None):
    """Return a structured result. Decimal exact; no null/zero or missing equivalence."""
    try:
        rows=unpack(actual)
        if isinstance(expected,dict):expected=expected['rows']
        if contract:
            item=contract['properties']['rows']['items'];required=set(item['required'])
        elif expected:required=set(expected[0])
        else:required=None
        for index,row in enumerate(rows):
            if not isinstance(row,dict):raise ValueError(f'row{index}: object required')
            if required is not None and set(row)!=required:raise ValueError(f'row{index}: missing/extra fields '+str(sorted(set(row)^required)))
        if len(rows)!=len(expected):return {'passed':False,'reason':'row_count','actual_count':len(rows),'expected_count':len(expected)}
        ordered=contract.get('properties',{}).get('rows',{}).get('x-order-by',[]) if contract else []
        if ordered:
            keys=[sort_key(row,ordered) for row in rows]
            if keys!=sorted(keys):return {'passed':False,'reason':'required_row_order','order_by':ordered}
            actual_canonical=[canonical(r) for r in rows]
            expected_canonical=[canonical(r) for r in expected]
        else:
            actual_canonical=sorted(canonical(r) for r in rows)
            expected_canonical=sorted(canonical(r) for r in expected)
        if actual_canonical!=expected_canonical:return {'passed':False,'reason':'business_value_mismatch','row_count':len(rows)}
        return {'passed':True,'reason':'exact_business_rows','row_count':len(rows)}
    except (ValueError,TypeError,KeyError) as error:return {'passed':False,'reason':'contract_error','detail':str(error)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--sample',required=True,type=Path);p.add_argument('--results',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise SystemExit('Refusing to overwrite prior score')
    questions=json.loads((a.sample/'bkn-eval/questions.json').read_text());results=[]
    # Require every fixed bank result before opening any reference answers.
    raw={q['id']:(a.results/(q['id']+'.json')).read_text() for q in questions}
    records={qid:json.loads(value) for qid,value in raw.items()}
    if any(r.get('status') not in ('answered','failed') for r in records.values()):raise SystemExit('All100 terminal required')
    expected=json.loads((a.sample/'bkn-eval/expected-results.json').read_text())
    for q in questions:
        r=records[q['id']]
        g={'passed':False,'reason':'terminal_failed'}
        if r['status']=='answered':g=grade(r.get('final',r.get('answer')),expected[q['id']],q['output_contract'])
        results.append({'id':q['id'],'scenario_id':q['scenario_id'],'difficulty':q['difficulty'],**g})
    report={'fixed_denominator':100,'passed':sum(r['passed'] for r in results),'results':results,'method':'first terminal per question; strict exact business rows; capture status separate'}
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'fixed_denominator':100}))
if __name__=='__main__':main()
