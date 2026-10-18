"""The World Cup sample queries through standard MCP tools, never Vega internals."""
from pathlib import Path

import yaml

SAMPLE = Path(__file__).resolve().parents[2]


def test_sample_publishes_no_custom_query_tool():
    manifest = yaml.safe_load((SAMPLE / 'sample.yaml').read_text())
    assert manifest['spec']['components']['functions'] is False
    assert manifest['spec']['capabilities']['required'] is False
    assert not list(SAMPLE.rglob('*.openapi.json'))
    assert 'vega-backend/in/' not in (SAMPLE / 'run.sh').read_text()
