#!/usr/bin/env python3
"""Load or verify the locked embedded manufacturing CSV files in MariaDB."""
import csv, hashlib, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SAMPLE='manufacturing-industry-en-us'
DATABASE='manufacturing_industry_en_us'

def require(v,m):
    if not v: raise RuntimeError(m)
def lock():
    document=json.loads((ROOT/'dataset.lock').read_text(encoding='utf-8'))
    files=document['files']; require(len(files)==40,'dataset.lock must list 40 CSV files')
    for name,digest in files.items():
        path=ROOT/'data'/name
        require(path.is_file(),'missing data file: '+name)
        actual='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual==digest,'data digest mismatch: '+name)
    return document
def connect(database):
    import pymysql
    args={'user':os.environ['MYSQL_USER'],'password':os.environ.get('MYSQL_PASSWORD',''),'database':database,'charset':'utf8mb4'}
    if os.environ.get('MYSQL_UNIX_SOCKET'): args['unix_socket']=os.environ['MYSQL_UNIX_SOCKET']
    else: args.update(host=os.environ['MYSQL_HOST'],port=int(os.environ.get('MYSQL_PORT','3306')))
    return pymysql.connect(**args)
def quote(value): return '`'+value.replace('`','``')+'`'
def init(doc):
    require(os.environ.get('BKN_SAMPLE_ID')==SAMPLE,'unexpected sample id')
    admin=connect(os.environ.get('MYSQL_ADMIN_DATABASE','mysql'))
    with admin.cursor() as q: q.execute('CREATE DATABASE IF NOT EXISTS '+quote(DATABASE)+' CHARACTER SET utf8mb4')
    admin.commit(); admin.close()
    db=connect(DATABASE)
    with db.cursor() as q:
        q.execute('SHOW TABLES'); existing={r[0] for r in q.fetchall()}
        if existing:
            q.execute('SELECT status,sample_version,data_digest FROM bkn_sample_meta WHERE sample_id=%s',(SAMPLE,))
            found=q.fetchone(); expected=hashlib.sha256((ROOT/'dataset.lock').read_bytes()).hexdigest()
            require(found==( 'ready',os.environ['BKN_SAMPLE_VERSION'],expected),'existing database is not this exact managed sample')
            return
        q.execute('CREATE TABLE bkn_sample_meta (sample_id VARCHAR(64) PRIMARY KEY,sample_version VARCHAR(32),status VARCHAR(16),data_digest VARCHAR(64))')
        for name in sorted(doc['files']):
            with (ROOT/'data'/name).open(encoding='utf-8',newline='') as f:
                reader=csv.DictReader(f); headers=reader.fieldnames or []
                require(headers and len(headers)==len(set(headers)), 'CSV headers must be present and unique: '+name)
                q.execute('CREATE TABLE '+quote(Path(name).stem)+' ('+', '.join(quote(h)+' TEXT' for h in headers)+') CHARACTER SET utf8mb4')
                values=[[row.get(h,'') for h in headers] for row in reader]
                q.executemany('INSERT INTO '+quote(Path(name).stem)+' VALUES ('+','.join(['%s']*len(headers))+')',values)
        q.execute('INSERT INTO bkn_sample_meta VALUES (%s,%s,%s,%s)',(SAMPLE,os.environ['BKN_SAMPLE_VERSION'],'ready',hashlib.sha256((ROOT/'dataset.lock').read_bytes()).hexdigest()))
    db.commit(); db.close()
def verify(doc):
    require(os.environ.get('BKN_SAMPLE_ID','') in ('',SAMPLE),'unexpected sample id')
    db=connect(DATABASE)
    with db.cursor() as q:
        q.execute('SELECT status,sample_version,data_digest FROM bkn_sample_meta WHERE sample_id=%s',(SAMPLE,))
        expected=('ready',os.environ.get('BKN_SAMPLE_VERSION',''),hashlib.sha256((ROOT/'dataset.lock').read_bytes()).hexdigest())
        require(q.fetchone()==expected,'database identity mismatch')
        total=0
        for name in doc['files']:
            q.execute('SELECT COUNT(*) FROM '+quote(Path(name).stem)); found=q.fetchone()[0]
            with (ROOT/'data'/name).open(encoding='utf-8',newline='') as f: expected_rows=sum(1 for _ in csv.DictReader(f))
            require(found==expected_rows,f'row count mismatch: {name}'); total+=found
    db.close(); require(total==2700,'total record count mismatch'); print(json.dumps({'ok':True,'tables':40,'records':total}))
if __name__=='__main__':
    document=lock()
    if sys.argv[1]=='init': init(document)
    elif sys.argv[1]=='verify': verify(document)
    else: raise SystemExit('expected init or verify')
