"""Register/verify the three retail functions and the Skills."""
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
OPERATIONS=('inventory_asof','fulfillment_plan','recall_assessment')
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
def retail_function(as_of_date: str, knowledge_date: str, product_ids: list=None, location_ids: list=None, lot_ids: list=None, order_ids: list=None, recall_id: str='', trace_lot_id: str='', mode: str='orders', horizon_date: str='2027-03-31') -> dict:
    scope=dict(product_ids=product_ids,as_of_date=as_of_date,knowledge_date=knowledge_date,location_ids=location_ids,lot_ids=lot_ids,order_ids=order_ids,recall_id=recall_id,trace_lot_id=trace_lot_id,mode=mode,horizon_date=horizon_date)
    # An action sends every declared input; an empty string means not set, so the default applies.
    scope={k:v for k,v in scope.items() if v!=''}
    return run_request(managed_query,KN_ID,CONTRACT,OPERATION,scope,execute)
"""
    return core+'\n'+loader+'\nKN_ID='+repr(kn_id)+'\nOPERATION='+repr(operation)+'\nCONTRACT='+repr(c)+'\n'+entry

# (name, type, required, English, Chinese) per operation; only what each calculation uses.
COMMON=[('as_of_date','string',True,'Business date YYYY-MM-DD.','业务日期 YYYY-MM-DD。'),
        ('knowledge_date','string',True,'Count only records known by this date, YYYY-MM-DD; usually the business date.','只计这一天及以前已记录的事件，YYYY-MM-DD；一般与业务日期相同。')]
INPUTS={
    'inventory_asof':[('product_ids','array',True,'1 to 50 product IDs.','1 到 50 个商品编号。'),
                      ('location_ids','array',False,'Locations to report; pass an empty list for all.','只看这些地点；传空列表表示不限。'),
                      ('lot_ids','array',False,'Lots to report; pass an empty list for all.','只看这些批次；传空列表表示不限。'),
                      ('trace_lot_id','string',False,'Lot whose connected upstream and downstream lots to trace; pass an empty string for none.','要追溯上下游相连批次的批次；不追溯时传空字符串。')],
    'fulfillment_plan':[('product_ids','array',True,'1 to 50 product IDs.','1 到 50 个商品编号。'),
                        ('mode','string',False,'orders allocates open orders; replenishment walks the forecast. Pass orders unless the question is about replenishment.','orders 为未完成订单配货；replenishment 按预测算补货。问补货时传 replenishment，其他传 orders。'),
                        ('order_ids','array',False,'Orders to report, pass an empty list for all; other orders keep their place in the queue.','只看这些订单，传空列表表示全部；其他订单仍按原顺序占用库存。'),
                        ('location_ids','array',False,'Locations to report; pass an empty list for all.','只看这些地点；传空列表表示不限。'),
                        ('horizon_date','string',False,'Replenishment horizon YYYY-MM-DD; 2027-03-31 for the March plan.','补货计算截至日期 YYYY-MM-DD；三月计划传 2027-03-31。')],
    'recall_assessment':[('recall_id','string',True,'Recall ID.','召回编号。')],
}
DESCRIPTIONS={
    'inventory_asof':('Replay stock movements as of a date and knowledge cutoff: on hand, in transit, quarantined, recall-blocked, reserved and available by lot and location, '
                      'inspection and expiry status, and data issues that make stock undeterminable.',
                      '按某天和当天已知的出入库事件回放库存：各批次地点的在库、在途、隔离、召回封存、预留和可用，质检和效期状态，以及导致库存算不清的数据问题。'),
    'fulfillment_plan':('Allocate available stock to open orders by priority, due date and earliest expiry with shelf-life checks, or walk the March forecast to recommend '
                        'replenishment from stock and eligible planned receipts.',
                        '按优先级、交期和先到期先出给未完成订单配货并检查剩余保质期；或按三月预测，用库存和合格计划到货算出建议补货量。'),
    'recall_assessment':('Trace an open recall from its root lot through splits and transformations and report, by product and location, on hand, in transit, sold, '
                         'returned, controlled, controllable, coverage and affected orders.',
                         '从召回根批次沿拆分和转换追到所有下游批次，按商品和地点给出在库、在途、已售、退回、已控制、可控制、控制比例和受影响订单。'),
}

ACTION_NAMES={'inventory_asof':('Inventory as of a date','按日期回放库存'),
              'fulfillment_plan':('Order allocation and replenishment','订单配货与补货'),
              'recall_assessment':('Recall control assessment','召回控制评估')}

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
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='RETAIL_'+manifest['metadata']['name'].rsplit('gs1-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Retail traceability, inventory and recall controls',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn'
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={};op_inputs={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':req,'description':zh_d if zh else en_d} for n,typ,req,en_d,zh_d in COMMON+INPUTS[operation]]
        op_inputs[operation]=inputs
        body=dict(name=operation,description=DESCRIPTIONS[operation][1 if zh else 0],script_type='python',code=code,inputs=inputs,outputs=[dict(name='result',type='object',required=True,description='Typed retail rows, completeness, issues and source evidence; null remains unknown')])
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
