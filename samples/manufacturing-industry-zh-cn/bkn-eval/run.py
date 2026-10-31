#!/usr/bin/env python3
"""Checks that the business-scenario test set still matches the delivered data.

The answer set must equal what the independent oracle computes from data/, and the question set
must carry no answers. Run after any data or question change.
"""
import importlib.util
import json
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SET = HERE / 'baselines' / '2026-10-30-business-scenarios-v1'

spec = importlib.util.spec_from_file_location('oracle', SET / 'oracle.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
questions = yaml.safe_load((SET / 'question-set-v1.yaml').read_text(encoding='utf-8'))
answers = yaml.safe_load((SET / 'answer-set-v1.yaml').read_text(encoding='utf-8'))

ids = [q['id'] for q in questions['questions']]
assert len(ids) == 50 == len(set(ids)) and ids == [a['id'] for a in answers['answers']]
assert questions['answer_set_access'] == 'forbidden' and all('expected' not in q for q in questions['questions'])
assert sorted(Counter(q['difficulty'] for q in questions['questions']).values()) == [12, 18, 20]
assert len({q['scenario'] for q in questions['questions']}) == 10
computed = {q['id']: json.loads(json.dumps(q['expected'])) for q in oracle.QUESTIONS}
assert {a['id']: a['expected'] for a in answers['answers']} == computed, 'answer set differs from the oracle'
assert {q['id']: q['question'] for q in questions['questions']} == {q['id']: q['question'] for q in oracle.QUESTIONS}
print('50 business-scenario questions match the oracle computed from the delivered data.')
