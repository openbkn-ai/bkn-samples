"""Read-only material shortage proposals; Workshop alone owns event writes."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone

from .errors import CannotCompute
from .material_assurance import MODEL_VERSION, validate_inputs

RULE_ID = 'supply.material-shortage'
RULE_VERSION = 1
CONTRACT_VERSION = 'samples.material-shortage.v1'
MAX_EVENTS = 50
CONFIG_KEYS = {'object_type_id','product_relation_type_id','demand_event_type',
               'shortage_event_type','verified_status','processing_status','closed_status'}


def require(ok, message):
    if not ok:raise CannotCompute(message)


def text(value, label, maximum=256):
    require(isinstance(value,str) and bool(value.strip()) and len(value)<=maximum
            and all(ord(c)>=32 for c in value), 'invalid '+label)
    return value.strip()


def instant(value):
    try:
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            require(math.isfinite(value), 'invalid event timestamp')
            result=datetime.fromtimestamp(value/1000,timezone.utc)
        else:
            require(isinstance(value,str), 'timestamp must be RFC3339 or epoch milliseconds')
            result=datetime.fromisoformat(value.replace('Z','+00:00'))
        require(result.tzinfo is not None and result.utcoffset() is not None,'timestamp needs an explicit timezone')
        return result.astimezone(timezone.utc)
    except (ValueError,OverflowError,OSError) as error:
        raise CannotCompute('invalid event timestamp') from error


def stamp(value):return instant(value).isoformat()


def validate_config(config, window_start, window_end):
    require(isinstance(config,dict) and set(config)==CONFIG_KEYS,'event_source must contain the complete v1 adapter configuration')
    result={key:text(value,key,128) for key,value in config.items()}
    require(result['demand_event_type']!=result['shortage_event_type'],'demand and shortage event types must differ')
    require(len({result[k] for k in ['verified_status','processing_status','closed_status']})==3,'lifecycle status mappings must differ')
    require(isinstance(window_start,str) and isinstance(window_end,str),'window boundaries must be RFC3339 strings')
    start,end=instant(window_start),instant(window_end)
    require(start<end,'window must be a nonempty half-open interval')
    return result,{'start':start.isoformat(),'end':end.isoformat()}


def object_value(value):
    if isinstance(value,str):
        def pairs(items):
            result={}
            for key,item in items:
                require(key not in result,'duplicate JSON detail field');result[key]=item
            return result
        try:value=json.loads(value,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError,TypeError) as error:raise CannotCompute('invalid event detail JSON') from error
    require(isinstance(value,dict),'event detail must be a JSON object')
    return value


def digest(value):
    return 'sha256:'+hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def request_values(detail):
    detail=object_value(detail)
    request={key:copy.deepcopy(detail.get(key)) for key in ['demand_qty','demand_purpose','warehouse_scope']}
    validate_inputs('validated-through-relation',request['demand_qty'],request['demand_purpose'],request['warehouse_scope'])
    if isinstance(request['warehouse_scope'],list):request['warehouse_scope']=sorted(set(request['warehouse_scope']))
    return request


def demand_snapshot(row, config):
    require(row.get('event_type')==config['demand_event_type'],'source demand event type changed')
    require(not row.get('merged_into'),'merged demand is not a confirmed independent input')
    return {'event_id':text(row.get('event_id'),'event_id'),
            'event_type':config['demand_event_type'],
            'occurred_at':stamp(row.get('occurred_at')),
            'verified_at':stamp(row.get('verified_at')),
            'verified_by':text(row.get('verified_by'),'verified_by'),
            'source':text(row.get('source'),'source'),
            'source_ref':text(row.get('source_ref'),'source_ref'),
            'request':request_values(row.get('detail'))}


def scoped_rows(rows, config, event_type, statuses, window):
    require(isinstance(rows,list),'event query did not return complete rows')
    result={}
    for row in rows:
        require(isinstance(row,dict),'invalid event row')
        if row.get('event_type')!=event_type or row.get('status') not in statuses:continue
        if event_type==config['demand_event_type'] and instant(row.get('verified_at'))>=instant(window['end']):continue
        event_id=text(row.get('event_id'),'event_id')
        require(event_id not in result,'event identity repeated or changed during read')
        result[event_id]=row
    require(len(result)<=MAX_EVENTS,'too many events; partition the configured event stream')
    return result


def evaluate(demand_rows, active_rows, *, config, window, kn_id, product_type_id,
             material_type_id, resolve_product, get_demand, calculate, title, implementation_digest):
    """Callbacks only read authorized facts. A failed call returns no actions."""
    require(isinstance(implementation_digest,str) and re.fullmatch(r'sha256:[0-9a-f]{64}',implementation_digest),'rule implementation digest is missing')
    configuration_digest=digest(config)
    demands=scoped_rows(demand_rows,config,config['demand_event_type'],{config['verified_status']},window)
    active=scoped_rows(active_rows,config,config['shortage_event_type'],{config['verified_status'],config['processing_status']},window)
    require(not set(demands).intersection(active),'event identity changed type during read')
    snapshots={};products={};coverages={};evaluations=[];candidates=[];closable=[];deferred=[];still_open=[]
    def suppress_candidate(source_id):
        candidates[:]=[c for c in candidates if c['detail']['input_event']['event_id']!=source_id]
    def product(row):
        event_id=row['event_id']
        if event_id not in products:products[event_id]=text(resolve_product(row),'linked product')
        return products[event_id]
    def identity(snapshot, code, event_window=None):
        return {'rule_id':RULE_ID,'rule_version':RULE_VERSION,'knowledge_network_id':kn_id,
                'source_event':{'object_type_id':config['object_type_id'],'event_id':snapshot['event_id']},
                'product':{'object_type_id':product_type_id,'key':{'material_number':code}},'window':event_window or window}
    def coverage(snapshot, code):
        request=snapshot['request'];key=digest({'product':code,'request':request})
        if key not in coverages:
            value=calculate(code,copy.deepcopy(request))
            require(isinstance(value,dict) and value.get('model_version')==MODEL_VERSION,'coverage model result is not supported')
            require(value.get('product_code')==code and value.get('demand_qty')==request['demand_qty']
                    and value.get('demand_purpose')==request['demand_purpose']
                    and value.get('warehouse_scope')==request['warehouse_scope'],'coverage result does not match the verified request')
            require(type(value.get('fully_covered')) is bool and isinstance(value.get('gaps'),list),'incomplete coverage result')
            require(value['fully_covered']==(value.get('covered_qty')==value['demand_qty'])
                    and value['fully_covered']==(not value['gaps']),'coverage result is inconsistent')
            require(isinstance(value.get('provenance'),dict) and value['provenance'].get('bom_digest')
                    and value['provenance'].get('inventory_digest'),'coverage evidence is missing')
            coverages[key]=value
        return coverages[key]
    def evidence(snapshot, code, result, event_window=None):
        evaluation_id=digest({'identity':identity(snapshot,code,event_window),'evaluation_window':window,'input':snapshot,
                              'model_version':MODEL_VERSION,'bom_digest':result['provenance']['bom_digest'],
                              'inventory_digest':result['provenance']['inventory_digest'],
                              'covered_qty':result['covered_qty'],'gaps':result['gaps']})
        return {'evaluation_id':evaluation_id,'input_event':snapshot,'coverage':result,
                'evaluation_scope':'independent_single_demand','not_evaluated':['cross_demand_inventory_allocation']}
    # New demand inputs must be verified now, not merely carry a past receipt.
    for event_id,row in sorted(demands.items()):
        snapshot=demand_snapshot(row,config);snapshots[event_id]=snapshot;code=product(row)
        result=coverage(snapshot,code);record=evidence(snapshot,code,result);evaluations.append(record)
        if result['fully_covered']:continue
        key=identity(snapshot,code)
        refs=[key['product']]
        refs += [{'object_type_id':material_type_id,'key':{'material_code':g['material_code']}} for g in result['gaps']]
        candidates.append({'event_type':config['shortage_event_type'],'source':'rule',
            'source_ref':f"{RULE_ID}@{RULE_VERSION}:"+record['evaluation_id'],
            'occurred_at':window['start'],'title':title+': '+code,
            'deduplication_key':copy.deepcopy(key),'proposed_object_refs':refs,
            'preconditions':{'source_event_id':event_id,'input_digest':digest(snapshot),'verified_at':snapshot['verified_at'],'verified_by':snapshot['verified_by'],'required_status':config['verified_status'],'configuration_digest':configuration_digest},
            'detail':{'contract_version':CONTRACT_VERSION,'rule_id':RULE_ID,'rule_version':RULE_VERSION,'creation_window':copy.deepcopy(window),
                      'identity_digest':digest(key),'rule_implementation_digest':implementation_digest,'configuration_digest':configuration_digest,'evaluation_id':record['evaluation_id'],
                      'input_event':snapshot,'demand_qty':result['demand_qty'],
                      'covered_qty':result['covered_qty'],
                      'shortages':[{'material':g['material_code'],'short_qty':g['shortage_qty']} for g in result['gaps']],
                      'model_version':MODEL_VERSION,'coverage_provenance':copy.deepcopy(result['provenance'])}})
    for event_id,row in sorted(active.items()):
        # Do not interpret another rule/version's detail or offer to close it.
        if row.get('source')!='rule' or not str(row.get('source_ref') or '').startswith(f'{RULE_ID}@{RULE_VERSION}:'):continue
        detail=object_value(row.get('detail'))
        require(detail.get('contract_version')==CONTRACT_VERSION and detail.get('rule_id')==RULE_ID
                and detail.get('rule_version')==RULE_VERSION and detail.get('configuration_digest')==configuration_digest,'owned rule event contract or configuration is inconsistent')
        require(isinstance(detail.get('evaluation_id'),str) and re.fullmatch(r'sha256:[0-9a-f]{64}',detail['evaluation_id']), 'owned rule evaluation identity is invalid')
        require(row['source_ref']==f'{RULE_ID}@{RULE_VERSION}:'+detail['evaluation_id'],'rule event evidence reference differs')
        if detail.get('rule_implementation_digest')!=implementation_digest:
            prior=detail.get('input_event')
            if isinstance(prior,dict):suppress_candidate(prior.get('event_id'))
            deferred.append({'event_id':event_id,'reason':'rule_implementation_changed'});continue
        frozen=detail.get('input_event');require(isinstance(frozen,dict),'owned shortage is missing the verified input receipt')
        source_id=text(frozen.get('event_id'),'source event id')
        current=demands.get(source_id)
        if current is None:current=get_demand(source_id)
        if current is None:
            deferred.append({'event_id':event_id,'reason':'source_demand_not_found'});continue
        if current.get('status') not in {config['verified_status'],config['processing_status'],config['closed_status']}:
            deferred.append({'event_id':event_id,'reason':'source_demand_not_verified_or_processed'});continue
        try:snapshot=demand_snapshot(current,config)
        except CannotCompute:
            deferred.append({'event_id':event_id,'reason':'source_demand_evidence_incomplete'});continue
        if snapshot!=frozen:
            deferred.append({'event_id':event_id,'reason':'source_demand_or_verification_changed'});continue
        if instant(snapshot['verified_at'])>=instant(window['end']):
            deferred.append({'event_id':event_id,'reason':'source_verification_after_evaluation_cutoff'});continue
        creation=detail.get('creation_window');require(isinstance(creation,dict) and set(creation)=={'start','end'},'shortage creation window missing')
        _,creation=validate_config(config,creation['start'],creation['end'])
        if instant(creation['end'])>instant(window['end']):
            deferred.append({'event_id':event_id,'reason':'shortage_created_after_evaluation_cutoff'});continue
        code=product(current)
        require(product(row)==code,'shortage product association differs from source demand')
        require(detail.get('identity_digest')==digest(identity(snapshot,code,creation)),'shortage identity/window does not match this rule')
        suppress_candidate(source_id)
        result=coverage(snapshot,code);record=evidence(snapshot,code,result,creation)
        evaluations.append({**record,'existing_event_id':event_id})
        if result['fully_covered']:closable.append({'event_id':event_id,'reason':'coverage_satisfied','evidence':record,
            'preconditions':{'source_event_id':source_id,'input_digest':digest(snapshot),
                             'existing_source_ref':row['source_ref'],'existing_identity_digest':detail['identity_digest'],
                             'observed_source_status':current['status'],'configuration_digest':configuration_digest}})
        else:still_open.append(event_id)
    return {'contract_version':CONTRACT_VERSION,'configuration_digest':configuration_digest,'status':'complete','rule':{'id':RULE_ID,'version':RULE_VERSION,'implementation_digest':implementation_digest},
            'knowledge_network_id':kn_id,'window':copy.deepcopy(window),'candidates':candidates,
            'closable_event_ids':[r['event_id'] for r in closable],'closure_evidence':closable,
            'evaluated_demand_ids':sorted(snapshots),'still_open_event_ids':still_open,'deferred':deferred,'evaluations':evaluations,
            'evaluated_at':datetime.now(timezone.utc).isoformat(),
            'has_deferred':bool(deferred),'requires_ingress_revalidation':True,
            'writes_performed':False,'event_id_authority':'Workshop event ingress'}
