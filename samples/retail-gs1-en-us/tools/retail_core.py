"""Read-only dated stock, fulfillment and recall calculations. No fixture access."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from collections import defaultdict

def D(x): return Decimal(str(x or '0'))
def Q(x): return None if x is None else str(D(x).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP))
def day(x): return str(x or '')[:10]
def visible(r,scope,field='known_date'): return day(r.get(field))<=scope['knowledge_date']
def dated(r,scope,field): return day(r.get(field))<=scope['as_of_date'] and visible(r,scope)
def active(r,s): return day(r['effective_from'])<=s['as_of_date']<=day(r['effective_to']) and visible(r,s)
def event_payload(r):
    """Compare business facts only, independently of source-row SDK metadata."""
    fields=('event_id','lot_id','event_type_code','view_code','source_location_id',
            'destination_location_id','event_date','event_sequence','quantity',
            'unit','transfer_id','order_id','reversal_of')
    return tuple(day(r.get(k)) if k=='event_date' else D(r.get(k))
                 if k in ('event_sequence','quantity') else r.get(k) or None
                 for k in fields)
def closure(roots,links):
    out=set(roots)
    for _ in range(len(links)+1):
        nxt=out|{r['child_lot_id'] for r in links if r['parent_lot_id'] in out}
        if nxt==out:return out
        out=nxt
    return out

def execute(operation,tables,contract,scope):
    s=dict(scope)
    for k in ('as_of_date','knowledge_date'):
        if k not in s or date.fromisoformat(s[k]).isoformat()!=s[k]:raise ValueError('DATE_REQUIRED:'+k)
    if s.get('view_kind','actual') not in ('actual','planned'):raise ValueError('INVALID_VIEW')
    ids=s.get('product_ids')
    if operation!='recall_assessment' and (not isinstance(ids,list) or not 1<=len(ids)<=50 or len(set(ids))!=len(ids)):raise ValueError('PRODUCT_SCOPE_1_TO_50_REQUIRED')
    if operation not in ('inventory_asof','fulfillment_plan','recall_assessment'):raise ValueError('UNKNOWN_OPERATION')
    products={r['product_id']:r for r in tables['products']};lots={r['lot_id']:r for r in tables['lots']}
    issues=[];evidence=defaultdict(set)
    def issue(code,ref,lot_id='',location_id=''):
        row={'code':code,'ref_id':ref,'lot_id':lot_id,'location_id':location_id}
        if row not in issues:issues.append(row)
    def ev(t,r):
        pk=contract['object_types'][t]['primary_key'];evidence[t].add(r[pk])
    links=[r for r in tables['lot_links'] if dated(r,s,'effective_date')]
    recalls=[r for r in tables['recalls'] if dated(r,s,'announced_date') and r['status_code']=='open']
    recalled=set()
    for r in recalls:recalled|=closure([r['root_lot_id']],links)
    inspections={};inspection_days={}
    for r in sorted(tables['inspections'],key=lambda r:(day(r['inspection_date']),r['inspection_id'])):
        if dated(r,s,'inspection_date'):
            k=(r['lot_id'],day(r['inspection_date']))
            if k in inspection_days and inspection_days[k]!=r['result_code']:
                issue('CONFLICTING_INSPECTION',r['inspection_id'],r['lot_id']);conflicts_inspection=True
            inspection_days[k]=r['result_code'];inspections[r['lot_id']]=r
    events={};conflicts=set();seq={}
    for r in tables['movements']:
        if r['view_code']!='actual' or day(r['event_date'])>s['as_of_date'] or not visible(r,s,'recorded_date'):continue
        signature=event_payload(r)
        prior=events.get(r['event_id'])
        if prior:
            old=event_payload(prior)
            if old!=signature:
                for event in (r,prior):
                    for field in ('source_location_id','destination_location_id'):
                        if event[field]:conflicts.add((event['lot_id'],event[field]))
                issue('CONFLICTING_EVENT',r['event_id'],r['lot_id'],r['source_location_id'] or r['destination_location_id'])
            else:issue('DUPLICATE_EVENT_IGNORED',r['event_id'],r['lot_id'])
            ev('movements',r);continue
        events[r['event_id']]=r
    reversals={r['reversal_of'] for r in events.values() if r['event_type_code']=='reversal'}
    for target in reversals:
        if target not in events:issue('REVERSAL_TARGET_MISSING',target)
    balance=defaultdict(lambda:{'on_hand':D(0),'in_transit':D(0),'sold':D(0),'returned':D(0),'invalid':False})
    transfers={};pending_arrivals=[]
    for r in sorted(events.values(),key=lambda r:(day(r['event_date']),int(D(r['event_sequence'])),r['event_id'])):
        ev('movements',r)
        if r['event_id'] in reversals or r['event_type_code']=='reversal':continue
        lot=lots.get(r['lot_id']);src=r['source_location_id'];dst=r['destination_location_id'];code=r['event_type_code']
        if not lot:issue('LOT_MASTER_MISSING',r['movement_id'],r['lot_id']);continue
        p=products[lot['product_id']];qty=D(r['quantity'])*(D(p['pack_multiplier']) if r['unit'] in ('case','箱') else D(1))
        if r['unit'] not in (p['unit'],'ea','件','case','箱'):issue('UNIT_UNKNOWN',r['movement_id'],r['lot_id']);conflicts.add(r['lot_id'])
        key=(r['lot_id'],day(r['event_date']),r['event_sequence'])
        if key in seq:issue('EVENT_SEQUENCE_TIE',r['event_id'],r['lot_id']);conflicts.add(r['lot_id'])
        seq[key]=r['event_id']
        a=balance[(r['lot_id'],src)] if src else None;b=balance[(r['lot_id'],dst)] if dst else None
        if code in ('receive','produce','adjust') and b is not None:b['on_hand']+=qty
        elif code=='dispatch' and a is not None and b is not None:
            a['on_hand']-=qty;b['in_transit']+=qty
            transfers[r['transfer_id']]=(r['lot_id'],dst,qty)
        elif code=='arrive' and b is not None:
            b['on_hand']+=qty;b['in_transit']-=qty;pending_arrivals.append((r,qty))
        elif code in ('sale','consume') and a is not None:
            a['on_hand']-=qty
            if code=='sale':a['sold']+=qty
        elif code=='return' and b is not None:b['on_hand']+=qty;b['returned']+=qty
        else:issue('EVENT_SHAPE_INVALID',r['event_id'],r['lot_id']);conflicts.add(r['lot_id'])
        if a is not None and a['on_hand']<0:issue('NEGATIVE_STOCK',r['event_id'],r['lot_id'],src);a['invalid']=True
    arrived=defaultdict(lambda:D(0))
    for r,qty in pending_arrivals:
        arrived[r['transfer_id']]+=qty;t=transfers.get(r['transfer_id'])
        if not t or t[:2]!=(r['lot_id'],r['destination_location_id']) or arrived[r['transfer_id']]>t[2]:
            b=balance[(r['lot_id'],r['destination_location_id'])];b['invalid']=True;issue('TRANSFER_COVERAGE_MISSING',r['event_id'],r['lot_id'],r['destination_location_id'])
    stock=[];reservation_assigned={}
    for (lid,loc),b in sorted(balance.items()):
        lot=lots[lid];p=products[lot['product_id']];ev('lots',lot);ev('products',p)
        inspection=inspections.get(lid);ic=inspection['result_code'] if inspection else 'pending'
        if inspection:ev('inspections',inspection)
        hs=[r for r in tables['holds'] if r['lot_id']==lid and r['location_id']==loc and active(r,s)]
        rs=[r for r in tables['reservations'] if r['lot_id']==lid and r['location_id']==loc and active(r,s)]
        for r in hs:ev('holds',r)
        for r in rs:ev('reservations',r)
        overlap=sum((D(r.get('return_overlap_quantity')) for r in hs),D(0));held=sum((D(r['quantity']) for r in hs),D(0))
        if overlap>b['returned'] or any(D(r.get('return_overlap_quantity'))>D(r['quantity']) for r in hs):issue('HOLD_OVERLAP_INVALID',lid,lid,loc);conflicts.add((lid,loc))
        quarantine=min(max(b['on_hand'],D(0)),max(b['returned']+held-overlap,b['on_hand'] if ic!='passed' else D(0)))
        if b['returned']+held-overlap>b['on_hand']:issue('HOLD_EXCEEDS_ON_HAND',lid,lid,loc)
        if b['returned']>b['sold']:issue('RETURN_EXCEEDS_SALES',lid,lid,loc);conflicts.add((lid,loc))
        recall_blocked=max(D(0),b['on_hand']-quarantine) if lid in recalled else D(0)
        expired=day(lot['expiry_date'])<s['as_of_date'];eligible=max(D(0),b['on_hand']-quarantine-recall_blocked) if not expired else D(0)
        wanted=sum((D(r['quantity']) for r in rs),D(0));reserved=min(eligible,wanted)
        unassigned=reserved
        for res in sorted(rs,key=lambda r:r['reservation_id']):
            assigned=min(unassigned,D(res['quantity']));reservation_assigned[res['reservation_id']]=assigned;unassigned-=assigned
        if wanted>eligible:issue('OVERRESERVATION',lid,lid,loc)
        unknown=b['invalid'] or lid in conflicts or (lid,loc) in conflicts or b['on_hand']<0 or b['in_transit']<0 or any(x['code']=='CONFLICTING_INSPECTION' and x['lot_id']==lid for x in issues)
        row={'product_id':lot['product_id'],'lot_id':lid,'location_id':loc,'unit':p['unit'],'expiry_date':day(lot['expiry_date']),'inspection_status_code':ic,'on_hand':Q(None if unknown else b['on_hand']),'in_transit':Q(None if unknown else b['in_transit']),'quarantined':Q(None if unknown else quarantine),'recall_blocked':Q(None if unknown else recall_blocked),'reserved':Q(None if unknown else reserved),'available':Q(None if unknown else eligible-reserved),'sold':Q(max(D(0),b['sold']-b['returned'])),'returned':Q(b['returned']),'expired':expired,'near_expiry':0<=(date.fromisoformat(day(lot['expiry_date']))-date.fromisoformat(s['as_of_date'])).days<=14,'quality_status':'unknown' if unknown else 'known'}
        stock.append(row)
    def selected(r):return (not ids or r['product_id'] in ids) and (not s.get('location_ids') or r['location_id'] in s['location_ids']) and (not s.get('lot_ids') or r['lot_id'] in s['lot_ids'])
    rows=[];extra={}
    if operation=='inventory_asof':
        rows=[r for r in stock if selected(r)]
        if s.get('trace_lot_id'):
            connected={s['trace_lot_id']}
            for _ in range(len(links)+1):
                new=connected|{r[k] for r in links if r['parent_lot_id'] in connected or r['child_lot_id'] in connected for k in ('parent_lot_id','child_lot_id')}
                if new==connected:break
                connected=new
            extra['trace_rows']=[{k:r[k] for k in ('link_id','parent_lot_id','child_lot_id','link_type_code')} for r in links if r['parent_lot_id'] in connected and r['child_lot_id'] in connected]
            for r in links:
                if r['parent_lot_id'] in connected:ev('lot_links',r)
    elif operation=='recall_assessment':
        recall=next((r for r in recalls if r['recall_id']==s.get('recall_id')),None)
        if not recall:issue('RECALL_NOT_ACTIVE',s.get('recall_id',''))
        else:
            ev('recalls',recall);affected=closure([recall['root_lot_id']],links)
            for r in links:
                if r['parent_lot_id'] in affected:ev('lot_links',r)
            # Detect cycles within the relevant directed graph.
            def cyclic(node,path):
                if node in path:return True
                return any(cyclic(r['child_lot_id'],path|{node}) for r in links if r['parent_lot_id']==node)
            cycle=cyclic(recall['root_lot_id'],set())
            if cycle:issue('LOT_LINK_CYCLE',recall['recall_id'])
            groups=defaultdict(list)
            for r in stock:
                if r['lot_id'] in affected:groups[(r['product_id'],r['location_id'],r['unit'])].append(r)
            for (pid,loc,unit),items in sorted(groups.items()):
                unknown=cycle or any(r['on_hand'] is None or r['in_transit'] is None for r in items)
                def total(k):return None if unknown else sum((D(r[k]) for r in items),D(0))
                onhand=total('on_hand');transit=total('in_transit');controlled=total('quarantined');den=None if unknown else onhand+transit
                affected_orders={r['order_id'] for r in events.values() if r['event_type_code']=='sale' and r['source_location_id']==loc and r['lot_id'] in {i['lot_id'] for i in items} and r['order_id'] and r['event_id'] not in reversals}
                line_orders={r['line_id']:r['order_id'] for r in tables['order_lines']}
                open_orders={r['order_id'] for r in tables['orders'] if dated(r,s,'order_date') and r['status_code']=='open'}
                affected_orders|={line_orders.get(r['line_id']) for r in tables['reservations'] if r['location_id']==loc and line_orders.get(r['line_id']) in open_orders and r['lot_id'] in {i['lot_id'] for i in items} and active(r,s)}
                rows.append({'recall_id':recall['recall_id'],'product_id':pid,'location_id':loc,'unit':unit,'affected_lot_ids':sorted(r['lot_id'] for r in items),'on_hand':Q(onhand),'in_transit':Q(transit),'sold':Q(sum((D(r['sold']) for r in items),D(0))),'returned':Q(sum((D(r['returned']) for r in items),D(0))),'controlled_quantity':Q(controlled),'controllable_quantity':Q(den),'pending_control_quantity':Q(None if unknown else den-controlled),'coverage_ratio':Q(controlled/den if den is not None and den>0 else None),'affected_order_ids':sorted(x for x in affected_orders if x)})
    else:
        pool={ (r['lot_id'],r['location_id']):None if r['available'] is None else D(r['available']) for r in stock if selected(r)}
        if s.get('mode','orders')=='replenishment':
            horizon=s.get('horizon_date',s.get('end_date','2027-03-31'));date.fromisoformat(horizon)
            if horizon<s['as_of_date']:raise ValueError('HORIZON_BEFORE_ASOF')
            forecasts=[r for r in tables['demand_forecasts'] if r['product_id'] in ids and (not s.get('location_ids') or r['location_id'] in s['location_ids']) and visible(r,s) and s['as_of_date']<day(r['demand_date'])<=horizon and r['view_code']=='planned']
            added=set()
            for f in sorted(forecasts,key=lambda r:(day(r['demand_date']),r['forecast_id'])):
                ev('demand_forecasts',f);pid=f['product_id'];loc=f['location_id'];dd=day(f['demand_date'])
                for e in tables['movements']:
                    lot=lots[e['lot_id']]
                    if e['movement_id'] in added or e['view_code']!='planned' or e['event_type_code'] not in ('receive','produce') or e['destination_location_id']!=loc or lot['product_id']!=pid or not visible(e,s,'recorded_date') or not s['as_of_date']<day(e['event_date'])<=dd:continue
                    added.add(e['movement_id']);ev('movements',e)
                    if e['lot_id'] in recalled or inspections.get(e['lot_id'],{}).get('result_code')!='passed':continue
                    key=(e['lot_id'],loc);pool[key]=pool.get(key,D(0))+D(e['quantity'])*(D(products[pid]['pack_multiplier']) if e['unit'] in ('case','箱') else D(1))
                keys=[key for key in pool if key[1]==loc and lots[key[0]]['product_id']==pid and day(lots[key[0]]['expiry_date'])>=(date.fromisoformat(dd)+timedelta(days=int(D(products[pid]['min_shelf_days'])))).isoformat()]
                unknown=any(pool[k] is None for k in keys);qty=D(f['quantity']);eligible=None if unknown else sum((pool[k] for k in keys),D(0));allocated=None if unknown else min(qty,eligible)
                if not unknown:
                    left=allocated
                    for key in sorted(keys,key=lambda k:(day(lots[k[0]]['expiry_date']),k[0])):
                        take=min(left,pool[key]);pool[key]-=take;left-=take
                shortage=None if unknown else qty-allocated
                rows.append({'forecast_id':f['forecast_id'],'product_id':pid,'location_id':loc,'demand_date':dd,'unit':f['unit'],'demand_quantity':Q(qty),'eligible_supply_quantity':Q(eligible),'allocated_quantity':Q(allocated),'shortage_quantity':Q(shortage),'recommended_quantity':Q(shortage)})
        else:
            orders={r['order_id']:r for r in tables['orders'] if dated(r,s,'order_date') and r['status_code']=='open'}
            demand=[r for r in tables['order_lines'] if r['order_id'] in orders and r['product_id'] in ids and (not s.get('order_ids') or r['order_id'] in s['order_ids']) and (not s.get('location_ids') or orders[r['order_id']]['location_id'] in s['location_ids'])]
            for line in sorted(demand,key=lambda r:(int(D(orders[r['order_id']]['priority'])),day(orders[r['order_id']]['due_date']),r['order_id'],r['line_id'])):
                order=orders[line['order_id']];loc=order['location_id'];pid=line['product_id'];ev('orders',order);ev('order_lines',line)
                own=[r for r in tables['reservations'] if r['line_id']==line['line_id'] and active(r,s)]
                # Restore only usable reserved stock, never recalled or quarantined.
                for res in own:
                    key=(res['lot_id'],loc);sr=next((r for r in stock if (r['lot_id'],r['location_id'])==key),None)
                    if key in pool and pool[key] is not None and sr and not sr['expired'] and D(sr['recall_blocked'])==0 and sr['inspection_status_code']=='passed':pool[key]+=reservation_assigned.get(res['reservation_id'],D(0))
                deadline=(date.fromisoformat(max(s['as_of_date'],day(order['due_date'])))+timedelta(days=int(D(line['min_shelf_days'])))).isoformat()
                keys=[k for k in pool if k[1]==loc and lots[k[0]]['product_id']==pid and day(lots[k[0]]['expiry_date'])>=deadline]
                unknown=any(pool[k] is None for k in keys);left=D(line['quantity']);alloc=[]
                if not unknown:
                    for key in sorted(keys,key=lambda k:(day(lots[k[0]]['expiry_date']),k[0])):
                        take=min(left,pool[key]);pool[key]-=take;left-=take
                        if take:alloc.append({'lot_id':key[0],'quantity':Q(take)})
                rows.append({'line_id':line['line_id'],'order_id':line['order_id'],'product_id':pid,'location_id':loc,'unit':line['unit'],'requested_quantity':Q(line['quantity']),'allocated_quantity':Q(None if unknown else D(line['quantity'])-left),'shortage_quantity':Q(None if unknown else left),'allocation_status_code':'unknown' if unknown else 'full' if left==0 else 'shortage' if left==D(line['quantity']) else 'partial','allocations':alloc})
    # Keep unrelated fixture anomalies out of a bounded question's completeness.
    relevant_lots={r['lot_id'] for r in lots.values() if not ids or r['product_id'] in ids}
    if operation=='recall_assessment' and s.get('recall_id'):relevant_lots=affected if 'affected' in locals() else set()
    issues=[r for r in issues if not r['lot_id'] or r['lot_id'] in relevant_lots]
    serious=[r for r in issues if r['code'] not in ('DUPLICATE_EVENT_IGNORED','OVERRESERVATION')]
    if operation=='recall_assessment':
        for row in rows:
            if row['on_hand'] is None:row['sold']=None;row['returned']=None
    else:
        for row in rows:
            if 'quality_status' in row and row['quality_status']=='unknown':row['sold']=None;row['returned']=None
    def related(r):
        if 'lot_id' in r:return r['lot_id'] in relevant_lots
        if 'parent_lot_id' in r:return r['parent_lot_id'] in relevant_lots or r['child_lot_id'] in relevant_lots
        if 'product_id' in r:return not ids or r['product_id'] in ids
        return True
    safe_evidence={}
    for t,refids in evidence.items():
        pk=contract['object_types'][t]['primary_key'];refs={r[pk] for r in tables[t] if r[pk] in refids and related(r)}
        if refs:safe_evidence[t]=sorted(refs)
    return dict(schema_version=1,capability=operation,scope=s,rows=rows,issues=issues,evidence=safe_evidence,completeness='partial' if serious else 'complete',**extra)
