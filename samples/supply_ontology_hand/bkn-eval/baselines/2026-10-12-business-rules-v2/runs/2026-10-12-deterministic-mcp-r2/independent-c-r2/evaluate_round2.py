import json,hashlib,pathlib,importlib.util,copy
import yaml
P=pathlib.Path(__file__).resolve().parent.parent; A=P/'independent-a-r2'; C=P/'independent-c-r2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
spec=importlib.util.spec_from_file_location('compare',P.parents[2]/'samples/supply_ontology_hand/bkn-eval/baselines/2026-10-12-business-rules-v2/gold-evidence/offline_compare.py')
# Locate only the explicitly authorized comparator.
spec=importlib.util.spec_from_file_location('compare',pathlib.Path.cwd()/'samples/supply_ontology_hand/bkn-eval/baselines/2026-10-12-business-rules-v2/gold-evidence/offline_compare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=read(A/'answers.json'); gold=yaml.safe_load((pathlib.Path.cwd()/'samples/supply_ontology_hand/bkn-eval/baselines/2026-10-12-business-rules-v2/answer-set-v3.yaml').read_text())['answers']; by={r['id']:r for r in a['answers']}
manifest=read(A/'manifest.json'); hash_issues=[f['path'] for f in manifest['files'] if sha(A/f['path'])!=f['sha256']]
identity={'candidate':a['candidate'],'answers_sha256':sha(A/'answers.json'),'question_sha256':sha(pathlib.Path.cwd()/'samples/supply_ontology_hand/bkn-eval/baselines/2026-10-12-business-rules-v2/question-set-v3.yaml'),'gold_sha256':sha(pathlib.Path.cwd()/'samples/supply_ontology_hand/bkn-eval/baselines/2026-10-12-business-rules-v2/answer-set-v3.yaml'),'manifest_hash_mismatches':hash_issues}
assert identity['answers_sha256']=='c1452b7345ce938df79e843f423a34aa782fc4d0d0804e492850292e2b288e06'
assert identity['question_sha256']=='51c60429b17053071ad8eef59de734e3297835430d274b9a58d24082e63e0026'
assert identity['gold_sha256']=='0ed51302d2fe0ddc579d01d16b13aceb391eea594449919bcc8eca52da1596ab'
assert a['candidate']['package_sha256']=='b9d87928142a93f01bc1cd45cad1d010a77fa482111dc51d014a110214197d06'
assert a['candidate']['installation_id']=='inst-supply-chain-14a1838eceeb4e88b2e4e045d875406c'
def shortages(rows,key):
 out={}
 for x in rows:out[x['material_code']]=out.get(x['material_code'],0)+x[key]
 return out
def norm(q,o,answer):
 n=copy.deepcopy(o)
 aliases={'product':'product_code','qty':'demand_qty','finished_goods_allocated_qty':'fg_allocated','root_net_demand':'manufacturing_qty','kitting_ok':'inventory_covers','gap_count':'shortage_material_count','shared_codes':'material_codes','l1_main_count':'count','affected_product_count':'count','signed_qty':'signing_qty','shipped_qty':'shipping_qty','final_leaf_shortage_qty':'net_shortage','on_time_covered':'on_time','remaining_finished_goods_qty':'remaining_qty','satisfied':'covers','shortfall':'capacity_shortfall'}
 for k,v in aliases.items():
  if k in o:n[v]=o[k]
 if q.startswith('M-'):
  if q in ['M-10','M-11','M-12']:pass
  elif 'count' in o:n['value']=o['count']
  elif 'open_count' in o:n['value']=o['open_count']
  elif 'available_qty' in o:n['value']=o['available_qty']
 if q in ['M-11','M-12']:n['count']=o['open_count'];n['qty']=o['demand_qty']
 if 'materials' in o:n['material_codes']=[x['material_code'] for x in o['materials']]
 if 'gaps' in o:n['leaf_shortages']=shortages(o['gaps'],'net_shortage_qty')
 if 'build_qty' in o:n['theoretical_build_qty']=o['build_qty']
 if q in ['R-03','R-04']:n['count']=o['main_only_unique_material_count']
 if q=='R-08':n['count']=o['shared_count']
 if q=='R-09':
  mains=[x for x in o['members'] if not x['is_substitute']]
  if len(mains)==1:n['main_material_code']=mains[0]['material_code']
  n['substitutes']=[dict(material_code=x['material_code'],available_qty=x['available_qty'],usage=x['standard_usage']) for x in o['substitutes']]
 if q=='F-14' and o.get('consistency_status')=='consistent' and 'reported_rows_incl_root' in o:n['node_count']=o['reported_rows_incl_root']
 if q=='S-02' and '不等于交期承诺' in answer:n['delivery_promise']=False
 if q=='S-08':
  for k,v in {'available_qty':'inventory_qty','on_time_supply_qty':'confirmed_supply_qty','on_time_shortage_qty':'shortage_qty','on_time_covered':'covers'}.items():
   if k in o:n[v]=o[k]
 if 'allocations' in o:
  n['all_covered']=o['all_satisfied'];n['demands']=[]
  for x in o['allocations']:
   d={'product_code':x['product_code'],'demand_qty':x['demand_qty'],'inventory_covers':x['satisfied'],'shortage_material_count':x['shortage_count'],'leaf_shortages':shortages(x['shortages'],'shortage')};n['demands'].append(d)
 if 'shared_main_count' in o:n['shared_count']=o['shared_main_count']
 return n
results=[];call_counts={}; function_ids=set();metric_ids=set()
for g in gold:
 q=g['id'];r=by.get(q);issues=[]; evidence=[]
 if not r:issues=[{'error':'missing_question'}];n={}
 else:
  n=norm(q,r['observed'],r['answer']);issues=m.differences(g['expected'],n)
  for ref in r['evidence_ref']:
   raw=read(A/ref);trace=raw.get('trace',{});receipts=raw.get('receipts',[])
   ei=[]
   if trace.get('execution_status')!='completed' or trace.get('evidence_status')!='complete':ei.append('incomplete_trace')
   for call in raw.get('calls',[]):
    t=call['tool'];call_counts[t]=call_counts.get(t,0)+1
    prm=call['params']; matched=[x for x in receipts if x.get('tool_name')==t and x.get('receipt_status')=='completed']
    if not matched:ei.append('missing_completed_receipt:'+t)
    if t=='execute_tool':
     tid=prm['tool_id'];function_ids.add(tid)
     if not any(any(b.get('ref_type')=='function' and b.get('ref_id')=='function:supply_ontology_hand:'+tid for b in x.get('business_refs',[])) for x in receipts):ei.append('missing_function_business_ref:'+tid)
    elif t=='query_metric':metric_ids.add(prm['metric_id'])
   evidence.append({'file':ref,'sha256':sha(A/ref),'interaction_id':trace.get('interaction_id'),'execution_status':trace.get('execution_status'),'evidence_status':trace.get('evidence_status'),'receipt_count':len(receipts),'issues':ei})
   issues += [{'error':x,'evidence_ref':ref} for x in ei]
  if q=='F-14' and r['observed'].get('consistency_status')=='contradictory':issues.append({'error':'contradictory_published_result'})
 results.append({'id':q,'passed':not issues,'expected':g['expected'],'normalized_observed':n,'differences':issues,'evidence':evidence})
skills=[]
for f in sorted(A.glob('skill-*.json')):
 s=read(f);skills.append({'file':f.name,'skill_id':s['skill_id'],'status':s['status'],'sha256':sha(f)})
summary={'round':2,'judge':'independent-c','total':len(gold),'answered':len(by),'passed':sum(r['passed'] for r in results),'failed':sum(not r['passed'] for r in results),'unexpected_ids':sorted(set(by)-{g['id'] for g in gold}),'failed_ids':[r['id'] for r in results if not r['passed']],'identity':identity,'published_skill_reads':skills,'MCP_call_counts':call_counts,'function_ids':sorted(function_ids),'metric_ids':sorted(metric_ids),'strict_policy':'All frozen expected fields required; alias/list-map normalization only; no inferred missing answers; duplicate shortage positions summed by material code without altering total quantity.','decisive_question_results':{r['id']:{'passed':r['passed'],'normalized_observed':r['normalized_observed']} for r in results if r['id'] in ['S-01','S-05','S-08']}}
(C/'judgment.json').write_text(json.dumps({'round':2,'results':results},ensure_ascii=False,indent=2)+'\n');(C/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['total','passed','failed','failed_ids','MCP_call_counts']},ensure_ascii=False))
