"""Load an immutable typed CSV fixture into the installer-owned shared database."""
import csv,datetime,hashlib,json,os,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'sample.yaml').read_text()); SAMPLE=MANIFEST['metadata']['name']; DB=MANIFEST['spec']['database']['name']
def require(ok,message):
    if not ok: raise ValueError(message)
def fixture():
    lock=json.loads((ROOT/'dataset.lock').read_text()); contract=json.loads((ROOT/'model-contract.json').read_text())['object_types']; rows={}
    require(set(lock['files'])=={t+'.csv' for t in contract},'fixture inventory differs')
    for t,spec in contract.items():
        path=ROOT/'data'/(t+'.csv'); require('sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()==lock['files'][path.name],'data digest mismatch')
        with path.open() as f:
            reader=csv.DictReader(f); require(reader.fieldnames==list(spec['fields']),'field order differs'); rows[t]=list(reader)
        require(len(rows[t])==lock['record_counts'][t],'record count differs')
    return contract,rows,hashlib.sha256((ROOT/'dataset.lock').read_bytes()).hexdigest()
def cast(value,kind):
    if value=='': return None
    if kind=='decimal': return Decimal(value)
    if kind=='integer': return int(value)
    if kind=='boolean': return value.lower()=='true'
    if kind=='date': return datetime.date.fromisoformat(value)
    return value
def main():
    import pymysql
    require(os.environ['MYSQL_DATABASE']==DB and os.environ.get('BKN_SAMPLE_ID')==SAMPLE,'database ownership differs')
    specs,rows,digest=fixture();options=dict(user=os.environ['MYSQL_USER'],password=os.environ['MYSQL_PASSWORD'],database=DB,charset='utf8mb4')
    if os.environ.get('MYSQL_UNIX_SOCKET'): options['unix_socket']=os.environ['MYSQL_UNIX_SOCKET']
    else: options.update(host=os.environ['MYSQL_HOST'],port=int(os.environ['MYSQL_PORT']))
    with pymysql.connect(**options) as conn:
        with conn.cursor() as q:
            q.execute('SHOW TABLES');existing=q.fetchall()
            if sys.argv[1]=='init' and not existing:
                q.execute('CREATE TABLE bkn_sample_meta (sample_id VARCHAR(64) PRIMARY KEY,sample_version VARCHAR(32),status VARCHAR(16),data_digest VARCHAR(64))')
                for table,spec in specs.items():
                    defs=[]
                    for field,kind in spec['fields'].items():
                        typ={'decimal':'DECIMAL(30,6)','integer':'BIGINT','boolean':'BOOLEAN','date':'DATE','string':'VARCHAR(512)'}[kind]
                        if field==spec['primary_key']: typ='VARCHAR(128) PRIMARY KEY'
                        defs.append('`'+field+'` '+typ)
                    q.execute('CREATE TABLE `'+table+'` ('+','.join(defs)+') CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
                    data=[tuple(cast(r[f],k) for f,k in spec['fields'].items()) for r in rows[table]]
                    stmt='INSERT INTO `'+table+'` VALUES ('+','.join(['%s']*len(spec['fields']))+')'
                    for start in range(0,len(data),500):q.executemany(stmt,data[start:start+500])
                q.execute("INSERT INTO bkn_sample_meta VALUES (%s,%s,'ready',%s)",(SAMPLE,os.environ['BKN_SAMPLE_VERSION'],digest));conn.commit()
            elif sys.argv[1] not in ('init','verify'): raise ValueError('expected init or verify')
            q.execute('SELECT sample_version,status,data_digest FROM bkn_sample_meta WHERE sample_id=%s',(SAMPLE,));require(q.fetchone()==(os.environ['BKN_SAMPLE_VERSION'],'ready',digest),'database identity differs')
            for table,spec in specs.items():
                fields=list(spec['fields']);pk=spec['primary_key']; q.execute('SELECT '+','.join('`'+f+'`' for f in fields)+' FROM `'+table+'` ORDER BY `'+pk+'`')
                actual=q.fetchall(); expected=sorted([tuple(cast(r[f],spec['fields'][f]) for f in fields) for r in rows[table]],key=lambda r:r[fields.index(pk)])
                require(list(actual)==expected,'database content differs: '+table)
    print(json.dumps({'ok':True,'tables':len(specs),'records':sum(map(len,rows.values())),'data_digest':digest}))
if __name__=='__main__':main()
