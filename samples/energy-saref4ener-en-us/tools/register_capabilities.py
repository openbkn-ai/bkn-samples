"""Register/verify the three demand-response functions and the Skills."""
import hashlib,json,os,subprocess

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
OPERATIONS=('flexibility_assessment','dispatch_plan','settlement_assessment')
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
    source=json.loads((ROOT/'model-contract.json').read_text())
    c={'block_durations':source['block_durations'],'object_types':{t:{'primary_key':s['primary_key'],'fields':s['fields']} for t,s in source['object_types'].items()}}
    core=(ROOT/'tools/energy.py').read_text();loader=(ROOT/'tools/managed_execution.py').read_text()
    entry="\nfrom sandbox_sdk import tool\nfrom bkn_osdk import kn\nfrom bkn_osdk.config import Context\nimport os\nfrom urllib.parse import urlsplit\n\ndef managed_query(*args, **kwargs):\n    base = os.environ.get('BKN_BASE_URL')\n    if not base:\n        parsed = urlsplit(os.environ.get('BKN_SANDBOX_MCP_URL', ''))\n        if not parsed.scheme or not parsed.netloc:\n            raise ValueError('MISSING_MANAGED_BASE_URL')\n        base = parsed.scheme+'://'+parsed.netloc\n    ctx = Context(base_url=base, token=os.environ.get('BKN_TOKEN', ''),\n        conversation_id=os.environ.get('BKN_CONVERSATION_ID'),\n        interaction_id=os.environ.get('BKN_INTERACTION_ID'),\n        parent_operation_id=os.environ.get('BKN_PARENT_OPERATION_ID'), traced=True)\n    if not ctx.token or not ctx.interaction_id:\n        raise ValueError('MISSING_MANAGED_CALL_CONTEXT')\n    return kn.query_object_instance(*args, context=ctx, **kwargs)\n\n@tool\ndef energy_function(event_ids: list, as_of_date: str, knowledge_date: str) -> dict:\n    scope = dict(event_ids=event_ids, as_of_date=as_of_date, knowledge_date=knowledge_date)\n    return run_request(managed_query, KN_ID, CONTRACT, OPERATION, scope, execute)\n"
    return core+'\n'+loader+'\nKN_ID='+repr(kn_id)+'\nOPERATION='+repr(operation)+'\nCONTRACT='+repr(c)+'\n'+entry

# (English, Chinese) inputs and descriptions; every function takes the same dated scope.
INPUTS=[('event_ids','array','1 to 20 event IDs; events sharing a date and block are always assessed together.','1 到 20 个事件编号；同一天同一时段的事件总是一起评估。'),
        ('as_of_date','string','Business date YYYY-MM-DD.','业务日期 YYYY-MM-DD。'),
        ('knowledge_date','string','Count only records known by this date, YYYY-MM-DD; usually the business date.','只计这一天及以前已知的记录，YYYY-MM-DD；一般与业务日期相同。')]
DESCRIPTIONS={
    'flexibility_assessment':('Eligible reduction for events: per device the minimum of offer, device limit, forecast or baseline above service load and caps, limited by site caps, '
                              'with reasons a device is excluded or its capacity is undeterminable.',
                              '计算事件的可承诺削减：每台设备取申报、设备上限、预测或基线扣除保障负荷后的余量和限额中的最小值，再受场所上限约束，并给出设备被排除或算不清的原因。'),
    'dispatch_plan':('Read-only plan for events sharing a date and block: existing commitments first, then new allocation by priority and offer cost within device and site limits; '
                     'committed, new, shortfall and estimated cost.',
                     '同一天同一时段事件的只读调度方案：已承诺的先占用，再按优先级和申报成本在设备和场所上限内新增，给出已承诺、新增、缺口和预计成本。'),
    'settlement_assessment':('Settlement for past events: verified energy from receipts, approved baselines and valid readings shared across same-block commitments, delivery ratio, '
                             'revenue, customer compensation, net and the ledger difference.',
                             '已发生事件的结算：按执行回执、核定基线和有效读数核实电量并在同时段承诺间分摊，给出交付比例、收入、客户补偿、净额和与台账的差额。'),
}

ACTION_NAMES={'flexibility_assessment':('Eligible reduction for events','事件可承诺削减'),
              'dispatch_plan':('Dispatch plan for events','事件调度方案'),
              'settlement_assessment':('Settlement for past events','已发生事件结算')}

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
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='ENERGY_'+manifest['metadata']['name'].rsplit('saref4ener-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Read-only synthetic demand-response assessment, proposal and settlement',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn'
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={};op_inputs={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':True,'description':zh_d if zh else en_d} for n,typ,en_d,zh_d in INPUTS]
        op_inputs[operation]=inputs
        body=dict(name=operation,description=DESCRIPTIONS[operation][1 if zh else 0],script_type='python',code=code,inputs=inputs,outputs=[dict(name='result',type='object',required=True,description='Typed energy rows, completeness, issues and source evidence; null remains unknown')])
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
        skills=register_skills(apply=False,kn_id=kn_id)
        listed=entries(cli('skill','list','--all'),'data','entries')
        for local in skills['skills']:
            matches=[s for s in listed if s.get('name')==local['name']]
            if len(matches)!=1:raise ValueError('missing/ambiguous installed Skill')
            sid=matches[0].get('skill_id') or matches[0].get('id')
            require_owned('skills',sid)
            if matches[0].get('status')!='published':raise ValueError('unpublished Skill')
    return {'toolbox_id':bid,'tool_ids':tids,'action_ids':[kn_id+'_'+op for op in OPERATIONS],'source_sha256':hashes,'skills':skills,'ownedExecution':read()}
