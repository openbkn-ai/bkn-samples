"""Independent source-fact oracle. Does not import the production calculator.

Rules are implemented from the PRD/public semantics. This is evaluator-only code.
"""
from collections import defaultdict, deque
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv, json
from pathlib import Path

D=Decimal
ZERO=D('0')
def number(v): return D(str(v or 0))
def fixed(v): return None if v is None else format(v.quantize(D('.000001'),rounding=ROUND_HALF_UP),'f')
def day(v): return date.fromisoformat(str(v)[:10])
def active(r, a, k): return r['effective_from']<=a<=r['effective_to'] and r['known_date']<=k

class Reference:
    def __init__(self, root):
        self.tables={p.stem:list(csv.DictReader(p.open(encoding='utf-8'))) for p in Path(root).glob('*.csv')}
        self.products={r['product_id']:r for r in self.tables['products']}
        self.lots={r['lot_id']:r for r in self.tables['lots']}
        self.orders={r['order_id']:r for r in self.tables['orders']}
        self.lines={r['line_id']:r for r in self.tables['order_lines']}
    def visible_events(self,a,k):
        physical=[r for r in self.tables['movements'] if r['view_code']=='actual' and r['event_date']<=a and r['recorded_date']<=k]
        grouped=defaultdict(list)
        for r in physical: grouped[r['event_id']].append(r)
        events=[];bad=set();diagnostics=[]
        for eid,rs in grouped.items():
            signatures={tuple((key,v) for key,v in sorted(r.items()) if key not in ('movement_id','recorded_date')) for r in rs}
            if len(signatures)>1:
                for r in rs:
                    for loc in (r['source_location_id'],r['destination_location_id']):
                        if loc: bad.add((r['lot_id'],loc))
                diagnostics.append({'code':'conflicting_event','event_id':eid})
            else:
                events.append(sorted(rs,key=lambda r:(r['recorded_date'],r['movement_id']))[0])
                if len(rs)>1: diagnostics.append({'code':'duplicate_event','event_id':eid})
        reversed_ids={r['reversal_of'] for r in events if r['event_type_code']=='reversal'}
        events=[r for r in events if r['event_type_code']!='reversal' and r['event_id'] not in reversed_ids]
        for r in physical:
            if r['event_type_code']=='reversal':diagnostics.append({'code':'reversal','event_id':r['event_id'],'reversal_of':r['reversal_of']})
        sequences=defaultdict(list)
        for r in events:sequences[(r['lot_id'],r['event_date'],r['event_sequence'])].append(r)
        for key,rs in sequences.items():
            if len(rs)>1:
                for r in rs:
                    for loc in (r['source_location_id'],r['destination_location_id']):
                        if loc:bad.add((r['lot_id'],loc))
                diagnostics.append({'code':'sequence_tie','lot_id':key[0]})
        return sorted(events,key=lambda r:(r['event_date'],number(r['event_sequence']),r['event_id'])),bad,diagnostics
    def links(self,a,k): return [r for r in self.tables['lot_links'] if r['effective_date']<=a and r['known_date']<=k]
    def closure(self,root,a,k,both=False):
        edges=self.links(a,k);seen={root};todo=[root]
        while todo:
            node=todo.pop()
            for e in edges:
                nxt=e['child_lot_id'] if e['parent_lot_id']==node else e['parent_lot_id'] if both and e['child_lot_id']==node else None
                if nxt and nxt not in seen: seen.add(nxt);todo.append(nxt)
        return seen
    def inspection(self,lot,a,k):
        rows=[r for r in self.tables['inspections'] if r['lot_id']==lot and r['inspection_date']<=a and r['known_date']<=k]
        return max(rows,key=lambda r:(r['inspection_date'],r['inspection_id']))['result_code'] if rows else 'pending'
    def recalled(self,a,k):
        result=set()
        for r in self.tables['recalls']:
            if r['announced_date']<=a and r['known_date']<=k and r['status_code']=='open':result|=self.closure(r['root_lot_id'],a,k)
        return result
    def inventory(self,a='2027-02-28',k='2027-02-28'):
        events,bad,diagnostics=self.visible_events(a,k)
        cells=defaultdict(lambda:{'on_hand':ZERO,'in_transit':ZERO,'sold':ZERO,'returned':ZERO})
        transit=defaultdict(lambda:{'out':ZERO,'in':ZERO,'cells':set()})
        for r in events:
            lot=self.lots.get(r['lot_id']);qty=number(r['quantity']);typ=r['event_type_code']
            if not lot:
                diagnostics.append({'code':'missing_lot','event_id':r['event_id']});continue
            prod=self.products[lot['product_id']]
            if r['unit'] in ('case','箱'):qty*=number(prod['pack_multiplier'])
            elif r['unit'] not in (prod['unit'],'ea','件'):
                for loc in (r['source_location_id'],r['destination_location_id']):
                    if loc:bad.add((r['lot_id'],loc))
                diagnostics.append({'code':'unit_mismatch','event_id':r['event_id']});continue
            s=(r['lot_id'],r['source_location_id']);t=(r['lot_id'],r['destination_location_id'])
            if typ in ('receive','produce','adjust'):cells[t]['on_hand']+=qty
            if typ in ('sale','consume','dispatch'):cells[s]['on_hand']-=qty
            if typ=='sale':cells[s]['sold']+=qty
            if typ=='return':cells[t]['on_hand']+=qty;cells[t]['returned']+=qty
            if typ in ('dispatch','arrive'):
                tr=transit[(r['transfer_id'],r['lot_id'])];tr['cells'].add(t)
                tr['out' if typ=='dispatch' else 'in']+=qty
                cells[t]['in_transit']+=qty if typ=='dispatch' else -qty
                if typ=='arrive':cells[t]['on_hand']+=qty
        for (transfer,lot),tr in transit.items():
            if tr['in']>tr['out']:
                bad.update(tr['cells']);diagnostics.append({'code':'missing_or_insufficient_dispatch','transfer_id':transfer})
        rec=self.recalled(a,k);rows=[]
        for (lid,loc),s in sorted(cells.items()):
            lot=self.lots[lid];product=self.products[lot['product_id']]
            if s['on_hand']<0 or s['in_transit']<0:
                bad.add((lid,loc));diagnostics.append({'code':'negative_inventory','lot_id':lid,'location_id':loc})
            unknown=(lid,loc) in bad
            status=self.inspection(lid,a,k);physical=max(ZERO,s['on_hand'])
            if s['returned']>s['sold']:
                unknown=True;diagnostics.append({'code':'returns_exceed_sales','lot_id':lid,'location_id':loc})
            hold=sum((number(r['quantity']) for r in self.tables['holds'] if r['lot_id']==lid and r['location_id']==loc and active(r,a,k)),ZERO)
            overlap=sum((number(r.get('return_overlap_quantity')) for r in self.tables['holds'] if r['lot_id']==lid and r['location_id']==loc and active(r,a,k)),ZERO)
            if overlap>s['returned'] or any(number(r.get('return_overlap_quantity'))>number(r['quantity']) for r in self.tables['holds'] if r['lot_id']==lid and r['location_id']==loc and active(r,a,k)):
                unknown=True;diagnostics.append({'code':'invalid_overlap','lot_id':lid,'location_id':loc})
            quarantine=min(physical,max(s['returned']+hold-overlap,physical if status!='passed' else ZERO))
            expired=lot['expiry_date']<a
            recall_block=max(ZERO,physical-quarantine) if lid in rec else ZERO
            eligible=ZERO if expired else max(ZERO,physical-quarantine-recall_block)
            requested=sum((number(r['quantity']) for r in self.tables['reservations'] if r['lot_id']==lid and r['location_id']==loc and active(r,a,k)),ZERO)
            reserved=min(eligible,requested)
            if requested>eligible:diagnostics.append({'code':'overreservation','lot_id':lid,'location_id':loc})
            row={'product_id':lot['product_id'],'lot_id':lid,'location_id':loc,'unit':product['unit'],'expiry_date':lot['expiry_date'],'inspection_status_code':status,
                 'on_hand':None if unknown else s['on_hand'],'in_transit':None if unknown else s['in_transit'],'quarantined':None if unknown else quarantine,'recall_blocked':None if unknown else recall_block,
                 'reserved':None if unknown else reserved,'available':None if unknown else eligible-reserved,'sold':None if unknown else max(ZERO,s['sold']-s['returned']),'returned':None if unknown else s['returned'],
                 'expired':expired,'near_expiry':0<=(day(lot['expiry_date'])-day(a)).days<=14,'quality_status':'unknown' if unknown else 'known'}
            rows.append(row)
        return rows,diagnostics,events
    def allocation(self,product_ids,a,k,order_ids=None):
        inventory,_,_=self.inventory(a,k)
        balances={(r['lot_id'],r['location_id']):r['available'] for r in inventory}
        rows=[];visible=[r for r in self.orders.values() if r['order_date']<=a and r['known_date']<=k and r['status_code']=='open' and (order_ids is None or r['order_id'] in order_ids)]
        visible.sort(key=lambda r:(number(r['priority']),r['due_date'],r['order_id']))
        for order in visible:
            for line in sorted(self.lines.values(),key=lambda r:r['line_id']):
                if line['order_id']!=order['order_id'] or line['product_id'] not in product_ids:continue
                candidates=[r for r in inventory if r['location_id']==order['location_id'] and r['product_id']==line['product_id']]
                unknown=any(r['available'] is None for r in candidates)
                for res in self.tables['reservations']:
                    key=(res['lot_id'],res['location_id'])
                    if res['line_id']==line['line_id'] and active(res,a,k) and key in balances and balances[key] is not None:
                        # Own reservation restores at most this lot's eligible stock.
                        original=next(r for r in candidates if r['lot_id']==key[0])
                        ceiling=original['on_hand']-original['quarantined']-original['recall_blocked']
                        if original['expired']:ceiling=ZERO
                        balances[key]=min(ceiling,balances[key]+number(res['quantity']))
                need=number(line['quantity']);assign=[]
                if not unknown:
                    for r in sorted(candidates,key=lambda r:(r['expiry_date'],r['lot_id'])):
                        if r['inspection_status_code']!='passed' or day(r['expiry_date'])<max(day(a),day(order['due_date']))+timedelta(days=int(number(line['min_shelf_days']))):continue
                        key=(r['lot_id'],r['location_id']);take=min(need,max(ZERO,balances[key]))
                        if take:assign.append({'lot_id':r['lot_id'],'quantity':take});balances[key]-=take;need-=take
                requested=number(line['quantity']);allocated=None if unknown else requested-need
                rows.append({'line_id':line['line_id'],'order_id':order['order_id'],'product_id':line['product_id'],'location_id':order['location_id'],'unit':line['unit'],'requested_quantity':requested,'allocated_quantity':allocated,'shortage_quantity':None if unknown else need,'allocation_status_code':'unknown' if unknown else 'full' if not need else 'shortage' if allocated==0 else 'partial','allocations':assign})
        return rows
    def plan(self,product_ids,a,k,horizon='2027-03-31'):
        inventory,_,_=self.inventory(a,k);buckets=defaultdict(dict);unknown=set()
        for r in inventory:
            key=(r['product_id'],r['location_id'])
            if r['available'] is None:unknown.add(key)
            else:buckets[key][r['lot_id']]=r['available']
        forecasts=[r for r in self.tables['demand_forecasts'] if r['product_id'] in product_ids and r['view_code']=='planned' and r['known_date']<=k and a<r['demand_date']<=horizon]
        forecasts.sort(key=lambda r:(r['demand_date'],r['forecast_id']))
        applied=set();recalled=self.recalled(a,k);rows=[]
        for f in forecasts:
            key=(f['product_id'],f['location_id']);prd=self.products[f['product_id']];due=f['demand_date']
            for m in self.tables['movements']:
                lot=self.lots[m['lot_id']]
                if m['event_id'] in applied or m['view_code']!='planned' or m['event_type_code'] not in ('receive','produce') or m['recorded_date']>k or not a<m['event_date']<=due:continue
                if (lot['product_id'],m['destination_location_id'])!=key:continue
                applied.add(m['event_id'])
                if m['lot_id'] in recalled or self.inspection(m['lot_id'],due,k)!='passed':continue
                if day(lot['expiry_date'])<day(due)+timedelta(days=int(number(prd['min_shelf_days']))):continue
                qty=number(m['quantity'])*(number(prd['pack_multiplier']) if m['unit'] in ('case','箱') else 1)
                buckets[key][m['lot_id']]=buckets[key].get(m['lot_id'],ZERO)+qty
            for lid in buckets[key]:
                if day(self.lots[lid]['expiry_date'])<day(due)+timedelta(days=int(number(prd['min_shelf_days']))):buckets[key][lid]=ZERO
            supply=sum(buckets[key].values(),ZERO);need=number(f['quantity']);left=need
            for lid in sorted(buckets[key],key=lambda x:(self.lots[x]['expiry_date'],x)):
                take=min(left,buckets[key][lid]);buckets[key][lid]-=take;left-=take
            rows.append({'forecast_id':f['forecast_id'],'product_id':f['product_id'],'location_id':f['location_id'],'demand_date':due,'unit':f['unit'],'demand_quantity':need,'eligible_supply_quantity':None if key in unknown else supply,'allocated_quantity':None if key in unknown else need-left,'shortage_quantity':None if key in unknown else left,'recommended_quantity':None if key in unknown else left})
        return rows
    def recall(self,recall_id,a,k):
        rec=next(r for r in self.tables['recalls'] if r['recall_id']==recall_id)
        if rec['announced_date']>a or rec['known_date']>k or rec['status_code']!='open':return []
        affected=self.closure(rec['root_lot_id'],a,k);inv,_,ev=self.inventory(a,k);groups=defaultdict(list)
        for r in inv:
            if r['lot_id'] in affected:groups[(r['product_id'],r['location_id'],r['unit'])].append(r)
        rows=[]
        for (product,loc,unit),group in sorted(groups.items()):
            unknown=any(r['quality_status']=='unknown' for r in group);tot={key:None if unknown else sum((r[key] for r in group),ZERO) for key in ('on_hand','in_transit','sold','returned','quarantined')}
            denominator=None if unknown else tot['on_hand']+tot['in_transit'];controlled=tot['quarantined'];ratio=None if denominator is None or denominator<=0 else controlled/denominator
            fulfilled={m['order_id'] for m in ev if m['event_type_code']=='sale' and m['lot_id'] in affected and m['source_location_id']==loc and self.lots[m['lot_id']]['product_id']==product and m['order_id']}
            reserved={self.lines[r['line_id']]['order_id'] for r in self.tables['reservations'] if r['lot_id'] in {x['lot_id'] for x in group} and r['location_id']==loc and active(r,a,k) and self.orders[self.lines[r['line_id']]['order_id']]['status_code']=='open'}
            rows.append({'recall_id':recall_id,'product_id':product,'location_id':loc,'unit':unit,'affected_lot_ids':sorted(r['lot_id'] for r in group),**{x:tot[x] for x in ('on_hand','in_transit','sold','returned')},'controlled_quantity':controlled,'controllable_quantity':denominator,'pending_control_quantity':None if unknown else denominator-controlled,'coverage_ratio':ratio,'affected_order_ids':sorted(fulfilled|reserved)})
        return rows

def serialize(v):
    if isinstance(v,D):return fixed(v)
    if isinstance(v,list):return [serialize(x) for x in v]
    if isinstance(v,dict):return {k:serialize(x) for k,x in v.items()}
    return v
