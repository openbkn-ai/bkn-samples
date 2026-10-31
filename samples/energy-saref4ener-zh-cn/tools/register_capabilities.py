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

def run(kn_id,apply):
    manifest=json.loads((ROOT/'sample.yaml').read_text());name='ENERGY_'+manifest['metadata']['name'].rsplit('saref4ener-',1)[1].replace('-','_')+'_Functions'
    boxes=entries(cli('toolbox','list','--keyword',name,'--limit','100'),'data','entries');matches=[b for b in boxes if b['box_name']==name]
    if len(matches)>1:raise ValueError('ambiguous owned toolbox')
    if not matches:
        if not apply:raise ValueError('missing owned toolbox')
        box=cli('call',API+'/tool-box','-X','POST','-d',json.dumps(dict(box_name=name,box_desc='Read-only synthetic demand-response assessment, proposal and settlement',box_category='data_process',metadata_type='function',source='custom')));remember('toolboxes',box['box_id'])
    else:box=matches[0];require_owned('toolboxes',box['box_id'])
    zh=json.loads((ROOT/'model-contract.json').read_text()).get('language')=='zh-cn'
    bid=box['box_id'];tools=entries(cli('tool','list','--toolbox',bid,'--all'),'tools','data','entries');tids={};hashes={}
    for operation in OPERATIONS:
        code=tool_code(operation,kn_id);hashes[operation]=hashlib.sha256(code.encode()).hexdigest();found=next((t for t in tools if t['name']==operation),None)
        inputs=[{'name':n,'type':typ,'required':True,'description':zh_d if zh else en_d} for n,typ,en_d,zh_d in INPUTS]
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
        cli('bkn','capability','attach',kn_id,'--box',bid,'--tool',','.join(tids.values()))
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
    return {'toolbox_id':bid,'tool_ids':tids,'source_sha256':hashes,'skills':skills,'ownedExecution':read()}
