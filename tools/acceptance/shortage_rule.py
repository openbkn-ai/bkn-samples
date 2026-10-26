"""Local synthetic-event/locked-CSV replay; never a live Workshop receipt."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def replay(language):
    sample=ROOT/'samples'/('supply_ontology_hand' if language=='zh-CN' else 'supply_ontology_en')
    sys.path.insert(0,str(sample/'tools'))
    from fn.shortage_rule import evaluate,validate_config
    from fn.material_assurance import material_coverage
    from fn.snapshot import load_csv_snapshot
    from shortage_rule_runtime import implementation_digest,KN_ID,_OBJECT_TYPES
    lock=json.loads((sample/'dataset.lock').read_text())
    for item in lock['files']:
        if hashlib.sha256((sample/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('locked fixture differs')
    config,window=validate_config({'object_type_id':'SYNTHETIC_EVENTS','product_relation_type_id':'SYNTHETIC_EVENT_PRODUCT',
        'demand_event_type':'demand_registered','shortage_event_type':'material_shortage','verified_status':'verified',
        'processing_status':'processing','closed_status':'closed'},'2026-10-03T00:00:00Z','2026-10-04T00:00:00Z')
    demand={'event_id':'SYNTHETIC-DEMAND-60','event_type':'demand_registered','status':'verified',
        'occurred_at':'2026-10-03T01:00:00Z','verified_at':'2026-10-03T01:02:00Z','verified_by':'SYNTHETIC-VERIFIER',
        'source':'report','source_ref':'SYNTHETIC-REPORT','detail':{'demand_qty':60,'demand_purpose':'customer_delivery','warehouse_scope':'all'}}
    snapshot=load_csv_snapshot()
    def calculate(product,request):return material_coverage(snapshot,product,request['demand_qty'],demand_purpose=request['demand_purpose'],warehouse_scope=request['warehouse_scope'])
    def run(demands,active,source):return evaluate(demands,active,config=config,window=window,kn_id=KN_ID,
        product_type_id=_OBJECT_TYPES['product'],material_type_id=_OBJECT_TYPES['material'],resolve_product=lambda row:'623-000034',
        get_demand=lambda key:copy.deepcopy(source),calculate=calculate,title='SYNTHETIC SHORTAGE',implementation_digest=implementation_digest())
    first=run([demand],[],None);repeat=run([demand],[],None);candidate=first['candidates'][0]
    assert candidate['detail']['covered_qty']==43
    assert {s['material']:s['short_qty'] for s in candidate['detail']['shortages']}=={'468-000282':17,'606-000129':17}
    assert candidate['deduplication_key']==repeat['candidates'][0]['deduplication_key']
    active={'event_id':'SYNTHETIC-EXISTING-SHORTAGE','event_type':'material_shortage','status':'processing',
        'source':'rule','source_ref':candidate['source_ref'],'occurred_at':candidate['occurred_at'],'detail':copy.deepcopy(candidate['detail'])}
    closed_source={**copy.deepcopy(demand),'status':'closed'}
    still_short=run([], [active],closed_source);assert still_short['closable_event_ids']==[]
    for code in ['468-000282','606-000129']:
        row=next(r for r in snapshot.inv_by_material[code] if float(r.get('available_inventory_qty') or 0)>0)
        row['available_inventory_qty']=str(float(row['available_inventory_qty'])+17)
    satisfied=run([], [active],closed_source);assert satisfied['closable_event_ids']==['SYNTHETIC-EXISTING-SHORTAGE']
    absent=run([], [active],None);assert absent['closable_event_ids']==[] and absent['has_deferred']
    return {'sample':sample.name,'language':language,'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        'working_tree_changes':bool(subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'])),
        'evidence_kind':'local synthetic events with locked CSV and hypothetical copied inventory; no BKN/Workshop calls',
        'platform_acceptance':'not-run','dataset_lock_digest':hashlib.sha256((sample/'dataset.lock').read_bytes()).hexdigest(),
        'scenarios':{'baseline':first,'repeat_key_matches':True,'still_short':still_short,'hypothetical_full_coverage':satisfied,'missing_source':absent}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--language',choices=['zh-CN','en-US'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve()
    if output.is_relative_to(ROOT):raise ValueError('write generated evidence outside source repository')
    result=replay(args.language);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(args.language,'synthetic-event baseline, retry key and closure scenarios passed; real integration pending')
