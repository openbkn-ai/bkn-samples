#!/usr/bin/env python3
"""Compare normalized offline observations against independently frozen gold.

Usage: python3 offline_compare.py observations.yaml [--output report.json]
Input: {answers: [{id: M-01, observed: {value: 30}}, ...]}
Normalize tested function returns to each gold expected field before this step;
this checker does not call functions, infer omitted results, or generate gold.
"""
import argparse
import json
import math
from pathlib import Path
import yaml

def differences(expected, observed, path='expected'):
    issues = []
    if isinstance(expected, bool):
        if type(observed) is not bool or observed != expected:
            issues.append(dict(path=path, expected=expected, observed=observed))
    elif isinstance(expected, (int, float)):
        if isinstance(observed, bool) or not isinstance(observed, (int, float)) or not math.isclose(expected, observed, rel_tol=1e-9, abs_tol=1e-7):
            issues.append(dict(path=path, expected=expected, observed=observed))
    elif isinstance(expected, dict):
        if not isinstance(observed, dict):
            issues.append(dict(path=path, expected=expected, observed=observed))
        else:
            for key, value in expected.items():
                if key not in observed:
                    issues.append(dict(path=path+'.'+key, expected=value, error='missing_field'))
                else:
                    issues += differences(value, observed[key], path+'.'+key)
            # Net shortage maps must not contain unexplained additional material codes.
            if path.endswith('leaf_shortages'):
                for key in observed.keys()-expected.keys():
                    issues.append(dict(path=path+'.'+key, error='unexpected_shortage', observed=observed[key]))
    elif isinstance(expected, list):
        if path.endswith(('material_codes', 'product_codes')):
            if not isinstance(observed, list) or sorted(expected) != sorted(observed):
                issues.append(dict(path=path, expected=expected, observed=observed))
        elif not isinstance(observed, list) or len(expected) != len(observed):
            issues.append(dict(path=path, expected=expected, observed=observed))
        else:
            for index, (a, b) in enumerate(zip(expected, observed)):
                issues += differences(a, b, path+f'[{index}]')
    elif observed != expected:
        issues.append(dict(path=path, expected=expected, observed=observed))
    return issues

def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observations', type=Path)
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    baseline=Path(__file__).resolve().parent.parent/'answer-set-v3.yaml'
    gold=yaml.safe_load(baseline.read_text())['answers']
    raw=yaml.safe_load(args.observations.read_text())
    observed=raw['answers'] if isinstance(raw,dict) else raw
    ids=[r['id'] for r in observed]
    assert len(ids)==len(set(ids)), 'duplicate observation IDs'
    byid={r['id']:r for r in observed}
    reports=[]
    for row in gold:
        qid=row['id']
        if qid not in byid:
            issues=[dict(error='missing_question')]
        elif 'observed' not in byid[qid]:
            issues=[dict(error='missing_observed_object')]
        else:
            issues=differences(row['expected'],byid[qid]['observed'])
        reports.append(dict(id=qid,passed=not issues,differences=issues))
    extras=sorted(set(byid)-{r['id'] for r in gold})
    result=dict(total=len(gold),passed=sum(r['passed'] for r in reports),
                failed=sum(not r['passed'] for r in reports),unexpected_ids=extras,results=reports)
    output=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output: args.output.write_text(output,encoding='utf-8')
    print(output)
    raise SystemExit(0 if result['failed']==0 and not extras else 1)

if __name__=='__main__':
    run()
