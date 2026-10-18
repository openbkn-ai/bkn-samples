"""Contracts for the Chinese World Cup scenario baseline."""
import importlib.util
import json
from pathlib import Path
import yaml

SAMPLE = Path(__file__).resolve().parents[2]
EVAL = SAMPLE / 'bkn-eval'


def test_recalculated_chinese_reference_matches_frozen_csv():
    spec = importlib.util.spec_from_file_location('worldcup_cn_reference', EVAL / 'scripts/recalculate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.calculate() == yaml.safe_load(module.ANSWER.read_text())


def test_question_distribution_and_complete_table_coverage():
    questions = yaml.safe_load((EVAL / 'datasets/question-set-v1.yaml').read_text())['questions']
    cases = json.loads((EVAL / 'gold/cases.json').read_text())
    assert len({q['id'] for q in questions}) == 50
    assert {category: sum(q['category'] == category for q in questions) for category in 'BJRA'} == {'B': 10, 'J': 12, 'R': 14, 'A': 14}
    assert {q['id'] for q in questions} == {q['id'] for q in cases}
    assert all(q['output_fields'] and q['row_order'] for q in questions)
    assert {table for case in cases for table in case['tables']} == {p.stem for p in (SAMPLE / 'data').glob('*.csv')}


def test_business_answers_match_the_same_locked_snapshot():
    english = SAMPLE.parent / 'world-cup-en'
    assert (SAMPLE / 'dataset.lock').read_bytes() == (english / 'dataset.lock').read_bytes()
    cn = yaml.safe_load((EVAL / 'gold/answer-set-v1.yaml').read_text())
    en = yaml.safe_load((english / 'bkn-eval/gold/answer-set-v1.yaml').read_text())
    assert cn['source_commit'] == en['source_commit']
    assert cn['row_counts'] == en['row_counts']
    assert cn['answers'] == en['answers']
    assert sum(cn['row_counts'].values()) == 81200


def test_grading_preserves_identity_and_requires_ordered_complete_results():
    spec = importlib.util.spec_from_file_location('worldcup_cn_grader', EVAL / 'scripts/grade_answers.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.same_value(3, '3', 0.0005)
    assert not module.same_value(3, 3.0001, 0.0005)
    assert not module.same_value('P-00001', 'P-1', 0.0005)
    assert not module.same_value(2.5, 'nan', 0.0005)
    expected = [{'player_id': 'P-00001', 'ranking': 1}, {'player_id': 'P-00002', 'ranking': 1}]
    assert not module.row_differences(expected, expected, 0.0005)
    assert module.row_differences(expected, list(reversed(expected)), 0.0005)
    assert module.row_differences(expected, expected[:1], 0.0005)
    report = module.grade([])
    assert report['correct'] == 0 and report['total'] == 50


def test_sample_publishes_no_custom_query_tool():
    manifest = yaml.safe_load((SAMPLE / 'sample.yaml').read_text())
    assert manifest['spec']['components']['functions'] is False
    assert manifest['spec']['capabilities']['required'] is False
    assert not list(SAMPLE.rglob('*.openapi.json'))
    assert 'vega-backend/in/' not in (SAMPLE / 'run.sh').read_text()
