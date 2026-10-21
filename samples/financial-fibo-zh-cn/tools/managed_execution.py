"""Bounded and complete BKN source loading through the official SDK only."""
import json
from datetime import date

BATCH_PORTFOLIOS = 20
BATCH_OBSERVATIONS = 12
BATCH_OUTPUT_BYTES = 3 * 1024 * 1024

def fetch_rows(query, kn_id, table, primary_key, field, values):
    if not values: return []
    values=sorted(set(values))
    if len(values)>1000:
        result=[]
        for offset in range(0,len(values),1000):result.extend(fetch_rows(query,kn_id,table,primary_key,field,values[offset:offset+1000]))
        if len({r[primary_key] for r in result})!=len(result):raise ValueError('DUPLICATE_BATCH_KEY:'+table)
        return sorted(result,key=lambda r:str(r[primary_key]))
    # SDK-supported IN uses one predicate, rather than one OR leaf per ID.
    condition={'field':field,'operation':'==' if len(values)==1 else 'in','value':values[0] if len(values)==1 else values,'value_from':'const'}
    result=[];seen=set();total=None;offset=0
    for _ in range(200):
        payload=query(kn_id,table,condition=condition,limit=10000,offset=offset,sort=[{'field':primary_key,'direction':'asc'}])
        if not isinstance(payload,dict) or not isinstance(payload.get('datas'),list):raise ValueError('INVALID_QUERY_PAYLOAD:'+table)
        if payload.get('partial') or payload.get('partial_reasons'):raise ValueError('PARTIAL_QUERY:'+table)
        batch=payload['datas']
        if offset==0:total=payload.get('total_count')
        for row in batch:
            k=row.get(primary_key)
            if not k or k in seen:raise ValueError('DUPLICATE_PAGE_KEY:'+table)
            seen.add(k);result.append(row)
        offset+=len(batch)
        if total is not None and offset>int(total):raise ValueError('SOURCE_COUNT_CHANGED:'+table)
        if not batch or len(batch)<10000:
            if total is not None and offset!=int(total):raise ValueError('TRUNCATED_SOURCE:'+table)
            return result
        if total is not None and offset==int(total):return result
    raise ValueError('SOURCE_PAGE_LIMIT:'+table)

def load_sources(query, kn_id, contract, scope, operation=None):
    tables={t:[] for t in contract['object_types']}
    def read(table,field,values):
        tables[table]=fetch_rows(query,kn_id,table,contract['object_types'][table]['primary_key'],field,values);return tables[table]
    ids=scope['portfolio_ids']
    if not isinstance(ids,list) or not ids or len(ids)>200:raise ValueError('PORTFOLIO_SCOPE_1_TO_200_REQUIRED')
    read('portfolios','portfolio_id',ids)
    accounts=read('accounts','portfolio_id',ids);aids=[r['account_id'] for r in accounts]
    opens=read('opening_positions','account_id',aids)
    orders=read('trade_orders','account_id',aids)
    trades=read('securities_transactions','order_id',[r['order_id'] for r in orders])
    instructions=read('settlement_instructions','trade_id',[r['trade_id'] for r in trades])
    read('settlement_events','instruction_id',[r['instruction_id'] for r in instructions])
    instruments=read('financial_instruments','instrument_id',[r['instrument_id'] for r in opens+orders])
    if operation=='settlement_asof':return tables
    positions=read('positions','opening_id',[r['opening_id'] for r in opens])
    read('valuation_snapshots','position_id',[r['position_id'] for r in positions])
    read('market_prices','instrument_id',[r['instrument_id'] for r in instruments])
    read('fx_rates','from_currency',[r['currency'] for r in instruments])
    if operation=='valuation_asof':return tables
    read('mandate_limits','portfolio_id',ids)
    read('issuer_exposures','portfolio_id',ids)
    read('counterparty_exposures','portfolio_id',ids)
    return tables

def run_request(query, kn_id, contract, operation, scope, execute, additional_observations=None):
    """Keep scalar calls compatible; reuse one source pool for bounded dates.

    Additional observations use JSON object strings containing exactly
    as_of_date, knowledge_date and view_kind; dicts remain SDK-compatible.
    The source loader is date/view independent for a fixed portfolio set.
    Each kernel invocation copies/indexes source facts and keeps its own scope,
    evidence and issues. Nothing is cached across requests or source changes.
    """
    if additional_observations is not None and not isinstance(additional_observations,list):
        raise ValueError('ADDITIONAL_OBSERVATIONS_MUST_BE_ARRAY')
    if not additional_observations:
        tables=load_sources(query,kn_id,contract,scope,operation)
        result=execute(operation,tables,contract,scope)
        result['data_source']={'knowledge_network_id':kn_id,'loaded_counts':{t:len(v) for t,v in tables.items() if v}}
        return result
    ids=scope.get('portfolio_ids')
    if not isinstance(ids,list) or not 1<=len(ids)<=BATCH_PORTFOLIOS or any(not isinstance(v,str) or not v for v in ids) or len(set(ids))!=len(ids):
        raise ValueError('BATCH_REQUIRES_1_TO_20_UNIQUE_PORTFOLIOS')
    if len(additional_observations)>=BATCH_OBSERVATIONS:
        raise ValueError('AT_MOST_11_ADDITIONAL_OBSERVATIONS')
    keys=('as_of_date','knowledge_date','view_kind')
    observations=[{k:scope[k] for k in keys}]+additional_observations
    scopes=[];seen=set()
    for item in observations:
        if isinstance(item,str):
            # Keep object pairs until duplicate wire keys have been rejected.
            item=json.loads(item,object_pairs_hook=tuple)
            if not isinstance(item,tuple):raise ValueError('EXACT_OBSERVATION_FIELDS_REQUIRED')
            if len({k for k,v in item})!=len(item):raise ValueError('DUPLICATE_OBSERVATION_FIELDS')
            item=dict(item)
        if not isinstance(item,dict) or set(item)!=set(keys):raise ValueError('EXACT_OBSERVATION_FIELDS_REQUIRED')
        for key in ('as_of_date','knowledge_date'):
            value=item[key]
            if not isinstance(value,str) or len(value)!=10 or date.fromisoformat(value).isoformat()!=value:raise ValueError('OBSERVATION_DATE_ONLY_REQUIRED')
        if item['view_kind'] not in ('actual','planned'):raise ValueError('OBSERVATION_VIEW_MUST_BE_ACTUAL_OR_PLANNED')
        identity=(item['as_of_date'],item['knowledge_date'],item['view_kind'])
        if identity in seen:raise ValueError('DUPLICATE_OBSERVATION')
        seen.add(identity);scopes.append(dict(item,portfolio_ids=list(ids)))
    tables=load_sources(query,kn_id,contract,scopes[0],operation)
    origin={'knowledge_network_id':kn_id,'loaded_counts':{t:len(v) for t,v in tables.items() if v}}
    response={'schema_version':1,'capability':operation,'mode':'observations','source_loads':1,'observations':[]}
    size=len(json.dumps(response,ensure_ascii=False,separators=(',',':')).encode())
    for current in scopes:
        result=execute(operation,tables,contract,current)
        result['data_source']={'knowledge_network_id':origin['knowledge_network_id'],'loaded_counts':dict(origin['loaded_counts'])}
        size+=len(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())+int(bool(response['observations']))
        if size>BATCH_OUTPUT_BYTES:raise ValueError('BATCH_OUTPUT_EXCEEDED_REDUCE_PORTFOLIOS_OR_OBSERVATIONS')
        response['observations'].append(result)
    return response
