"""Managed native BKN installation with portable identities and ownership receipts."""
from concurrent.futures import ThreadPoolExecutor
import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener
import yaml

try:
    from installer.sample_logging import run as run_command
except ImportError:
    run_command = subprocess.run

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'tools/assets'
SAMPLE = 'ecommerce-ops-zh-cn'
KN = 'ecommerce_ops_zh_cn'
BASE = '/api/bkn-backend/v1/knowledge-networks/' + KN
TOOLS = '/api/agent-operator-integration/v1/tool-box'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def entries(value):
    if isinstance(value, list):
        return value
    for key in ('entries', 'data', 'tools', 'instances'):
        if isinstance(value.get(key), list):
            return value[key]
    raise ValueError('expected result collection')


def cli(*args):
    result = run_command(['openbkn', '--json', *map(str, args)], capture_output=True, text=True, timeout=1200)
    if result.returncode:
        # Server error bodies and command arguments can contain credentials.
        raise RuntimeError('OpenBKN operation failed: ' + ' '.join(map(str, args[:2])))
    return json.loads(result.stdout or '{}')


def api(method, path, body=None):
    base = os.environ['BKN_BASE_URL'].rstrip('/')
    token = os.environ['BKN_TOKEN']
    request = Request(base + path, method=method,
                      data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=180) as response:
            raw = response.read()
        return json.loads(raw) if raw else {}
    except HTTPError as error:
        raise RuntimeError('platform API returned HTTP ' + str(error.code) + ' at ' + path.split('?')[0]) from None


def persist(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


class State:
    def __init__(self):
        require(bool(os.environ.get('BKN_SAMPLE_RECEIPT')), 'managed resource receipt is required')
        self.path = Path(os.environ['BKN_SAMPLE_RECEIPT'])
        self.owned = load(self.path) if self.path.exists() else {'toolboxes': [], 'skills': []}
        self.value = self.owned.get('deployment', {'sample': SAMPLE, 'kn_id': KN, 'map': {}, 'phases': []})
        require(self.value['sample'] == SAMPLE and self.value['kn_id'] == KN, 'receipt identity conflict')

    def save(self):
        self.owned['deployment'] = self.value
        persist(self.path, self.owned)

    def remember(self, kind, token, value):
        if value not in self.owned[kind]:
            self.owned[kind].append(value)
        self.value['map'][token] = value
        self.save()

    def render(self, value):
        if isinstance(value, dict):
            return {k: self.render(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.render(v) for v in value]
        if isinstance(value, str):
            for source, target in sorted(self.value['map'].items(), key=lambda item: -len(item[0])):
                value = value.replace(source, target)
        return value

    def phase(self, name):
        if name not in self.value['phases']:
            self.value['phases'].append(name)
        self.save()


def tool_body(definition, state):
    d = state.render(definition)
    if d['metadata_type'] == 'function':
        body = {'metadata_type': 'function', 'function_input': d['function_input']}
    else:
        source = d['openapi']
        spec = source['api_spec']
        responses = {r['status_code']: {k: v for k, v in r.items() if k != 'status_code' and v is not None} for r in spec['responses']}
        operation = {'operationId': d['name'], 'summary': d['name'], 'description': d['description'],
                     'parameters': spec.get('parameters') or [], 'responses': responses}
        if spec.get('request_body', {}).get('content'):
            operation['requestBody'] = spec['request_body']
        document = {'openapi': '3.0.3', 'info': {'title': d['name'], 'version': '0.1.0'},
                    'servers': [{'url': source['server_url']}], 'paths': {source['path']: {source['method'].lower(): operation}}}
        body = {'metadata_type': 'openapi', 'data': document}
    if d.get('global_parameters', {}).get('name'):
        body['global_parameters'] = d['global_parameters']
    if d.get('use_rule'):
        body['use_rule'] = d['use_rule']
    return body


def register_tools(state):
    definitions = load(ASSETS / 'functions.json')
    for box in load(ASSETS / 'toolboxes.json'):
        if box['token'] in state.value['map']:
            require(state.value['map'][box['token']] in state.owned['toolboxes'], 'toolbox ownership conflict')
            continue
        body = {'box_name': box['name'], 'box_desc': box['description'], 'metadata_type': box['metadata_type'], 'source': 'custom', 'box_category': 'data_process'}
        if box.get('service_url'):
            body['box_svc_url'] = box['service_url']
        result = api('POST', TOOLS, body)
        state.remember('toolboxes', box['token'], result['box_id'])
    for d in definitions:
        if d['token'] in state.value['map']:
            continue
        result = api('POST', TOOLS + '/' + state.value['map'][d['box_token']] + '/tool', tool_body(d, state))
        require(not result.get('failure_count') and len(result.get('success_ids', [])) == 1, 'tool creation was incomplete: ' + d['name'])
        state.value['map'][d['token']] = result['success_ids'][0]; state.save()
    # A second pass resolves cross-function references after every tool has an ID.
    for d in definitions:
        bid = state.value['map'][d['box_token']]; tid = state.value['map'][d['token']]
        body = tool_body(d, state)
        if 'function_input' in body:
            body['function_input'].pop('name', None); body['function_input'].pop('description', None)
        body.update(name=d['name'], description=d['description'])
        api('POST', TOOLS + '/' + bid + '/tool/' + tid, body)
        cli('tool', 'enable' if d['status'] == 'enabled' else 'disable', '--toolbox', bid, tid)
    for box in load(ASSETS / 'toolboxes.json'):
        cli('toolbox', 'publish', state.value['map'][box['token']])
    state.phase('tools')


def register_skills(state):
    for s in load(ASSETS / 'skills.json'):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / s['name']; shutil.copytree(ROOT / s['directory'], directory)
            for path in directory.rglob('*'):
                if path.is_file():
                    try:
                        path.write_text(state.render(path.read_text(encoding='utf-8')), encoding='utf-8')
                    except UnicodeDecodeError:
                        pass
            if s['token'] in state.value['map']:
                sid = state.value['map'][s['token']]
                require(sid in state.owned['skills'], 'Skill ownership conflict')
                cli('skill', 'update-package', sid, directory)
            else:
                created = cli('skill', 'register', directory, '--source', 'custom')
                sid = created.get('skill_id') or created.get('id') or created.get('data', {}).get('skill_id')
                require(bool(sid), 'Skill registration did not return an identity')
                state.remember('skills', s['token'], sid)
            cli('skill', 'set-status', sid, 'published')
    state.phase('skills')


def bind_capabilities(state):
    mounts = [{'capability_type': 'function', 'box_id': state.value['map'][d['box_token']],
               'capability_id': state.value['map'][d['token']], 'comment': d['comment']}
              for d in load(ASSETS / 'functions.json')]
    mounts += [{'capability_type': 'skill', 'capability_id': state.value['map'][s['token']], 'comment': s['comment']}
               for s in load(ASSETS / 'skills.json')]
    mounts += [{k: v for k, v in e.items() if k != 'name'} for e in load(ASSETS / 'external-mounts.json')]
    api('POST', BASE + '/capabilities', {'capabilities': mounts})
    state.phase('mounts')


def install_model(state, tags):
    with tempfile.TemporaryDirectory() as temp:
        dest = Path(temp) / 'kn'; shutil.copytree(ROOT / 'kn', dest)
        for file in dest.rglob('*'):
            if file.is_file():
                file.write_text(state.render(file.read_text(encoding='utf-8')), encoding='utf-8')
        file = dest / 'network.bkn'
        _, head, body = file.read_text(encoding='utf-8').split('---', 2)
        meta = yaml.safe_load(head); meta['tags'] = sorted(tags | {'电商', '经营决策'})
        file.write_text('---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---' + body, encoding='utf-8')
        cli('bkn', 'validate', dest)
        cli('bkn', 'push', dest, '--import-mode', 'overwrite')
    state.phase('model')


def install_events(state):
    existing = {e['code']: e for e in entries(api('GET', BASE + '/event-types'))}
    for event in state.render(load(ASSETS / 'events.json')):
        code = event['code']
        api('PUT' if code in existing else 'POST', BASE + '/event-types' + ('/' + code if code in existing else ''), event)
    for group in load(ASSETS / 'groups.json'):
        ids = group.get('object_type_ids') or []
        if ids:
            api('POST', BASE + '/concept-groups/' + group['id'] + '/object-types?branch=main&strict_mode=true', [{'id': i} for i in ids])
    state.phase('events')


def scan_events(state):
    functions = {d['name']: d for d in load(ASSETS / 'functions.json')}
    recorder = functions['ecommerce_record_business_event_check']
    for event in load(ASSETS / 'events.json'):
        if event.get('rule_tool'):
            result = api('POST', BASE + '/event-types/' + event['code'] + '/check')
            require(result.get('status') not in ('failed', 'unknown'), 'native event check incomplete')
        elif event['code'] in ('purchase_expected_receipt_gap', 'payment_failure_unrecovered', 'logistics_tracking_stalled', 'return_received_processing_wait'):
            result = cli('function', 'execute', state.value['map'][recorder['token']], '--toolbox', state.value['map'][recorder['box_token']], '--body', json.dumps({'kn_id': KN, 'event_type': event['code']}))
            require(result.get('status_code') == 200 and result.get('body', {}).get('exit_code') == 0 and result.get('body', {}).get('result', {}).get('status') == 'complete', 'business event detector failed or incomplete')
        elif event['code'] == 'coupon_invalid_validity':
            # Preserve the existing application's exact predicate, without a
            # Top-N graph query standing in for a complete coverage scan.
            binding = load(ASSETS / 'bindings.json')['user_coupon']
            rid = state.value['map'][binding['resource_token']]
            hits, covered = [], []
            for offset in range(0, 250000, 5000):
                result = api('POST', '/api/vega-backend/v1/resources/query', {
                    'query': 'SELECT user_coupon_id,coupon_code,status,user_id,receive_time,expire_time FROM {{' + rid + '}} ORDER BY user_coupon_id',
                    'query_format': 'sql', 'paging': {'mode': 'single', 'limit': 5000, 'offset': offset}})
                require(not result.get('warnings') and not result.get('limited'), 'coupon source scan incomplete')
                rows = entries(result)
                for row in rows:
                    if row.get('receive_time') and row.get('expire_time'):
                        covered.append(str(row['user_coupon_id']))
                        if row['expire_time'] < row['receive_time']:
                            hits.append({'key': str(row['user_coupon_id']), 'name': str(row['coupon_code']),
                                         'attributes': {k: {'key': str(row[f])[:250], 'label': str(row[f])[:256]} for k, f in [('coupon_status', 'status'), ('user_id', 'user_id'), ('received_at', 'receive_time'), ('expires_at', 'expire_time')] if row.get(f) is not None}})
                if len(rows) < 5000:
                    break
            else:
                raise ValueError('coupon coverage exceeds bounded full scan')
            check_tool = functions['ecommerce_coupon_validity_anomalies']['function_input']
            api('POST', BASE + '/rule-checks', {'event_type': event['code'], 'rule_version': hashlib.sha256(check_tool['code'].encode()).hexdigest()[:16], 'status': 'ok', 'hits': hits, 'covered': covered})
    state.phase('initial-event-check')


def verify(state, tags):
    network = api('GET', BASE + '?mode=export')
    require(tags <= set(network.get('tags', [])), 'network ownership differs')
    contract = load(ROOT / 'model-contract.json')
    for collection, key in [('object_types', 'objects'), ('relation_types', 'relations'), ('action_types', 'actions'), ('value_types', 'value_types')]:
        require(len(network[collection]) == contract['counts'][key], collection + ' count differs')
    objects = {o['id']: o for o in network['object_types']}
    for oid, binding in contract['bindings'].items():
        require(objects[oid]['data_source']['id'] == state.value['map'][binding['resource_token']], 'resource binding differs: ' + oid)
        actual = {p['name']: p.get('mapped_field') for p in objects[oid]['data_properties']}
        require(actual == binding['fields'], 'field mapping differs: ' + oid)
    for oid, expected in state.render(load(ASSETS / 'object-semantics.json')).items():
        for key, value in expected.items():
            require(objects[oid].get(key) == value, 'object definition differs: ' + oid + '/' + key)
    actions = {a['id']: a for a in network['action_types']}
    for action in state.render(load(ASSETS / 'actions.json')):
        for key in ('parameters', 'action_source', 'condition', 'operation_config'):
            require(actions[action['id']].get(key) == action.get(key), 'action definition differs: ' + action['id'] + '/' + key)
    require(len(entries(api('GET', BASE + '/object-metrics?limit=500'))) == 67, 'metric count differs')
    require(len(entries(api('GET', BASE + '/event-types'))) == 7, 'event class count differs')
    require(len(entries(api('GET', BASE + '/capabilities?limit=500'))) == 53, 'capability count differs')
    for baseline in state.render(load(ASSETS / 'business-baseline.json')):
        response = api('POST', '/api/vega-backend/v1/resources/query', {'query': baseline['query'], 'query_format': 'sql', 'paging': {'mode': 'single', 'limit': 2, 'offset': 0}})
        require(not response.get('warnings') and not response.get('limited'), 'business baseline result incomplete')
        actual = entries(response); require(len(actual) == 1, 'business aggregate missing')
        for key, value in baseline['expected'].items():
            require((actual[0].get(key) is None if value is None else actual[0].get(key) is not None and Decimal(str(actual[0][key])) == Decimal(str(value))), 'business result differs: ' + baseline['name'] + '/' + key)
    return {'model-and-bindings': True, 'metrics': True, 'event-types': True, 'capabilities': True, 'business-baseline': True}


def main():
    mode = sys.argv[1]; require(mode in ('install', 'verify'), 'expected install or verify')
    payload = load(os.environ['BKN_SAMPLE_INPUT'])
    require(payload['sample'] == SAMPLE and payload['knowledgeNetwork']['id'] == KN and payload['database']['name'] == KN, 'managed installation identity differs')
    tags = {'bkn-samples', 'bkn-sample-' + SAMPLE, 'bkn-samples-version-' + payload['version'].replace('.', '-')}
    state = State()
    if mode == 'install':
        listing = entries(cli('vega', 'resource', 'list', '--catalog-id', payload['catalog']['id'], '--category', 'table', '--limit', '100'))
        for binding in load(ASSETS / 'bindings.json').values():
            found = [r for r in listing if r['name'].rsplit('.', 1)[-1] == binding['table']]
            require(len(found) == 1, 'missing or ambiguous table resource: ' + binding['table'])
            state.value['map'][binding['resource_token']] = found[0]['id']
        state.save()
        # Never adopt or overwrite a network without matching sample ownership.
        known = entries(cli('bkn', 'list', '--limit', '1000'))
        existing = next((n for n in known if n['id'] == KN), None)
        if existing:
            require(tags <= set(existing.get('tags', [])), 'network ownership conflict')
        else:
            bootstrap = state.render(load(ASSETS / 'bootstrap.json'))
            bootstrap['tags'] = sorted(tags)
            api('POST', '/api/bkn-backend/v1/knowledge-networks?strict_mode=false', bootstrap)
        if 'tools' not in state.value['phases']:
            register_tools(state)
        if 'model' not in state.value['phases']:
            install_model(state, tags)
        if 'skills' not in state.value['phases']:
            register_skills(state)
        if 'mounts' not in state.value['phases']:
            bind_capabilities(state)
        if 'events' not in state.value['phases']:
            install_events(state)
        if 'indices' not in state.value['phases']:
            bindings = load(ASSETS / 'bindings.json')
            for oid, config in load(ASSETS / 'indices.json').items():
                rid = state.value['map'][bindings[oid]['resource_token']]
                current = entries(api('GET', '/api/vega-backend/v1/resources/' + rid))[0]
                require(current['catalog_id'] == payload['catalog']['id'], 'resource catalog ownership differs')
                body = {key: current[key] for key in ('name', 'catalog_id', 'tags', 'description', 'category', 'enabled')}
                body.update(config); body['expected_update_time'] = current['update_time']
                api('PUT', '/api/vega-backend/v1/resources/' + rid, body)
            resource_ids = sorted({state.value['map'][b['resource_token']] for b in bindings.values()})
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda rid: cli('vega', 'resource', 'build', rid, '--wait', '--timeout', '900'), resource_ids))
            state.phase('indices')
        if 'initial-event-check' not in state.value['phases']:
            scan_events(state)
    checks = verify(state, tags)
    summary = hashlib.sha256(json.dumps(state.value['map'], sort_keys=True).encode()).hexdigest()
    result = {'ok': True, 'stage': 'platform-' + mode, 'resources': {'catalogId': payload['catalog']['id'], 'knowledgeNetworkId': KN,
              'ownedExecution': state.owned, 'capabilitySummary': summary}, 'checks': [{'name': k, 'ok': v} for k, v in checks.items()], 'degrade': [], 'message': ''}
    persist(Path(os.environ['BKN_SAMPLE_OUTPUT']), result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        result = {'ok': False, 'code': 'ecommerce_sample_hook_failed', 'message': type(error).__name__ + ': ' + str(error)[:300]}
        if os.environ.get('BKN_SAMPLE_OUTPUT'):
            persist(Path(os.environ['BKN_SAMPLE_OUTPUT']), result)
        print(json.dumps(result)); sys.exit(1)
