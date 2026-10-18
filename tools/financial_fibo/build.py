#!/usr/bin/env python3
"""Reproduce the fictional bilingual FIBO dataset and native BKN model. Stdlib only."""
import argparse, csv, hashlib, json, shutil, sqlite3
from semantics import OBJECTS,field_description,ANALYSIS_CONTRACT
from pathlib import Path
from decimal import Decimal as D, ROUND_HALF_UP
from datetime import date, timedelta
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
REV='2d73435a4419b66b7c9f44cb9763e35fe8ac7890'
CURRENT='2027-02-28'
PORTFOLIOS=200
ISSUER_OFFSETS=(0,7,17,29)
DATES=['2026-11-30','2026-12-31','2027-01-31',CURRENT,'2027-03-31']
BASE='https://spec.edmcouncil.org/fibo/ontology/'
ANCHORS={
 'financial_instruments':('FBC/FinancialInstruments/FinancialInstruments','FinancialInstrument'),
 'security_identifiers':('SEC/Securities/SecuritiesIdentification','SecurityIdentifier'),
 'portfolios':('FND/OwnershipAndControl/Ownership','Portfolio'),
 'positions':('FBC/ProductsAndServices/FinancialProductsAndServices','Position'),
 'securities_transactions':('FBC/FinancialInstruments/FinancialInstruments','SecuritiesTransaction'),
 'market_prices':('FBC/FinancialInstruments/InstrumentPricing','MarketPrice'),
}
# type names are translated, machine identifiers and public source labels remain stable.
NAMES={
 'legal_entities':('Legal Entity','法律实体'), 'legal_entity_identifiers':('Entity Identifier','法律实体标识'),
 'financial_instruments':('Financial Instrument','金融工具'), 'security_identifiers':('Security Identifier','证券标识'),
 'portfolios':('Investment Portfolio','投资组合'), 'accounts':('Investment Account','投资账户'),
 'opening_positions':('Opening Position','期初持仓'), 'trade_orders':('Trade Order','交易订单'),
 'securities_transactions':('Executed Trade','证券成交'), 'settlement_instructions':('Settlement Instruction','结算指令'),
 'settlement_events':('Settlement Event','结算事件'), 'positions':('Dated Position','日期持仓'),
 'market_prices':('Market Price','市场价格'), 'fx_rates':('FX Rate','汇率'),
 'valuation_snapshots':('Position Valuation','持仓估值'), 'issuer_exposures':('Issuer Exposure','发行方敞口'),
 'exposure_contributions':('Exposure Contribution','敞口构成'), 'counterparty_exposures':('Unsettled Receivable','未结算应收金额'),
 'mandate_limits':('Mandate Limit','授权限额'), 'limit_assessments':('Limit Assessment','限额评估'),
}
# schema: primary key, display name field, direct FK mappings
SCHEMA={
 'legal_entities':('entity_id','name',{}),
 'legal_entity_identifiers':('identifier_id','synthetic_code',{'entity_id':'legal_entities'}),
 'financial_instruments':('instrument_id','name',{'issuer_id':'legal_entities'}),
 'security_identifiers':('identifier_id','synthetic_code',{'instrument_id':'financial_instruments'}),
 'portfolios':('portfolio_id','name',{'manager_id':'legal_entities'}),
 'accounts':('account_id','name',{'portfolio_id':'portfolios'}),
 'opening_positions':('opening_id','opening_id',{'account_id':'accounts','instrument_id':'financial_instruments'}),
 'trade_orders':('order_id','order_id',{'account_id':'accounts','instrument_id':'financial_instruments','counterparty_id':'legal_entities'}),
 'securities_transactions':('trade_id','trade_id',{'order_id':'trade_orders'}),
 'settlement_instructions':('instruction_id','instruction_id',{'trade_id':'securities_transactions'}),
 'settlement_events':('event_id','event_id',{'instruction_id':'settlement_instructions'}),
 'positions':('position_id','position_id',{'opening_id':'opening_positions'}),
 'market_prices':('price_id','price_id',{'instrument_id':'financial_instruments'}),
 'fx_rates':('fx_id','fx_id',{}),
 'valuation_snapshots':('valuation_id','valuation_id',{'position_id':'positions','price_id':'market_prices','fx_id':'fx_rates'}),
 'issuer_exposures':('exposure_id','exposure_id',{'portfolio_id':'portfolios','issuer_id':'legal_entities'}),
 'exposure_contributions':('contribution_id','contribution_id',{'exposure_id':'issuer_exposures','valuation_id':'valuation_snapshots'}),
 'counterparty_exposures':('exposure_id','exposure_id',{'portfolio_id':'portfolios','counterparty_id':'legal_entities'}),
 'mandate_limits':('limit_id','limit_id',{'portfolio_id':'portfolios','entity_id':'legal_entities'}),
 'limit_assessments':('assessment_id','assessment_id',{'limit_id':'mandate_limits','issuer_exposure_id':'issuer_exposures','counterparty_exposure_id':'counterparty_exposures'}),
}
ZH={
 'issuer':'发行方','broker':'经纪商','manager':'资产管理人','equity':'股票','bond':'债券','share':'股','face_unit':'面值单位',
 'buy':'买入','sell':'卖出','executed':'已成交','planned':'计划','actual':'实际','approved':'已批准','unapproved':'未批准',
 'settled':'已结算','pending':'待结算','partial':'部分结算','failed':'结算失败','complete':'完整','blocked':'受阻',
 'current':'有效','stale':'价格陈旧','missing':'价格缺失','price_unapproved':'价格未批准',
 'within':'限额内','breach':'超限','unknown':'无法判定','issuer_ratio':'发行方集中度','receivable_amount':'未结算应收金额',
 'normal':'正常结算','pending_settlement':'待结算','failed_settlement':'结算失败','price_exception':'价格例外',
 'issuer_breach':'发行方超限','counterparty_breach':'交易对手超限','future_limit':'未来限额变更',
 'none':'无','insufficient_securities':'证券不足','cash_mismatch':'金额不匹配','awaiting_confirmation':'等待确认',
 'awaiting_balance':'等待剩余结算','forecast_only':'仅计划预测','equity_mark':'股票市值法','bond_dirty':'债券全价法',
 'synthetic':'虚构','local_security_code':'本地合成证券编码','synthetic_entity_code':'本地合成实体编码',
 'long_only':'仅多头','dirty_per_100':'每百元面值全价','per_share':'每股价格',
 'overdue':'已逾期','not_due':'未到期','accepted':'已接受','cancelled':'已取消','day_close':'日终收盘','demo_pricing':'模拟价格源',
}
FIELDS_ZH={
 'name':'名称','entity_id':'实体编号','entity_role':'实体角色','country':'国家或地区','sector':'行业','synthetic_code':'合成编码',
 'identifier_id':'标识编号','scheme':'标识体系','is_synthetic':'是否合成','instrument_id':'工具编号','issuer_id':'发行方编号',
 'asset_class':'资产类别','currency':'币种','unit':'数量单位','price_basis':'价格口径','price_multiplier':'价格乘数',
 'maturity_date':'到期日期','manager_id':'管理人编号','portfolio_id':'组合编号','base_currency':'本位币','mandate':'投资授权',
 'branch':'业务分支','account_id':'账户编号','opening_id':'期初记录编号','opening_date':'期初日期','quantity':'数量',
 'cost_unit_price':'单位成本','order_id':'订单编号','order_date':'订单日期','side':'方向','order_quantity':'订单数量',
 'order_status':'订单状态','counterparty_id':'交易对手编号','trade_id':'成交编号','trade_date':'成交日期','execution_price':'成交价格',
 'trade_quantity':'成交数量','gross_amount':'成交总额','trade_status':'成交状态','known_date':'已知日期','view_kind':'视图类型',
 'instruction_id':'指令编号','due_date':'约定结算日期','required_quantity':'应结算数量','event_id':'事件编号',
 'event_sequence':'指令内事件顺序','event_date':'事件日期','event_status':'事件状态','settled_quantity':'本次结算数量','failure_reason':'失败原因',
 'position_id':'持仓编号','as_of_date':'截至日期','trade_basis_quantity':'交易日口径数量','settled_basis_quantity':'结算日口径数量',
 'unsettled_delta':'未结算数量变动','cost_amount':'交易币种成本','realized_pnl':'当期已实现损益','price_id':'价格编号',
 'price_date':'价格日期','published_date':'发布日期','price':'价格','approval':'批准状态','pricing_source':'价格来源',
 'fx_id':'汇率编号','from_currency':'源币种','to_currency':'目标币种','rate':'汇率','valuation_id':'估值编号',
 'valuation_status':'估值状态','reason':'原因','market_value_local':'交易币种市值','market_value_base':'本位币市值',
 'cost_value_base':'本位币成本','unrealized_pnl_base':'本位币未实现损益','valuation_method':'估值方法',
 'exposure_id':'敞口编号','exposure_status':'敞口状态','exposure_amount':'敞口金额','denominator_amount':'分母金额',
 'ratio':'集中度','contribution_id':'构成编号','contribution_amount':'构成金额','unsettled_receivable':'未结算应收金额',
 'limit_id':'限额编号','measure':'衡量口径','threshold':'阈值','effective_from_date':'生效起日','effective_to_date':'生效止日',
 'assessment_id':'评估编号','issuer_exposure_id':'发行方敞口编号','counterparty_exposure_id':'交易对手敞口编号',
 'observed_value':'观察值','assessment_status':'评估状态','excess_value':'超限值','decision_date':'决策日期',
}
EN_ENTITY_PARTS=['Alder','Birch','Cedar','Dawn','Elm','Falcon','Grove','Harbor','Iris','Juniper']
ZH_ENTITY_PARTS=['青禾','远川','澄岳','云杉','星桥','松澜','景辰','海棠','岚峰','锦林']
SECTORS=[('Technology','科技'),('Healthcare','医疗'),('Industrials','工业'),('Consumer','消费'),('Utilities','公用事业')]

def money(x): return str(D(x).quantize(D('.01'), rounding=ROUND_HALF_UP))
def dec(x): return str(D(x).quantize(D('.000001'), rounding=ROUND_HALF_UP))
def jwrite(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvwrite(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def business_day(dt,forward=False):
 d=date.fromisoformat(dt)
 while d.weekday()>4:d+=timedelta(days=1 if forward else -1)
 return d.isoformat()
def plus_business_days(dt,n):
 d=date.fromisoformat(dt)
 while n:
  d+=timedelta(days=1)
  if d.weekday()<5:n-=1
 return d.isoformat()
def quote(idx,m,bond):
 return (D(98+idx%7)+D(m)*D((idx//2)%3-1)*D('.25')) if bond else (D(20+idx%13)+D(m)*D(((idx-1)//2)%5-2)*D('.40'))
def branch(i):
 i=i%50
 return 'normal' if i<18 else 'pending_settlement' if i<28 else 'failed_settlement' if i<34 else 'price_exception' if i<40 else 'issuer_breach' if i<45 else 'counterparty_breach' if i<48 else 'future_limit'
def make_data():
 from collections import defaultdict
 T={t:[] for t in SCHEMA};ledger=defaultdict(list)
 def add(t,**r):
  T[t].append(r)
  if t=='settlement_events':
   r['event_sequence']=str(len(ledger[r['instruction_id']])+1);ledger[r['instruction_id']].append(r)
 for i in range(50):
  for role,prefix in [('issuer','ISS'),('broker','CP'),('manager','MGR')]:
   eid=f'{prefix}-{i+1:03}'
   add('legal_entities',entity_id=eid,name=f'{EN_ENTITY_PARTS[i%10]} {SECTORS[i//10][0]} '+{'issuer':'Holdings','broker':'Securities','manager':'Asset Management'}[role],entity_role=role,country=['CN','US','DE'][i%3],sector=SECTORS[i//10][0],is_synthetic='true')
   add('legal_entity_identifiers',identifier_id=f'EID-{eid}',entity_id=eid,synthetic_code=f'DEMO-ENTITY-{eid}',scheme='synthetic_entity_code',is_synthetic='true')
 for i in range(100):
  issuer=i//2; bond=i%2==1;cc=['CNY','USD','EUR'][issuer%3]
  add('financial_instruments',instrument_id=f'INS-{i+1:03}',name=f'{EN_ENTITY_PARTS[issuer%10]} {SECTORS[issuer//10][0]} '+('2030 Note' if bond else 'Ordinary Share'),issuer_id=f'ISS-{issuer+1:03}',asset_class='bond' if bond else 'equity',currency=cc,unit='face_unit' if bond else 'share',price_basis='dirty_per_100' if bond else 'per_share',price_multiplier='0.01' if bond else '1',maturity_date='2030-06-30' if bond else '',is_synthetic='true')
  add('security_identifiers',identifier_id=f'SID-{i+1:03}',instrument_id=f'INS-{i+1:03}',synthetic_code=f'DEMO-SEC-{i+1:05}',scheme='local_security_code',is_synthetic='true')
 # 50 fixing dates per currency, including each business snapshot. No invented currencies.
 fixing_set=set(DATES)
 for k in range(90):
  if len(fixing_set)==50:break
  fixing_set.add(str(date(2026,11,2)+timedelta(days=3*k)))
 fixings=sorted(fixing_set)
 assert len(fixings)==50
 for k,dt in enumerate(fixings):
  fixing_index=(date.fromisoformat(business_day(dt))-date(2026,11,2)).days
  for cc,rate in [('USD',D(1)),('CNY',D('.139')+D(fixing_index%7)/10000),('EUR',D('1.065')+D(fixing_index%9)/1000)]:
   add('fx_rates',fx_id=f'FX-{cc}-{dt}',as_of_date=dt,from_currency=cc,to_currency='USD',rate=dec(rate),published_date=business_day(dt),view_kind='planned' if dt>CURRENT else 'actual',known_date='2027-02-28' if dt>CURRENT else business_day(dt))
 inst={r['instrument_id']:r for r in T['financial_instruments']};fx={(r['from_currency'],r['as_of_date']):r for r in T['fx_rates']}
 # Five price dates per instrument; negative scenarios are instrument-wide, not portfolio-specific prices.
 bad={f'INS-{2*i+1:03}':i-34 for i in range(34,40)}
 for iid,r in inst.items():
  idx=int(iid[4:]);bond=r['asset_class']=='bond'
  for m,dt in enumerate(DATES):
   special=bad.get(iid) if dt==CURRENT else None
   if special in (2,5): continue
   price_date=business_day(str(date.fromisoformat(dt)-timedelta(days=10))) if special in (0,3) else business_day(dt)
   price=quote(idx,m,bond)
   add('market_prices',price_id=f'PX-{idx:03}-{m+1}',instrument_id=iid,as_of_date=dt,price_date=price_date,published_date=price_date,price=money(price),currency=r['currency'],approval='unapproved' if special in (1,4) else 'approved',pricing_source='demo_pricing',view_kind='planned' if dt>CURRENT else 'actual',known_date='2027-02-28' if dt>CURRENT else price_date)
 prices={(r['instrument_id'],str(DATES.index(r['as_of_date'])+1)):r for r in T['market_prices']}
 for i in range(PORTFOLIOS):
  base_i=i%50
  pid=f'PF-{i+1:03}';acct=f'ACC-{i+1:03}';b=branch(i)
  add('portfolios',portfolio_id=pid,name=f'{EN_ENTITY_PARTS[base_i%10]} {SECTORS[base_i//10][0]} '+['Core','Select','Balanced','Long Horizon'][i//50]+' Portfolio',manager_id=f'MGR-{base_i+1:03}',base_currency='USD',mandate='long_only',branch=b)
  add('accounts',account_id=acct,name=f'{EN_ENTITY_PARTS[base_i%10]} {SECTORS[base_i//10][0]} '+['Core','Select','Balanced','Long Horizon'][i//50]+' Custody Account',portfolio_id=pid,currency='USD')
  # Two securities from each of two issuers; issuers are shared across portfolios.
  instrument_ids=[f'INS-{2*((base_i+offset)%50)+n:03}' for offset in ISSUER_OFFSETS for n in (1,2)]
  histories={}
  for k,iid in enumerate(instrument_ids):
   r=inst[iid];mult=D(r['price_multiplier']);cc=r['currency'];idx=int(iid[4:]);p0=D(98+idx%7) if r['asset_class']=='bond' else D(20+idx%13)
   base=D(45000 if b=='issuer_breach' and k<2 else 10000)*(1+D(i//50)/5)
   q=(base/(p0*mult*D(fx[(cc,DATES[0])]['rate']))).quantize(D('1'))
   opening=f'OP-{i+1:03}-{k+1}';cost=q*p0*mult
   add('opening_positions',opening_id=opening,account_id=acct,instrument_id=iid,opening_date='2026-11-01',quantity=str(q),cost_unit_price=money(p0),currency=cc)
   histories[k]=dict(q=q,initial=q,settled=q,cost=cost,opening=opening,unsettled=D(0))
  for m,dt in enumerate(DATES):
   kind='planned' if dt>CURRENT else 'actual';known='2027-02-28' if kind=='planned' else dt
   month=dt[:7]; valuations=[]; open_rec=D(0)
   for k,iid in enumerate(instrument_ids):
    r=inst[iid];h=histories[k];mult=D(r['price_multiplier']);cc=r['currency'];idx=int(iid[4:]);key=f'{i+1:03}-{k+1}-{m+1}'
    # Even slots buy; odd slots sell. First month opens fully settled activity.
    side=('sell' if m in (2,4) else 'buy') if k==0 else ('buy' if m%2==0 else 'sell') if k==2 else 'sell';sign=1 if side=='buy' else -1
    qty=D(max(1,int(h['initial']/40)))*(1+m%2)
    px=quote(idx,m,r['asset_class']=='bond')
    trade_date=business_day(month+f'-{8+(i*3+k*2)%15:02}',forward=True);due=plus_business_days(trade_date,2);status='settled';reason='none';fraction=D(1)
    if dt==CURRENT and k%2==1:
     if b=='pending_settlement':
      status='pending' if i%2==0 else 'partial';fraction=D(0) if i%2==0 else D('.5');reason='awaiting_confirmation' if i%2==0 else 'awaiting_balance'
      if i%2==0:trade_date='2027-02-26';due='2027-03-02'
     if b in ('failed_settlement','counterparty_breach'):
      status='failed';fraction=D(0);reason='insufficient_securities' if i%2==0 else 'cash_mismatch'
    if kind=='planned' and k%2==1:
     if b=='failed_settlement' and i%3==0:
      status='failed';fraction=D(0);reason='insufficient_securities'
     elif b=='counterparty_breach' and base_i==47:
      status='failed';fraction=D(0);reason='cash_mismatch'
     elif b=='pending_settlement' and i%2==1:
      status='partial';fraction=D('.5');reason='awaiting_balance'
    oid='ORD-'+key;tid='TR-'+key;sid='SI-'+key
    add('trade_orders',order_id=oid,account_id=acct,instrument_id=iid,counterparty_id=f'CP-{base_i+1:03}',order_date=trade_date,side=side,order_quantity=str(qty),order_status='planned' if kind=='planned' else 'accepted',view_kind=kind,known_date='2027-02-28' if kind=='planned' else trade_date)
    add('securities_transactions',trade_id=tid,order_id=oid,trade_date=trade_date,trade_quantity=str(qty),execution_price=money(px),gross_amount=money(qty*px*mult),currency=cc,trade_status='planned' if kind=='planned' else 'executed',known_date='2027-02-28' if kind=='planned' else trade_date)
    add('settlement_instructions',instruction_id=sid,trade_id=tid,due_date=due,required_quantity=str(qty),currency=cc)
    event_date=trade_date if status=='pending' else due
    # Explicit zero-transfer acknowledgement then outcome; event quantities are incremental.
    if status!='pending':
     add('settlement_events',event_id='ACK-'+key,instruction_id=sid,event_date=trade_date,event_status='pending',settled_quantity='0',failure_reason='awaiting_confirmation',view_kind=kind,known_date=CURRENT if kind=='planned' else trade_date)
    add('settlement_events',event_id='SE-'+key,instruction_id=sid,event_date=event_date,event_status=status,settled_quantity=str(qty*fraction),failure_reason=reason,view_kind=kind,known_date=CURRENT if kind=='planned' else event_date)
    if dt==CURRENT and k%2==1 and fraction<1:
     # Current failures/pending remain actual at February end. Projected recoveries are explicit.
     recover= b=='pending_settlement' or (b=='failed_settlement' and i%3!=0) or (b=='counterparty_breach' and base_i!=47)
     if recover:
      add('settlement_events',event_id='REC-'+key,instruction_id=sid,event_date='2027-03-04',event_status='settled',settled_quantity=str(qty*(1-fraction)),failure_reason='none',view_kind='planned',known_date=CURRENT)
    if side=='buy':h['cost']+=qty*px*mult;realized=D(0)
    else:
     avg=h['cost']/h['q'];realized=qty*(px*mult-avg);h['cost']-=qty*avg
    h['q']+=sign*qty;h['settled']+=sign*qty*fraction;h['unsettled']+=sign*qty*(1-fraction)
    if kind=='planned':
     cumulative=D(next(x['quantity'] for x in T['opening_positions'] if x['opening_id']==h['opening']))
     orders_for_position={o['order_id']:o for o in T['trade_orders'] if o['account_id']==acct and o['instrument_id']==iid}
     tx_for_position={t['trade_id']:t for t in T['securities_transactions'] if t['order_id'] in orders_for_position and t['trade_date']<=dt}
     instructions_for_position={q['instruction_id']:q for q in T['settlement_instructions'] if q['trade_id'] in tx_for_position}
     for ev in T['settlement_events']:
      if ev['instruction_id'] in instructions_for_position and ev['event_date']<=dt:
       tx=tx_for_position[instructions_for_position[ev['instruction_id']]['trade_id']]
       sign=1 if orders_for_position[tx['order_id']]['side']=='buy' else -1
       cumulative+=sign*D(ev['settled_quantity'])
     h['settled']=cumulative;h['unsettled']=h['q']-cumulative
    pos='POS-'+key
    add('positions',position_id=pos,opening_id=h['opening'],as_of_date=dt,trade_basis_quantity=dec(h['q']),settled_basis_quantity=dec(h['settled']),unsettled_delta=dec(h['unsettled']),cost_amount=money(h['cost']),realized_pnl=money(realized),currency=cc,view_kind=kind,known_date=known)
    p=prices.get((iid,str(m+1)));f=fx[(cc,dt)]
    why='missing' if p is None else 'price_unapproved' if p['approval']!='approved' else 'stale' if (date.fromisoformat(dt)-date.fromisoformat(p['price_date'])).days>3 else 'none'
    valid=why=='none';local=h['q']*D(p['price'])*mult if valid else None
    mv=D(money(D(money(local))*D(f['rate']))) if valid else None;cb=D(money(D(money(h['cost']))*D(f['rate'])))
    v=dict(valuation_id='VAL-'+key,position_id=pos,price_id=p['price_id'] if p else '',fx_id=f['fx_id'],as_of_date=dt,valuation_status='complete' if valid else 'blocked',reason=why,market_value_local=money(local) if valid else '',market_value_base=money(mv) if valid else '',cost_value_base=money(cb),unrealized_pnl_base=money(mv-cb) if valid else '',currency='USD',valuation_method='bond_dirty' if r['asset_class']=='bond' else 'equity_mark',view_kind=kind,known_date=known)
    T['valuation_snapshots'].append(v);valuations.append((r['issuer_id'],v))
   # Aggregate ALL currently open sell instructions, including prior periods, not only this month's event.
   orders={r['order_id']:r for r in T['trade_orders']}; trades={r['trade_id']:r for r in T['securities_transactions']}
   for ins in T['settlement_instructions']:
    t=trades[ins['trade_id']];o=orders[t['order_id']]
    if o['account_id']!=acct or t['trade_date']>dt or o['side']!='sell':continue
    if kind=='actual' and o['view_kind']!='actual':continue
    settled=sum((D(ev['settled_quantity']) for ev in ledger[ins['instruction_id']] if ev['event_date']<=dt and (kind=='planned' or ev['view_kind']=='actual')),D(0))
    ir=inst[o['instrument_id']];rate=D(fx[(ir['currency'],dt)]['rate'])
    open_rec+=(D(t['trade_quantity'])-settled)*D(t['execution_price'])*D(ir['price_multiplier'])*rate
   cp_id=f'CE-{i+1:03}-{m+1}'
   add('counterparty_exposures',exposure_id=cp_id,portfolio_id=pid,counterparty_id=f'CP-{base_i+1:03}',as_of_date=dt,unsettled_receivable=money(open_rec),currency='USD',view_kind=kind,known_date=known)
   complete=all(v['valuation_status']=='complete' for _,v in valuations)
   total=sum((D(v['market_value_base']) for _,v in valuations if v['market_value_base']),D(0))
   issuer_ids=sorted(set(e for e,v in valuations));expos=[]
   for g,issuer in enumerate(issuer_ids):
    eid=f'IE-{i+1:03}-{g+1}-{m+1}';members=[v for e,v in valuations if e==issuer];amount=sum((D(v['market_value_base']) for v in members if v['market_value_base']),D(0))
    add('issuer_exposures',exposure_id=eid,portfolio_id=pid,issuer_id=issuer,as_of_date=dt,exposure_status='complete' if complete else 'blocked',exposure_amount=money(amount) if complete else '',denominator_amount=money(total) if complete else '',ratio=dec(amount/total) if complete and total else '',currency='USD',view_kind=kind,known_date=known)
    expos.append(T['issuer_exposures'][-1])
    for v in members:add('exposure_contributions',contribution_id=f'EC-{eid}-{v["valuation_id"]}',exposure_id=eid,valuation_id=v['valuation_id'],contribution_amount=v['market_value_base'],currency='USD')
   # Limits: two issuer limits and one receivable limit, with explicit versioned future limits.
   if m==0:
    for g,issuer in enumerate(issuer_ids):
     lim=f'LIM-{i+1:03}-I{g+1}';threshold='0.30' if b=='issuer_breach' else '0.80'
     add('mandate_limits',limit_id=lim,portfolio_id=pid,entity_id=issuer,measure='issuer_ratio',threshold=threshold,currency='',effective_from_date='2026-11-01',effective_to_date='2027-03-14' if b=='future_limit' else '2027-03-31',approval='approved',decision_date='2026-10-20')
     if b=='future_limit':add('mandate_limits',limit_id=lim+'-NEXT',portfolio_id=pid,entity_id=issuer,measure='issuer_ratio',threshold='0.20',currency='',effective_from_date='2027-03-15',effective_to_date='2027-03-31',approval='approved',decision_date='2027-02-28')
    add('mandate_limits',limit_id=f'LIM-{i+1:03}-C',portfolio_id=pid,entity_id=f'CP-{base_i+1:03}',measure='receivable_amount',threshold='500.00' if b=='counterparty_breach' else '1000000.00',currency='USD',effective_from_date='2026-11-01',effective_to_date='2027-03-31',approval='approved',decision_date='2026-10-20')
   for lim in T['mandate_limits']:
    if lim['portfolio_id']!=pid or not(lim['effective_from_date']<=dt<=lim['effective_to_date']) or lim['decision_date']>known:continue
    ie=next((e for e in expos if e['issuer_id']==lim['entity_id']),None) if lim['measure']=='issuer_ratio' else None
    observed=(ie['ratio'] if ie else None) if lim['measure']=='issuer_ratio' else money(open_rec)
    st='unknown' if observed in ('',None) else 'breach' if D(observed)>D(lim['threshold']) else 'within'
    add('limit_assessments',assessment_id=f'LA-{lim["limit_id"]}-{m+1}',limit_id=lim['limit_id'],issuer_exposure_id=ie['exposure_id'] if ie else '',counterparty_exposure_id=cp_id if not ie else '',as_of_date=dt,observed_value=observed or '',assessment_status=st,excess_value=dec(max(D(0),D(observed)-D(lim['threshold']))) if observed not in ('',None) else '',view_kind=kind,known_date=known)
 return T

def localize(T):
 out={}
 for table,rows in T.items():
  out[table]=[]
  for row in rows:
   r={k:ZH.get(v,v) if isinstance(v,str) and k not in ('source_label','source_definition') else v for k,v in row.items()}
   if table=='legal_entities':
    i=int(row['entity_id'].split('-')[1])-1
    r['name']=ZH_ENTITY_PARTS[i%10]+SECTORS[i//10][1]+{'issuer':'控股有限公司','broker':'证券有限公司','manager':'资产管理有限公司'}[row['entity_role']]
    r['sector']=SECTORS[i//10][1];r['country']={'CN':'中国','US':'美国','DE':'德国'}[row['country']]
   if table=='financial_instruments':
    i=(int(row['instrument_id'][4:])-1)//2
    r['name']=ZH_ENTITY_PARTS[i%10]+SECTORS[i//10][1]+('2030年债券' if row['asset_class']=='bond' else '普通股')
   if table in ('portfolios','accounts'):
    i=int(row['portfolio_id'][3:])-1;idx=i%50
    r['name']=ZH_ENTITY_PARTS[idx%10]+SECTORS[idx//10][1]+['核心','精选','均衡','长期'][i//50]+('投资组合' if table=='portfolios' else '托管账户')
   out[table].append(r)
 return out

def extract_reference(src,out):
 ns={'owl':'http://www.w3.org/2002/07/owl#','rdfs':'http://www.w3.org/2000/01/rdf-schema#','skos':'http://www.w3.org/2004/02/skos/core#'};about='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about'
 selected=sorted(set([path+'.rdf' for path,_ in ANCHORS.values()]+['BE/LegalEntities/LEIEntities.rdf']))
 classes={};props={};files={}
 for rel in selected:
  p=src/rel;r=ET.parse(p).getroot();dest=out/'sources'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  files[rel]='sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
  for tag,store in [('Class',classes),('ObjectProperty',props),('DatatypeProperty',props)]:
   for e in r.findall('owl:'+tag,ns):
    iri=e.get(about)
    if not iri:continue
    definition=' '.join(''.join(x.itertext()).strip() for x in e.findall('skos:definition',ns))
    label=' '.join(''.join(x.itertext()).strip() for x in e.findall('rdfs:label',ns))
    store.setdefault(iri,dict(iri=iri,label=label,definition=definition,kind=tag,source_files=[],deprecated=False))
    v=store[iri];v['source_files'].append(rel);v['deprecated']|=e.find('owl:deprecated',ns) is not None
    if label:v['label']=label
    if definition:v['definition']=definition
 shutil.copy2(src/'LICENSE',out/'LICENSE-FIBO.txt')
 jwrite(out/'source-lock.json',dict(repository='https://github.com/edmcouncil/fibo',revision=REV,license='MIT',files=files,scope='Selected source documents, not all FIBO or its import closure'))
 jwrite(out/'classes.json',list(classes.values()));jwrite(out/'properties.json',list(props.values()))
 return classes

def model(sample,T,zh,classes):
 import re
 kn=sample/'kn';names={t:NAMES[t][1 if zh else 0] for t in T};relations=[]
 # Keep opaque technical FK names; compact relation IDs without loss of provenance.
 short={t:s for t,s in zip(SCHEMA,['entity','entity_id','instrument','security_id','portfolio','account','opening','order','trade','settle_instr','settle_event','position','price','fx','valuation','issuer_exp','contribution','cp_exp','limit','assessment'])}
 for t,(pk,display,fks) in SCHEMA.items():
  name=names[t];lines=['---','type: object_type','id: '+t,'name: '+name,'tags: [finance, fibo]','---','','## ObjectType: '+name,'',OBJECTS[t][1 if zh else 0]]
  if t in ANCHORS:
   mod,c=ANCHORS[t];iri=BASE+mod+'/'+c;cl=classes[iri]
   assert not cl['deprecated'] and cl['definition'],iri
   lines+=['', '### Semantic Provenance','', '| Key | Value |','|---|---|',f'| source_iri | {iri} |',f'| source_label | {cl["label"]} |',f'| source_definition | {cl["definition"].replace(chr(10)," ").replace("|","/")} |',f'| source_revision | {REV} |','| source_license | MIT |','| source_repository | https://github.com/edmcouncil/fibo |']
  else:lines+=['',('本地运营扩展，非 FIBO 等价类。' if zh else 'Local operational extension; no FIBO equivalence asserted.')]
  lines+=['','### Data Properties','','| Name | Display Name | Type | Description | Mapped Field |','|---|---|---|---|---|']
  for f in T[t][0]:
   dtype=field_type(f)
   label=FIELDS_ZH.get(f,f) if zh else f.replace('_',' ').title()
   assert not zh or f in FIELDS_ZH, f
   description=field_description(t,f,zh,SCHEMA)
   if f in {'view_kind','side','trade_status','event_status','valuation_status','exposure_status','assessment_status','approval','measure','branch'}:
    values=sorted({r[f] for r in T[t] if r[f]!=''})
    description+=(' 允许取值：' if zh else ' Allowed values: ')+', '.join(values)+'.'
   lines.append(f'| {f} | {label} | {dtype} | {description} | {f} |')
  lines+=['','### Keys','',f'Primary Keys: {pk}',f'Display Key: {display}','Incremental Key:','']
  p=kn/'object_types'/(t+'.bkn');p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(lines),encoding='utf-8')
  for fk,target in fks.items():
   rid=short[t]+'_to_'+(short[target] if fk==SCHEMA[target][0] else fk.removesuffix('_id'))
   assert len(rid)<=40
   rn=(names[t]+'关联'+FIELDS_ZH[fk].removesuffix('编号')) if zh else rid.replace('_',' ').title()
   relations.append(dict(id=rid,source=t,source_property=fk,target=target,target_property=SCHEMA[target][0],nullable=any(r[fk]=='' for r in T[t])))
   p=kn/'relation_types'/(rid+'.bkn');p.parent.mkdir(parents=True,exist_ok=True)
   p.write_text(f'---\ntype: relation_type\nid: {rid}\nname: {rn}\ntags: [finance, fibo]\n---\n\n## RelationType: {rn}\n\n'+('通过外键连接业务记录。空外键表示该证据不适用或缺失，不创建关系。' if zh else 'Foreign-key business association. Empty keys represent absent or inapplicable evidence and create no relationship.')+f'\n\n### Endpoint\n\n| Source | Target | Type |\n|---|---|---|\n| {t} | {target} | direct |\n\n### Mapping Rules\n\n| Source Property | Target Property |\n|---|---|\n| {fk} | {SCHEMA[target][0]} |\n',encoding='utf-8')
 groups=[('reference_data',('Reference Data','金融主数据'),list(T)[:6]),('post_trade',('Trades and Positions','交易结算与持仓'),list(T)[6:12]),('valuation_controls',('Valuation and Controls','估值与授权控制'),list(T)[12:])]
 for gid,gn,tables in groups:
  name=gn[1 if zh else 0];p=kn/'concept_groups'/(gid+'.bkn');p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(f'---\ntype: concept_group\nid: {gid}\nname: {name}\ntags: [finance, fibo]\n---\n\n## ConceptGroup: {name}\n\n### Object Types\n\n| ID | Name | Description |\n|---|---|---|\n'+'\n'.join(f'| {t} | {names[t]} | {names[t]} |' for t in tables)+'\n',encoding='utf-8')
 name='金融投资组合运营' if zh else 'Financial Portfolio Operations'
 (kn/'network.bkn').write_text(f'---\ntype: knowledge_network\nid: financial_fibo_{"zh_cn" if zh else "en_us"}\nname: {name}\ntags: [finance, fibo]\nversion: 0.1.0\nbranch: main\n---\n\n# {name}\n\n'+('虚构的证券交易、结算、持仓、估值、敞口与限额控制。' if zh else 'Fictional securities trading, settlement, positions, valuation, exposure and mandate controls.')+'\n\n'+ANALYSIS_CONTRACT[1 if zh else 0]+f'\n\n## Network Overview\n\n- **ObjectTypes** ({len(T)})\n- **RelationTypes** ({len(relations)})\n- **ConceptGroups** (3)\n',encoding='utf-8')
 jwrite(sample/'model-contract.json',{'object_types':{t:{'primary_key':v[0],'display_key':v[1],'fields':{f:field_type(f) for f in T[t][0]}} for t,v in SCHEMA.items()},'relations':relations,'current_as_of':CURRENT,'planning_end':'2027-03-31','numeric_rounding':'ROUND_HALF_UP; money 2dp; ratio and FX 6dp','source_revision':REV,'localized_values':ZH,'portfolios':PORTFOLIOS,'positions_per_portfolio':len(ISSUER_OFFSETS)*2,'limits_per_snapshot':len(ISSUER_OFFSETS)+1,'calendar':'Fictional Monday-Friday; no jurisdiction holidays; sample T+2 business days'})
 return relations

def field_type(f):
 if f=='event_sequence':return 'integer'
 if f.endswith('_date'):return 'date'
 if f=='is_synthetic':return 'boolean'
 if f in {'price_multiplier','quantity','cost_unit_price','order_quantity','execution_price','trade_quantity','gross_amount','required_quantity','settled_quantity','trade_basis_quantity','settled_basis_quantity','unsettled_delta','cost_amount','realized_pnl','price','rate','market_value_local','market_value_base','cost_value_base','unrealized_pnl_base','exposure_amount','denominator_amount','ratio','contribution_amount','unsettled_receivable','threshold','observed_value','excess_value'}:return 'decimal'
 return 'string'

def sqlite_db(T):
 db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
 for t,rows in T.items():
  fields=list(rows[0]);db.execute('CREATE TABLE '+t+' ('+','.join('"'+f+'" '+('REAL' if field_type(f)=='decimal' else 'INTEGER' if field_type(f)=='integer' else 'TEXT') for f in fields)+')')
  db.executemany('INSERT INTO '+t+' VALUES ('+','.join('?' for _ in fields)+')',[[None if r[f]=='' else r[f] for f in fields] for r in rows])
 for t,rows in T.items():
  for f in rows[0]:
   if f.endswith('_id') or f.endswith('_date'):
    db.execute('CREATE INDEX idx_'+t+'_'+f+' ON '+t+' ("'+f+'")')
 db.execute('ANALYZE')
 import sys
 sys.path.insert(0,str(ROOT/'tools/financial_fibo/assets'))
 from settlement_views import create_views
 from decimal_sql import register
 register(db)
 create_views(db,actual='实际' if T['trade_orders'][0]['view_kind']=='实际' else 'actual')
 return db

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fibo-source',type=Path,required=True);args=ap.parse_args()
 import subprocess
 assert subprocess.check_output(['git','-C',str(args.fibo_source),'rev-parse','HEAD'],text=True).strip()==REV
 T=make_data()
 for zh in (False,True):
  sample=ROOT/'samples'/('financial-fibo-zh-cn' if zh else 'financial-fibo-en-us');sample.mkdir(parents=True,exist_ok=True)
  classes=extract_reference(args.fibo_source,sample/'fibo-reference');data=localize(T) if zh else T
  for t,rows in data.items():csvwrite(sample/'data'/(t+'.csv'),rows)
  model(sample,data,zh,classes)
  jwrite(sample/'dataset.lock',{'version':'0.1.0','as_of_date':CURRENT,'files':{p.name:'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((sample/'data').glob('*.csv'))},'record_counts':{t:len(r) for t,r in data.items()}})
  for name,folder in [('verify.py','tools'),('settlement_views.py','tools'),('decimal_sql.py','tools'),('run.py','bkn-eval')]:
   dest=sample/folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'tools/financial_fibo/assets'/name,dest)
  from questions import build_questions
  build_questions(sample,data,zh)
  print(sample.name, len(data),'tables',sum(map(len,data.values())),'records')
if __name__=='__main__':main()
