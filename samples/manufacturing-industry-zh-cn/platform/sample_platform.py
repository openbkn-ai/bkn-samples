#!/usr/bin/env python3
"""Install and verify the resource-backed BKN manufacturing sample."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SAMPLE='manufacturing-industry-zh-cn'; KN='manufacturing_industry_zh_cn'
def run(*args):
    p=subprocess.run(['openbkn','--json',*args],text=True,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr or p.stdout)
    return json.loads(p.stdout or '{}')
def payload():
    p=json.loads(Path(os.environ['BKN_SAMPLE_INPUT']).read_text(encoding='utf-8'))
    if p.get('sample')!=SAMPLE: raise RuntimeError('unexpected sample')
    return p
def entries(v): return v.get('entries',v) if isinstance(v,dict) else v
def output(raw,ok,checks,message=''):
    body={'ok':ok,'stage':'platform-'+sys.argv[1],'resources':{'catalogId':raw['catalog']['id'],'knowledgeNetworkId':KN,'ownedExecution':{'toolboxes':[],'skills':[]}},'checks':checks,'degrade':[],'message':message}
    Path(os.environ['BKN_SAMPLE_OUTPUT']).write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(body,ensure_ascii=False))
def config(raw):
    db=raw['database']; return {'database':{'engine':'mysql','host':db['host'],'port':int(db['port']),'database':db['name'],'user':db['user'],'password':db['password']},'vega':{'catalog_name':SAMPLE+'-'+raw['version'],'catalog_host':db['host'],'connector_type':'mysql'},'openbkn':{'kn_id':KN}}
def main():
    raw=payload()
    if os.environ.get('BKN_SAMPLE_PRINT_ONLY')=='1':
        output(raw,True,[{'name':'offline-install-plan','ok':True}]); return
    if sys.argv[1]=='install':
        subprocess.run(['openbkn','bkn','validate',str(ROOT/'kn')],check=True)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'; p.write_text(json.dumps(config(raw)),encoding='utf-8')
            # The standard CLI imports the BKN directory; the installer then binds every object type to its discovered CSV table resource.
            subprocess.run(['openbkn','bkn','push',str(ROOT/'kn')],check=True)
            resources=entries(run('vega','resource','list','--catalog-id',raw['catalog']['id'],'--category','table','--limit','100'))
            if not isinstance(resources,list): raise RuntimeError('catalog table resources are unavailable')
            for ot in (ROOT/'kn'/'object_types').glob('*.bkn'):
                ot_id=ot.stem; match=[r for r in resources if str(r.get('name','')).rsplit('.',1)[-1]==ot_id]
                if len(match)!=1: raise RuntimeError('missing or ambiguous resource: '+ot_id)
                current=entries(run('bkn','object-type','get',KN,ot_id)); current=current[0] if isinstance(current,list) else current
                current['data_source']={'type':'resource','id':match[0]['id']}
                body=Path(d)/(ot_id+'.json'); body.write_text(json.dumps(current),encoding='utf-8')
                run('bkn','object-type','update',KN,ot_id,'--body-file',str(body))
        output(raw,True,[{'name':'model-imported','ok':True},{'name':'40-table-resources-bound','ok':True}]); return
    if sys.argv[1]=='verify':
        objects=entries(run('bkn','object-type','list',KN)); relations=entries(run('bkn','relation-type','list',KN))
        ok=len(objects)==40 and len(relations)==71 and all(o.get('data_source',{}).get('type')=='resource' for o in objects)
        output(raw,ok,[{'name':'40-object-types','ok':len(objects)==40},{'name':'71-relation-types','ok':len(relations)==71},{'name':'resource-bindings','ok':all(o.get('data_source',{}).get('type')=='resource' for o in objects)}]); return
    raise RuntimeError('expected install or verify')
try: main()
except Exception as e:
    raw=payload(); output(raw,False,[],str(e)); raise
