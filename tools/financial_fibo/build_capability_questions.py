"""AUTHORING ONLY: implementation-derived public development cases, not independent gold."""
import sys,json,csv,importlib.util
from pathlib import Path
from build_response_contracts import capability_contract
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[2];s=root/'samples/financial-fibo-en-us';spec=importlib.util.spec_from_file_location('core',s/'tools/post_trade.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
for lang in ('en-us','zh-cn'):
 p=root/'samples'/('financial-fibo-'+lang);c=json.loads((p/'model-contract.json').read_text());T={}
 for t in c['object_types']:
  with (p/'data'/(t+'.csv')).open() as f:T[t]=list(csv.DictReader(f))
 zh=lang=='zh-cn';qs=[];gold={}
 portfolios=['PF-001','PF-019','PF-029','PF-035','PF-041','PF-046','PF-049','PF-050','PF-073','PF-139']
 for n,pid in enumerate(portfolios):
  scope=dict(portfolio_ids=[pid],as_of_date='2027-02-28',knowledge_date='2027-02-28',view_kind='actual')
  settlement=core.execute('settlement_asof',T,c,scope)
  fields=['portfolio_id','trade_id','instruction_id','instrument_id','counterparty_id','side','required_quantity','settled_quantity','remaining_quantity','latest_event_id','status_code','overdue','event_ids']
  qid=f'CAP-{n+1:03}';qs.append(dict(id=qid,level='hard_complex',scenario_id='C01',as_of_date=scope['as_of_date'],requested_fields=fields,question=(f'中台需要排查{pid}截至2027-02-28、知识截止同日的实际结算义务。请仅列尚未完全结算或数量未知的指令，区分逾期与失败、部分和待结算，给出所要求字段和增量结算事件证据。无例外返回空列表。' if zh else f'Middle office is triaging actual settlement obligations for {pid} as of 2027-02-28, knowledge cutoff the same day. List only instructions not fully transferred or with unknown quantities, distinguish overdue from failed/partial/pending, and include requested fields and incremental-event evidence. Return an empty list if no exceptions.')))
  gold[qid]={'rows':[{f:r[f] for f in fields} for r in settlement['rows'] if r['status_code']!='settled']}
  actual=core.execute('valuation_asof',T,c,scope);planned=core.execute('valuation_asof',T,c,{**scope,'as_of_date':'2027-03-31','view_kind':'planned'})
  av={r['opening_id']:r for r in actual['rows']};pv={r['opening_id']:r for r in planned['rows']};rows=[]
  for oid in sorted(av):
   a,b=av[oid],pv[oid];rows.append(dict(opening_id=oid,instrument_id=a['instrument_id'],actual_status=a['status_code'],planned_status=b['status_code'],actual_value=a['market_value_base'],planned_value=b['market_value_base'],value_change=None if a['market_value_base'] is None or b['market_value_base'] is None else str(core.number(b['market_value_base'])-core.number(a['market_value_base'])),actual_settled_quantity=a['settled_basis_quantity'],planned_settled_quantity=b['settled_basis_quantity'],actual_price_id=a['price_id'],planned_price_id=b['price_id']))
  qid=f'CAP-{n+11:03}';qs.append(dict(id=qid,level='hard_complex',scenario_id='C02',as_of_date='2027-02-28',requested_fields=list(rows[0]),question=(f'会计与组合经理共同复核{pid}：比较2027-02-28实际与2027-03-31计划的逐期初持仓估值和已结算数量，两者知识截止均为2027-02-28。计算计划减实际的美元市值变化，任何一侧未知则变化为空，不能把计划当实际。附两侧价格主键；状态用稳定机器码。' if zh else f'Accounting and the portfolio manager review {pid}: compare each opening position at actual 2027-02-28 versus planned 2027-03-31, both known as of 2027-02-28. Show valuation and settled quantities, planned minus actual USD value (null if either side unknown), and each side price ID. Use stable machine status codes and do not present plans as actual facts.')));gold[qid]={'rows':rows}
  assessed=core.execute('limit_assessment_asof',T,c,{**scope,'as_of_date':'2027-03-31','view_kind':'planned'})
  fields=['portfolio_id','entity_id','measure','observed_value','limit_id','threshold','excess_value','status_code','selection_status','recorded_value','recorded_difference']
  qid=f'CAP-{n+21:03}';qs.append(dict(id=qid,level='hard_complex',scenario_id='C03',as_of_date='2027-03-31',requested_fields=fields,question=(f'风控审核{pid}的2027-03-31计划，知识截止为2027-02-28。请从原始事实重算全部发行方集中度与非净额未结算卖出应收并匹配生效限额；检查超限、无法判断与版本选择问题。每项比较已记录快照，给出差异；未知不能按零处理。列全所有实体，不只列超限。' if zh else f'Risk reviews the 2027-03-31 plan for {pid}, known on 2027-02-28. Reconstruct all issuer concentrations and non-netted unsettled SELL receivables from source facts, match effective mandates and distinguish threshold breaches, unknowns and version-selection defects. Compare each reconstructed result with its recorded exposure and show differences. List every entity, not only breaches; unknown is not zero.')));gold[qid]={'rows':[{f:r[f] for f in fields} for r in assessed['rows']]}
 for q in qs:
  q['response_contract']=capability_contract(q['requested_fields'],gold[q['id']]['rows'],p,zh,q['scenario_id'])
 (p/'bkn-eval/capability-questions.json').write_text(json.dumps(sorted(qs,key=lambda q:q['id']),ensure_ascii=False,indent=2)+'\n');(p/'bkn-eval/capability-expected.json').write_text(json.dumps(gold,ensure_ascii=False,indent=2)+'\n')
