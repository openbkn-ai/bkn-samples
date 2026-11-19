"""Load and verify the frozen typed snapshot using the installer's scoped account."""
import base64
import datetime as dt
import decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = 'ecommerce-ops-zh-cn'
DATABASE = 'ecommerce_ops_zh_cn'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def decode(value):
    if not isinstance(value, dict):
        return value
    require(len(value) == 1, 'invalid typed value')
    kind, value = next(iter(value.items()))
    casts = {'$decimal': decimal.Decimal, '$date': dt.date.fromisoformat,
             '$datetime': dt.datetime.fromisoformat, '$time': dt.time.fromisoformat,
             '$bytes': base64.b64decode, '$timedelta': lambda x: dt.timedelta(seconds=float(x))}
    require(kind in casts, 'unknown typed value')
    return casts[kind](value)


def encode(value):
    if isinstance(value, decimal.Decimal):
        return {'$decimal': str(value)}
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return {'$' + type(value).__name__: value.isoformat()}
    if isinstance(value, dt.timedelta):
        return {'$timedelta': str(value.total_seconds())}
    if isinstance(value, bytes):
        return {'$bytes': base64.b64encode(value).decode()}
    raise TypeError(type(value).__name__)


def quote(name):
    require(bool(re.fullmatch(r'[A-Za-z0-9_]+', name)), 'invalid SQL identifier')
    return '`' + name + '`'


def fixture():
    schema = json.loads((ROOT / 'db/schema.json').read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'dataset.lock').read_text(encoding='utf-8'))
    require(set(lock['files']) == {t['file'] for t in schema['tables'].values()}, 'snapshot inventory differs')
    for spec in schema['tables'].values():
        path = ROOT / 'data' / spec['file']
        require('sha256:' + hashlib.sha256(path.read_bytes()).hexdigest() == lock['files'][path.name], 'snapshot file digest differs')
    return schema, hashlib.sha256((ROOT / 'dataset.lock').read_bytes()).hexdigest()


def verify_table(cursor, table, spec):
    fields = [c['Field'] for c in spec['columns']]
    order = spec['primary_keys'] or fields
    cursor.execute('SELECT ' + ','.join(map(quote, fields)) + ' FROM ' + quote(table) + ' ORDER BY ' + ','.join(map(quote, order)))
    digest = hashlib.sha256()
    count = 0
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
        for row in rows:
            digest.update((json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=encode) + '\n').encode())
            count += 1
    require(count == spec['rows'], 'row count differs: ' + table)
    require(digest.hexdigest() == spec['logical_sha256'], 'business data differs: ' + table)


def main():
    import pymysql
    mode = sys.argv[1]
    require(mode in ('init', 'verify'), 'expected init or verify')
    require(os.environ.get('BKN_SAMPLE_ID') == SAMPLE and os.environ['MYSQL_DATABASE'] == DATABASE, 'database ownership differs')
    schema, digest = fixture()
    options = dict(user=os.environ['MYSQL_USER'], password=os.environ['MYSQL_PASSWORD'], database=DATABASE,
                   charset='utf8mb4', connect_timeout=15, read_timeout=180, write_timeout=180)
    if os.environ.get('MYSQL_UNIX_SOCKET'):
        options['unix_socket'] = os.environ['MYSQL_UNIX_SOCKET']
    else:
        options.update(host=os.environ['MYSQL_HOST'], port=int(os.environ['MYSQL_PORT']))
    with pymysql.connect(**options) as connection, connection.cursor() as q:
        session = schema['session']; offset = session['utc_offset_seconds']
        sign = '+' if offset >= 0 else '-'; hours, remainder = divmod(abs(offset), 3600)
        q.execute('SET SESSION time_zone=%s', (f'{sign}{hours:02}:{remainder // 60:02}',))
        q.execute('SET SESSION sql_mode=%s', (session['sql_mode'],))
        q.execute('SHOW TABLES')
        existing = {r[0] for r in q.fetchall()}
        if mode == 'init' and not existing:
            q.execute('CREATE TABLE bkn_sample_meta (sample_id VARCHAR(64) PRIMARY KEY,sample_version VARCHAR(32),status VARCHAR(16),data_digest VARCHAR(64))')
            q.execute('INSERT INTO bkn_sample_meta VALUES (%s,%s,%s,%s)', (SAMPLE, os.environ['BKN_SAMPLE_VERSION'], 'loading', digest))
            connection.commit()
        q.execute('SELECT sample_version,status,data_digest FROM bkn_sample_meta WHERE sample_id=%s', (SAMPLE,))
        meta = q.fetchone()
        require(meta is not None and meta[0] == os.environ['BKN_SAMPLE_VERSION'] and meta[2] == digest, 'database is not owned by this package')
        require(mode == 'init' or meta[1] == 'ready', 'snapshot loading incomplete')
        q.execute('SET FOREIGN_KEY_CHECKS=0')
        if mode == 'init' and meta[1] != 'ready':
            q.execute('SHOW TABLES'); existing = {r[0] for r in q.fetchall()}
            require(existing <= set(schema['tables']) | {'bkn_sample_meta'}, 'unexpected tables in owned database')
            for table, spec in schema['tables'].items():
                if table in existing:
                    try:
                        verify_table(q, table, spec)
                        continue
                    except ValueError:
                        # Only a package-owned interrupted load is replaced.
                        q.execute('DELETE FROM ' + quote(table))
                else:
                    q.execute(spec['ddl'])
                columns = [c['Field'] for c in spec['columns'] if 'GENERATED' not in c['Extra'].upper()]
                indices = [i for i, c in enumerate(spec['columns']) if c['Field'] in columns]
                stmt = 'INSERT INTO ' + quote(table) + ' (' + ','.join(map(quote, columns)) + ') VALUES (' + ','.join(['%s'] * len(columns)) + ')'
                batch = []
                with gzip.open(ROOT / 'data' / spec['file'], 'rt', encoding='utf-8') as source:
                    for line in source:
                        row = json.loads(line)
                        batch.append(tuple(decode(row[i]) for i in indices))
                        if len(batch) == 500:
                            q.executemany(stmt, batch); batch.clear()
                    if batch:
                        q.executemany(stmt, batch)
                connection.commit()
                verify_table(q, table, spec)
            q.execute("UPDATE bkn_sample_meta SET status='ready' WHERE sample_id=%s", (SAMPLE,)); connection.commit()
        for table, spec in schema['tables'].items():
            verify_table(q, table, spec)
        q.execute('SET FOREIGN_KEY_CHECKS=1')
    print(json.dumps({'ok': True, 'tables': len(schema['tables']), 'records': sum(t['rows'] for t in schema['tables'].values()), 'data_digest': digest}))


if __name__ == '__main__':
    main()
