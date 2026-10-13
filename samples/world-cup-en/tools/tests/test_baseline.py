"""World Cup model, baseline and mounted-capability acceptance contracts."""
import importlib.util
import json
from pathlib import Path
import re
import yaml

SAMPLE = Path(__file__).resolve().parents[2]


def load(relative):
    spec = importlib.util.spec_from_file_location('worldcup_' + Path(relative).stem, SAMPLE / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recalculated_answers_match_locked_reference():
    oracle = load('bkn-eval/scripts/recalculate.py')
    assert oracle.calculate() == yaml.safe_load(oracle.ANSWER.read_text())


def test_scenario_distribution_and_complete_table_coverage():
    questions = yaml.safe_load((SAMPLE / 'bkn-eval/datasets/question-set-v1.yaml').read_text())['questions']
    cases = json.loads((SAMPLE / 'bkn-eval/gold/cases.json').read_text())
    assert len({q['id'] for q in questions}) == 50
    assert {category: sum(q['category'] == category for q in questions) for category in 'BJRA'} == {'B': 10, 'J': 12, 'R': 14, 'A': 14}
    assert {q['id'] for q in questions} == {q['id'] for q in cases}
    assert {table for case in cases for table in case['tables']} == {p.stem for p in (SAMPLE / 'data').glob('*.csv')}


def test_published_metadata_is_english_and_uses_standard_objects():
    for path in SAMPLE.rglob('*'):
        if path.is_file() and path.suffix in {'.bkn', '.json', '.md', '.yaml', '.py', '.sh'}:
            assert not re.search(r'[\u3400-\u9fff]', path.read_text()), path
    manifest = yaml.safe_load((SAMPLE / 'sample.yaml').read_text())
    assert not manifest['spec']['components']['functions']
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
