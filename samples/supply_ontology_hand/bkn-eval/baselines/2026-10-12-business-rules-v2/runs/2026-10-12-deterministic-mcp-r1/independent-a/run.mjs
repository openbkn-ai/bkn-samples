import fs from 'node:fs';
import {createClient} from '/Users/leecky/Downloads/Dev/oneclick-onboard/tooling/bkn-sdk-703921d/dist/index.js';
const dir='artifacts/acceptance/supply-deterministic-v3/independent-a';
const c=createClient({baseUrl:'http://localhost:8081',retry:false}); const kn='supply_ontology_hand';
const caps=JSON.parse(fs.readFileSync(dir+'/search_capabilities.json')).capabilities;
const objects=JSON.parse(fs.readFileSync(dir+'/objects.json')).object_types;
const yaml=fs.readFileSync('samples/supply_ontology_hand/bkn-eval/baselines/2026-10-12-business-rules-v2/question-set-v3.yaml','utf8');
const questions=[...yaml.matchAll(/- id: ([MFRS]-\d+)\n  question: ([\s\S]*?)(?=\n- id:|\nsnapshot_kind:)/g)].map(m=>({id:m[1],question:m[2].replace(/\n    /g,' ')}));
const redact=(x)=>JSON.parse(JSON.stringify(x,(k,v)=>/^(lease_token|token|authorization|credential|password)$/i.test(k)?'[REDACTED]':v));
const write=(p,x)=>fs.writeFileSync(dir+'/'+p,JSON.stringify(redact(x),null,2)+'\n');
const eq=(field,value)=>({field,operation:'==',value,value_from:'const'});
const and=(...sub_conditions)=>({operation:'and',sub_conditions});
const open={field:'closestatus_title',operation:'!=',value:'已关闭',value_from:'const'};
const metric=(name,condition)=>({tool:'query_metric',args:{kn_id:kn,metric_id:objects.flatMap(o=>o.related_metrics||[]).find(x=>x.name===name).id,time:{instant:true},response_format:'json',...(condition?{condition}:{})}});
const fn=(name,arguments_)=>({tool:'execute_tool',args:{...caps.find(x=>x.name===name).call.arguments,arguments:arguments_}});
const bom=p=>fn('BOM清单',{product:p,depth:99,include_substitute:false});
const sell=(product,substitute_enabled=false,finished_goods_scope='all')=>fn('合计可售',{product,substitute_enabled,production_scope:'all',finished_goods_scope});
const net=(product,qty)=>fn('要X套净需求与齐套',{product,qty,substitute_enabled:false,warehouse_scope:'all'});
const multi=(p1='382-000005',q1=50,p2='P61-000351',q2=60)=>fn('共用料与多需求争用',{demands:[{product:p1,qty:q1},{product:p2,qty:q2}],substitute_enabled:false,warehouse_scope:'all'});
const common=(products,depth=99)=>fn('产品BOM共用清单',{products,depth,include_substitute:false});
const plans={
'M-02':[metric('物料总数')],'M-03':[metric('供应商总数')],'M-04':[metric('销售订单数')],'M-05':[metric('仓库数')],
'M-06':[sell('382-000005',false,'finished_goods')],'M-07':[metric('预测需求量合计',open)],'M-08':[fn('未关闭预测单数',{})],'M-09':[metric('销售订单数',eq('order_status','执行中'))],
'M-10':[metric('签约数量合计',eq('product_code','382-000005')),metric('发货数量合计',eq('product_code','382-000005'))],
'M-11':[fn('未关闭预测单数',{product_code:'382-000005'}),metric('预测需求量合计',and(open,eq('material_number','382-000005')))],
'M-12':[fn('未关闭预测单数',{product_code:'U00-000080'}),metric('预测需求量合计',and(open,eq('material_number','U00-000080')))],
'M-13':[metric('物料总数',eq('materialattr','外购'))],'M-14':[metric('物料总数',eq('materialattr','自制'))],'M-15':[metric('供应商总数',eq('purchaserid_name','杨强云'))],
'F-01':[fn('BOM清单',{product:'382-000005',depth:1,include_substitute:false})],'F-02':[common(['382-000005','P61-000351'])],'F-03':[common(['382-000005','P61-000351','U00-000151'])],
'F-04':[sell('382-000005')],'F-05':[sell('U00-000151')],'F-06':[net('382-000005',50)],'F-07':[fn('标准交期',{material_code:'606-000989'})],
'F-08':[fn('理论可产',{product:'382-000005',substitute_enabled:false,warehouse_scope:'production_available'})],'F-09':[fn('理论可产',{product:'U00-000151',substitute_enabled:false,warehouse_scope:'production_available'})],
'F-10':[net('P61-000351',60)],'F-11':[multi()],'F-12':[common(['P61-000351','U00-000151'])],'F-13':[fn('无需采购最大可产',{product:'382-000005',substitute_enabled:false,warehouse_scope:'production_available'})],
'F-14':[fn('BOM清单',{product:'U00-000080',depth:99,include_substitute:false,report_grain:'full',page_size:500,offset:0})],'F-15':[sell('382-000005',true)],
'R-01':[fn('BOM清单',{product:'P61-000351',depth:1,include_substitute:false})],'R-02':[fn('BOM清单',{product:'U00-000080',depth:1,include_substitute:false})],'R-03':[bom('U00-000080')],'R-04':[bom('382-000005')],
'R-05':[fn('物料反查产品',{material_code:'321-000569'})],'R-06':[fn('物料反查产品',{material_code:'606-000989'})],'R-07':[fn('物料反查产品',{material_code:'725-000226'})],'R-08':[common(['382-000005','382-000006'],1)],
'R-09':[fn('替代料状态',{product:'382-000005',warehouse_scope:'all',substitute_enabled:true})],
'S-01':[net('P61-000351',60)],'S-02':[sell('U00-000151')],'S-03':[net('382-000005',50)],'S-04':[multi()],'S-05':[common(['382-000005','P61-000351']),multi()],'S-06':[net('P61-000351',60)],
'S-07':[fn('生产计划齐套倒排',{product:'382-000005',demand_qty:50,demand_end:'2026-09-05',business_date:'2026-08-25',substitute_enabled:true,warehouse_scope:'all'})],
'S-08':[fn('供应状态诊断',{material_code:'321-000569',due_date:'2026-09-08',gross_requirement:240,warehouse_scope:'all'})],
'S-09':[sell('U00-000151')],'S-10':[sell('U00-000151')],'S-11':[multi('P61-000351',60,'U00-000151',50)]};
let convo=JSON.parse(fs.readFileSync(dir+'/start-test.json')).conversation_id;
for(const q of questions.filter(q=>q.id!=='M-01')){
 const p=dir+'/raw-'+q.id+'.json'; if(fs.existsSync(p)){console.log('EXISTS',q.id);continue;}
 let raw={id:q.id,question:q.question,calls:[]};
 raw.start=await c.context.toolCall(kn,'bkn_start_interaction',{conversation_mode:'continue',conversation_id:convo,question:q.question,agent_name:'supply-deterministic-v3-independent-a'});
 const ctx={conversation_id:raw.start.conversation_id,interaction_id:raw.start.interaction_id};
 write('raw-'+q.id+'.json',raw);
 try{
  for(const plan of plans[q.id]){const params={...plan.args,bkn_context:ctx};let output=await c.context.toolCall(kn,plan.tool,params);raw.calls.push({tool:plan.tool,params,output});write('raw-'+q.id+'.json',raw);}
  raw.finish=await c.context.toolCall(kn,'bkn_finish_interaction',{interaction_id:ctx.interaction_id,outcome:'completed',answer:JSON.stringify({id:q.id,observed:raw.calls.map(x=>x.output),scope:'题设明确范围；数量题仅可用库存，不含PO或新采购。'})});
  write('raw-'+q.id+'.json',raw);
  for(let i=0;i<90;i++){raw.trace=await c.trace.lifecycle.getInteraction(ctx.interaction_id);if(raw.trace.evidence_status!=='assembling')break;await new Promise(r=>setTimeout(r,1000));}
  raw.receipts=[];for(const receipt of raw.trace.closure_manifest?.expected_receipts||[])raw.receipts.push(await c.trace.lifecycle.getReceipt(receipt.receipt_id));
  write('raw-'+q.id+'.json',raw);console.log(q.id,raw.trace.execution_status,raw.trace.evidence_status,raw.calls.map(x=>JSON.stringify(x.output).length).join(','));
 }catch(e){raw.error={name:e.name,message:e.message};write('raw-'+q.id+'.json',raw);console.log('ERROR',q.id,e.message);throw e;}
}
