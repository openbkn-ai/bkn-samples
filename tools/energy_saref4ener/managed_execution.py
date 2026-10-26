"""Bounded managed SDK loader; no local data or credential files."""
import datetime
import json
import re
from decimal import Decimal

MAX_ROWS = 20000
PAGE_SIZE = 1000
MAX_OUTPUT_BYTES = 1024 * 1024


def source_value(value, kind):
    if value is None:
        return ''
    if kind == 'date':
        if isinstance(value, datetime.datetime):
            if value.time() != datetime.time():
                raise ValueError('NON_MIDNIGHT_SOURCE_DATE')
            return value.date().isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        value = str(value)
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}T00:00:00(?:\.0+)?(?:Z|[+-]\d{2}:\d{2})?', value):
            value = value[:10]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('INVALID_SOURCE_DATE')
        datetime.date.fromisoformat(value)
        return value
    if isinstance(value, (dict, list, tuple)):
        raise ValueError('INVALID_SOURCE_CELL')
    return str(value)


def load_sources(query, kn_id, contract, scope, operation=None):
    tables = {}
    for table, spec in contract['object_types'].items():
        rows, seen, offset = [], set(), 0
        pk = spec['primary_key']
        while True:
            limit = min(PAGE_SIZE, MAX_ROWS-offset) if offset < MAX_ROWS else 1
            payload = query(kn_id=kn_id, ot_id=table, limit=limit, offset=offset,
                            sort=[{'field': pk, 'direction': 'asc'}])
            if not isinstance(payload, dict) or not isinstance(payload.get('datas'), list):
                raise ValueError('INVALID_SOURCE:' + table)
            if payload.get('isError') or payload.get('error') or payload.get('errors') or payload.get('partial') or payload.get('partial_reasons') or payload.get('exit_code', 0) != 0 or payload.get('success') is False or payload.get('error_code') not in (None, '', 0, '0'):
                raise ValueError('PARTIAL_OR_FAILED_SOURCE:' + table)
            for receipt in (payload.get('bkn_receipt'), payload.get('receipt')):
                if isinstance(receipt, dict) and (receipt.get('partial_reasons') or receipt.get('receipt_status') in {'pending', 'failed'}):
                    raise ValueError('PARTIAL_OR_FAILED_SOURCE_RECEIPT:' + table)
            batch = payload['datas']
            if len(batch) > limit or offset+len(batch) > MAX_ROWS:
                raise ValueError('SOURCE_BOUND_EXCEEDED:' + table)
            for row in batch:
                if not isinstance(row, dict) or not row.get(pk):
                    raise ValueError('INVALID_SOURCE_ROW:' + table)
                normalized = {f: source_value(row.get(f), kind) for f, kind in spec['fields'].items()}
                key = normalized[pk]
                if key in seen:
                    raise ValueError('DUPLICATE_SOURCE_KEY:' + table)
                seen.add(key)
                rows.append(normalized)
            offset += len(batch)
            total = payload.get('total_count')
            if total is not None:
                if isinstance(total, bool) or not str(total).isdigit() or int(total) > MAX_ROWS or offset > int(total):
                    raise ValueError('INVALID_SOURCE_COUNT:' + table)
                if offset == int(total):
                    break
                if len(batch) < limit:
                    raise ValueError('SOURCE_COUNT_MISMATCH:' + table)
            elif len(batch) < limit:
                break
        tables[table] = rows
    return tables


def run_request(query, kn_id, contract, operation, scope, execute):
    validator = execute.__globals__.get('validate')
    if not callable(validator):
        raise ValueError('MISSING_SCOPE_VALIDATOR')
    validator(operation, scope)
    tables = load_sources(query, kn_id, contract, scope, operation)
    result = execute(operation, tables, contract, scope)
    result['data_source'] = {'knowledge_network_id': kn_id, 'loaded_counts': {t: len(rows) for t, rows in tables.items()}}
    if len(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('OUTPUT_BOUND_EXCEEDED_REDUCE_SCOPE')
    return result
