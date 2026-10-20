"""Deterministic, bilingual fictional fixtures; never a production data source."""
import csv,json,hashlib,shutil
from pathlib import Path
from schema import TABLES,LABELS
from retail_core import execute
ROOT=Path(__file__).resolve().parents[2]
CONTRACT=json.loads(Path(__file__).with_name('schema-contract.json').read_text())
WORDS={
 'supplier':('Supplier','供应商'),'retailer':('Retailer','零售商'),'warehouse':('Warehouse','仓库'),'store':('Store','门店'),
 'receive':('Receiving','收货'),'dispatch':('Shipping','发运'),'arrive':('Arriving','到货'),'sale':('Retail sale','零售销售'),'return':('Customer return','客户退货'),
 'consume':('Transformation input','转换投入'),'produce':('Transformation output','转换产出'),'adjust':('Stock adjustment','库存调整'),'reversal':('Error declaration','错误撤销'),
 'passed':('Passed','合格'),'failed':('Failed','不合格'),'pending':('Pending','待检'),'actual':('Actual','实际'),'planned':('Planned','计划'),
 'open':('Open','进行中'),'closed':('Closed','已关闭'),'split':('Lot split','批次拆分'),'transform':('Product transformation','商品转换'),
}
FLAVORS=[('Original','原味'),('Strawberry','草莓'),('Blueberry','蓝莓'),('Mango','芒果'),('Peach','蜜桃'),('Coconut','椰香'),('Vanilla','香草'),('Cocoa','可可'),('Sesame','芝麻'),('Oat','燕麦')]
FOODS=[('Yogurt','酸奶','Dairy','乳制品'),('Wholegrain Biscuit','全麦饼干','Bakery','烘焙食品'),('Fruit Drink','果饮','Beverages','饮料'),('Breakfast Cereal','早餐谷物','Cereals','谷物食品'),('Nut Bar','坚果棒','Snacks','休闲食品')]
CITIES=[('Hangzhou','杭州'),('Suzhou','苏州'),('Nanjing','南京'),('Ningbo','宁波'),('Wuxi','无锡')]
BRANDS=[('Greenfield','青禾'),('Harvest','丰穗'),('Springwell','泉润'),('Sunridge','晴岭'),('Riverbend','江湾')]
DISTRICTS=[('Central','中心'),('East Lake','东湖'),('West Park','西园'),('Riverside','滨江'),('South Gate','南门')]
def build(lang):
 z=lang=='zh-cn';idx=int(z);tables={t:[] for t in TABLES}
 def word(c):return WORDS[c][idx]
 def add(t,**kw):
  r={f:str(kw.get(f,'')) for f in TABLES[t][1].split()};tables[t].append(r);return r
 for i in range(1,51):
  n=(i-1)%25;city=CITIES[n//5][idx];brand=BRANDS[n%5][idx];role='supplier' if i<=25 else 'retailer'
  add('organizations',organization_id=f'ORG-{i:03}',name=(city+brand+('食品有限公司' if role=='supplier' else '商贸有限公司')) if z else f'{city} {brand} '+('Foods Ltd' if role=='supplier' else 'Retail Ltd'),role=word(role),role_code=role)
 for i in range(1,26):
  city=CITIES[(i-1)//5][idx];district=DISTRICTS[(i-1)%5][idx]
  for code,prefix in [('warehouse','WH'),('store','STORE')]:
   add('locations',location_id=f'{prefix}-{i:03}',name=(city+district+('配送中心' if code=='warehouse' else '生活超市')) if z else f'{city} {district} '+('Distribution Center' if code=='warehouse' else 'Grocery'),location_type=word(code),location_type_code=code,organization_id=f'ORG-{i+25:03}')
 mid=0
 def movement(lid,code,qty,day,seq,src='',dst='',transfer='',order='',known=None,view='actual',event=None,reversal='',unit=None):
  nonlocal mid
  mid+=1
  return add('movements',movement_id=f'MOV-{mid:05}',event_id=event or f'EV-{mid:05}',lot_id=lid,event_type=word(code),event_type_code=code,source_location_id=src,destination_location_id=dst,transfer_id=transfer,order_id=order,quantity=qty,unit=unit or ('件' if z else 'ea'),event_date=day,event_sequence=seq,recorded_date=known or day,view_kind=word(view),view_code=view,reversal_of=reversal)
 for i in range(1,51):
  pid=f'PRD-{i:03}';j=(i-1)%25+1;wh=f'WH-{j:03}';store=f'STORE-{j:03}';supplier=f'ORG-{j:03}';food=FOODS[(i-1)//10];flavor=FLAVORS[(i-1)%10]
  add('products',product_id=pid,name=flavor[idx]+food[1]+'250克' if z else f'{flavor[0]} {food[0]} 250 g',category=food[3] if z else food[2],unit='件' if z else 'ea',pack_multiplier=6 if i%2 else 12,supplier_id=supplier,min_shelf_days=3+(i%4))
  for suffix,produced,expiry,received,qty in [('A','2026-11-01','2027-02-20','2026-11-03',120+i%7),('B','2027-02-01','2027-03-10','2027-02-02',150+i%9),('C','2027-01-15','2027-03-31','2027-01-16',180+i%11),('D','2027-02-15','2027-03-05','2027-02-16',80+i%5)]:
   lid=f'LOT-{i:03}-{suffix}'
   add('lots',lot_id=lid,product_id=pid,supplier_id=supplier,produced_date=produced,expiry_date=expiry,supplier_lot=f'SUP-{j:03}-{i:03}-{suffix}')
   movement(lid,'receive',qty,received,10,dst=wh)
   transfer=f'TRF-{i:03}-{suffix}';movement(lid,'dispatch',40,'2027-02-22',20,src=wh,dst=store,transfer=transfer)
   movement(lid,'arrive',35 if suffix=='B' and i%5==0 else 40,'2027-02-23',30,dst=store,transfer=transfer)
   sale=movement(lid,'sale',15+i%3,'2027-02-24',40,src=store,order=f'ORD-{i:03}-H')
   if suffix in ('B','C'):movement(lid,'return',3,'2027-02-25',50,dst=store,order=f'ORD-{i:03}-H')
   status='failed' if suffix=='C' and i%11==0 else 'pending' if suffix=='D' and i%13==0 else 'passed'
   add('inspections',inspection_id=f'QC-{i:03}-{suffix}',lot_id=lid,location_id=wh,inspection_date=received,known_date=received,result=word(status),result_code=status,reason=('微生物指标异常' if z else 'Microbial test exceeded control') if status=='failed' else ('待复检' if z else 'Awaiting retest') if status=='pending' else ('验收合格' if z else 'Receiving test passed'))
   if suffix=='C':
    add('holds',hold_id=f'HOLD-{i:03}-R',lot_id=lid,location_id=store,quantity=5,return_overlap_quantity=3,effective_from='2027-02-25',effective_to='2027-03-31',known_date='2027-02-25',reason='退货及包装复检' if z else 'Returns and packaging retest')
   if suffix=='B':
    add('holds',hold_id=f'HOLD-{i:03}-Q',lot_id=lid,location_id=wh,quantity=20,return_overlap_quantity=0,effective_from='2027-02-27',effective_to='2027-03-31',known_date='2027-02-27',reason='召回预隔离' if z else 'Recall precautionary hold',recall_id=f'REC-{i:03}')
   if i==41 and suffix=='C':movement(lid,'sale',7,'2027-02-26',60,src=store,known='2027-03-02',order=f'ORD-{i:03}-H')
   if i==42 and suffix=='C':movement(lid,'sale',sale['quantity'],sale['event_date'],sale['event_sequence'],src=store,order=sale['order_id'],event=sale['event_id'],known='2027-02-26')
   if i==43 and suffix=='C':movement(lid,'sale',99,sale['event_date'],sale['event_sequence'],src=store,order=sale['order_id'],event=sale['event_id'],known='2027-02-26')
   if i==44 and suffix=='C':
    err=movement(lid,'sale',9,'2027-02-26',60,src=store);movement(lid,'reversal',0,'2027-02-27',70,reversal=err['event_id'])
   if i==45 and suffix=='C':movement(lid,'arrive',8,'2027-02-26',60,dst=store,transfer='TRF-MISSING')
   if i==45 and suffix=='D':movement(lid,'arrive',8,'2027-02-26',60,dst=store,transfer='TRF-MISSING-D')
   if i==46 and suffix=='C':movement(lid,'sale',999,'2027-02-26',60,src=store)
  # Explicit input/output event pair; no inference from link quantities alone.
  future=f'LOT-{i:03}-P'
  add('lots',lot_id=future,product_id=pid,supplier_id=supplier,produced_date='2027-02-26',expiry_date='2027-03-31',supplier_lot=f'SUP-{j:03}-{i:03}-P')
  movement(future,'receive',25+i%4,'2027-03-05',80,dst=wh,view='planned',known='2027-02-26' if i%7 else '2027-03-01')
  add('inspections',inspection_id=f'QC-{i:03}-P',lot_id=future,location_id=wh,inspection_date='2027-02-27',known_date='2027-02-27',result=word('passed'),result_code='passed',reason='供应方出库抽检合格' if z else 'Supplier dispatch inspection passed')
  parent=f'LOT-{i:03}-B';child=f'LOT-{i:03}-D'
  movement(parent,'consume',20,'2027-02-21',15,src=wh);movement(child,'produce',20,'2027-02-21',15,dst=wh)
  add('lot_links',link_id=f'LINK-{i:03}',parent_lot_id=parent,child_lot_id=child,link_type=word('split'),link_type_code='split',parent_quantity=20,child_quantity=20,unit='件' if z else 'ea',effective_date='2027-02-21',known_date='2027-02-21')
  recallstatus='closed' if i==50 else 'open'
  add('recalls',recall_id=f'REC-{i:03}',root_lot_id=parent,announced_date='2027-02-27',known_date='2027-02-27',reason=('供应商包装密封缺陷' if z else 'Supplier seal integrity defect'),status=word(recallstatus),status_code=recallstatus)
  add('orders',order_id=f'ORD-{i:03}-H',customer_id=f'ORG-{j+25:03}',location_id=store,order_date='2027-02-20',due_date='2027-02-24',known_date='2027-02-20',priority=1,status=word('closed'),status_code='closed')
  add('order_lines',line_id=f'LINE-{i:03}-H',order_id=f'ORD-{i:03}-H',product_id=pid,quantity=4*(15+i%3)+(7 if i==41 else 0),unit='件' if z else'ea',min_shelf_days=0)
  for suffix,priority,qty,own in [('A',1,110+i%8,20),('B',2,100+i%5,10)]:
   oid=f'ORD-{i:03}-{suffix}';line=f'LINE-{i:03}-{suffix}'
   add('orders',order_id=oid,customer_id=f'ORG-{j+25:03}',location_id=wh,order_date='2027-02-20',due_date='2027-02-27' if i==49 and suffix=='A' else '2027-03-02' if suffix=='A' else'2027-03-04',known_date='2027-02-20',priority=priority,status=word('open'),status_code='open')
   add('order_lines',line_id=line,order_id=oid,product_id=pid,quantity=qty,unit='件' if z else'ea',min_shelf_days=3 if suffix=='A' else 7)
   add('reservations',reservation_id=f'RSV-{i:03}-{suffix}',line_id=line,lot_id=f'LOT-{i:03}-C',location_id=wh,quantity=own,effective_from='2027-02-22',effective_to='2027-03-04',known_date='2027-02-22')
  for month,dd in [('M1','2027-03-05'),('M2','2027-03-15'),('M3','2027-03-31')]:
   add('demand_forecasts',forecast_id=f'FC-{i:03}-{month}',product_id=pid,location_id=wh,demand_date=dd,quantity=80+i%15,unit='件' if z else'ea',known_date='2027-02-26',view_kind=word('planned'),view_code='planned')
 # Multi-parent transformation changes product: trace connectivity does not imply qty equivalence.
 add('lot_links',link_id='LINK-047-MULTI',parent_lot_id='LOT-048-B',child_lot_id='LOT-047-D',link_type=word('transform'),link_type_code='transform',parent_quantity=5,child_quantity=4,unit='件' if z else'ea',effective_date='2027-02-21',known_date='2027-02-21')
 movement('LOT-048-B','consume',5,'2027-02-21',16,src='WH-023')
 movement('LOT-047-D','produce',4,'2027-02-21',16,dst='WH-022')
 # Scope snapshots are recorded separately and can be reconciled with generic functions.
 for i in range(1,51):
  scope={'product_ids':[f'PRD-{i:03}'],'as_of_date':'2027-02-28','knowledge_date':'2027-02-28','view_kind':'actual'}
  stock=execute('inventory_asof',tables,CONTRACT,scope)
  for row in stock['rows']:
   add('inventory_snapshots',snapshot_id='IS-'+row['lot_id']+'-'+row['location_id'],product_id=row['product_id'],lot_id=row['lot_id'],location_id=row['location_id'],as_of_date='2027-02-28',knowledge_date='2027-02-28',unit=row['unit'],**{k:row[k] if row[k] is not None else '' for k in ['on_hand','in_transit','quarantined','reserved','available']})
  recall=execute('recall_assessment',tables,CONTRACT,dict(scope,recall_id=f'REC-{i:03}'))
  grouped={}
  for row in recall['rows']:
   g=grouped.setdefault(row['product_id'],[0,0,True,row['unit']]);g[2]&=row['controlled_quantity'] is not None and row['controllable_quantity'] is not None
   from decimal import Decimal
   g[0]+=Decimal(row['controlled_quantity'] or'0');g[1]+=Decimal(row['controllable_quantity'] or'0')
  for pid,(num,den,complete,unit) in grouped.items():
   from retail_core import Q
   add('recall_snapshots',snapshot_id=f'RC-{i:03}-{pid}',recall_id=f'REC-{i:03}',product_id=pid,as_of_date='2027-02-28',knowledge_date='2027-02-28',unit=unit,controlled_quantity=Q(num) if complete else'',controllable_quantity=Q(den) if complete else'',coverage_ratio=Q(num/den) if complete and den>0 else'')
 return tables

def main():
 for lang in ['en-us','zh-cn']:
  p=ROOT/'samples'/('retail-gs1-'+lang);(p/'data').mkdir(parents=True,exist_ok=True);(p/'tools').mkdir(exist_ok=True)
  tables=build(lang)
  for t,rows in tables.items():
   with (p/'data'/(t+'.csv')).open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=TABLES[t][1].split());w.writeheader();w.writerows(rows)
  c=dict(CONTRACT,language=lang)
  (p/'model-contract.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
  shutil.copyfile(Path(__file__).with_name('retail_core.py'),p/'tools/retail_core.py')
  shutil.copyfile(Path(__file__).with_name('managed_execution.py'),p/'tools/managed_execution.py')
  hashes={f.name:{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'rows':len(tables[f.stem])} for f in sorted((p/'data').glob('*.csv'))}
  (p/'dataset.lock').write_text(json.dumps({'version':1,'files':hashes},indent=2)+'\n')
  print(lang,{t:len(v) for t,v in tables.items()})
if __name__=='__main__':main()
