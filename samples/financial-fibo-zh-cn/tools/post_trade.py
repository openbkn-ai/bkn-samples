"""Read-only post-trade decisions over atomic BKN facts. No fixture or gold access."""
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

D = Decimal

def number(x):
    n = D(str(x))
    if not n.is_finite():
        raise ValueError('NONFINITE_NUMBER')
    return n

def rounded(x, places=2):
    return number(x).quantize(D(10) ** -places, rounding=ROUND_HALF_UP)

def day(x):
    s = str(x)
    # The source schema is DATE; SDK may serialize it at midnight.
    if len(s) > 10 and not re.fullmatch(r'\d{4}-\d{2}-\d{2}T00:00:00(?:\.0+)?(?:Z|[+-]\d{2}:\d{2})?',s):
        raise ValueError('INVALID_DATE')
    return date.fromisoformat(s[:10]).isoformat()

def serial(x):
    if isinstance(x, D): return format(x, 'f')
    if isinstance(x, dict): return {k: serial(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [serial(v) for v in x]
    return x

class BusinessError(ValueError):
    pass

class Decisions:
    def __init__(self, tables, contract, scope):
        self.t = tables
        self.c = contract
        self.scope = dict(scope)
        ids = scope.get('portfolio_ids')
        if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
            raise ValueError('NONEMPTY_UNIQUE_PORTFOLIO_IDS_REQUIRED')
        self.asof = day(scope['as_of_date']); self.known = day(scope['knowledge_date'])
        self.zh = contract.get('language', '').startswith('zh')
        self.labels = contract['localized_values']
        # Operational enums have a typed vocabulary. Portfolio branch labels can
        # share Chinese wording with event states and must not overwrite them.
        branch_codes={'normal','pending_settlement','failed_settlement','price_exception','issuer_breach','counterparty_breach','future_limit'}
        self.reverse = {v:k for k,v in self.labels.items() if k not in branch_codes}
        self.view = self.norm(scope['view_kind'])
        if self.view not in ('actual', 'planned'): raise ValueError('INVALID_VIEW_KIND')
        self.scope.update(as_of_date=self.asof, knowledge_date=self.known, view_kind=self.view)
        self.issues = []; self.evidence = defaultdict(set); self.by = {}
        for t, rows in tables.items():
            pk = contract['object_types'][t]['primary_key']; index = {}
            for raw in rows:
                r = dict(raw)
                for f, typ in contract['object_types'][t]['fields'].items():
                    if typ == 'date' and r.get(f): r[f] = day(r[f])
                    if typ == 'string' and r.get(f) is None:r[f]=''
                key = r.get(pk)
                if not key or key in index: raise ValueError('DUPLICATE_OR_MISSING_KEY:' + t)
                index[key] = r
            self.by[t] = index
        if not set(ids) <= set(self.by['portfolios']): raise ValueError('UNKNOWN_PORTFOLIO')
        self.ids = set(ids)
        for pid in sorted(self.ids):self.ev('portfolios',self.by['portfolios'][pid])
        self.accounts = {k:r for k,r in self.by['accounts'].items() if r['portfolio_id'] in self.ids}
        self.openings = {k:r for k,r in self.by['opening_positions'].items() if r['account_id'] in self.accounts and r['opening_date'] <= min(self.asof,self.known)}
        self.orders = {k:r for k,r in self.by['trade_orders'].items() if r['account_id'] in self.accounts and self.eligible(r, 'order_date')}
        self.trades = {k:r for k,r in self.by['securities_transactions'].items() if r['order_id'] in self.orders and self.eligible(r, 'trade_date')}
        self.instructions = defaultdict(list); self.events = defaultdict(list)
        for r in self.by['settlement_instructions'].values():
            if r['trade_id'] in self.trades: self.instructions[r['trade_id']].append(r)
        for r in self.by['settlement_events'].values():
            if self.eligible(r, 'event_date'): self.events[r['instruction_id']].append(r)
        self.settlement_cache = None; self.valuation_cache = None
    def norm(self, s): return self.reverse.get(s,s)
    def eligible(self,r,f):
        kind = self.norm(r.get('view_kind', r.get('trade_status','actual')))
        return r[f] <= self.asof and r.get('known_date', r[f]) <= self.known and (self.view=='planned' or kind!='planned')
    def ev(self,t,r):
        self.evidence[t].add(r[self.c['object_types'][t]['primary_key']]); return r
    def issue(self,code,**ids):
        item={'code':code,**ids}
        if item not in self.issues: self.issues.append(item)
    def fail(self,code,**ids):
        self.issue(code,**ids); raise BusinessError(code)
    def pf(self,o): return self.accounts[o['account_id']]['portfolio_id']
    def instrument(self,oid):
        r=self.by['financial_instruments'][oid]; self.ev('financial_instruments',r)
        mult=number(r['price_multiplier'])
        if mult != (D('.01') if self.norm(r['asset_class'])=='bond' else D(1)):
            self.fail('INVALID_PRICE_MULTIPLIER',instrument_id=oid)
        return r
    def fx(self,currency):
        rows=[r for r in self.by['fx_rates'].values() if r['from_currency']==currency and r['to_currency']=='USD' and r['as_of_date']==self.asof and r['published_date']<=self.asof and (self.view=='planned' or r['published_date']<=self.known) and r['known_date']<=self.known and self.norm(r['view_kind'])==self.view]
        for candidate in rows:self.ev('fx_rates',candidate)
        # A bad external record cannot change the USD reporting identity.
        # Retain its evidence and quality error, without using its rate or ID.
        if currency=='USD':
            if len(rows)==1:
                try:valid=number(rows[0]['rate'])==1
                except (ValueError,ArithmeticError):valid=False
                if valid:return rows[0],D(1)
                self.issue('INVALID_FX',fx_id=rows[0]['fx_id'])
            elif rows:self.issue('MISSING_OR_AMBIGUOUS_FX',currency=currency)
            return {'fx_id':None},D(1)
        if len(rows)!=1: self.fail('MISSING_OR_AMBIGUOUS_FX',currency=currency)
        r=self.ev('fx_rates',rows[0]); n=number(r['rate'])
        if n<=0 or (currency=='USD' and n!=1): self.fail('INVALID_FX',fx_id=r['fx_id'])
        return r,n
    def settlement(self):
        if self.settlement_cache is not None: return self.settlement_cache
        rows=[]
        for tid,t in sorted(self.trades.items()):
            o=self.orders[t['order_id']]; ins=self.instructions[tid]
            self.ev('securities_transactions',t);self.ev('trade_orders',o);self.ev('accounts',self.accounts[o['account_id']])
            instrument=self.ev('financial_instruments',self.by['financial_instruments'][o['instrument_id']])
            if not ins:
                self.issue('MISSING_INSTRUCTION',trade_id=tid)
                rows.append({'portfolio_id':self.pf(o),'trade_id':tid,'instruction_id':None,'instrument_id':o['instrument_id'],'counterparty_id':o['counterparty_id'],'side':self.norm(o['side']),'required_quantity':number(t['trade_quantity']),'settled_quantity':None,'remaining_quantity':None,'latest_event_id':None,'due_date':None,'failure_reason':None,'unit':instrument['unit'],'status_code':'unknown','overdue':None,'event_ids':[]});continue
            valid= sum((number(s['required_quantity']) for s in ins),D(0))==number(t['trade_quantity'])
            for s in sorted(ins,key=lambda r:r['instruction_id']):
                self.ev('settlement_instructions',s); events=self.events[s['instruction_id']]
                for e in events: self.ev('settlement_events',e)
                events=sorted(events,key=lambda e:(e['event_date'],int(e['event_sequence'])))
                keys=[(e['event_date'],int(e['event_sequence'])) for e in events]
                qty=number(s['required_quantity']);done=sum((number(e['settled_quantity']) for e in events),D(0))
                bad=not valid or qty<0 or any(number(e['settled_quantity'])<0 for e in events) or done>qty or len(set(keys))!=len(keys)
                latest=events[-1] if events else None
                if bad: self.issue('INVALID_SETTLEMENT',instruction_id=s['instruction_id'])
                status='unknown' if bad else 'settled' if done==qty else 'failed' if latest and self.norm(latest['event_status'])=='failed' else 'partial' if done>0 else 'pending'
                rows.append({'portfolio_id':self.pf(o),'trade_id':tid,'instruction_id':s['instruction_id'],'instrument_id':o['instrument_id'],'counterparty_id':o['counterparty_id'],'side':self.norm(o['side']),'required_quantity':qty,'settled_quantity':None if bad else done,'remaining_quantity':None if bad else qty-done,'latest_event_id':latest['event_id'] if latest else None,'due_date':s['due_date'],'failure_reason':latest['failure_reason'] if latest else None,'unit':instrument['unit'],'status_code':status,'overdue':None if bad else done<qty and s['due_date']<self.asof,'event_ids':[e['event_id'] for e in events]})
        self.settlement_cache=rows;return rows
    def valuation(self):
        if self.valuation_cache is not None:return self.valuation_cache
        settles=defaultdict(list)
        for item in self.settlement():settles[item['trade_id']].append(item)
        rows=[]
        for op in sorted(self.openings.values(),key=lambda r:r['opening_id']):
            self.ev('opening_positions',op);a=self.ev('accounts',self.accounts[op['account_id']]);i=self.instrument(op['instrument_id'])
            r={'portfolio_id':a['portfolio_id'],'opening_id':op['opening_id'],'account_id':op['account_id'],'instrument_id':i['instrument_id'],'issuer_id':i['issuer_id'],'currency':i['currency'],'base_currency':'USD','unit':i['unit'],'status_code':'complete','price_id':None,'fx_id':None}
            numeric=('trade_basis_quantity','settled_basis_quantity','unsettled_delta','cost_amount','realized_pnl_month','realized_pnl_cumulative','market_value_local','market_value_base','cost_value_base','unrealized_pnl_base')
            r.update({k:None for k in numeric});reasons=[]
            def blocked(error):
                if str(error) not in reasons:reasons.append(str(error))
            trades=sorted((t for t in self.trades.values() if self.orders[t['order_id']]['account_id']==op['account_id'] and self.orders[t['order_id']]['instrument_id']==i['instrument_id']),key=lambda t:(t['trade_date'],t['trade_id']))
            groups=defaultdict(list)
            for t in trades:groups[t['trade_date']].append(t)
            mult=number(i['price_multiplier'])
            # Quantity conservation is independent of intraday weighted-cost order.
            try:
                q=number(op['quantity']);sq=q
                if q<0:self.fail('NEGATIVE_LONG_ONLY_POSITION',opening_id=op['opening_id'])
                for dt,day_trades in sorted(groups.items()):
                    delta=D(0)
                    for t in day_trades:
                        side=self.norm(self.orders[t['order_id']]['side']);qty=number(t['trade_quantity'])
                        if qty<0:self.fail('INVALID_TRADE',trade_id=t['trade_id'])
                        if side not in ('buy','sell'):self.fail('INVALID_SIDE',trade_id=t['trade_id'])
                        sign=1 if side=='buy' else -1;delta+=sign*qty
                        if any(v['settled_quantity'] is None for v in settles[t['trade_id']]):
                            self.issue('UNKNOWN_SETTLED_QUANTITY',trade_id=t['trade_id']);blocked('UNKNOWN_SETTLED_QUANTITY');sq=None
                        elif sq is not None:sq+=sign*sum((v['settled_quantity'] for v in settles[t['trade_id']]),D(0))
                    q+=delta
                    if q<0:self.fail('LONG_ONLY_OVERSELL',opening_id=op['opening_id'],trade_date=dt)
                if sq is not None and sq<0:
                    self.issue('NEGATIVE_LONG_ONLY_POSITION',opening_id=op['opening_id']);blocked('NEGATIVE_LONG_ONLY_POSITION');sq=None
                r.update(trade_basis_quantity=q,settled_basis_quantity=sq,unsettled_delta=q-sq if sq is not None else None)
            except BusinessError as e:blocked(e)
            # Only cost and realized P&L depend on the unavailable buy/sell order.
            try:
                if r['trade_basis_quantity'] is None:self.fail('UNKNOWN_TRADE_QUANTITY',opening_id=op['opening_id'])
                if any(len({self.norm(self.orders[t['order_id']]['side']) for t in ts})>1 for ts in groups.values()):self.fail('AMBIGUOUS_TRADE_ORDER',opening_id=op['opening_id'])
                q=number(op['quantity']);cost=q*number(op['cost_unit_price'])*mult;month=D(0);total=D(0)
                for t in trades:
                    o=self.orders[t['order_id']];qty=number(t['trade_quantity']);price=number(t['execution_price'])
                    if price<=0:self.fail('INVALID_TRADE',trade_id=t['trade_id'])
                    if self.norm(o['side'])=='buy':cost+=qty*price*mult;q+=qty;rp=D(0)
                    else:
                        if qty>q or q<=0:self.fail('LONG_ONLY_OVERSELL',trade_id=t['trade_id'])
                        avg=cost/q;rp=qty*(price*mult-avg);cost-=qty*avg;q-=qty
                    total+=rp
                    if t['trade_date'][:7]==self.asof[:7]:month+=rp
                r.update(cost_amount=rounded(cost),realized_pnl_month=rounded(month),realized_pnl_cumulative=rounded(total))
            except BusinessError as e:blocked(e)
            rate=None
            try:
                f,rate=self.fx(i['currency']);r['fx_id']=f['fx_id']
                if f['fx_id'] is None:r['fx_basis']='currency_identity'
                if r['cost_amount'] is not None:r['cost_value_base']=rounded(r['cost_amount']*rate)
            except BusinessError as e:blocked(e)
            if r['cost_amount']==0:r['cost_value_base']=rounded(0)
            if r['trade_basis_quantity']==0:r.update(market_value_local=rounded(0),market_value_base=rounded(0))
            if rate is None and (r['cost_amount']==0 or r['trade_basis_quantity']==0):r['fx_basis']='zero_amount'
            # Quote selection and local market value do not depend on cost or FX.
            try:
                prices=[x for x in self.by['market_prices'].values() if x['instrument_id']==i['instrument_id'] and x['as_of_date']==self.asof and x['known_date']<=self.known and x['published_date']<=self.asof and (self.view=='planned' or x['published_date']<=self.known) and x['price_date']<=self.asof and self.norm(x['view_kind'])==self.view]
                for candidate in prices:self.ev('market_prices',candidate)
                if len(prices)!=1:self.fail('MISSING_OR_AMBIGUOUS_PRICE',instrument_id=i['instrument_id'])
                quote=self.ev('market_prices',prices[0]);r['price_id']=quote['price_id']
                if self.norm(quote['approval'])!='approved':self.fail('PRICE_UNAPPROVED',price_id=quote['price_id'])
                if (date.fromisoformat(self.asof)-date.fromisoformat(quote['price_date'])).days>3:self.fail('STALE_PRICE',price_id=quote['price_id'])
                if number(quote['price'])<=0 or quote['currency']!=i['currency']:self.fail('INVALID_PRICE',price_id=quote['price_id'])
                if r['trade_basis_quantity'] is not None:
                    local=rounded(r['trade_basis_quantity']*number(quote['price'])*mult);r['market_value_local']=local
                    if rate is not None:r['market_value_base']=rounded(local*rate)
                if r['market_value_base'] is not None and r['cost_value_base'] is not None:r['unrealized_pnl_base']=r['market_value_base']-r['cost_value_base']
            except BusinessError as e:blocked(e)
            if r['market_value_base'] is not None and r['cost_value_base'] is not None:r['unrealized_pnl_base']=r['market_value_base']-r['cost_value_base']
            if reasons:r.update(status_code='blocked',reason_code=reasons[0],reason_codes=reasons)
            rows.append(r)
        present={(o['account_id'],o['instrument_id']) for o in self.openings.values()}
        for t in self.trades.values():
            o=self.orders[t['order_id']]
            if (o['account_id'],o['instrument_id']) not in present:self.issue('MISSING_OPENING_POSITION',trade_id=t['trade_id'])
        self.recorded_diagnostics(rows)
        self.valuation_cache=rows;return rows
    def recorded_diagnostics(self, rows):
        """Compare caches after reconstruction; never use them as calculation inputs."""
        ledger_fields={'trade_basis_quantity':'trade_basis_quantity','settled_basis_quantity':'settled_basis_quantity','unsettled_delta':'unsettled_delta','cost_amount':'cost_amount','realized_pnl':'realized_pnl_month'}
        value_fields={k:k for k in ('market_value_local','market_value_base','cost_value_base','unrealized_pnl_base')}
        def mismatch(cached, current, fields):
            differences={}
            for field,target in fields.items():
                a=cached.get(field);b=current.get(target)
                a=None if a in ('',None) else number(a);b=None if b in ('',None) else number(b)
                if b is not None and a!=b:differences[field]={'recorded':a,'recomputed':b,'difference':None if a is None or b is None else b-a}
            return differences
        position_index=defaultdict(list);valuation_index=defaultdict(list)
        for p in self.by['positions'].values():
            if p['as_of_date']==self.asof and p['known_date']<=self.known and self.norm(p['view_kind'])==self.view:position_index[p['opening_id']].append(p)
        for v in self.by['valuation_snapshots'].values():
            if v['as_of_date']==self.asof and v['known_date']<=self.known and self.norm(v['view_kind'])==self.view:valuation_index[v['position_id']].append(v)
        for current in rows:
            positions=position_index[current['opening_id']]
            for p in positions:self.ev('positions',p)
            if len(positions)>1:
                self.issue('AMBIGUOUS_RECORDED_POSITION',opening_id=current['opening_id'],position_ids=sorted(p['position_id'] for p in positions));continue
            if not positions:continue
            p=positions[0];differences=mismatch(p,current,ledger_fields)
            if differences:self.issue('STALE_RECORDED_POSITION',position_id=p['position_id'],differences=differences)
            values=valuation_index[p['position_id']]
            for v in values:self.ev('valuation_snapshots',v)
            if len(values)>1:self.issue('AMBIGUOUS_RECORDED_VALUATION',position_id=p['position_id'],valuation_ids=sorted(v['valuation_id'] for v in values));continue
            if not values:continue
            v=values[0];differences=mismatch(v,current,value_fields)
            if differences:self.issue('STALE_RECORDED_VALUATION',valuation_id=v['valuation_id'],differences=differences)
    def exposures(self):
        vals=self.valuation();rows=[]
        for pid in sorted(self.ids):
            vs=[v for v in vals if v['portfolio_id']==pid]
            missing_trades=[self.trades[i['trade_id']] for i in self.issues if i['code']=='MISSING_OPENING_POSITION' and self.pf(self.orders[self.trades[i['trade_id']]['order_id']])==pid]
            missing_issuers=set();unassigned=any(not v.get('issuer_id') for v in vs)
            for trade in missing_trades:
                instrument=self.by['financial_instruments'].get(self.orders[trade['order_id']]['instrument_id'])
                if instrument and instrument.get('issuer_id'):missing_issuers.add(instrument['issuer_id'])
                else:unassigned=True
            complete=bool(vs) and all(v['market_value_base'] is not None for v in vs) and not missing_trades and not unassigned
            denom=sum((v['market_value_base'] for v in vs),D(0)) if complete else None
            if denom is not None and denom<=0:self.issue('INVALID_DENOMINATOR',portfolio_id=pid)
            issuers={v['issuer_id'] for v in vs if v.get('issuer_id')}|missing_issuers|{l['entity_id'] for l in self.by['mandate_limits'].values() if l['portfolio_id']==pid and self.norm(l['measure'])=='issuer_ratio'}
            for issuer in sorted(issuers):
                own=[v for v in vs if v.get('issuer_id')==issuer]
                known=bool(vs) and not unassigned and issuer not in missing_issuers and all(v['market_value_base'] is not None for v in own)
                amount=sum((v['market_value_base'] for v in own),D(0)) if known else None
                ratio=rounded(amount/denom,6) if amount is not None and denom is not None and denom>0 else None
                rows.append({'portfolio_id':pid,'entity_id':issuer,'measure':'issuer_ratio','observed_value':ratio,'exposure_amount':amount,'denominator_amount':denom})
        settles=defaultdict(list)
        for s in self.settlement():settles[(s['portfolio_id'],s['counterparty_id'])].append(s)
        for pid in sorted(self.ids):
            cps={l['entity_id'] for l in self.by['mandate_limits'].values() if l['portfolio_id']==pid and self.norm(l['measure'])=='receivable_amount'}|{self.orders[t['order_id']]['counterparty_id'] for t in self.trades.values() if self.pf(self.orders[t['order_id']])==pid}
            for cp in sorted(cps):
                amount=D(0);contributions=[];bad=False
                for s in settles[(pid,cp)]:
                    if s['side']!='sell':continue
                    if s['remaining_quantity'] is None:bad=True;continue
                    if s['remaining_quantity']==0:
                        contributions.append({'trade_id':s['trade_id'],'instruction_id':s['instruction_id'],'fx_id':None,'fx_basis':'zero_amount','remaining_quantity':D(0),'unrounded_receivable_usd':D(0)})
                        continue
                    t=self.trades[s['trade_id']]
                    try:
                        i=self.instrument(s['instrument_id']);f,rate=self.fx(i['currency'])
                        value=s['remaining_quantity']*number(t['execution_price'])*number(i['price_multiplier'])*rate
                        amount+=value;contribution={'trade_id':t['trade_id'],'instruction_id':s['instruction_id'],'fx_id':f['fx_id'],'remaining_quantity':s['remaining_quantity'],'unrounded_receivable_usd':value}
                        if f['fx_id'] is None:contribution['fx_basis']='currency_identity'
                        contributions.append(contribution)
                    except BusinessError:bad=True
                rows.append({'portfolio_id':pid,'entity_id':cp,'measure':'receivable_amount','observed_value':None if bad else rounded(amount),'contributions':contributions,'rounding_residual':None if bad else rounded(amount)-sum((rounded(c['unrounded_receivable_usd']) for c in contributions),D(0))})
        return rows
    def assessments(self):
        rows=[]
        for e in self.exposures():
            key={k:e[k] for k in ('portfolio_id','entity_id','measure')}
            candidates=[l for l in self.by['mandate_limits'].values() if l['portfolio_id']==e['portfolio_id'] and l['entity_id']==e['entity_id'] and self.norm(l['measure'])==e['measure'] and self.norm(l['approval'])=='approved' and l['decision_date']<=self.known and l['effective_from_date']<=self.asof<=l['effective_to_date']]
            for l in candidates:self.ev('mandate_limits',l)
            r={**e,'limit_id':None,'threshold':None,'excess_value':None,'status_code':'unknown','selection_status':'valid'}
            if len(candidates)!=1:
                r['selection_status']='missing' if not candidates else 'ambiguous';self.issue('LIMIT_'+r['selection_status'].upper(),**key)
            else:
                l=candidates[0];threshold=number(l['threshold']);r.update(limit_id=l['limit_id'],threshold=threshold)
                valid=threshold>=0 and (e['measure']!='issuer_ratio' or threshold<=1) and l['currency']==('' if e['measure']=='issuer_ratio' else 'USD')
                if not valid:r['selection_status']='invalid';self.issue('INVALID_LIMIT',limit_id=l['limit_id'])
                elif e['observed_value'] is not None:r.update(status_code='breach' if e['observed_value']>threshold else 'within',excess_value=max(D(0),e['observed_value']-threshold))
            # Cache diagnostics are never used in reconstruction.
            table='issuer_exposures' if e['measure']=='issuer_ratio' else 'counterparty_exposures';entity='issuer_id' if e['measure']=='issuer_ratio' else 'counterparty_id';value='ratio' if e['measure']=='issuer_ratio' else 'unsettled_receivable'
            cached=[x for x in self.by[table].values() if x['portfolio_id']==e['portfolio_id'] and x[entity]==e['entity_id'] and x['as_of_date']==self.asof and x['known_date']<=self.known and self.norm(x['view_kind'])==self.view]
            r['recorded_value']=None;r['recorded_difference']=None
            if len(cached)==1:
                self.ev(table,cached[0]);v=cached[0][value];v=None if v in ('',None) else number(v);r['recorded_value']=v
                if v is not None and e['observed_value'] is not None:r['recorded_difference']=e['observed_value']-v
                if e['observed_value'] is not None and v!=e['observed_value']:self.issue('STALE_RECORDED_EXPOSURE',exposure_id=cached[0]['exposure_id'])
            rows.append(r)
        return rows
    def result(self,capability):
        with localcontext() as ctx:
            ctx.prec=38
            if capability=='settlement_asof':rows=self.settlement()
            elif capability=='valuation_asof':rows=self.valuation()
            elif capability=='limit_assessment_asof':rows=self.assessments()
            else:raise ValueError('UNKNOWN_CAPABILITY')
        for r in rows:
            code=r['status_code'];r['status']=self.labels.get(code,code) if self.zh else code
        invalid=[r for r in rows if r['status_code'] in ('blocked','unknown')]
        completeness='blocked' if not rows or len(invalid)==len(rows) else 'partial' if invalid or self.issues else 'complete'
        return serial({'schema_version':1,'capability':capability,'scope':self.scope,'completeness':completeness,'rows':rows,'issues':self.issues,'evidence':{t:sorted(ids) for t,ids in sorted(self.evidence.items())}})

def execute(capability,tables,contract,scope):
    return Decisions(tables,contract,scope).result(capability)
