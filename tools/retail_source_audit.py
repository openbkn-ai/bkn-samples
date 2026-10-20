"""Structural/source audit, separate from formal question answering."""
import csv,hashlib,json
from datetime import date
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    contract=json.loads((ROOT/'tools/retail_gs1/schema-contract.json').read_text())
    report={'stage':'source-structural-preflight-not-agent-acceptance','languages':{}}
    tables={}
    for lang in ('en-us','zh-cn'):
        sample=ROOT/'samples'/('retail-gs1-'+lang);tables[lang]={};counts={}
        manifest=json.loads((sample/'sample.yaml').read_text())
        assert manifest['metadata']['name']=='retail-gs1-'+lang
        assert manifest['spec']['database']['expectedTables']==len(contract['object_types'])
        for name,spec in contract['object_types'].items():
            p=sample/'data'/(name+'.csv')
            with p.open(encoding='utf-8',newline='') as f:
                reader=csv.DictReader(f);assert set(reader.fieldnames)==set(spec['fields']),(lang,name,'columns');rows=list(reader)
            assert len(rows)>=50,(lang,name,'fewer than50 source records')
            pk=spec['primary_key'];assert len({r[pk] for r in rows})==len(rows),(lang,name,'duplicate PK')
            for r in rows:
                assert r[pk],(lang,name,'empty PK')
                for field,typ in spec['fields'].items():
                    value=r[field]
                    if value and typ=='date':assert date.fromisoformat(value).isoformat()==value
                    if value and typ=='decimal':assert Decimal(value).is_finite()
            tables[lang][name]=rows;counts[name]=len(rows)
        for name,spec in contract['object_types'].items():
            for field,(target,key) in spec.get('foreign_keys',{}).items():
                valid={r[key] for r in tables[lang][target]}
                missing=[r[spec['primary_key']] for r in tables[lang][name] if r[field] and r[field] not in valid]
                assert not missing,(lang,name,field,'FK missing',missing[:5])
        report['languages'][lang]={'tables':counts,'records':sum(counts.values())}
    for name,spec in contract['object_types'].items():
        pk=spec['primary_key'];a={r[pk]:r for r in tables['en-us'][name]};b={r[pk]:r for r in tables['zh-cn'][name]}
        assert a.keys()==b.keys(),(name,'bilingual identities')
        # Text labels/localized units may differ; identifiers, quantities, dates and codes cannot.
        stable=[f for f,t in spec['fields'].items() if t in ('date','decimal') or f.endswith('_id') or f.endswith('_code') or f in ('event_sequence','reversal_of','supplier_lot')]
        for key in a:
            for field in stable:assert a[key][field]==b[key][field],(name,key,field,'bilingual fact divergence')
    report['bilingual_fact_identity']=True
    out=ROOT/'artifacts/retail-gs1/source-structural-preflight.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
