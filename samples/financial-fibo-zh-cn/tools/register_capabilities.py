"""Register/verify the three recomputation functions and the Skills."""
import hashlib,json,subprocess

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    # Older installers retain the original subprocess behavior.
    run_sample_command = subprocess.run
from pathlib import Path
from ownership_receipt import read, remember, require_owned
from register_skills import run as register_skills
ROOT=Path(__file__).resolve().parents[1]
API='/api/agent-operator-integration/v1'
OPERATIONS=('settlement_asof','valuation_asof','limit_assessment_asof')
def cli(*args):
    p=run_sample_command(['openbkn','--json',*args],capture_output=True,text=True)
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
    entry='''\nfrom sandbox_sdk import tool\nfrom bkn_osdk import kn\nfrom bkn_osdk.config import Context\nimport os\nfrom urllib.parse import urlsplit\ndef managed_query(*args, **kwargs):\n    base=os.environ.get('BKN_BASE_URL')\n    if not base:\n        parsed=urlsplit(os.environ.get('BKN_SANDBOX_MCP_URL',''))\n        if not parsed.scheme or not parsed.netloc:raise ValueError('MISSING_MANAGED_BASE_URL')\n        base=parsed.scheme+'://'+parsed.netloc\n    ctx=Context(base_url=base,token=os.environ.get('BKN_TOKEN',''),conversation_id=os.environ.get('BKN_CONVERSATION_ID'),interaction_id=os.environ.get('BKN_INTERACTION_ID'),parent_operation_id=os.environ.get('BKN_PARENT_OPERATION_ID'),traced=True)\n    if not ctx.token or not ctx.interaction_id:raise ValueError('MISSING_MANAGED_CALL_CONTEXT')\n    return kn.query_object_instance(*args,context=ctx,**kwargs)\n@tool\ndef financial_function(portfolio_ids: list, as_of_date: str, knowledge_date: str, view_kind: str) -> dict:\n    scope=dict(portfolio_ids=portfolio_ids,as_of_date=as_of_date,knowledge_date=knowledge_date,view_kind=view_kind)\n    return run_request(managed_query,KN_ID,CONTRACT,OPERATION,scope,execute)\n'''
    return core+'\n'+loader+'\nKN_ID='+repr(kn_id)+'\nOPERATION='+repr(operation)+'\nCONTRACT='+repr(c)+'\n'+entry

DESCRIPTIONS={
    'settlement_asof':(
        'Recompute settlement status as of a date from trades and incremental settlement events known by the cutoff: '
        'settled, partial, pending or failed, remaining quantity, overdue flag and failure reason per instruction.',
        '按某天及当天已知的成交和逐笔交收事件重算交收状态：每条指令已结算、部分结算、待结算或结算失败，剩余数量、是否逾期和失败原因。'),
    'valuation_asof':(
        'Recompute positions and valuations as of a date: trade and settled quantities, weighted-average cost, realized P&L, '
        'eligible price and FX, local and USD market value, or the reason a value is unknown.',
        '按某天重算持仓和估值：交易口径与已交收数量、加权平均成本、已实现损益、合格价格与汇率、本币和美元市值，或市值未知的原因。'),
    'limit_assessment_asof':(
        'Recompute issuer concentration and counterparty unsettled-sale receivables as of a date, pick the single applicable '
        'approved limit, and report breach, excess or why it cannot be judged.',
        '按某天重算发行方集中度和交易对手未结算卖出应收，选出唯一适用的已批准限额，给出是否超限、超出多少或无法判定的原因。'),
}

ACTION_NAMES={'settlement_asof':('Settlement status as of a date','按日期计算交收状态'),
              'valuation_asof':('Valuation as of a date','按日期计算估值'),
              'limit_assessment_asof':('Limit assessment as of a date','按日期评估限额')}

BKN_API='/api/bkn-backend/v1'
ACTION_RULE=('Run as an action: get_action_info for the parameters, execute_action, then get_action_execution for the result. '
             'Pass every parameter: the dates and scope are the assumptions of the answer, so pass them explicitly and state them in the answer. '
             'Check completeness and issues in the result; a completed execution does not mean the calculation succeeded.',
             '作为行动执行：先用 get_action_info 取参数定义，再用 execute_action 执行，最后用 get_action_execution 取结果。'
             '每个参数都要传：日期和范围是这次计算的假设，要显式传入，并在回答里说明按什么假设算的。'
             '检查结果里的 completeness 和 issues，执行状态 completed 不等于计算成功。')

def action_definitions(kn_id,box_id,tool_ids,inputs,zh):
    """One tool action per function. The platform requires every input, so each execution records the dates and scope it assumed."""
    return [{'id':kn_id+'_'+op,'name':ACTION_NAMES[op][1 if zh else 0],'branch':'main','operation_config':{'type':'tool'},'object_type_id':'',
             'action_type':'modify','action_intent':'modify','action_source':{'type':'tool','box_id':box_id,'tool_id':tool_ids[op]},
             'parameters':[{'name':i['name'],'type':i['type'],'value_from':'input','comment':i['description']} for i in inputs[op]],
             'comment':DESCRIPTIONS[op][1 if zh else 0]+'\n'+ACTION_RULE[1 if zh else 0]} for op in OPERATIONS]

def actions_ready(kn_id,box_id,tool_ids):
    """Every enabled function is the source of a tool action in the network."""
    listing=entries(cli('bkn','action-type','list',kn_id),'entries','data')
    sources={(a.get('action_source') or {}).get('tool_id') for a in listing
             if (a.get('operation_config') or {}).get('type')=='tool' and (a.get('action_source') or {}).get('box_id')==box_id}
    return set(tool_ids.values())<=sources

def run(kn_id,apply):
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='FIBO_'+manifest['metadata']['name'].rsplit('fibo-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Atomic post-trade controls / 原始事实交易后控制',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn'
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={};op_inputs={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':True,'description':desc} for n,typ,desc in [('portfolio_ids','array','Nonempty portfolio IDs / 组合主键'),('as_of_date','string','Business date YYYY-MM-DD / 业务日期'),('knowledge_date','string','Knowledge cutoff YYYY-MM-DD / 知识截止日期'),('view_kind','string','actual or planned / 实际或计划')]]
        op_inputs[operation]=inputs
        body=dict(name=operation,description=DESCRIPTIONS[operation][1 if zh else 0],script_type='python',code=code,inputs=inputs,outputs=[dict(name='result',type='object',required=True,description='Typed rows, completeness, issues and evidence; blocked can retain independent known fields; USD identity may have null fx_id / 业务结果及证据；blocked仍可保留独立已知值，美元恒等换算可无fx_id')])
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
        # Each function runs as a tool action; overwrite keeps a repeated install idempotent and follows re-created tool IDs.
        cli('call',BKN_API+'/knowledge-networks/'+kn_id+'/action-types?import_mode=overwrite','-X','POST','-d',json.dumps({'entries':action_definitions(kn_id,bid,tids,op_inputs,zh)},ensure_ascii=False))
    elif not actions_ready(kn_id,bid,tids):raise ValueError('missing function action')
    if apply:skills=register_skills(apply=True,kn_id=kn_id)
    else:
        skills={'owned':read()['skills']}
        if not skills['owned']:raise ValueError('missing owned Skill')
    return {'toolbox_id':bid,'tool_ids':tids,'action_ids':[kn_id+'_'+op for op in OPERATIONS],'source_sha256':hashes,'skills':skills,'ownedExecution':read()}
