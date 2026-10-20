"""Cross-check independently implemented primitive calculations before freeze.

This is development verification, not agent answering or a hidden holdout score.
"""
import importlib.util,json
from pathlib import Path
from oracle import Reference,serialize
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('retail_production',ROOT/'tools/retail_gs1/retail_core.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
def canonical(rows):return sorted([json.dumps(serialize(r),sort_keys=True,ensure_ascii=False) for r in rows])
def main():
    cases=[]
    for lang in ('en-us','zh-cn'):
        sample=ROOT/'samples'/('retail-gs1-'+lang);ref=Reference(sample/'data');contract=json.loads((sample/'model-contract.json').read_text())
        products=sorted(ref.products)
        scope={'product_ids':products,'as_of_date':'2027-02-28','knowledge_date':'2027-02-28','view_kind':'actual'}
        tests=[('inventory_asof',scope,ref.inventory()[0]),('fulfillment_plan',scope,ref.allocation(products,scope['as_of_date'],scope['knowledge_date'])),('fulfillment_plan',dict(scope,mode='replenishment'),ref.plan(products,scope['as_of_date'],scope['knowledge_date']))]
        tests.extend(('recall_assessment',dict(scope,recall_id=r['recall_id']),ref.recall(r['recall_id'],scope['as_of_date'],scope['knowledge_date'])) for r in ref.tables['recalls'])
        for op,s,expected in tests:
            actual=core.execute(op,ref.tables,contract,s)['rows']
            ea=canonical(expected);aa=canonical(actual)
            cases.append({'language':lang,'operation':op,'recall_id':s.get('recall_id'),'pass':ea==aa,'actual_count':len(actual),'expected_count':len(expected),'only_production':list(sorted(set(aa)-set(ea)))[:2],'only_reference':list(sorted(set(ea)-set(aa)))[:2]})
    folder=ROOT/'artifacts/retail-gs1';folder.mkdir(parents=True,exist_ok=True)
    ordinal=len(list(folder.glob('development-independent-comparison*.json')))+1
    out=folder/f'development-independent-comparison-{ordinal:02d}.json'
    with out.open('x') as f:json.dump({'stage':'development-not-formal-agent-score','cases':cases},f,ensure_ascii=False,indent=2)
    failures=[r for r in cases if not r['pass']]
    print(json.dumps({'checks':len(cases),'failures':len(failures),'details':failures[:5],'report':str(out)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
