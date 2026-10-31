#!/usr/bin/env python3
"""Independent oracle for the World Cup business-scenario question set.

Loads the locked CSV files of this package into SQLite and runs the reference SQL in
reference-queries.json; it never calls the platform or the knowledge network. The zh-CN and
en-US packages share the same data and this script, so their expected values are identical;
only question-text.yaml differs.

Writes question-set-v1.yaml (no answers) and answer-set-v1.yaml next to this file.
"""
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# id, scenario, difficulty, role; question wording lives in question-text.yaml of each language package
Q = [
    ('B-01', 'S01', 'basic', 'ED'),
    ('B-02', 'S01', 'basic', 'DS'),
    ('B-03', 'S01', 'basic', 'ED'),
    ('B-04', 'S02', 'basic', 'DS'),
    ('B-05', 'S03', 'basic', 'DS'),
    ('B-06', 'S06', 'basic', 'ED'),
    ('B-07', 'S05', 'basic', 'ED'),
    ('B-08', 'S04', 'basic', 'ED'),
    ('B-09', 'S10', 'basic', 'DS'),
    ('B-10', 'S10', 'basic', 'ED'),
    ('J-01', 'S03', 'medium', 'ED'),
    ('J-02', 'S05', 'medium', 'DS'),
    ('J-03', 'S03', 'medium', 'AN'),
    ('J-04', 'S07', 'basic', 'ED'),
    ('J-05', 'S07', 'medium', 'DS'),
    ('J-06', 'S08', 'medium', 'AN'),
    ('J-07', 'S01', 'basic', 'ED'),
    ('J-08', 'S09', 'medium', 'AN'),
    ('J-09', 'S07', 'medium', 'AN'),
    ('J-10', 'S04', 'medium', 'ED'),
    ('J-11', 'S02', 'medium', 'DS'),
    ('J-12', 'S09', 'medium', 'AN'),
    ('R-01', 'S04', 'complex', 'ED'),
    ('R-02', 'S04', 'complex', 'ED'),
    ('R-03', 'S04', 'medium', 'ED'),
    ('R-04', 'S02', 'medium', 'AN'),
    ('R-05', 'S02', 'complex', 'AN'),
    ('R-06', 'S10', 'medium', 'DS'),
    ('R-07', 'S05', 'medium', 'AN'),
    ('R-08', 'S05', 'medium', 'ED'),
    ('R-09', 'S04', 'medium', 'ED'),
    ('R-10', 'S04', 'medium', 'ED'),
    ('R-11', 'S02', 'complex', 'AN'),
    ('R-12', 'S07', 'medium', 'DS'),
    ('R-13', 'S03', 'medium', 'AN'),
    ('R-14', 'S06', 'medium', 'ED'),
    ('A-01', 'S08', 'complex', 'AN'),
    ('A-02', 'S08', 'complex', 'AN'),
    ('A-03', 'S04', 'complex', 'AN'),
    ('A-04', 'S05', 'complex', 'ED'),
    ('A-05', 'S03', 'complex', 'AN'),
    ('A-06', 'S04', 'complex', 'AN'),
    ('A-07', 'S09', 'complex', 'AN'),
    ('A-08', 'S03', 'complex', 'ED'),
    ('A-09', 'S01', 'complex', 'DS'),
    ('A-10', 'S03', 'complex', 'ED'),
    ('A-11', 'S08', 'complex', 'AN'),
    ('A-12', 'S06', 'complex', 'AN'),
    ('A-13', 'S10', 'complex', 'DS'),
    ('A-14', 'S05', 'complex', 'DS'),
]


def calculate():
    lock = yaml.safe_load((ROOT / 'dataset.lock').read_text())
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.create_function('CONCAT', -1, lambda *p: None if None in p else ''.join(map(str, p)))
    for entry in lock['files']:
        path = ROOT / 'data' / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'locked CSV checksum mismatch: {entry["path"]}')
        with path.open(newline='', encoding='utf-8-sig') as h:
            reader = csv.DictReader(h)
            headers, rows = reader.fieldnames, list(reader)
        schema = (ROOT / 'kn' / 'object_types' / f'{path.stem}.bkn').read_text()
        types = dict(re.findall(r'^\| (\w+) \| [^|]+ \| (string|integer|float|double|number|boolean) \|', schema, re.M))
        numeric = {k for k, v in types.items() if v in ('integer', 'float', 'double', 'number')}
        cols = ','.join(f'"{h}" {"NUMERIC" if h in numeric else "TEXT"}' for h in headers)
        db.execute(f'CREATE TABLE "{path.stem}" ({cols})')
        db.executemany(f'INSERT INTO "{path.stem}" VALUES ({",".join("?" for _ in headers)})', [[r[h] for h in headers] for r in rows])
    refs = json.loads((HERE / 'reference-queries.json').read_text())
    out = {}
    for qid, ref in refs.items():
        rows = [dict(r) for r in db.execute(ref['sql'])]
        if not rows:
            raise ValueError(f'{qid}: empty reference result')
        out[qid] = rows
    return out


def expected(qid, rows):
    if qid == 'B-01':
        return {r['competition']: r['editions'] for r in rows}
    return {'rows': rows}


def main():
    assert len(Q) == 50 and len({q[0] for q in Q}) == 50
    text = yaml.safe_load((HERE / 'question-text.yaml').read_text(encoding='utf-8'))
    results = calculate()
    meta = dict(schema_version='1.0', set_id='worldcup-business-scenarios-v1', business_date='2022-12-18', prd='docs/PRD.md')
    questions = [dict(id=i, scenario=s, difficulty=text['levels'][lv], role=text['roles'][r], **text['questions'][i]) for i, s, lv, r in Q]
    answers = [dict(id=i, question=text['questions'][i]['question'], expected=expected(i, results[i])) for i, *_ in Q]
    dump = lambda d: yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=200)
    (HERE / 'question-set-v1.yaml').write_text(dump(dict(meta, audience='evaluated_agent', answer_set_access='forbidden', questions=questions)), encoding='utf-8')
    (HERE / 'answer-set-v1.yaml').write_text(dump(dict(meta, generation_method='independent CSV oracle (oracle.py + reference-queries.json)', answers=answers)), encoding='utf-8')
    print(len(Q), Counter(q[2] for q in Q), Counter(q[3] for q in Q), Counter(q[1] for q in Q))


if __name__ == '__main__':
    main()
