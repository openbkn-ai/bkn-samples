"""Apply source-contract errata without touching the original formal score/freeze.

This authoring operation creates a new, formally UNTESTED bank revision. It never
loads actual submissions, scoring files or answerer traces.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
LANGUAGES=('en-us','zh-cn')
def normalized_rows(rows):
    fixed=[{k:None if v=='' else v for k,v in row.items()} for row in rows]
    return sorted(fixed,key=lambda row:json.dumps(row,ensure_ascii=False,sort_keys=True))
def main():
    previous={}
    for lang in LANGUAGES:
        p=BASE/'samples'/('retail-gs1-'+lang)/'bkn-eval'
        previous[lang]={'freeze':(p/'freeze.json').read_bytes(),'gold':json.loads((p/'expected-results.json').read_text())}
    subprocess.run([sys.executable,str(Path(__file__).with_name('build_bank.py')),'--write','--revision-after-formal'],check=True,capture_output=True,text=True)
    for lang in LANGUAGES:
        p=BASE/'samples'/('retail-gs1-'+lang)/'bkn-eval';gold=json.loads((p/'expected-results.json').read_text())
        assert (p/'freeze.json').read_bytes()==previous[lang]['freeze'],'Original freeze mutated'
        for qid,value in gold.items():
            assert normalized_rows(value['rows'])==normalized_rows(previous[lang]['gold'][qid]['rows']),f'Unexpected business-value change {lang} {qid}'
        revision={'revision':'post-formal-contract-errata-1','formal_validation_status':'NOT_RUN_ON_REVISED_BANK','original_formal_scores_fixed':{'en-us':{'passed':96,'denominator':100},'zh-cn':{'passed':95,'denominator':100}},'original_freeze_sha256':hashlib.sha256(previous[lang]['freeze']).hexdigest(),'original_archive':'original/','business_value_change':'No quantity or fact changes. Absent optional source values represented as null; required event ordering preserved. Reference rows otherwise identical as multisets.','changes':['Explicit positive-return filter for Q018','Explicit positive-quarantine filter for Q033','Generic nullable-source normalization and contract-declared ordered rows for event journeys','Bilingual Q028 requests full upstream/downstream undirected connected component including sibling branches','Connected-component provenance includes all visible component edges','quantity schema uses decimal_exact'],'revision_files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.glob('*.json')) if f.name not in ('freeze.json','revision-errata.json')}}
        (p/'revision-errata.json').write_text(json.dumps(revision,ensure_ascii=False,indent=2)+'\n')
        print(lang,'original freeze preserved; all100 business-row multisets unchanged except null transport; revision untested')
if __name__=='__main__':main()
