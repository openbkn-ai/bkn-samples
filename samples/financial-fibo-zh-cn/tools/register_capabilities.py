"""Register/verify two immutable metrics, three readable functions and one Skill."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
from ownership_receipt import read, remember, require_owned
from register_skills import run as register_skills
ROOT=Path(__file__).resolve().parents[1]
API='/api/agent-operator-integration/v1'
OPERATIONS=('settlement_asof','valuation_asof','limit_assessment_asof')
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
    core=(ROOT/'tools/post_trade.py').read_text();loader=(ROOT/'tools/managed_execution.py').read_text()
    # Readable self-contained Python, not an encoded archive. Contract is public schema only.
    entry='''\nfrom sandbox_sdk import tool\nfrom bkn_osdk import kn\nfrom bkn_osdk.config import Context\nimport os\nfrom urllib.parse import urlsplit\ndef managed_query(*args, **kwargs):\n    base=os.environ.get('BKN_BASE_URL')\n    if not base:\n        parsed=urlsplit(os.environ.get('BKN_SANDBOX_MCP_URL',''))\n        if not parsed.scheme or not parsed.netloc:raise ValueError('MISSING_MANAGED_BASE_URL')\n        base=parsed.scheme+'://'+parsed.netloc\n    ctx=Context(base_url=base,token=os.environ.get('BKN_TOKEN',''),conversation_id=os.environ.get('BKN_CONVERSATION_ID'),interaction_id=os.environ.get('BKN_INTERACTION_ID'),parent_operation_id=os.environ.get('BKN_PARENT_OPERATION_ID'),traced=True)\n    if not ctx.token or not ctx.interaction_id:raise ValueError('MISSING_MANAGED_CALL_CONTEXT')\n    return kn.query_object_instance(*args,context=ctx,**kwargs)\n@tool\ndef financial_function(portfolio_ids: list, as_of_date: str, knowledge_date: str, view_kind: str, additional_observations: list = None) -> dict:\n    scope=dict(portfolio_ids=portfolio_ids,as_of_date=as_of_date,knowledge_date=knowledge_date,view_kind=view_kind)\n    return run_request(managed_query,KN_ID,CONTRACT,OPERATION,scope,execute,additional_observations)\n'''
    return core+'\n'+loader+'\nKN_ID='+repr(kn_id)+'\nOPERATION='+repr(operation)+'\nCONTRACT='+repr(c)+'\n'+entry

def metric_definitions():
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn';result=[]
    for table,prop,code,scale,name in [('issuer_exposures','ratio','issuer_ratio_recorded',6,'已记录发行方集中度' if zh else 'Recorded issuer concentration'),('counterparty_exposures','unsettled_receivable','sell_receivable_recorded_usd',2,'已记录未结算应收美元' if zh else 'Recorded sell receivable USD')]:
        result.append({'version':1,'code':code,'name':name,'description':('仅已记录快照；每个结果只对应一个带日期的敞口实例，不跨期聚合，不代表实时重算。' if zh else 'Recorded snapshots only, one dated exposure instance per result; no cross-date aggregate; not live reconstruction.'),'owner_object_type_id':table,'metric_type':'atomic','calculation_scope':'object_instance','result_semantics':{'statistical_grain':{'group_by_dimensions':[]},'value':{'physical_type':'decimal','semantic_type':'ratio' if table=='issuer_exposures' else 'amount','unit':{'system':'UCUM' if table=='issuer_exposures' else 'ISO_4217','quantity_kind':'dimensionless' if table=='issuer_exposures' else 'currency','code':'1' if table=='issuer_exposures' else 'USD','scale_factor':1},'precision':38,'scale':scale,'rounding_mode':'half_up'},'no_data_policy':'null','partial_data_policy':'reject'},'specification':{'kind':'atomic','measure':{'aggregation':'identity','expression':{'node_type':'property','property_ref':{'object_type_id':table,'property_name':prop}}}},'query_capabilities':{'analysis_dimensions':[],'time_dimensions':[]},'lifecycle':{'status':'draft','ontology_version':'1.0','expression_language_version':'1.0','function_registry_version':'1.0','aggregation_registry_version':'1.0','unit_registry_version':'1.0'}})
    return result

def metric_call(action,kn_id,metric=None,definition=None):
    args=['bkn','object-metric',action,kn_id]
    if metric:args += [metric['id'],'--metric-version',str(metric['version'])]
    if definition:
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(definition,f);f.flush();return cli(*args,'--body-file',f.name)
    return cli(*args)

def run(kn_id,apply):
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='FIBO_'+manifest['metadata']['name'].rsplit('fibo-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Atomic post-trade controls / 原始事实交易后控制',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':True,'description':desc} for n,typ,desc in [('portfolio_ids','array','Nonempty portfolio IDs / 组合主键'),('as_of_date','string','Business date YYYY-MM-DD / 业务日期'),('knowledge_date','string','Knowledge cutoff YYYY-MM-DD / 知识截止日期'),('view_kind','string','actual or planned / 实际或计划')]]
        inputs.append({'name':'additional_observations','type':'array','required':False,'description':'Up to11 JSON object strings with exactly as_of_date,knowledge_date,view_kind (dicts also accepted for SDK compatibility); YYYY-MM-DD dates; batch fixed1..20 portfolios,total<=12 scopes,UTF8 compact UTF8 JSON result<=3MiB (platform native output quota4MiB); omitted/empty keeps scalar1..200 behavior / 最多11个JSON对象字符串，仅含as_of_date、knowledge_date、view_kind（兼容SDK字典对象）；日期格式YYYY-MM-DD；批量固定1至20组合、总计至多12范围、紧凑UTF8 JSON结果至多3MiB（平台原生输出限额4MiB）；省略或空数组保持单范围1至200组合'})
        body=dict(name=operation,description=operation+'; atomic facts, explicit dated scope, Decimal and source evidence; optional bounded request-local dated observations / 原始事实重算及证据，可选有界多日期观察',script_type='python',code=code,inputs=inputs,outputs=[dict(name='result',type='object',required=True,description='Typed rows, completeness, issues and evidence; blocked can retain independent known fields; USD identity may have null fx_id / 业务结果及证据；blocked仍可保留独立已知值，美元恒等换算可无fx_id')])
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
