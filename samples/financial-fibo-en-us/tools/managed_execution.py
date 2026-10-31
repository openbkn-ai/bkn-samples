"""Bounded and complete BKN source loading through the official SDK only."""

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

def run_request(query, kn_id, contract, operation, scope, execute):
    """Load the facts for the requested portfolios and recompute one dated scope."""
    tables=load_sources(query,kn_id,contract,scope,operation)
    result=execute(operation,tables,contract,scope)
    result['data_source']={'knowledge_network_id':kn_id,'loaded_counts':{t:len(v) for t,v in tables.items() if v}}
    return result
