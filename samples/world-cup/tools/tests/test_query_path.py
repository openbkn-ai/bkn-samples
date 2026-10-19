"""The World Cup sample reads through the public interface, never Vega internals."""
from pathlib import Path

import yaml

SAMPLE = Path(__file__).resolve().parents[2]


def test_sample_publishes_only_native_functions_on_the_public_interface():
    manifest = yaml.safe_load((SAMPLE / 'sample.yaml').read_text())
    assert manifest['spec']['components']['functions'] is True
    assert manifest['spec']['capabilities']['required'] is True
    assert not list(SAMPLE.rglob('*.openapi.json'))
    for path in [SAMPLE / 'run.sh', *(SAMPLE / 'tools' / 'functions').glob('*.py'), SAMPLE / 'tools' / 'register_functions.py']:
        assert 'vega-backend/in/' not in path.read_text(), path
