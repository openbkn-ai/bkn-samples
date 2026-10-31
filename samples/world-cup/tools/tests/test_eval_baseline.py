"""Contracts for the Chinese World Cup business-scenario baseline."""
import importlib.util
import json
from collections import Counter
from pathlib import Path
import yaml

SAMPLE = Path(__file__).resolve().parents[2]


BASELINE = SAMPLE / 'bkn-eval' / 'baselines' / '2026-10-31-business-scenarios-v1'


def _oracle():
    spec = importlib.util.spec_from_file_location('worldcup_oracle_' + SAMPLE.name.replace('-', '_'), BASELINE / 'oracle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_answer_set_is_what_the_oracle_computes_from_the_locked_csv():
    oracle = _oracle()
    computed = oracle.calculate()
    answers = yaml.safe_load((BASELINE / 'answer-set-v1.yaml').read_text(encoding='utf-8'))['answers']
    assert {a['id']: a['expected'] for a in answers} == {qid: oracle.expected(qid, rows) for qid, rows in computed.items()}


def test_question_set_is_business_language_without_answers():
    questions = yaml.safe_load((BASELINE / 'question-set-v1.yaml').read_text(encoding='utf-8'))
    items = questions['questions']
    assert questions['answer_set_access'] == 'forbidden' and all('expected' not in q for q in items)
    assert len({q['id'] for q in items}) == 50 and len({q['scenario'] for q in items}) == 10
    assert sorted(Counter(q['difficulty'] for q in items).values()) == [12, 18, 20]
    tables = {t for ref in json.loads((BASELINE / 'reference-queries.json').read_text()).values() for t in ref['tables']}
    assert tables == {p.stem for p in (SAMPLE / 'data').glob('*.csv')}


def test_both_languages_share_data_and_answers():
    english = SAMPLE.parent / 'world-cup-en'
    assert (SAMPLE / 'dataset.lock').read_bytes() == (english / 'dataset.lock').read_bytes()
    other = english / BASELINE.relative_to(SAMPLE)
    assert (BASELINE / 'oracle.py').read_bytes() == (other / 'oracle.py').read_bytes()
    assert (BASELINE / 'reference-queries.json').read_bytes() == (other / 'reference-queries.json').read_bytes()
    cn = yaml.safe_load((BASELINE / 'answer-set-v1.yaml').read_text(encoding='utf-8'))['answers']
    en = yaml.safe_load((other / 'answer-set-v1.yaml').read_text(encoding='utf-8'))['answers']
    assert [a['expected'] for a in cn] == [a['expected'] for a in en]


def test_sample_publishes_skills_and_no_sql_tool():
    manifest = yaml.safe_load((SAMPLE / 'sample.yaml').read_text())
    assert manifest['spec']['components']['skills'] and not manifest['spec']['components']['functions']
    assert not (SAMPLE / 'vega_sql_execute.openapi.json').exists() and 'toolbox' not in (SAMPLE / 'run.sh').read_text()
