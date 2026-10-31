"""World Cup model, baseline and mounted-capability acceptance contracts."""
import importlib.util
import json
from collections import Counter
from pathlib import Path
import re
import yaml

SAMPLE = Path(__file__).resolve().parents[2]


def load(relative):
    spec = importlib.util.spec_from_file_location('worldcup_' + Path(relative).stem, SAMPLE / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_published_metadata_is_english_and_uses_standard_objects():
    for path in SAMPLE.rglob('*'):
        if path.name.startswith('release-notes.') and path.name != 'release-notes.en-US.md':
            continue  # Release-note translations do not change sample content language.
        if path.is_file() and path.suffix in {'.bkn', '.json', '.md', '.yaml', '.py', '.sh'}:
            assert not re.search(r'[\u3400-\u9fff]', path.read_text()), path
    manifest = yaml.safe_load((SAMPLE / 'sample.yaml').read_text())
    assert not manifest['spec']['components']['functions'] and manifest['spec']['components']['skills']
    assert not (SAMPLE / 'vega_sql_execute.openapi.json').exists()


def test_managed_install_entrypoint_is_executable():
    assert (SAMPLE / "run.sh").stat().st_mode & 0o111


def test_model_ids_meet_platform_length_limits():
    for path in (SAMPLE / "kn").rglob("*.bkn"):
        match = re.search(r"^id: (.+)$", path.read_text(), re.M)
        if match:
            assert re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", match.group(1)), path


def test_index_configuration_preserves_unrelated_fields_and_features():
    builder = load('scripts/build_resource_index.py')
    resource = {'schema_definition': [
        {'name': 'key_id', 'type': 'string', 'features': [{'name': 'keyword', 'feature_type': 'keyword', 'ref_property': 'key_id'}]},
        {'name': 'team_name', 'type': 'string', 'features': [{'name': 'keyword', 'feature_type': 'keyword', 'ref_property': 'team_name'}]},
        {'name': 'team_code', 'type': 'string'}],
        'index_config': {'incremental_fields': ['key_id']}}
    schema, config = builder.index_patch(resource, ['team_name'])
    assert config['primary_key_fields'] == ['key_id']
    assert config['incremental_fields'] == ['key_id']
    assert schema[0]['features'][0]['feature_type'] == 'keyword'
    assert {feature['feature_type'] for feature in schema[1]['features']} == {'keyword', 'fulltext'}
    assert schema[2]['name'] == 'team_code'
    try:
        builder.index_patch(resource, ['nonexistent'])
    except ValueError:
        pass
    else:
        raise AssertionError('Missing index field must fail before update')
