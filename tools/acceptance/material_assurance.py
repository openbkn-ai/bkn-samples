"""Replay issue #189 against locked repository CSVs, without contacting OpenBKN."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def replay(language):
    sample=ROOT/'samples'/('supply_ontology_hand' if language=='zh-CN' else 'supply_ontology_en')
    sys.path.insert(0,str(sample/'tools'))
    from fn.snapshot import load_csv_snapshot
    from fn.material_assurance import material_coverage,replenishment_draft
    from fn.bom import classify_bom_row
    from collections import Counter
    lock=json.loads((sample/'dataset.lock').read_text())
    for entry in lock['files']:
        if hashlib.sha256((sample/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('fixture digest differs: '+entry['path'])
    results=[]
    for purpose,manual,tray,expected in [
        ('customer_delivery',0,0,43),('new_production',0,0,26),
        ('customer_delivery',17,0,43),('new_production',17,0,26),
        ('customer_delivery',17,17,60),('new_production',17,17,43),
        ('customer_delivery',34,34,60),('new_production',34,34,60)]:
        snapshot=load_csv_snapshot()
        for code,quantity in [('468-000282',manual),('606-000129',tray)]:
            row=next(r for r in snapshot.inv_by_material[code] if float(r.get('available_inventory_qty') or 0)>0)
            row['available_inventory_qty']=str(float(row['available_inventory_qty'])+quantity)
        result=material_coverage(snapshot,'623-000034',60,demand_purpose=purpose)
        if result['covered_qty']!=expected:raise ValueError('coverage replay failed')
        results.append({'demand_purpose':purpose,'hypothetical_manual_supply':manual,'hypothetical_tray_supply':tray,
                        'expected_covered_qty':expected,'result':result,'draft':replenishment_draft(result)})
    source={'commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            'working_tree_changes':bool(subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain']))}
    return {'sample':sample.name,'language':language,'source':source,'status':'local-locked-csv-replay-passed',
            'historical_receipts':'not available locally; original eight-case reconciliation pending',
            'case_origin':'eight new regression cases from the design, not recovered historical receipts',
            'platform_acceptance':'not-run','dataset_lock_digest':hashlib.sha256((sample/'dataset.lock').read_bytes()).hexdigest(),
            'bom_classification':dict(Counter(classify_bom_row(r) for r in load_csv_snapshot().bom)),
            'cases':results}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--language',choices=['zh-CN','en-US'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve()
    if output.is_relative_to(ROOT):raise ValueError('write generated evidence outside the source repository')
    report=replay(args.language);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(args.language,len(report['cases']),'local cases passed; original receipts and target acceptance pending')
