"""Native read adapter for the sample v1 shortage rule; no event writes."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from fn.shortage_rule import evaluate, validate_config, require, text, MAX_EVENTS
from fn.read_complete import read_complete
from managed_execution import KN_ID, _OBJECT_TYPES, _page_rows, load_bkn_rows, execute_from_bkn_rows

TITLE = '材料覆盖不足'


def equal(field,value):return {'field':field,'operation':'==','value':value,'value_from':'const'}
def both(*conditions):return {'operation':'and','sub_conditions':list(conditions)}


def checked_response(value):
    require(isinstance(value,dict),'invalid BKN query response')
    require(value.get('status') not in {'partial','incomplete','failed','error'}
            and not any(value.get(key) for key in ['warnings','limited','truncated']),'BKN query is incomplete or carries warnings')
    return value


def implementation_digest():
    hasher=hashlib.sha256()
    model_files=['shortage_rule','material_assurance','allocation','bom','inventory','snapshot','warehouse','errors','read_complete']
    files=[*(Path(__file__).parent/'fn'/(name+'.py') for name in model_files),Path(__file__),Path(__file__).parent/'managed_execution.py']
    for path in files:
        hasher.update(path.relative_to(Path(__file__).parent).as_posix().encode());hasher.update(b'\0');hasher.update(path.read_bytes())
    return 'sha256:'+hasher.hexdigest()


def run(query_objects, query_subgraph, event_source, window_start, window_end):
    config,window=validate_config(event_source,window_start,window_end)
    def query(**kwargs):return checked_response(query_objects(**kwargs))
    def events(condition,maximum):
        return read_complete(query,{'kn_id':KN_ID,'ot_id':config['object_type_id'],'condition':condition},
                             _page_rows,page_size=min(500,maximum),max_rows=maximum)
    # Read all unprocessed verified demands up to the fixed cutoff, including
    # old occurrences verified late. Re-evaluate active shortages across windows.
    demands=events(both(equal('event_type',config['demand_event_type']),equal('status',config['verified_status']),
                        {'field':'verified_at','operation':'<','value':window['end'],'value_from':'const'}),MAX_EVENTS+1)
    active=events(both(equal('event_type',config['shortage_event_type']),
                       {'field':'status','operation':'in','value':[config['verified_status'],config['processing_status']],'value_from':'const'}),MAX_EVENTS+1)
    source_cache={}
    def source(event_id):
        if event_id not in source_cache:
            rows=events(equal('event_id',event_id),3)
            require(len(rows)<=1,'source demand identity is ambiguous')
            if rows:require(rows[0].get('event_id')==event_id,'source event query returned a different identity')
            source_cache[event_id]=rows[0] if rows else None
        return source_cache[event_id]
    def product(event):
        result=checked_response(query_subgraph(kn_id=KN_ID,response_format='json',relation_type_paths=[{
            'object_types':[{'id':config['object_type_id'],'condition':equal('event_id',event['event_id']),'limit':1},
                            {'id':_OBJECT_TYPES['product'],'condition':{'operation':'and','sub_conditions':[]},'limit':2}],
            'relation_types':[{'relation_type_id':config['product_relation_type_id']}], 'limit':2}]))
        entries=result.get('entries');require(isinstance(entries,list) and len(entries)==1,'product relation query did not return one subgraph')
        graph=checked_response(entries[0]);objects=graph.get('objects');paths=graph.get('relation_paths')
        require(isinstance(objects,dict) and isinstance(paths,list) and len(paths)==1
                and not graph.get('cursor') and not graph.get('isolated_objects'),'event must have one complete product relation')
        require(graph.get('total_count',1)==1 and graph.get('current_path_number',1)==1,'product relation is truncated or ambiguous')
        require(len(objects)==2 and all(isinstance(o,dict) for o in objects.values()),'unexpected product subgraph objects')
        starts=[(key,obj) for key,obj in objects.items() if obj.get('object_type_id')==config['object_type_id']]
        targets=[(key,obj) for key,obj in objects.items() if obj.get('object_type_id')==_OBJECT_TYPES['product']]
        require(len(starts)==len(targets)==1,'event product reference is missing or ambiguous')
        start_key,start=starts[0];target_key,target=targets[0]
        require(isinstance(start.get('properties'),dict) and start['properties'].get('event_id')==event['event_id'],'subgraph event identity differs')
        relations=paths[0].get('relations')
        require(paths[0].get('length')==1 and isinstance(relations,list) and len(relations)==1,'unexpected event product path')
        edge=relations[0]
        require(edge.get('relation_type_id')==config['product_relation_type_id']
                and {edge.get('source_object_id'),edge.get('target_object_id')}=={start_key,target_key},'product relation does not bind this event')
        require(isinstance(target.get('properties'),dict),'product properties missing')
        code=text(target['properties'].get('material_number'),'product material_number')
        identity=target.get('_instance_identity')
        require(isinstance(identity,dict) and identity.get('material_number')==code,'product primary-key evidence missing')
        return code
    def calculate(code,request):
        params={'product':code,'qty':request['demand_qty'],'demand_purpose':request['demand_purpose'],'warehouse_scope':copy.deepcopy(request['warehouse_scope'])}
        rows=load_bkn_rows('material_coverage',query,params)
        return execute_from_bkn_rows('material_coverage',rows,params)
    implementation=implementation_digest()
    report=evaluate(demands,active,config=config,window=window,kn_id=KN_ID,
                    product_type_id=_OBJECT_TYPES['product'],material_type_id=_OBJECT_TYPES['material'],
                    resolve_product=product,get_demand=source,calculate=calculate,title=TITLE,
                    implementation_digest=implementation)
    for closure in report['closure_evidence']:closure['evidence']['rule_implementation_digest']=implementation
    report['data_source']={'knowledge_network_id':KN_ID,'event_object_type_id':config['object_type_id'],
                           'product_relation_type_id':config['product_relation_type_id'],
                           'auth':'caller identity injected by official SDK; no credential business input',
                           'collection_semantics':'authorized live reads, not a transactional snapshot'}
    return report
