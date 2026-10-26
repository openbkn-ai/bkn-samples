"""Proposed event adapter v1; mocks are not Workshop integration receipts."""
import copy
import json
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest
from fn.errors import CannotCompute
from fn.shortage_rule import evaluate,validate_config,instant,RULE_ID,RULE_VERSION,digest
from fn.material_assurance import material_coverage
from fn.snapshot import load_csv_snapshot
from managed_execution import KN_ID,_OBJECT_TYPES

START='2026-10-03T00:00:00Z';END='2026-10-04T00:00:00Z'
CONFIG={'object_type_id':'configured_events','product_relation_type_id':'configured_event_product',
        'demand_event_type':'demand_registered','shortage_event_type':'material_shortage',
        'verified_status':'verified','processing_status':'processing','closed_status':'closed'}


def demand(event_id='demand-1',status='verified',qty=60,purpose='customer_delivery'):
    return {'event_id':event_id,'event_type':'demand_registered','status':status,
            'occurred_at':'2026-10-03T01:00:00Z','recorded_at':'2026-10-03T01:01:00Z',
            'verified_at':'2026-10-03T01:02:00Z','verified_by':'test-verifier',
            'source':'report','source_ref':'test-report-1',
            'detail':{'demand_qty':qty,'demand_purpose':purpose,'warehouse_scope':'all'}}


def calculate(full=False):
    snapshot=load_csv_snapshot()
    if full:
        for code in ['468-000282','606-000129']:
            row=next(r for r in snapshot.inv_by_material[code] if float(r.get('available_inventory_qty') or 0)>0)
            row['available_inventory_qty']=str(float(row['available_inventory_qty'])+17)
    return lambda code,request:material_coverage(snapshot,code,request['demand_qty'],demand_purpose=request['demand_purpose'],warehouse_scope=request['warehouse_scope'])


def evaluation(demands,active=None,source=None,full=False,product=None,calculate_fn=None):
    config,window=validate_config(CONFIG,START,END)
    return evaluate(copy.deepcopy(demands),copy.deepcopy(active or []),config=config,window=window,
                    kn_id=KN_ID,product_type_id=_OBJECT_TYPES['product'],material_type_id=_OBJECT_TYPES['material'],
                    resolve_product=product or (lambda row:'623-000034'),
                    get_demand=lambda event_id:copy.deepcopy(source),calculate=calculate_fn or calculate(full),title='Shortage',implementation_digest='sha256:'+'a'*64)


def active_event(candidate,event_id='existing-shortage'):
    return {'event_id':event_id,'event_type':candidate['event_type'],'status':'processing',
            'occurred_at':candidate['occurred_at'],'source':'rule','source_ref':candidate['source_ref'],
            'detail':copy.deepcopy(candidate['detail'])}


@pytest.mark.parametrize('purpose,covered,shortage',[('customer_delivery',43,17),('new_production',26,34)])
def test_verified_demand_generates_evidenced_candidate(purpose,covered,shortage):
    report=evaluation([demand(purpose=purpose)])
    candidate=report['candidates'][0]
    assert candidate['detail']['covered_qty']==covered
    assert {s['material']:s['short_qty'] for s in candidate['detail']['shortages']}=={'468-000282':shortage,'606-000129':shortage}
    assert candidate['detail']['rule_version']==RULE_VERSION
    assert candidate['detail']['input_event']['verified_by']=='test-verifier'
    assert candidate['detail']['coverage_provenance']['bom_row_count']==549
    assert len(candidate['proposed_object_refs'])==3
    assert 'event_id' not in candidate
    assert report['writes_performed'] is False and report['closable_event_ids']==[]


def test_unverified_processing_closed_other_type_and_outside_events_are_not_new_inputs():
    rows=[demand(str(n),status) for n,status in enumerate(['pending','processing','closed','rejected','duplicate'])]
    rows += [{**demand('other'),'event_type':'another_type'}, {**demand('boundary'),'verified_at':END}]
    report=evaluation(rows,calculate_fn=lambda *args:pytest.fail('ineligible demand was evaluated'))
    assert report['candidates']==report['evaluated_demand_ids']==[]


def test_duplicate_demand_identity_and_missing_verification_fail():
    for rows in [[demand(),{**demand(),'detail':{'demand_qty':100}}],[{**demand(),'verified_by':''}],[{**demand(),'verified_at':None}]]:
        with pytest.raises(CannotCompute):evaluation(rows)


def test_repeat_and_equivalent_windows_produce_same_ingress_deduplication_key():
    one=evaluation([demand()]);two=evaluation([demand()])
    assert one['candidates'][0]['deduplication_key']==two['candidates'][0]['deduplication_key']
    assert one['candidates'][0]['detail']['evaluation_id']==two['candidates'][0]['detail']['evaluation_id']
    _,window=validate_config(CONFIG,'2026-10-03T08:00:00+08:00','2026-10-04T08:00:00+08:00')
    assert window==one['window']
    distinct=evaluation([demand('one'),demand('two')])
    assert distinct['candidates'][0]['deduplication_key']!=distinct['candidates'][1]['deduplication_key']
    assert all(e['evaluation_scope']=='independent_single_demand' for e in distinct['evaluations'])


def test_full_new_demand_is_evaluated_without_a_shortage_event():
    report=evaluation([demand()],full=True)
    assert report['candidates']==[] and report['evaluated_demand_ids']==['demand-1']


@pytest.mark.parametrize('source_status',['verified','processing','closed'])
def test_owned_active_shortage_closes_only_after_fresh_full_coverage(source_status):
    candidate=evaluation([demand()])['candidates'][0]
    current=demand(status=source_status)
    active=active_event(candidate)
    assert evaluation([], [active],source=current)['closable_event_ids']==[]
    result=evaluation([], [active],source=current,full=True)
    assert result['closable_event_ids']==['existing-shortage']
    assert result['closure_evidence'][0]['evidence']['coverage']['fully_covered'] is True
    assert result['candidates']==[]


@pytest.mark.parametrize('mutation',['missing','pending','rejected','changed_qty','changed_verifier','changed_timestamp'])
def test_missing_unverified_or_changed_source_never_causes_automatic_close(mutation):
    active=active_event(evaluation([demand()])['candidates'][0]);current=demand(status='closed')
    if mutation=='missing':current=None
    if mutation in ['pending','rejected']:current['status']=mutation
    if mutation=='changed_qty':current['detail']['demand_qty']=100
    if mutation=='changed_verifier':current['verified_by']='another-verifier'
    if mutation=='changed_timestamp':current['verified_at']='2026-10-03T02:00:00Z'
    report=evaluation([], [active],source=current,full=True)
    assert report['closable_event_ids']==[] and report['deferred'][0]['event_id']=='existing-shortage'


def test_foreign_rule_versions_are_never_closed():
    original=active_event(evaluation([demand()])['candidates'][0])
    rows=[{**original,'event_id':'foreign','source_ref':'another-rule@1:hash'},
          {**original,'event_id':'old-version','source_ref':f'{RULE_ID}@0:hash'}]
    report=evaluation([],rows,source=demand(status='closed'),full=True)
    assert report['closable_event_ids']==[]


def test_corrupt_owned_evidence_or_changed_product_is_a_failed_run():
    active=active_event(evaluation([demand()])['candidates'][0]);active['detail']['identity_digest']='tampered'
    with pytest.raises(CannotCompute):evaluation([], [active],source=demand(status='closed'),full=True)
    active=active_event(evaluation([demand()])['candidates'][0])
    with pytest.raises(CannotCompute):evaluation([], [active],source=demand(status='closed'),full=True,product=lambda row:'other-product' if row['event_id']=='existing-shortage' else '623-000034')


def test_event_detail_is_strict_json_and_not_a_caller_supplied_product_reference():
    row=demand();row['detail']=json.dumps(row['detail'])
    assert len(evaluation([row])['candidates'])==1
    row['detail']='{"demand_qty":60,"demand_qty":100}'
    with pytest.raises(CannotCompute):evaluation([row])


@pytest.mark.parametrize('change',['token','missing_status','same_types','same_statuses','naive_window','reversed_window'])
def test_invalid_configuration_is_rejected_before_reads(change):
    from shortage_rule_runtime import run
    config=copy.deepcopy(CONFIG);start,end=START,END
    if change=='token':config['token']='not-a-real-secret'
    if change=='missing_status':config.pop('closed_status')
    if change=='same_types':config['shortage_event_type']=config['demand_event_type']
    if change=='same_statuses':config['closed_status']=config['verified_status']
    if change=='naive_window':start='2026-10-03T00:00:00'
    if change=='reversed_window':start,end=end,start
    def forbidden(**kwargs):pytest.fail('invalid config attempted to read BKN')
    with pytest.raises(CannotCompute):run(forbidden,forbidden,config,start,end)


class FakeBKN:
    def __init__(self,events=None,full=False):
        from support_bkn_rows import bkn_rows
        self.events=copy.deepcopy(events or []);self.rows=bkn_rows();self.calls=[];self.fail=None;self.graph_mode=None
        if full:
            for code in ['468-000282','606-000129']:
                row=next(r for r in self.rows['inventory'] if r['material_code']==code and float(r.get('available_inventory_qty') or 0)>0)
                row['available_inventory_qty']=str(float(row['available_inventory_qty'])+17)
    def match(self,row,c):
        if not c:return True
        op=c['operation']
        if op=='and':return all(self.match(row,i) for i in c['sub_conditions'])
        value=row.get(c['field']);expected=c['value']
        if op=='==':return value==expected
        if op=='in':return value in expected
        if op in ['>=','<']:
            a,b=instant(value),instant(expected);return a>=b if op=='>=' else a<b
        raise AssertionError(c)
    def query_object_instance(self,**kwargs):
        self.calls.append(('objects',copy.deepcopy(kwargs)))
        if self.fail=='query':raise RuntimeError('simulated read failure')
        ot=kwargs['ot_id']
        if ot==CONFIG['object_type_id']:rows=self.events
        elif ot==_OBJECT_TYPES['bom']:rows=self.rows['bom']
        elif ot==_OBJECT_TYPES['inventory']:rows=self.rows['inventory']
        else:raise AssertionError(ot)
        rows=[copy.deepcopy(r) for r in rows if self.match(r,kwargs.get('condition'))]
        offset=kwargs.get('offset',0);page={'datas':rows[offset:offset+kwargs['limit']],'total_count':len(rows)}
        if self.fail=='partial':page['warnings']=['partial read']
        return page
    def query_instance_subgraph(self,**kwargs):
        self.calls.append(('graph',copy.deepcopy(kwargs)));path=kwargs['relation_type_paths'][0]
        assert path['object_types'][0]['id']==CONFIG['object_type_id']
        assert path['object_types'][1]['limit']==2 and path['limit']==2
        event_id=path['object_types'][0]['condition']['value']
        objects={'e':{'object_type_id':CONFIG['object_type_id'],'properties':{'event_id':event_id}},
                 'p':{'object_type_id':_OBJECT_TYPES['product'],'properties':{'material_number':'623-000034'},'_instance_identity':{'material_number':'623-000034'}}}
        graph={'objects':objects,'relation_paths':[{'length':1,'relations':[{'relation_type_id':CONFIG['product_relation_type_id'],'source_object_id':'e','target_object_id':'p'}]}],'total_count':1}
        if self.graph_mode=='cursor':graph['cursor']='more'
        if self.graph_mode=='ambiguous':graph['relation_paths']*=2
        if self.graph_mode=='partial':graph['warnings']=['truncated']
        if self.graph_mode=='missing':graph['relation_paths']=[]
        if self.graph_mode=='wrong_event':objects['e']['properties']['event_id']='another-event'
        if self.graph_mode=='wrong_edge':graph['relation_paths'][0]['relations'][0]['target_object_id']='unknown'
        if self.graph_mode=='identity_missing':objects['p'].pop('_instance_identity')
        return {'entries':[graph]}


def test_native_function_reads_authorized_events_relations_and_full_bom(monkeypatch):
    from native_function_bundle import build_native_function_code
    fake=FakeBKN([demand()]);sdk=types.ModuleType('sandbox_sdk');sdk.tool=lambda f:f;sdk.bkn=fake
    monkeypatch.setitem(sys.modules,'sandbox_sdk',sdk)
    namespace={};exec(build_native_function_code(fixed_operation='shortage_rule'),namespace)
    report=namespace['supply_function'](event_source=CONFIG,window_start=START,window_end=END)
    assert len(report['candidates'])==1
    assert report['candidates'][0]['detail']['covered_qty']==43
    assert report['candidates'][0]['detail']['coverage_provenance']['bom_row_count']==549
    assert report['rule']['implementation_digest'].startswith('sha256:')
    assert all(name in {'objects','graph'} for name,_ in fake.calls)
    assert not any('token' in kwargs or 'key' in kwargs for _,kwargs in fake.calls)
    second=namespace['supply_function'](event_source=CONFIG,window_start=START,window_end=END)
    assert report['candidates'][0]['deduplication_key']==second['candidates'][0]['deduplication_key']


@pytest.mark.parametrize('mode',['cursor','missing','wrong_event','wrong_edge','identity_missing','ambiguous','partial'])
def test_product_relation_failures_do_not_emit_a_successful_evaluation(mode):
    from shortage_rule_runtime import run
    fake=FakeBKN([demand()]);fake.graph_mode=mode
    with pytest.raises(CannotCompute):run(fake.query_object_instance,fake.query_instance_subgraph,CONFIG,START,END)


@pytest.mark.parametrize('failure',['query','partial'])
def test_failed_or_partial_reads_are_not_empty_success(failure):
    from shortage_rule_runtime import run
    fake=FakeBKN([demand()]);fake.fail=failure
    with pytest.raises((RuntimeError,CannotCompute)):run(fake.query_object_instance,fake.query_instance_subgraph,CONFIG,START,END)



def test_native_closure_reads_processed_source_without_bypassing_verification():
    from shortage_rule_runtime import run
    initial=FakeBKN([demand()]);candidate=run(initial.query_object_instance,initial.query_instance_subgraph,CONFIG,START,END)['candidates'][0]
    fake=FakeBKN([demand(status='closed'),active_event(candidate)],full=True)
    report=run(fake.query_object_instance,fake.query_instance_subgraph,CONFIG,START,END)
    assert report['closable_event_ids']==['existing-shortage']
    assert report['evaluated_demand_ids']==[]
    assert report['requires_ingress_revalidation'] is True
    assert report['closure_evidence'][0]['preconditions']['observed_source_status']=='closed'
    assert any(c.get('condition',{}).get('field')=='event_id' for kind,c in fake.calls if kind=='objects')


def test_bound_and_cross_type_identity_changes_fail_before_model_evaluation():
    with pytest.raises(CannotCompute):evaluation([demand('d'+str(n)) for n in range(51)],calculate_fn=lambda *args:pytest.fail('bound was not enforced'))
    candidate=evaluation([demand()])['candidates'][0]
    with pytest.raises(CannotCompute):evaluation([demand()], [active_event(candidate,event_id='demand-1')])


def test_owned_event_from_another_configuration_is_not_reinterpreted():
    row=active_event(evaluation([demand()])['candidates'][0]);row['detail']['configuration_digest']='a different configuration'
    with pytest.raises(CannotCompute):evaluation([], [row],source=demand(status='closed'),full=True)



def test_epoch_milliseconds_and_window_boundaries_are_explicit():
    row=demand();row['occurred_at']=int(instant(row['occurred_at']).timestamp()*1000)
    row['verified_at']=int(instant(row['verified_at']).timestamp()*1000)
    assert evaluation([row])['candidates'][0]['deduplication_key']==evaluation([demand()])['candidates'][0]['deduplication_key']
    assert len(evaluation([{**demand(),'occurred_at':START}])['candidates'])==1
    assert evaluation([{**demand(),'verified_at':END}])['candidates']==[]
    with pytest.raises(CannotCompute):evaluation([{**demand(),'occurred_at':'2026-10-03T01:00:00'}])


def test_failed_source_lookup_is_not_interpreted_as_absent_source():
    from shortage_rule_runtime import run
    first=FakeBKN([demand()]);candidate=run(first.query_object_instance,first.query_instance_subgraph,CONFIG,START,END)['candidates'][0]
    fake=FakeBKN([active_event(candidate),demand(status='closed')],full=True)
    def objects(**kwargs):
        if kwargs.get('condition',{}).get('field')=='event_id':raise RuntimeError('source lookup failed')
        return fake.query_object_instance(**kwargs)
    with pytest.raises(RuntimeError,match='source lookup failed'):run(objects,fake.query_instance_subgraph,CONFIG,START,END)



def test_changed_rule_implementation_never_closes_an_old_event():
    row=active_event(evaluation([demand()])['candidates'][0]);row['detail']['rule_implementation_digest']='sha256:'+'b'*64
    report=evaluation([], [row],source=demand(status='closed'),full=True)
    assert report['closable_event_ids']==[]
    assert report['deferred'][0]['reason']=='rule_implementation_changed'



def test_native_missing_source_defers_instead_of_closing():
    from shortage_rule_runtime import run
    first=FakeBKN([demand()]);candidate=run(first.query_object_instance,first.query_instance_subgraph,CONFIG,START,END)['candidates'][0]
    fake=FakeBKN([active_event(candidate)],full=True)
    result=run(fake.query_object_instance,fake.query_instance_subgraph,CONFIG,START,END)
    assert result['closable_event_ids']==[] and result['has_deferred'] is True
    assert result['deferred'][0]['reason']=='source_demand_not_found'


def test_product_reference_is_resolved_from_relations_not_detail():
    from shortage_rule_runtime import run
    row=demand();row['detail']['product_code']='not-the-linked-product'
    fake=FakeBKN([row]);report=run(fake.query_object_instance,fake.query_instance_subgraph,CONFIG,START,END)
    assert report['candidates'][0]['deduplication_key']['product']['key']=={'material_number':'623-000034'}



def test_late_verified_old_occurrence_is_not_lost():
    row=demand();row['occurred_at']='2026-10-01T01:00:00Z'
    assert len(evaluation([row])['candidates'])==1


def test_old_window_shortage_can_close_in_a_later_evaluation_window():
    candidate=evaluation([demand()])['candidates'][0];active=active_event(candidate)
    config,window=validate_config(CONFIG,'2026-10-05T00:00:00Z','2026-10-06T00:00:00Z')
    report=evaluate([], [active],config=config,window=window,kn_id=KN_ID,
        product_type_id=_OBJECT_TYPES['product'],material_type_id=_OBJECT_TYPES['material'],
        resolve_product=lambda row:'623-000034',get_demand=lambda event_id:demand(status='closed'),
        calculate=calculate(True),title='Shortage',implementation_digest='sha256:'+'a'*64)
    assert report['closable_event_ids']==['existing-shortage']
    assert report['window']!=candidate['deduplication_key']['window']



def test_existing_owned_shortage_suppresses_duplicate_after_a_new_window():
    candidate=evaluation([demand()])['candidates'][0];active=active_event(candidate)
    config,window=validate_config(CONFIG,'2026-10-05T00:00:00Z','2026-10-06T00:00:00Z')
    report=evaluate([demand()], [active],config=config,window=window,kn_id=KN_ID,
        product_type_id=_OBJECT_TYPES['product'],material_type_id=_OBJECT_TYPES['material'],
        resolve_product=lambda row:'623-000034',get_demand=lambda event_id:demand(),
        calculate=calculate(),title='Shortage',implementation_digest='sha256:'+'a'*64)
    assert report['candidates']==[] and report['closable_event_ids']==[]
    assert report['still_open_event_ids']==['existing-shortage']
