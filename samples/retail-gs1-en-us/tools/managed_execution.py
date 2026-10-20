"""Bounded official SDK source loader, no files or hidden evaluation data."""
def load_sources(query,kn_id,contract,scope,operation=None):
    tables={t:[] for t in contract['object_types']}
    for table,spec in contract['object_types'].items():
        if table in ('inventory_snapshots','recall_snapshots'):continue
        pk=spec['primary_key'];seen=set();offset=0
        for _ in range(20):
            payload=query(kn_id=kn_id,ot_id=table,limit=1000,offset=offset,sort=[{'field':pk,'direction':'asc'}])
            if not isinstance(payload,dict) or not isinstance(payload.get('datas'),list):raise ValueError('INVALID_SOURCE:'+table)
            if payload.get('partial') or payload.get('partial_reasons'):raise ValueError('PARTIAL_SOURCE:'+table)
            batch=payload['datas']
            for row in batch:
                if not row.get(pk) or row[pk] in seen:raise ValueError('DUPLICATE_SOURCE_KEY:'+table)
                seen.add(row[pk]);tables[table].append(row)
            offset+=len(batch)
            total=payload.get('total_count')
            if len(batch)<1000 or total is not None and offset==int(total):
                if total is not None and offset!=int(total):raise ValueError('SOURCE_COUNT_MISMATCH:'+table)
                break
        else:raise ValueError('SOURCE_BOUND_EXCEEDED:'+table)
    return tables

def run_request(query,kn_id,contract,operation,scope,execute):
    import json
    tables=load_sources(query,kn_id,contract,scope,operation)
    result=execute(operation,tables,contract,scope)
    result['data_source']={'knowledge_network_id':kn_id,'loaded_counts':{t:len(v) for t,v in tables.items() if v}}
    if len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode('utf-8'))>1024*1024:raise ValueError('OUTPUT_BOUND_EXCEEDED_REDUCE_SCOPE')
    return result
