"""Run actual industry/energy database hooks in one disposable isolated MariaDB."""
import argparse,json,os,subprocess,sys,time,uuid
from pathlib import Path
import pymysql
ROOT=Path(__file__).resolve().parents[2]
SAMPLES=['manufacturing-industry-en-us','manufacturing-industry-zh-cn','energy-saref4ener-en-us','energy-saref4ener-zh-cn']


def run(output,image):
    name='samples021-four-'+uuid.uuid4().hex[:12]
    network=name+'-bridge';created=False;net_created=False
    def docker(*args):
        return subprocess.check_output(['docker',*args],text=True).strip()
    report={'scope':'actual local database hooks; not OpenBKN platform acceptance','samples':[]}
    try:
        image_id=docker('image','inspect',image,'--format','{{.Id}}');report['image']=image_id
        docker('network','create',network);net_created=True
        docker('run','-d','--rm','--pull=never','--network',network,'--name',name,'-p','127.0.0.1::3306','-e','MARIADB_ROOT_PASSWORD=local-acceptance-only','-e','MARIADB_ROOT_HOST=%',image_id);created=True
        port=int(docker('port',name,'3306/tcp').split(':')[-1])
        options=dict(host='127.0.0.1',port=port,user='root',password='local-acceptance-only',charset='utf8mb4',connect_timeout=2)
        for _ in range(50):
            try:
                conn=pymysql.connect(**options);break
            except pymysql.Error:time.sleep(.5)
        else:raise RuntimeError('isolated MariaDB did not become ready')
        with conn:
            with conn.cursor() as q:
                q.execute('SELECT VERSION()');report['server_version']=q.fetchone()[0]
                for sample in SAMPLES:
                    source=ROOT/'samples'/sample;manifest=json.loads((source/'sample.yaml').read_text());database=manifest['spec']['database']['name'];assert database.replace('_','').isalnum()
                    q.execute('CREATE DATABASE `'+database+'` CHARACTER SET utf8mb4')
                    env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'PYTHONIOENCODING':'utf-8','MYSQL_HOST':'127.0.0.1','MYSQL_PORT':str(port),'MYSQL_USER':'root','MYSQL_PASSWORD':'local-acceptance-only','MYSQL_DATABASE':database,'MYSQL_UNIX_SOCKET':'','BKN_SAMPLE_ID':sample,'BKN_SAMPLE_VERSION':manifest['metadata']['version']}
                    steps=[]
                    for action in ('init','verify','init','verify'):
                        p=subprocess.run([sys.executable,str(source/'db/database.py'),action],env=env,capture_output=True,text=True,timeout=120)
                        if p.returncode:raise RuntimeError(sample+'/'+action+': '+p.stderr[-2000:])
                        steps.append({'action':action,'result':json.loads(p.stdout)})
                    q.execute('SELECT COLUMN_NAME,DATA_TYPE,TABLE_NAME FROM information_schema.columns WHERE TABLE_SCHEMA=%s AND TABLE_NAME<>%s',(database,'bkn_sample_meta'));columns=q.fetchall()
                    contract=json.loads((source/'model-contract.json').read_text())['object_types']
                    sql_types={'string':'varchar','decimal':'decimal','date':'date','integer':'bigint','boolean':'tinyint'}
                    for column,kind,table in columns:
                        expected='varchar' if column==contract[table]['primary_key'] else sql_types[contract[table]['fields'][column]]
                        assert kind==expected,(sample,table,column,kind,expected)
                    report['samples'].append({'sample':sample,'version':manifest['metadata']['version'],'tables':len(contract),'records':steps[0]['result']['records'],'typed_columns':len(columns),'steps':steps})
                    print(sample,'database hooks and full typed readback passed',flush=True)
    finally:
        if created:subprocess.run(['docker','rm','-f',name],capture_output=True)
        if net_created:subprocess.run(['docker','network','rm',network],capture_output=True)
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--image',default='mariadb:11.4');args=p.parse_args()
    run(args.output,args.image)
