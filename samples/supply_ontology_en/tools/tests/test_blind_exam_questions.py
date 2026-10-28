"""Candidate delivery contains questions, never examiner rules or hints."""
from pathlib import Path
import yaml

PACK=Path(__file__).resolve().parents[2]

def test_core_candidate_file_contains_only_fifty_id_question_pairs():
    q=yaml.safe_load((PACK/'bkn-eval/datasets/sample-question-set-v1.yaml').read_text())
    assert set(q)=={'questions'}
    assert len(q['questions'])==50
    assert len({x['id'] for x in q['questions']})==50
    assert all(set(x)=={'id','question'} for x in q['questions'])

def test_candidate_questions_do_not_teach_algorithms_or_tool_selection():
    q=yaml.safe_load((PACK/'bkn-eval/datasets/sample-question-set-v1.yaml').read_text())
    text=' '.join(x['question'] for x in q['questions']).lower()
    for hint in ['allocate finished stock first','at each level','array order','one shared pool',
                 'shared stock pool','deduct component stock','own usage ratio','select one candidate',
                 'max(qty-actqty,0)','production_available','deterministic allocation policy',
                 'query the full structure','do not substitute','business date:','2026-08-25']:
        assert hint not in text, hint

def test_exam_time_statement_is_separate_from_candidate_questions():
    text=(PACK/'bkn-eval/exam-time-reference.txt').read_text()
    assert '2026-08-25' in text and '2026-10-12' in text
    for hint in ['allocation','substitution','warehouse_scope','Available','tool','function','metric']:
        assert hint not in text
