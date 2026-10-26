"""Validate locked source, typed data, model links and historical projections locally."""
import argparse,collections,csv,hashlib,importlib.util,json,sys
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evaluation import project
ROOT=Path(__file__).resolve().parents[2]


def comparable(rows):
    def value(v):
        if isinstance(v,dict):return tuple(sorted((k,value(x)) for k,x in v.items()))
        if isinstance(v,list):return tuple(value(x) for x in v)
        if isinstance(v,str):
            try:return Decimal(v)
            except Exception:return v
        return v
    return collections.Counter(value(r) for r in rows)


def verify(language):
    root=ROOT/'samples'/('energy-saref4ener-'+language)
    contract=json.loads((root/'model-contract.json').read_text());lock=json.loads((root/'dataset.lock').read_text());tables={}
    for name,spec in contract['object_types'].items():
        path=root/'data'/(name+'.csv');entry=lock['files'][path.name]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],path
        with path.open() as f:reader=csv.DictReader(f);assert reader.fieldnames==list(spec['fields']);rows=list(reader)
        assert len(rows)==entry['rows'] and len(rows)>=50
        ids={r[spec['primary_key']] for r in rows};assert len(ids)==len(rows)
        tables[name]=rows
    assert len(tables)==15 and sum(map(len,tables.values()))==14787
    for name,spec in contract['object_types'].items():
        for key,target in spec.get('foreign_keys',{}).items():
            allowed={r[target[1]] for r in tables[target[0]]}
            assert all(not r[key] or r[key] in allowed for r in tables[name]),(name,key)
    module=importlib.util.spec_from_file_location('energy_'+language,root/'tools/energy.py');engine=importlib.util.module_from_spec(module);module.loader.exec_module(engine)
    questions=json.loads((root/'bkn-eval/questions.json').read_text());expected=json.loads((root/'bkn-eval/expected-results.json').read_text())['cases'];expected={q['id']:q for q in expected}
    assert len(questions)==len(expected)==100
    assert collections.Counter(q['difficulty'] for q in questions)=={'easy':30,'medium':40,'hard':30}
    failed=[]
    for q in questions:
        actual,result=project(engine.execute,tables,contract,q)
        fields=q['output_contract']['fields']
        historical=[{k:r[k] for k in fields} for r in expected[q['id']]['rows']]
        if comparable(actual)!=comparable(historical):failed.append({'id':q['id'],'actual_count':len(actual),'expected_count':len(expected[q['id']]['rows']),'actual_first':actual[:1],'expected_first':expected[q['id']]['rows'][:1]})
        if q.get('reference_scope'):
            reference,_=project(engine.execute,tables,contract,q,q['reference_scope'])
            if comparable(reference)!=comparable([{k:r[k] for k in fields} for r in expected[q['id']]['reference_rows']]):failed.append({'id':q['id'],'reference':True})
    report={'language':language,'tables':len(tables),'records':sum(map(len,tables.values())),'historical_projection_cases':len(questions),'failed':failed,'scope':'local regression, not new Agent accuracy or platform acceptance'}
    print(json.dumps(report,ensure_ascii=False,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sample',choices=['en-us','zh-cn'],required=True);args=p.parse_args()
    raise SystemExit(bool(verify(args.sample)['failed']))
