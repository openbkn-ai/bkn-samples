"""Consume public Object Metrics V1 MCP results without changing their meaning.

Pass a tools/call adapter as call(tool_name, arguments) returning the decoded tool
payload. Preserve its structuredContent, or decode its JSON text with
json.loads(text, parse_float=Decimal) before calling these helpers. Tool errors
must raise; they must never be converted to empty successful results.
"""
from copy import deepcopy
from decimal import Decimal


def metric_result(payload, *, metric_id, version):
    if payload.get('metric_id') != metric_id or payload.get('version') != version:
        raise ValueError('Metric result identity or version differs')
    status = payload.get('status')
    if status not in ('ok', 'no_data', 'partial', 'unavailable'):
        raise ValueError('Unknown metric result status')
    if not isinstance(payload.get('entries'), list) or not isinstance(payload.get('total_count'), int):
        raise ValueError('Missing result entries or total_count')
    if payload['total_count'] < len(payload['entries']):
        raise ValueError('Result count is inconsistent')
    rows = []
    for entry in payload['entries']:
        if entry.get('status') not in ('ok', 'no_data', 'unavailable'):
            raise ValueError('Unknown metric entry status')
        value = entry.get('value')
        display = entry.get('display_value')
        if value is not None and isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            if display is None:
                display = str(value)
            if not Decimal(str(value)).is_finite() or not Decimal(display).is_finite():
                raise ValueError('Non-finite metric result')
        rows.append({**entry, 'display_value': display})
    return {'status': status, 'rows': rows, 'model': payload.get('model'),
            'warnings': payload.get('warnings', []), 'total_count': payload['total_count'],
            'next_cursor': payload.get('next_cursor'),
            'complete': status in ('ok', 'no_data') and all(row['status'] != 'unavailable' for row in rows) and not payload.get('warnings')
                        and not payload.get('next_cursor') and len(rows) == payload['total_count']}


def query_all(call, arguments, *, max_pages=1000):
    """Fetch complete pages; keep query scope and opaque cursors unchanged."""
    request = deepcopy(arguments)
    request['response_format'] = 'json'
    original = deepcopy(request.get('query', {}))
    rows, seen, expected_count = [], set(), None
    for _ in range(max_pages):
        payload = call('query_metric', request)
        result = metric_result(payload, metric_id=request['metric_id'], version=request['version'])
        if payload.get('kn_id') != request['kn_id']:
            raise ValueError('Metric network differs')
        if expected_count is not None and result['total_count'] != expected_count:
            raise ValueError('Results changed while paging; restart from the first page')
        expected_count = result['total_count']
        rows.extend({**row, 'source_query': deepcopy(request.get('query', {}))} for row in result['rows'])
        cursor = result['next_cursor']
        if result['status'] not in ('ok', 'no_data') or result['warnings'] or any(row['status'] == 'unavailable' for row in result['rows']):
            return {**result, 'rows': rows, 'complete': False}
        if not cursor:
            if len(rows) != expected_count:
                raise ValueError('Incomplete result without a continuation cursor')
            return {**result, 'rows': rows, 'complete': True}
        if not result['rows'] or not isinstance(cursor, str) or cursor in seen:
            raise ValueError('Empty or repeated result continuation')
        seen.add(cursor)
        request['query'] = {**original, 'cursor': cursor}
    raise ValueError('Metric page limit reached; result is incomplete')


def participants_all(call, arguments, entry, *, max_pages=50):
    """Keep the selected query and server bucket key; never infer contributions."""
    if 'participants' not in entry.get('available_actions', []) or not entry.get('bucket_key'):
        raise ValueError('Selected result does not expose participants')
    request = {k: deepcopy(arguments[k]) for k in ('kn_id', 'metric_id', 'version')}
    request.update(query=deepcopy(entry.get('source_query', arguments.get('query', {}))), bucket_key=entry['bucket_key'],
                   page_size=100, response_format='json')
    rows, seen = [], set()
    for _ in range(max_pages):
        payload = call('drill_through_metric', request)
        if any(payload.get(k) != request[k] for k in ('kn_id', 'metric_id', 'version')):
            raise ValueError('Participant result identity differs')
        if payload.get('status') not in ('ok', 'partial') or not isinstance(payload.get('participants'), list):
            raise ValueError('Invalid participant result')
        rows.extend(payload['participants'])
        if payload['status'] == 'partial' or payload.get('warnings'):
            return {**payload, 'participants': rows, 'complete': False}
        cursor = payload.get('next_cursor')
        if not cursor:
            return {**payload, 'participants': rows, 'complete': True}
        if not payload['participants'] or not isinstance(cursor, str) or cursor in seen:
            raise ValueError('Empty or repeated participant continuation')
        seen.add(cursor)
        request['cursor'] = cursor
    raise ValueError('Participant page limit reached; result is incomplete')
