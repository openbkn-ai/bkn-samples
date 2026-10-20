"""Source-only oracle and comparator controls; not a formal answerer run."""
import copy, hashlib, json
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
from oracle import Reference, serialize
from build_bank import ROOT, CASES, load_sql, resolve, source_evidence
from grade import grade

def main():
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    check('exact100_cases',len(CASES)==100)
    check('30basic40medium30complex',Counter(c['difficulty'] for c in CASES)==Counter(basic=30,medium=40,complex=30))
    for scene in range(1,11):check('scene'+str(scene)+'_10',sum(c['scenario_id']==f'S{scene:02}' for c in CASES)==10)
    golds={}
    for lang in ['en-us','zh-cn']:
        sample=ROOT/'samples'/('retail-gs1-'+lang);ref=Reference(sample/'data');con=load_sql(ref.tables)
        questions=json.loads((sample/'bkn-eval/questions.json').read_text());gold=json.loads((sample/'bkn-eval/expected-results.json').read_text());golds[lang]=gold
        check(lang+'_100_questions',len(questions)==100 and len({q['id'] for q in questions})==100)
        for c,q in zip(CASES,questions):
            expected=resolve(ref,con,c)
            check(lang+'_'+c['id']+'_independent_source_identity',expected==gold[c['id']]['rows'])
            check(lang+'_'+c['id']+'_strict_self_compare',grade({'rows':expected},gold[c['id']],q['output_contract'])['passed'])
            evidence=source_evidence(ref,c)
            check(lang+'_'+c['id']+'_source_evidence_identity',evidence==gold[c['id']]['source_evidence'])
        revision=sample/'bkn-eval/revision-errata.json'
        if revision.exists():
            manifest=json.loads(revision.read_text())
            check(lang+'_original_freeze_preserved',hashlib.sha256((sample/'bkn-eval/freeze.json').read_bytes()).hexdigest()==manifest['original_freeze_sha256'])
            hashes=manifest['revision_files']
        else:hashes=json.loads((sample/'bkn-eval/freeze.json').read_text())['files']
        for p,sha in hashes.items():check(lang+'_hash_'+p,hashlib.sha256((sample/'bkn-eval'/p).read_bytes()).hexdigest()==sha)
        inv=ref.inventory()[0];cell=lambda lid,loc:next(r for r in inv if r['lot_id']==lid and r['location_id']==loc)
        # Hand-derived fixture controls (never read production engine/results).
        c=cell('LOT-001-C','STORE-001')
        check(lang+'_return_hold_union_3plus5minus3equals5',c['returned']==D(3) and c['quarantined']==D(5) and c['on_hand']==D(27) and c['available']==D(22))
        c=cell('LOT-001-C','WH-001')
        check(lang+'_reservations30_stock141_available111',c['on_hand']==D(141) and c['reserved']==D(30) and c['available']==D(111))
        check(lang+'_conflicting_sale_only_store_unknown',cell('LOT-043-C','STORE-018')['available'] is None and cell('LOT-043-C','WH-018')['on_hand'] is not None)
        check(lang+'_missing_dispatch_recalledchild_unknown',cell('LOT-045-D','STORE-020')['on_hand'] is None)
        check(lang+'_negative_not_zero',cell('LOT-046-C','STORE-021')['on_hand'] is None)
        check(lang+'_closed_recall_no_active_assessment',ref.recall('REC-050','2027-02-28','2027-02-28')==[])
        check(lang+'_unannounced_recall_no_active_assessment',ref.recall('REC-010','2027-02-28','2027-02-20')==[])
        check(lang+'_cross_product_descendant',ref.closure('LOT-048-B','2027-02-28','2027-02-28')=={'LOT-048-B','LOT-048-D','LOT-047-D'})
        check(lang+'_no_sibling_overreach','LOT-043-C' not in ref.closure('LOT-043-B','2027-02-28','2027-02-28'))
        alloc=ref.allocation(['PRD-001'],'2027-02-28','2027-02-28')
        check(lang+'_shared_stock_not_double_spent',sum(r['allocated_quantity'] for r in alloc)==D(141))
        check(lang+'_own_reservation_released_once',[(r['allocated_quantity'],r['shortage_quantity']) for r in alloc]==[(D(111),D(0)),(D(30),D(71))])
        check(lang+'_overdue_order_retained','ORD-049-A' in {r['order_id'] for r in ref.allocation(['PRD-049'],'2027-02-28','2027-02-28')})
        # Source counterexample distinguishes overlap from disjoint hold quantity.
        altered=copy.deepcopy(ref)
        next(r for r in altered.tables['holds'] if r['hold_id']=='HOLD-001-R')['return_overlap_quantity']='0'
        changed=next(r for r in altered.inventory()[0] if r['lot_id']=='LOT-001-C' and r['location_id']=='STORE-001')
        check(lang+'_disjoint_hold_not_max_union',changed['quarantined']==D(8) and changed['available']==D(19))
        # One source quantity mutation must change its reference business result.
        altered=copy.deepcopy(ref);row=next(r for r in altered.tables['movements'] if r['lot_id']=='LOT-001-C' and r['event_type_code']=='receive');row['quantity']=str(D(row['quantity'])+1)
        changed=next(r for r in altered.inventory()[0] if r['lot_id']=='LOT-001-C' and r['location_id']=='WH-001')
        check(lang+'_oracle_sensitive_to_source_quantity',changed['on_hand']==D(142))
    # Compare language-invariant answers after only explicit public display translations.
    def translate(x):
        if isinstance(x,dict):return {k:translate(v) for k,v in x.items()}
        if isinstance(x,list):return [translate(v) for v in x]
        return {'件':'ea','箱':'case'}.get(x,x) if isinstance(x,str) else x
    # Name/reason queries are intentionally localized and not lexical-equal.
    for c in CASES:
        if any(f in c['fields'] for f in ('name','supplier_name','organization_name','reason')):continue
        check(c['id']+'_bilingual_business_values',translate(golds['en-us'][c['id']]['rows'])==translate(golds['zh-cn'][c['id']]['rows']))
    expected={'rows':[{'lot_id':'LOT-X','quantity':'2.000000','expiry_date':'2027-03-31','available':None,'allocations':[{'lot_id':'LOT-Y','quantity':'1.000000'}]}]}
    good={'rows':[{'lot_id':'LOT-X','quantity':2,'expiry_date':'2027-03-31T00:00:00+08:00','available':None,'allocations':[{'lot_id':'LOT-Y','quantity':1}]}]}
    check('decimal_and_midnight_transport_equivalence',grade(good,expected)['passed'])
    mutants=[]
    for field,value in [('quantity','2.000001'),('available',0),('lot_id','LOT-Z'),('expiry_date','2027-03-31T01:00:00+08:00')]:
        m=copy.deepcopy(good);m['rows'][0][field]=value;mutants.append(m)
    m=copy.deepcopy(good);del m['rows'][0]['available'];mutants.append(m)
    m=copy.deepcopy(good);m['rows'].append(copy.deepcopy(m['rows'][0]));mutants.append(m)
    m=copy.deepcopy(good);m['rows'][0]['allocations']=[];mutants.append(m)
    m=copy.deepcopy(good);m['rows'][0]['allocations']*=2;mutants.append(m)
    for n,m in enumerate(mutants):check('grader_rejects_mutation_'+str(n),not grade(m,expected)['passed'])
    ordered_contract={'properties':{'rows':{'x-order-by':['event_date','event_sequence','event_id'],'items':{'required':['event_id','event_date','event_sequence','quantity','source_location_id']}}}}
    ordered_expected={'rows':[{'event_id':'A','event_date':'2027-02-28','event_sequence':'2','quantity':'1.000000','source_location_id':None},{'event_id':'B','event_date':'2027-02-28','event_sequence':'10','quantity':'2.000000','source_location_id':'WH-X'}]}
    check('ordered_contract_accepts_numeric_sequence',grade(ordered_expected,ordered_expected,ordered_contract)['passed'])
    wrong_order={'rows':list(reversed(ordered_expected['rows']))}
    check('ordered_contract_rejects_permutation',not grade(wrong_order,ordered_expected,ordered_contract)['passed'])
    numeric_equivalent=copy.deepcopy(ordered_expected);numeric_equivalent['rows'][0]['quantity']=1;numeric_equivalent['rows'][1]['event_sequence']=10
    check('ordered_contract_preserves_decimal_equivalence',grade(numeric_equivalent,ordered_expected,ordered_contract)['passed'])
    blank_optional=copy.deepcopy(ordered_expected);blank_optional['rows'][0]['source_location_id']=''
    check('nullable_contract_rejects_empty_string_for_null',not grade(blank_optional,ordered_expected,ordered_contract)['passed'])
    for lang in ['en-us','zh-cn']:
        ref=Reference(ROOT/'samples'/('retail-gs1-'+lang)/'data')
        c=next(c for c in CASES if c['kind']=='links' and c['params'].get('root')=='LOT-047-D')
        evidence=source_evidence(ref,c)
        check(lang+'_connected_component_provenance_includes_sibling_link','LINK-048' in evidence['lot_links'])
    report={'passed':len(checks),'failed':0,'checks':checks,'formal_agent_rounds_executed':0,'method':'Independent source oracle plus manually derived and source-mutation controls; no production implementation imports or outputs.'}
    for lang in ['en-us','zh-cn']:
        sample=ROOT/'samples'/('retail-gs1-'+lang)
        if (sample/'bkn-eval/revision-errata.json').exists():
            out=sample/'bkn-eval';name='revision-development-checks.json'
            report['formal_validation_status']='DEVELOPMENT_CHECK_ONLY_NOT_A_QUESTION_ANSWER_RUN'
            report['original_formal_scores_fixed']={'en-us':'96/100','zh-cn':'95/100'}
        else:out=sample/'verification';name='independent-evaluation-preflight.json'
        out.mkdir(exist_ok=True)
        (out/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':len(checks),'failed':0,'formal_agent_rounds_executed':0}))
if __name__=='__main__':main()
