"""Register/verify two immutable metrics, three readable functions and one Skill."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
from ownership_receipt import read, remember, require_owned
from register_skills import run as register_skills
ROOT=Path(__file__).resolve().parents[1]
API='/api/agent-operator-integration/v1'
OPERATIONS=('flexibility_assessment','dispatch_plan','settlement_assessment')
def cli(*args):
    p=subprocess.run(['openbkn','--json',*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError('capability CLI failed: '+(p.stderr or p.stdout)[:1000])
    return json.loads(p.stdout or '{}')
def entries(p,*keys):
    if isinstance(p,list):return p
    for k in keys:
        if isinstance(p.get(k),list):return p[k]
    raise ValueError('missing capability collection')
def tool_code(operation,kn_id):
    source=json.loads((ROOT/'model-contract.json').read_text())
    c={'block_durations':source['block_durations'],'object_types':{t:{'primary_key':s['primary_key'],'fields':s['fields']} for t,s in source['object_types'].items()}}
    core=(ROOT/'tools/energy.py').read_text();loader=(ROOT/'tools/managed_execution.py').read_text()
    entry="\nfrom sandbox_sdk import tool\nfrom bkn_osdk import kn\nfrom bkn_osdk.config import Context\nimport os\nfrom urllib.parse import urlsplit\n\ndef managed_query(*args, **kwargs):\n    base = os.environ.get('BKN_BASE_URL')\n    if not base:\n        parsed = urlsplit(os.environ.get('BKN_SANDBOX_MCP_URL', ''))\n        if not parsed.scheme or not parsed.netloc:\n            raise ValueError('MISSING_MANAGED_BASE_URL')\n        base = parsed.scheme+'://'+parsed.netloc\n    ctx = Context(base_url=base, token=os.environ.get('BKN_TOKEN', ''),\n        conversation_id=os.environ.get('BKN_CONVERSATION_ID'),\n        interaction_id=os.environ.get('BKN_INTERACTION_ID'),\n        parent_operation_id=os.environ.get('BKN_PARENT_OPERATION_ID'), traced=True)\n    if not ctx.token or not ctx.interaction_id:\n        raise ValueError('MISSING_MANAGED_CALL_CONTEXT')\n    return kn.query_object_instance(*args, context=ctx, **kwargs)\n\n@tool\ndef energy_function(event_ids: list, as_of_date: str, knowledge_date: str) -> dict:\n    scope = dict(event_ids=event_ids, as_of_date=as_of_date, knowledge_date=knowledge_date)\n    return run_request(managed_query, KN_ID, CONTRACT, OPERATION, scope, execute)\n"
    return core+'\n'+loader+'\nKN_ID='+repr(kn_id)+'\nOPERATION='+repr(operation)+'\nCONTRACT='+repr(c)+'\n'+entry

def metric_definitions():
    zh=json.loads((ROOT/'sample.yaml').read_text())['metadata']['name'].endswith('zh-cn');result=[]
    for table,prop,code,name in [('capacity_snapshots','eligible_kw','recorded_eligible_kw','已记录可响应功率' if zh else 'Recorded eligible power'),('settlement_snapshots','delivery_ratio','recorded_delivery_ratio','已记录交付比例' if zh else 'Recorded delivery ratio')]:
        ratio=table=='settlement_snapshots'
        result.append({'version':1,'code':code,'name':name,'description':('单个事件、业务日期、知识截止日期的已记录快照；未知为空，不跨期合计，不替代重算。' if zh else 'One recorded event/as-of/knowledge snapshot instance; null is unknown; never aggregate history or substitute for reconstruction.'),'owner_object_type_id':table,'metric_type':'atomic','calculation_scope':'object_instance','result_semantics':{'statistical_grain':{'group_by_dimensions':[]},'value':{'physical_type':'decimal','semantic_type':'ratio' if ratio else 'measure','unit':{'system':'UCUM','quantity_kind':'dimensionless' if ratio else 'custom','code':'1' if ratio else 'kW','scale_factor':1},'precision':38,'scale':6,'rounding_mode':'half_up'},'no_data_policy':'null','partial_data_policy':'reject'},'specification':{'kind':'atomic','measure':{'aggregation':'identity','expression':{'node_type':'property','property_ref':{'object_type_id':table,'property_name':prop}}}},'query_capabilities':{'analysis_dimensions':[],'time_dimensions':[]},'lifecycle':{'status':'draft','ontology_version':'1.0','expression_language_version':'1.0','function_registry_version':'1.0','aggregation_registry_version':'1.0','unit_registry_version':'1.0'}})
    return result

def metric_call(action,kn_id,metric=None,definition=None):
    args=['bkn','object-metric',action,kn_id]
    if metric:args += [metric['id'],'--metric-version',str(metric['version'])]
    if definition:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(definition,f);f.flush();return cli(*args,'--body-file',f.name)
    return cli(*args)

def run(kn_id,apply):
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='ENERGY_'+manifest['metadata']['name'].rsplit('saref4ener-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Read-only synthetic demand-response assessment, proposal and settlement',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':True,'description':desc} for n,typ,desc in [('event_ids','array','1..20 distinct event IDs; complete overlap pool remains protected / 1至20个不同事件主键，保护完整重叠事件池'),('as_of_date','string','Business date YYYY-MM-DD / 业务日期'),('knowledge_date','string','Knowledge cutoff YYYY-MM-DD / 知识截止日期')]]
        body=dict(name=operation,description=operation+'; atomic facts, explicit dated scope, Decimal and source evidence; bounded synthetic energy operations and evidence',script_type='python',code=code,inputs=inputs,outputs=[dict(name='result',type='object',required=True,description='Typed energy rows, completeness, issues and source evidence; null remains unknown')])
        if apply:
            if found:
                tid=found['tool_id'];cli('call',API+'/tool-box/'+bid+'/tool/'+tid,'-X','POST','-d',json.dumps(dict(name=operation,description=body['description'],metadata_type='function',function_input=body),ensure_ascii=False))
            else:tid=cli('call',API+'/tool-box/'+bid+'/tool','-X','POST','-d',json.dumps(dict(metadata_type='function',function_input=body),ensure_ascii=False))['success_ids'][0]
            cli('tool','enable','--toolbox',bid,tid)
        else:
            if not found:raise ValueError('missing function '+operation)
            tid=found['tool_id']
            detail=cli('tool','get','--toolbox',bid,tid)
            # Function source is readable metadata, verify exact payload when exposed.
            meta=detail.get('metadata',{}).get('function_content',{});saved=meta.get('code')
            if saved!=code:raise ValueError('published source differs '+operation)
        tids[operation]=tid
    if apply:

        if box.get('status')!='published':cli('toolbox','publish',bid)
        cli('bkn','capability','attach',kn_id,'--box',bid,'--tool',','.join(tids.values()))
    metrics=[]
    existing=[e['definition'] for e in cli('bkn','object-metric','list',kn_id,'--limit','100')['entries']]
    for spec in metric_definitions():
        found=next((m for m in existing if m['code']==spec['code']),None)
        if not found:
            if not apply:raise ValueError('missing metric '+spec['code'])
            found=metric_call('create',kn_id,definition=spec)['definition']
        for key in ('version','code','owner_object_type_id','metric_type','calculation_scope','result_semantics','specification','query_capabilities'):
            if spec[key]!=found.get(key):raise ValueError('metric definition differs '+key)
        if found['lifecycle']['status']!='published':
            if not apply:raise ValueError('unpublished metric')
            metric_call('validate-saved',kn_id,found);found=metric_call('publish',kn_id,found)['definition']
        metrics.append({'code':found['code'],'id':found['id'],'version':found['version']})
    if apply:skills=register_skills(apply=True,kn_id=kn_id)
    else:
        skills=register_skills(apply=False,kn_id=kn_id)
        listed=entries(cli('skill','list','--all'),'data','entries')
        for local in skills['skills']:
            matches=[s for s in listed if s.get('name')==local['name']]
            if len(matches)!=1:raise ValueError('missing/ambiguous installed Skill')
            sid=matches[0].get('skill_id') or matches[0].get('id')
            require_owned('skills',sid)
            if matches[0].get('status')!='published':raise ValueError('unpublished Skill')
    return {'toolbox_id':bid,'tool_ids':tids,'source_sha256':hashes,'metrics':metrics,'skills':skills,'ownedExecution':read()}
