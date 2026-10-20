"""Register/verify two immutable metrics, three readable functions and one Skill."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
from ownership_receipt import read, remember, require_owned
from register_skills import run as register_skills
ROOT=Path(__file__).resolve().parents[1]
API='/api/agent-operator-integration/v1'
OPERATIONS=('inventory_asof','fulfillment_plan','recall_assessment')
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
    c=json.loads((ROOT/'model-contract.json').read_text())
    c={k:v for k,v in c.items() if k in ('language','default_as_of_date')}
    c['object_types']={t:{'primary_key':s['primary_key']} for t,s in json.loads((ROOT/'model-contract.json').read_text())['object_types'].items()}
    core=(ROOT/'tools/retail_core.py').read_text();loader=(ROOT/'tools/managed_execution.py').read_text()
    entry = """
from sandbox_sdk import tool
from bkn_osdk import kn
from bkn_osdk.config import Context
import os
from urllib.parse import urlsplit
def managed_query(*args, **kwargs):
    base=os.environ.get('BKN_BASE_URL')
    if not base:
        parsed=urlsplit(os.environ.get('BKN_SANDBOX_MCP_URL',''))
        if not parsed.scheme or not parsed.netloc:raise ValueError('MISSING_MANAGED_BASE_URL')
        base=parsed.scheme+'://'+parsed.netloc
    ctx=Context(base_url=base,token=os.environ.get('BKN_TOKEN',''),conversation_id=os.environ.get('BKN_CONVERSATION_ID'),interaction_id=os.environ.get('BKN_INTERACTION_ID'),parent_operation_id=os.environ.get('BKN_PARENT_OPERATION_ID'),traced=True)
    if not ctx.token or not ctx.interaction_id:raise ValueError('MISSING_MANAGED_CALL_CONTEXT')
    return kn.query_object_instance(*args,context=ctx,**kwargs)
@tool
def retail_function(product_ids: list, as_of_date: str, knowledge_date: str, view_kind: str='actual', location_ids: list=None, lot_ids: list=None, order_ids: list=None, recall_id: str='', trace_lot_id: str='', mode: str='orders', horizon_date: str='2027-03-31') -> dict:
    scope=dict(product_ids=product_ids,as_of_date=as_of_date,knowledge_date=knowledge_date,view_kind=view_kind,location_ids=location_ids,lot_ids=lot_ids,order_ids=order_ids,recall_id=recall_id,trace_lot_id=trace_lot_id,mode=mode,horizon_date=horizon_date)
    return run_request(managed_query,KN_ID,CONTRACT,OPERATION,scope,execute)
"""
    return core+'\n'+loader+'\nKN_ID='+repr(kn_id)+'\nOPERATION='+repr(operation)+'\nCONTRACT='+repr(c)+'\n'+entry

def metric_definitions():
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn';result=[]
    for table,prop,code,scale,name in [('inventory_snapshots','available','recorded_available_quantity',6,'已记录可用库存量' if zh else 'Recorded available inventory'),('recall_snapshots','coverage_ratio','recorded_recall_coverage',6,'已记录召回处置覆盖率' if zh else 'Recorded recall control coverage')]:
        result.append({'version':1,'code':code,'name':name,'description':('单个带日期快照实例；须匹配业务日、知识截止日、商品、地点或召回及单位。未知为空，不跨期合计。' if zh else 'One dated snapshot instance. Match business/knowledge date, product, location or recall and unit; null is unknown; never aggregate history.'),'owner_object_type_id':table,'metric_type':'atomic','calculation_scope':'object_instance','result_semantics':{'statistical_grain':{'group_by_dimensions':[]},'value':{'physical_type':'decimal','semantic_type':'ratio' if table=='recall_snapshots' else 'measure','unit':{'system':'UCUM','quantity_kind':'dimensionless' if table=='recall_snapshots' else 'count','code':'1','scale_factor':1},'precision':38,'scale':scale,'rounding_mode':'half_up'},'no_data_policy':'null','partial_data_policy':'reject'},'specification':{'kind':'atomic','measure':{'aggregation':'identity','expression':{'node_type':'property','property_ref':{'object_type_id':table,'property_name':prop}}}},'query_capabilities':{'analysis_dimensions':[],'time_dimensions':[]},'lifecycle':{'status':'draft','ontology_version':'1.0','expression_language_version':'1.0','function_registry_version':'1.0','aggregation_registry_version':'1.0','unit_registry_version':'1.0'}})
    return result

def metric_call(action,kn_id,metric=None,definition=None):
    args=['bkn','object-metric',action,kn_id]
    if metric:args += [metric['id'],'--metric-version',str(metric['version'])]
    if definition:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(definition,f);f.flush();return cli(*args,'--body-file',f.name)
    return cli(*args)

def run(kn_id,apply):
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='RETAIL_'+manifest['metadata']['name'].rsplit('gs1-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Retail traceability, inventory and recall controls',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':required,'description':desc} for n,typ,required,desc in [
            ('product_ids','array',True,'Product IDs 1..50; recall traverses full descendants regardless product filter'),
            ('as_of_date','string',True,'Business date YYYY-MM-DD'),('knowledge_date','string',True,'Knowledge cutoff YYYY-MM-DD'),
            ('view_kind','string',False,'actual or planned; inventory always realized events'),
            ('location_ids','array',False,'Optional output/demand location scope'),('lot_ids','array',False,'Optional inventory lot scope'),
            ('order_ids','array',False,'Optional order demand subset; other reservations remain protected'),
            ('recall_id','string',False,'Required for recall_assessment; active recall blocks inventory'),
            ('trace_lot_id','string',False,'Optional inventory connected upstream/downstream trace root'),
            ('mode','string',False,'fulfillment_plan: orders or replenishment'),
            ('horizon_date','string',False,'Replenishment horizon, default 2027-03-31')]]
        body=dict(name=operation,description=operation+'; atomic facts, explicit dated scope, Decimal and source evidence; bounded retail operations and evidence',script_type='python',code=code,inputs=inputs,outputs=[dict(name='result',type='object',required=True,description='Typed retail rows, completeness, issues and source evidence; null remains unknown')])
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
        skills={'owned':read()['skills']}
        if not skills['owned']:raise ValueError('missing owned Skill')
    return {'toolbox_id':bid,'tool_ids':tids,'source_sha256':hashes,'metrics':metrics,'skills':skills,'ownedExecution':read()}
