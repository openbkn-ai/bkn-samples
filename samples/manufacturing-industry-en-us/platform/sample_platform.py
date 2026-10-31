"""Native BKN import with explicit ownership, resource bindings and live queries."""
import json,os,re,shutil,subprocess,sys,tempfile

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    # Older installers retain the original subprocess behavior.
    run_sample_command = subprocess.run
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ownership_receipt import read as read_receipt,require_owned
from register_skills import run as register_skills
MANIFEST=json.loads((ROOT/'sample.yaml').read_text());SAMPLE=MANIFEST['metadata']['name'];KN=MANIFEST['spec']['knowledgeNetwork']['id']
def require(ok,msg):
    if not ok:raise ValueError(msg)
def cli(*args):
    p=run_sample_command(['openbkn','--json',*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError('OpenBKN call failed: '+re.sub(r'(?i)(password\s*[:=]\s*)[^\s,]+',r'\1***',(p.stderr or p.stdout))[:600])
    return json.loads(p.stdout or '{}')
def entries(value):
    if isinstance(value,list):return value
    for key in ('entries','datas','data','instances'):
        if isinstance(value.get(key),list):return value[key]
    raise ValueError('missing entries')
def single(v):return entries(v)[0] if isinstance(v,list) or 'entries' in v else v
def bind_resources(specs,bindings,apply):
    # Read every binding before mutating any object; never replace another source.
    pending=[]
    for table in specs:
        obj=single(cli('bkn','object-type','get',KN,table))
        source=obj.get('data_source')
        if source is None:source={}
        require(isinstance(source,dict),'invalid data source '+table)
        if source.get('type')=='resource' and source.get('id')==bindings[table]:continue
        empty=not source or (set(source)<= {'type','id'} and source.get('type') in (None,'','resource') and not source.get('id'))
        require(empty,'existing binding differs: '+table)
        require(apply,'binding missing: '+table)
        pending.append((table,obj))
    with tempfile.TemporaryDirectory() as directory:
        for table,obj in pending:
            obj['data_source']={'type':'resource','id':bindings[table]}
            path=Path(directory)/(table+'.json');path.write_text(json.dumps(obj))
            cli('bkn','object-type','update',KN,table,'--body-file',str(path))
def main():
    raw=json.loads(Path(os.environ['BKN_SAMPLE_INPUT']).read_text());require(raw['sample']==SAMPLE and raw['knowledgeNetwork']['id']==KN and raw['database']['name']==KN,'ownership identity differs')
    tags={'bkn-samples','bkn-sample-'+SAMPLE,'bkn-samples-version-'+raw['version'].replace('.','-')}
    specs=json.loads((ROOT/'model-contract.json').read_text())['object_types']
    resources=entries(cli('vega','resource','list','--catalog-id',raw['catalog']['id'],'--category','table','--limit','100'))
    bindings={}
    for table in specs:
        matches=[r for r in resources if r['name'].rsplit('.',1)[-1]==table];require(len(matches)==1,'missing/ambiguous resource '+table);bindings[table]=matches[0]['id']
    if sys.argv[1]=='install':
        existing=run_sample_command(['openbkn','--json','bkn','get',KN],capture_output=True,text=True)
        if existing.returncode==0:
            current=json.loads(existing.stdout);require(tags<=set(current.get('tags',[])),'knowledge network ownership conflict')
        else:
            require('404' in existing.stderr+existing.stdout,'cannot confirm network absence')
            with tempfile.TemporaryDirectory() as d:
                dest=Path(d)/'kn';shutil.copytree(ROOT/'kn',dest)
                n=dest/'network.bkn';n.write_text(re.sub(r'^tags:.*$', 'tags: '+json.dumps(sorted(tags|{'manufacturing','iof'})),n.read_text(),flags=re.M))
                cli('bkn','validate',str(dest));cli('bkn','push',str(dest))
        bind_resources(specs,bindings,apply=True)
    elif sys.argv[1]=='verify':bind_resources(specs,bindings,apply=False)
    else:raise ValueError('expected install or verify')
    network=cli('bkn','get',KN,'--export');require(tags<=set(network.get('tags',[])),'network ownership differs')
    require(len(network['object_types'])==len(specs) and len(network['relation_types'])==71,'model counts differ')
    for table,spec in specs.items():
        obj=single(cli('bkn','object-type','get',KN,table));require(obj['data_source']['id']==bindings[table],'binding differs')
        data=entries(cli('bkn','object-type','query',KN,table,'--body','{"limit":2}'));require(len(data)==2 and all(spec['primary_key'] in r for r in data),'live object query failed '+table)
    if sys.argv[1]=='install':skills=register_skills(apply=True,kn_id=KN)
    else:
        skills=register_skills(apply=False)
        listed=entries(cli('skill','list','--all'))
        for local in skills['skills']:
            matches=[s for s in listed if s.get('name')==local['name']];require(len(matches)==1,'missing/ambiguous installed Skill')
            require_owned('skills',matches[0].get('skill_id') or matches[0].get('id'));require(matches[0].get('status')=='published','unpublished Skill')
    require(len(skills['skills'])==2,'skill count differs')
    capabilities={'skills':skills,'ownedExecution':read_receipt()}
    result={'ok':True,'stage':'platform-'+sys.argv[1],'resources':{'catalogId':raw['catalog']['id'],'knowledgeNetworkId':KN,'ownedExecution':capabilities['ownedExecution'],'capabilitySummary':capabilities},'checks':[{'name':n,'ok':True} for n in ('ownership','40-object-types',str(71)+'-relations','40-resource-bindings','40-live-object-queries')],'degrade':[],'message':''}
    Path(os.environ['BKN_SAMPLE_OUTPUT']).write_text(json.dumps(result));print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except Exception as error:
        message=re.sub(r'(?i)(bearer\s+|password[\"\s:=]+|token[\"\s:=]+)[^\s,}]+',r'\1***',str(error))[:1000]
        result={'ok':False,'code':'manufacturing_platform_hook_failed','message':message}
        if os.environ.get('BKN_SAMPLE_OUTPUT'):Path(os.environ['BKN_SAMPLE_OUTPUT']).write_text(json.dumps(result))
        print(json.dumps(result));sys.exit(1)
