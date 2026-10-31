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

def run(kn_id,apply):
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='FIBO_'+manifest['metadata']['name'].rsplit('fibo-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Atomic post-trade controls / 原始事实交易后控制',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn'
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':True,'description':desc} for n,typ,desc in [('portfolio_ids','array','Nonempty portfolio IDs / 组合主键'),('as_of_date','string','Business date YYYY-MM-DD / 业务日期'),('knowledge_date','string','Knowledge cutoff YYYY-MM-DD / 知识截止日期'),('view_kind','string','actual or planned / 实际或计划')]]
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
        cli('bkn','capability','attach',kn_id,'--box',bid,'--tool',','.join(tids.values()))
    if apply:skills=register_skills(apply=True,kn_id=kn_id)
    else:
        skills={'owned':read()['skills']}
        if not skills['owned']:raise ValueError('missing owned Skill')
    return {'toolbox_id':bid,'tool_ids':tids,'source_sha256':hashes,'skills':skills,'ownedExecution':read()}
