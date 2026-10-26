"""Bind only this sample's owned draft-only action; never execute it."""
import json
import os
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _matches(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_matches(a, b) for a, b in zip(actual, expected))
    return actual == expected


def bind_draft_action(call, kn_id, box_id, tool_id):
    manifest = yaml.safe_load((ROOT / 'sample.yaml').read_text())
    expected_kn = manifest['spec']['knowledgeNetwork']['id']
    if kn_id != expected_kn:
        raise ValueError('draft action binding requires the sample knowledge network')
    network = call(['bkn', 'get', kn_id])
    tags = {t for t in os.environ.get('BKN_SAMPLE_OWNERSHIP_TAGS', '').split(',') if t}
    tags |= {'bkn-samples', 'bkn-sample-' + manifest['metadata']['name']}
    if not tags <= set(network.get('tags') or []):
        raise ValueError('draft action network ownership conflict')
    action_id = kn_id + '_act_replenishment_draft'
    definition = next(a for a in json.loads((ROOT / 'kn' / (kn_id + '.json')).read_text())['action_types'] if a['id'] == action_id)
    current = call(['bkn', 'action-type', 'get', kn_id, action_id])
    if isinstance(current, list):
        if len(current) != 1:raise ValueError('draft action identity is ambiguous')
        current = current[0]
    if isinstance(current, dict) and isinstance(current.get('entries'), list):
        if len(current['entries']) != 1:raise ValueError('draft action identity is ambiguous')
        current = current['entries'][0]
    if not isinstance(current, dict):raise ValueError('invalid draft action response')
    for key, value in definition.items():
        if key != 'action_source' and not _matches(current.get(key), value):
            raise ValueError('draft action definition ownership conflict: ' + key)
    expected_source = {'type': 'tool', 'box_id': box_id, 'tool_id': tool_id}
    source = current.get('action_source') or {}
    if not isinstance(source, dict):raise ValueError('invalid draft action source')
    if source.get("mcp_id") or source.get("tool_name"):raise ValueError("draft action contains another source kind")
    if _matches(source, expected_source):return
    if source.get('box_id') or source.get('tool_id') or source.get('type') not in (None, '', 'tool'):
        raise ValueError('draft action already refers to a different tool')
    body = {**definition, 'action_source': expected_source}
    call(['call', f'/api/bkn-backend/v1/knowledge-networks/{kn_id}/action-types/{action_id}',
          '-X', 'PUT', '-d', json.dumps(body, ensure_ascii=False)])
