"""Author the evaluator bank and independent gold; never run during acceptance."""
import argparse, csv, hashlib, json, sqlite3, sys, re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from oracle import Reference, serialize, number, ZERO, day

ROOT=Path(__file__).resolve().parents[2]
DEFAULT='2027-02-28'
DIFFICULTIES=[(6,3,1),(4,4,2),(3,4,3),(3,4,3),(3,4,3),(2,4,4),(2,4,4),(2,4,4),(2,4,4),(3,5,2)]
CASES=[]
def add(en,zh,kind,params,fields,tables,*,a=DEFAULT,k=DEFAULT):
    n=len(CASES);scene=n//10;index=n%10;b,m,h=DIFFICULTIES[scene]
    level='basic' if index<b else 'medium' if index<b+m else 'complex'
    CASES.append(dict(id=f'Q{n+1:03}',scenario_id=f'S{scene+1:02}',difficulty=level,en=en,zh=zh,kind=kind,params=params,fields=fields,tables=tables,as_of_date=a,knowledge_date=k))
def sql(en,zh,query,fields,tables,*,row_order=None,**kw):
    add(en,zh,'sql',{'sql':query},fields,tables,**kw)
    if row_order:CASES[-1]['row_order']=row_order
def inv(en,zh,p,fields,*,locations=None,condition=None,summary=False,a=DEFAULT,k=DEFAULT):
    add(en,zh,'inventory',dict(products=p,locations=locations,condition=condition,summary=summary),fields,['lots','products','movements','inspections','holds','reservations','recalls','lot_links'],a=a,k=k)
def alloc(en,zh,p,fields,*,orders=None,condition=None,summary=False):
    add(en,zh,'allocation',dict(products=p,orders=orders,condition=condition,summary=summary),fields,['orders','order_lines','reservations','movements','lots','products','inspections','holds','recalls','lot_links'])
def plan(en,zh,p,fields,*,condition=None,summary=False,k=DEFAULT,horizon='2027-03-31'):
    add(en,zh,'plan',dict(products=p,condition=condition,summary=summary,horizon=horizon),fields,['demand_forecasts','movements','lots','products','inspections','holds','reservations','recalls','lot_links'],k=k)
def recall(en,zh,r,fields,*,condition=None,summary=False,a=DEFAULT,k=DEFAULT):
    add(en,zh,'recall',dict(recall_id=r,condition=condition,summary=summary),fields,['recalls','lot_links','movements','holds','inspections','reservations','order_lines','orders','lots','products'],a=a,k=k)

# S01: ownership, units and responsibility paths.
sql('What are PRD-001’s name, unit and packaging multiplier?','PRD-001 的名称、基准单位及包装倍率是什么？',"SELECT product_id,name,unit,pack_multiplier FROM products WHERE product_id='PRD-001'",'product_id name unit pack_multiplier'.split(),['products'])
sql('Who supplies PRD-002? Return supplier identity and role.','PRD-002 由谁供货？返回供应商标识、名称及角色代码。',"SELECT p.product_id,o.organization_id,o.name,o.role_code FROM products p JOIN organizations o ON p.supplier_id=o.organization_id WHERE p.product_id='PRD-002'",'product_id organization_id name role_code'.split(),['products','organizations'])
sql('Who owns warehouse WH-001 and what type of location is it?','WH-001 仓库属于哪个组织，地点类型是什么？',"SELECT l.location_id,l.name,l.location_type_code,o.organization_id,o.name AS organization_name FROM locations l JOIN organizations o USING(organization_id) WHERE location_id='WH-001'",'location_id name location_type_code organization_id organization_name'.split(),['locations','organizations'])
sql('What is STORE-002’s operating organization?','STORE-002 由哪个组织运营？',"SELECT l.location_id,l.name,o.organization_id,o.name AS organization_name FROM locations l JOIN organizations o USING(organization_id) WHERE location_id='STORE-002'",'location_id name organization_id organization_name'.split(),['locations','organizations'])
sql('What are LOT-003-A’s product, production date and expiry date?','LOT-003-A 的商品、生产日期和到期日期是什么？',"SELECT lot_id,product_id,produced_date,expiry_date FROM lots WHERE lot_id='LOT-003-A'",'lot_id product_id produced_date expiry_date'.split(),['lots'])
sql('What minimum shelf life is declared for PRD-004?','PRD-004 声明的最小剩余保质期是多少天？',"SELECT product_id,min_shelf_days,unit FROM products WHERE product_id='PRD-004'",'product_id min_shelf_days unit'.split(),['products'])
sql('Convert three cases of each of PRD-001, PRD-002 and PRD-003 to base quantities, keeping products separate.','将 PRD-001、PRD-002、PRD-003 各三箱换算成基准数量，按商品分别返回。',"SELECT product_id,unit,3*CAST(pack_multiplier AS NUMERIC) AS base_quantity FROM products WHERE product_id IN ('PRD-001','PRD-002','PRD-003')",'product_id unit base_quantity'.split(),['products'])
sql('List all lots of PRD-005 with supplier names and expiry dates.','列出 PRD-005 的全部批次、供应商名称及到期日期。',"SELECT l.lot_id,l.product_id,o.name AS supplier_name,l.expiry_date FROM lots l JOIN organizations o ON l.supplier_id=o.organization_id WHERE l.product_id='PRD-005'",'lot_id product_id supplier_name expiry_date'.split(),['lots','organizations'])
sql('Count products assigned to each supplier-role organization; include suppliers with no product and do not count locations as suppliers.','统计每个供应商角色组织负责的商品数，保留零商品供应商，不把地点当作供应商。',"SELECT o.organization_id,o.name,COUNT(p.product_id) AS product_count FROM organizations o LEFT JOIN products p ON p.supplier_id=o.organization_id WHERE o.role_code='supplier' GROUP BY o.organization_id,o.name",'organization_id name product_count'.split(),['organizations','products'])
sql('Audit every lot-to-product-to-supplier path and list only missing or wrongly assigned supplier roles.','审计全部批次→商品→供应商路径，仅列出缺失供应商或角色错误的记录。',"SELECT l.lot_id,l.product_id,l.supplier_id,p.supplier_id AS product_supplier_id,o.role_code FROM lots l LEFT JOIN products p USING(product_id) LEFT JOIN organizations o ON l.supplier_id=o.organization_id WHERE p.product_id IS NULL OR o.organization_id IS NULL OR o.role_code!='supplier'",'lot_id product_id supplier_id product_supplier_id role_code'.split(),['lots','products','organizations'])

# S02: source inspections and usable receipts.
sql('List received actual events for LOT-001-A.','列出 LOT-001-A 的实际收货事件。',"SELECT movement_id,event_id,event_date,destination_location_id,quantity,unit FROM movements WHERE lot_id='LOT-001-A' AND event_type_code='receive' AND view_code='actual' AND event_date<='2027-02-28' AND recorded_date<='2027-02-28'",'movement_id event_id event_date destination_location_id quantity unit'.split(),['movements'])
sql('List inspections of LOT-002-A known by the observation date.','列出观察日已知的 LOT-002-A 检验记录。',"SELECT inspection_id,lot_id,inspection_date,result_code,reason FROM inspections WHERE lot_id='LOT-002-A' AND known_date<='2027-02-28' AND inspection_date<='2027-02-28'",'inspection_id lot_id inspection_date result_code reason'.split(),['inspections'])
inv('For PRD-003 at WH-003, list on-hand quantities and current inspection codes by lot.','按批次列出 WH-003 的 PRD-003 在库数量与当前检验代码。',['PRD-003'],'lot_id location_id on_hand inspection_status_code'.split(),locations=['WH-003'])
sql('List active physical holds for PRD-004 lots at the observation date.','列出观察日 PRD-004 各批次仍有效的实物隔离记录。',"SELECT h.hold_id,h.lot_id,h.location_id,h.quantity,h.reason FROM holds h JOIN lots l USING(lot_id) WHERE l.product_id='PRD-004' AND h.effective_from<='2027-02-28' AND h.effective_to>='2027-02-28' AND h.known_date<='2027-02-28'",'hold_id lot_id location_id quantity reason'.split(),['holds','lots'])
inv('Which PRD-011 lots have failed or pending inspection, and how much is physically quarantined at each location?','PRD-011 哪些批次检验失败或待检？各地点实物隔离量是多少？',['PRD-011'],'lot_id location_id inspection_status_code on_hand quarantined available'.split(),condition='not_passed')
inv('Reconcile on-hand, physical quarantine and available quantities for PRD-006, retaining locations with zero available stock.','勾稽 PRD-006 的在库、实物隔离及可用数量，保留可用量为零的地点。',['PRD-006'],'lot_id location_id on_hand quarantined recall_blocked reserved available'.split())
sql('For LOT-007-A, identify the latest visible inspection and the inspected location; do not use a future-known result.','找出 LOT-007-A 最新可见检验及受检地点，不能使用未来才可知的结果。',"SELECT inspection_id,lot_id,location_id,inspection_date,known_date,result_code FROM inspections WHERE lot_id='LOT-007-A' AND inspection_date<='2027-02-28' AND known_date<='2027-02-28' ORDER BY inspection_date DESC,inspection_id DESC LIMIT 1",'inspection_id lot_id location_id inspection_date known_date result_code'.split(),['inspections'])
inv('Show only PRD-008 lot/location stock rows with returned quantity greater than zero alongside physical quarantine, demonstrating that returns already included in on-hand are not added again.','仅列出 PRD-008 退货量大于零的批次地点库存行，并列示在库及实物隔离量；退货已计入在库不能再加一次。',['PRD-008'],'lot_id location_id on_hand returned quarantined available'.split(),condition='returned')
inv('For PRD-009, separate inspection quarantine, recall block and reservations to explain why received stock cannot all be promised.','对 PRD-009 分开列示检验状态、实物隔离、召回阻断和预留，解释为何不能承诺全部已收货库存。',['PRD-009'],'lot_id location_id inspection_status_code on_hand quarantined recall_blocked reserved available'.split())
inv('For PRD-010, compare inventory known on February 20 with February 28 at the same February 28 business date. Return both knowledge dates and the full stock split.','对 PRD-010 在同一2月28日业务日期下，比较2月20日与2月28日可知的库存，返回两个知识日期及完整数量拆分。',['PRD-010'],'knowledge_date lot_id location_id on_hand quarantined recall_blocked reserved available'.split(),condition='knowledge_compare')

# S03: directed lineage, connected tracing, and transformation constraints.
add('List direct child links of LOT-001-B visible at the observation date.','列出观察日可见的 LOT-001-B 直接下游关联。','links',{'root':'LOT-001-B','mode':'children'},'link_id parent_lot_id child_lot_id link_type_code'.split(),['lot_links'])
add('List direct parents of LOT-002-D visible at the observation date.','列出观察日可见的 LOT-002-D 直接上游批次。','links',{'root':'LOT-002-D','mode':'parents'},'link_id parent_lot_id child_lot_id link_type_code'.split(),['lot_links'])
sql('List PRD-003’s declared lot transformations with input and output quantities; keep each link separate.','列出 PRD-003 的已声明批次转换及输入输出数量，逐关联返回。',"SELECT x.link_id,x.parent_lot_id,x.child_lot_id,x.link_type_code,x.parent_quantity,x.child_quantity,x.unit FROM lot_links x JOIN lots l ON x.parent_lot_id=l.lot_id WHERE l.product_id='PRD-003' AND x.effective_date<='2027-02-28' AND x.known_date<='2027-02-28'",'link_id parent_lot_id child_lot_id link_type_code parent_quantity child_quantity unit'.split(),['lot_links','lots'])
add('Trace the complete connected upstream and downstream component of LOT-004-D, listing each visible link once.','追踪 LOT-004-D 完整的上下游连通批次链，每条可见关联只返回一次。','links',{'root':'LOT-004-D','mode':'connected'},'link_id parent_lot_id child_lot_id link_type_code'.split(),['lot_links'])
add('List all downstream lots reachable from LOT-005-B, including the root, with product IDs and expiry dates.','列出 LOT-005-B 可达的所有下游批次（含根批次）、商品标识及到期日。','closure',{'root':'LOT-005-B'},'lot_id product_id expiry_date'.split(),['lot_links','lots'])
add('For LOT-006-B’s connected component, identify same-product split links whose declared input and output quantities differ.','检查 LOT-006-B 连通批次链，仅列出同商品拆分中声明输入输出数量不一致的关联。','links',{'root':'LOT-006-B','mode':'split_mismatch'},'link_id parent_lot_id child_lot_id parent_quantity child_quantity unit'.split(),['lot_links','lots'])
sql('List the visible actual event journey of LOT-007-B in ascending business-date and numeric event-sequence order (event ID breaks ties), including both sides of transfers. Return null for absent source/destination locations.','按业务日期、数值事件序号升序列出 LOT-007-B 的可见实际流转，事件标识用于同序号排序，保留调拨两端；无来源或目的地点时返回 null。',"SELECT event_id,event_type_code,source_location_id,destination_location_id,event_date,event_sequence,quantity,unit FROM movements WHERE lot_id='LOT-007-B' AND event_date<='2027-02-28' AND recorded_date<='2027-02-28' AND view_code='actual' ORDER BY event_date,CAST(event_sequence AS NUMERIC),event_id",'event_id event_type_code source_location_id destination_location_id event_date event_sequence quantity unit'.split(),['movements'],row_order=['event_date','event_sequence','event_id'])
add('For LOT-047-D, trace the complete upstream and downstream undirected connected component of visible lot links, including different products and sibling branches. List every edge once and do not equate input units with output units.','对 LOT-047-D，沿可见批次关联追踪完整的上下游无向连通分量，包含不同商品和兄弟分支；每条边仅列一次，不能把输入单位直接视作输出单位。','links',{'root':'LOT-047-D','mode':'connected'},'link_id parent_lot_id child_lot_id link_type_code parent_quantity child_quantity unit'.split(),['lot_links'])
add('For recall REC-012, list all affected descendant lots and each product’s supplier; include indirect descendants exactly once.','对 REC-012 列出全部受影响下游批次及商品供应商，间接下游只计一次。','closure',{'root':'LOT-012-B','supplier':True},'lot_id product_id supplier_id expiry_date'.split(),['recalls','lot_links','lots','products'])
add('For LOT-041-B, compare the visible connected links at knowledge cutoffs February 20 and February 28, holding business date February 28 fixed.','固定业务日2月28日，比较 LOT-041-B 在2月20日及2月28日知识截止下的可见连通关联。','links',{'root':'LOT-041-B','mode':'knowledge_compare'},'knowledge_date link_id parent_lot_id child_lot_id link_type_code'.split(),['lot_links'])

# S04: actual balances, transfers and uncertainty.
inv('List PRD-001 inventory by lot and location at February 28.','列出2月28日 PRD-001 按批次地点拆分的库存。',['PRD-001'],'lot_id location_id on_hand in_transit available'.split())
inv('Which PRD-005 lots remain in transit, and toward which destinations?','PRD-005 哪些批次仍在途，目的地点在哪里？',['PRD-005'],'lot_id location_id in_transit'.split(),condition='transit')
inv('List only PRD-003 lot/location rows whose physical quarantine quantity is greater than zero.','仅列出 PRD-003 实物隔离数量大于零的批次地点行。',['PRD-003'],'lot_id location_id quarantined'.split(),condition='quarantined')
add('For PRD-004, query the recorded available-inventory metric and reconcile it with atomic reconstruction at the same dates; report recorded and reconstructed available quantities and their difference by lot/location.','对 PRD-004 查询已记录可用库存指标，并与相同日期的原子事实重算勾稽；按批次地点返回记录值、重算值及差异。','inventory_metric',{'products':['PRD-004']},'snapshot_id lot_id location_id recorded_available reconstructed_available difference'.split(),['inventory_snapshots','products','lots','movements','inspections','holds','reservations','recalls','lot_links'])
inv('Show only PRD-005 stock that is on hand but unavailable, with all blocking quantity categories.','仅列出 PRD-005 已在库但不可用的货，给出全部阻断数量分类。',['PRD-005'],'lot_id location_id on_hand quarantined recall_blocked reserved available'.split(),condition='unavailable')
inv('Compare PRD-006 stock at February 20 and February 28, using knowledge available on each date.','比较 PRD-006 在2月20日和2月28日的库存，分别使用当日已知信息。',['PRD-006'],'as_of_date lot_id location_id on_hand in_transit available'.split(),condition='business_compare')
inv('For PRD-007 at WH-007 and STORE-007, show cumulative sold, returned, on-hand and in-transit quantities without double counting transfer legs.','对 WH-007 与 STORE-007 的 PRD-007，列出累计净售出、退货、在库及在途量，不能重复计算调拨两端。',['PRD-007'],'lot_id location_id on_hand in_transit sold returned'.split(),locations=['WH-007','STORE-007'])
inv('For PRD-045, show stock balances and quality status after an arrival with missing dispatch; preserve unknown values.','对 PRD-045 到货缺少发运记录的情况，列出数量及可信状态，未知必须保留为空。',['PRD-045'],'lot_id location_id on_hand in_transit available quality_status'.split())
inv('For PRD-046, identify unreliable stock rows, keeping null balances rather than converting negative source balances to zero.','找出 PRD-046 不可信的库存行，保留空数量，不能把源负库存改成零。',['PRD-046'],'lot_id location_id on_hand in_transit available quality_status'.split(),condition='unknown')
inv('For PRD-008 and PRD-009, return per-product stock totals while excluding no blocked rows; if any row is unknown, that product total must be null.','对 PRD-008 和 PRD-009 分商品汇总库存，不得跳过受阻行；若任一行未知，该商品合计为空。',['PRD-008','PRD-009'],'product_id unit on_hand in_transit quarantined recall_blocked reserved available'.split(),summary=True)

# S05: expiry and decision eligibility.
inv('Which PRD-010 lots are already expired on February 28?','2月28日 PRD-010 哪些批次已过期？',['PRD-010'],'lot_id location_id expiry_date on_hand expired available'.split(),condition='expired')
inv('Which PRD-011 lots expire within 14 days, including the observation date?','PRD-011 哪些批次在观察日起14天内到期（含当天）？',['PRD-011'],'lot_id location_id expiry_date on_hand near_expiry available'.split(),condition='near_expiry')
sql('What is PRD-012’s shelf-life requirement and each lot’s expiry date?','PRD-012 的剩余保质期要求及各批次到期日是什么？',"SELECT p.product_id,p.min_shelf_days,l.lot_id,l.expiry_date FROM products p JOIN lots l USING(product_id) WHERE p.product_id='PRD-012'",'product_id min_shelf_days lot_id expiry_date'.split(),['products','lots'])
inv('List PRD-013 available lots at WH-013 in FEFO order, after quarantine and reservations.','按FEFO顺序列出 WH-013 的 PRD-013 可用批次，先扣除隔离和预留。',['PRD-013'],'lot_id expiry_date available'.split(),locations=['WH-013'],condition='fefo')
inv('Which PRD-014 near-expiry stock is physically on hand but blocked for another reason?','PRD-014 哪些近效期在库货物还因其他原因不可用？',['PRD-014'],'lot_id location_id expiry_date on_hand quarantined recall_blocked reserved available'.split(),condition='near_blocked')
inv('As of March 10 with knowledge cutoff February 28, report PRD-015 actual stock after expiry; do not credit planned receipts.','截至3月10日、知识截止2月28日，报告 PRD-015 考虑过期后的实际库存，不能计入计划收货。',['PRD-015'],'lot_id location_id expiry_date on_hand expired available'.split(),a='2027-03-10')
inv('For PRD-016, list stock that will satisfy a March 5 shipment with seven remaining shelf days; keep only positive available quantities and use FEFO.','对 PRD-016，列出能满足3月5日发货且仍有7天保质期的批次，只保留正可用量并按FEFO排序。',['PRD-016'],'lot_id location_id expiry_date available'.split(),condition='shelf_2027-03-12')
alloc('For PRD-017 open orders, allocate stock jointly using each line’s actual due date and shelf-life requirement.','对 PRD-017 未结订单，按各行真实交期和保质期要求共享分配库存。',['PRD-017'],'line_id order_id requested_quantity allocated_quantity shortage_quantity allocations allocation_status_code'.split())
plan('For PRD-018, plan March demand after stock expires and exclude planned receipts whose lots do not satisfy shelf life.','对 PRD-018 规划3月需求，考虑库存到期并排除保质期不达标的计划收货。',['PRD-018'],'forecast_id location_id demand_date demand_quantity eligible_supply_quantity allocated_quantity shortage_quantity'.split())
inv('For PRD-049 and PRD-050, list near-expiry available stock by product and location; do not mix units or include actively recalled stock as available, and distinguish a closed recall.','对 PRD-049 与 PRD-050，分商品地点列出近效期可用货量，不混单位，不能将有效召回货算为可用，并区分已关闭召回。',['PRD-049','PRD-050'],'product_id lot_id location_id unit expiry_date available'.split(),condition='near_available')

# S06: shared allocation, own reservations and restrictions.
sql('List open ORD-001-A order lines and their requested quantities and shelf-life requirements.','列出未结 ORD-001-A 的订单行、需求量与保质期要求。',"SELECT l.line_id,l.order_id,l.product_id,l.quantity,l.unit,l.min_shelf_days,o.due_date,o.priority FROM order_lines l JOIN orders o USING(order_id) WHERE o.order_id='ORD-001-A' AND o.status_code='open'",'line_id order_id product_id quantity unit min_shelf_days due_date priority'.split(),['orders','order_lines'])
sql('List reservations for ORD-002-A that are active at the observation date.','列出观察日 ORD-002-A 的有效预留。',"SELECT r.reservation_id,r.line_id,r.lot_id,r.location_id,r.quantity FROM reservations r JOIN order_lines l USING(line_id) WHERE l.order_id='ORD-002-A' AND r.effective_from<='2027-02-28' AND r.effective_to>='2027-02-28' AND r.known_date<='2027-02-28'",'reservation_id line_id lot_id location_id quantity'.split(),['reservations','order_lines'])
alloc('Can ORD-003-A be filled? Respect its own reservations, other orders’ reservations, expiry and quality.','ORD-003-A 能否足量履约？考虑自身及其他订单预留、效期和质量约束。',['PRD-003'],'line_id requested_quantity allocated_quantity shortage_quantity allocation_status_code allocations'.split(),orders=['ORD-003-A'])
alloc('Jointly allocate PRD-004’s two competing orders; report exact lot allocations.','共享分配 PRD-004 的两个竞争订单，给出准确批次分配。',['PRD-004'],'line_id order_id allocated_quantity shortage_quantity allocations'.split())
alloc('Which PRD-005 open order lines have a shortage after FEFO allocation?','PRD-005 未结订单行在FEFO分配后哪些仍有缺口？',['PRD-005'],'line_id order_id requested_quantity allocated_quantity shortage_quantity'.split(),condition='shortage')
alloc('Allocate PRD-049’s open backlog, including overdue ORD-049-A. Do not silently discard the overdue order; assess shelf life at the later of today and its due date.','分配 PRD-049 未结积压订单，必须包含逾期 ORD-049-A；不能静默忽略逾期订单，保质期基准使用观察日和交期中较晚者。',['PRD-049'],'line_id order_id allocated_quantity shortage_quantity allocations allocation_status_code'.split())
alloc('For PRD-007, allocate all competing lines jointly and reconcile total demand, allocation and shortage without spending stock twice.','对 PRD-007 全部竞争订单联合分配，并勾稽总需求、分配与缺口，库存不能用两次。',['PRD-007'],'product_id requested_quantity allocated_quantity shortage_quantity'.split(),summary=True)
alloc('If only ORD-008-B is investigated, keep excluded orders’ reservations unavailable and allocate B using its own reservation exactly once.','若只调查 ORD-008-B，应保留被排除订单的预留占用，并只释放一次B自身预留后分配。',['PRD-008'],'line_id requested_quantity allocated_quantity shortage_quantity allocations'.split(),orders=['ORD-008-B'])
alloc('For PRD-043, report allocation uncertainty caused by conflicting source events instead of promising zero or invented stock.','对 PRD-043，报告冲突源事件造成的分配不确定性，不能承诺零库存或编造货量。',['PRD-043'],'line_id requested_quantity allocated_quantity shortage_quantity allocation_status_code allocations'.split())
alloc('Allocate PRD-009 and PRD-010 independently by product but jointly across each product’s orders, respecting recall, quality, due dates and FEFO.','对 PRD-009 与 PRD-010 分商品、同商品跨订单共享分配，满足召回、质量、交期和FEFO约束。',['PRD-009','PRD-010'],'product_id line_id order_id requested_quantity allocated_quantity shortage_quantity allocations allocation_status_code'.split())

# S07: forecasts/plans are bounded, observed stock remains actual.
sql('List March planned forecasts for PRD-001 known by February 28.','列出2月28日前已知的 PRD-001 三月计划需求。',"SELECT forecast_id,product_id,location_id,demand_date,quantity,unit,known_date FROM demand_forecasts WHERE product_id='PRD-001' AND demand_date>'2027-02-28' AND demand_date<='2027-03-31' AND known_date<='2027-02-28' AND view_code='planned'",'forecast_id product_id location_id demand_date quantity unit known_date'.split(),['demand_forecasts'])
sql('List PRD-002’s planned incoming receipts known at February 28 through March 31.','列出2月28日已知且截至3月31日的 PRD-002 计划入库。',"SELECT m.event_id,m.lot_id,m.destination_location_id,m.event_date,m.quantity,m.unit FROM movements m JOIN lots l USING(lot_id) WHERE l.product_id='PRD-002' AND m.view_code='planned' AND m.event_type_code IN ('receive','produce') AND m.recorded_date<='2027-02-28' AND m.event_date>'2027-02-28' AND m.event_date<='2027-03-31'",'event_id lot_id destination_location_id event_date quantity unit'.split(),['movements','lots'])
plan('Plan PRD-003’s March replenishment: show each forecast, eligible supply, allocation, shortage and recommended quantity.','规划 PRD-003 三月补货，逐预测列示合格供给、分配、缺口及建议量。',['PRD-003'],'forecast_id product_id location_id demand_date demand_quantity eligible_supply_quantity allocated_quantity shortage_quantity recommended_quantity'.split())
plan('Which PRD-004 March forecasts have shortages after qualified planned receipts?','计入合格计划收货后，PRD-004 哪些三月预测仍短缺？',['PRD-004'],'forecast_id demand_date demand_quantity allocated_quantity shortage_quantity recommended_quantity'.split(),condition='shortage')
plan('Plan PRD-005 only through March 15; exclude later demand and receipts not yet eligible by each demand date.','仅规划 PRD-005 到3月15日，排除更晚需求，以及需求日尚未合格的收货。',['PRD-005'],'forecast_id demand_date eligible_supply_quantity allocated_quantity shortage_quantity'.split(),horizon='2027-03-15')
plan('Summarize PRD-006 March demand and replenishment need by product, preserving an unknown total if any forecast allocation is unknown.','分商品汇总 PRD-006 三月需求和补货缺口，任一预测分配未知时合计保持为空。',['PRD-006'],'product_id demand_quantity allocated_quantity shortage_quantity recommended_quantity'.split(),summary=True)
plan('For PRD-007, use stock once across sequential March forecasts, age each lot and apply supply before the day’s demand.','对 PRD-007，按顺序在三月各次预测间共享库存，逐批考虑效期，并先处理当日供给再分配当日需求。',['PRD-007'],'forecast_id demand_date demand_quantity eligible_supply_quantity allocated_quantity shortage_quantity'.split())
plan('For PRD-008 and PRD-009, report March plans separately by product/location, including recall or inspection exclusions.','对 PRD-008 和 PRD-009，分商品地点报告三月计划，考虑召回及检验不合格排除。',['PRD-008','PRD-009'],'product_id location_id forecast_id demand_date eligible_supply_quantity allocated_quantity shortage_quantity recommended_quantity'.split())
add('For PRD-007, compare the March plan at knowledge cutoffs February 28 and March 5, holding the February 28 business date fixed; show how later-known planned supply changes shortages.','对 PRD-007 固定业务日2月28日，比较知识截止2月28日及3月5日的三月计划，展示稍后可知的计划供给如何改变缺口。','plan_compare',{'products':['PRD-007'],'cutoffs':['2027-02-28','2027-03-05']},'knowledge_date forecast_id demand_date eligible_supply_quantity allocated_quantity shortage_quantity recommended_quantity'.split(),['demand_forecasts','movements','products','lots','inspections','holds','reservations','recalls','lot_links'],k='2027-03-05')
plan('For PRD-045, preserve unknown March recommendations when opening stock is unreliable; do not silently use zero opening stock.','对 PRD-045，期初库存不可信时三月建议应保持未知，不能静默以零期初量规划。',['PRD-045'],'forecast_id demand_date demand_quantity eligible_supply_quantity allocated_quantity shortage_quantity recommended_quantity'.split())

# S08: recall reach, location disposition and customer impact.
sql('What is REC-001’s root lot, announcement date, reason and status?','REC-001 的根批次、公告日期、原因和状态是什么？',"SELECT recall_id,root_lot_id,announced_date,reason,status_code FROM recalls WHERE recall_id='REC-001'",'recall_id root_lot_id announced_date reason status_code'.split(),['recalls'])
add('List affected lots of REC-002, including descendants and each lot’s product.','列出 REC-002 含下游的受影响批次及各批次商品。','closure',{'root':'LOT-002-B'},'lot_id product_id expiry_date'.split(),['recalls','lot_links','lots'])
recall('For REC-003, show affected stock and in-transit quantities by product and location.','对 REC-003，分商品地点列出受影响在库和在途数量。','REC-003','recall_id product_id location_id affected_lot_ids on_hand in_transit'.split())
recall('For REC-004, list net sold and returned affected quantities separately at each location.','对 REC-004，按地点分别列出受影响净售出量和退货量。','REC-004','product_id location_id sold returned'.split())
recall('Which locations have affected stock still in transit under REC-005?','REC-005 哪些目的地点仍有受影响在途货？','REC-005','product_id location_id affected_lot_ids in_transit'.split(),condition='transit')
recall('List customer order IDs affected by REC-006, including fulfilled sales and open reservations of affected lots.','列出 REC-006 影响的订单标识，包含已售订单及受影响批次的未结预留订单。','REC-006','product_id location_id affected_order_ids'.split())
recall('For REC-007, reconcile physical stock, transit, net sold and returns without counting returned quantities twice.','对 REC-007 勾稽实物在库、在途、净售出与退货，退货不能重复加总。','REC-007','product_id location_id on_hand in_transit sold returned controllable_quantity'.split())
recall('For REC-048, retain different products in separate rows while following every downstream conversion; list affected lots and order IDs.','对 REC-048 沿全部下游转换追踪，不同商品分行，列出受影响批次和订单标识。','REC-048','product_id location_id unit affected_lot_ids affected_order_ids on_hand in_transit'.split())
recall('For REC-043, show affected lots and control coverage; do not invalidate descendants merely because a non-descendant sibling lot has a conflicting event.','对 REC-043，列出受影响批次及控制覆盖率；不能因不属于下游的同商品兄弟批次有冲突事件，就把受影响范围也判为未知。','REC-043','product_id location_id affected_lot_ids on_hand in_transit controllable_quantity coverage_ratio'.split())
recall('Assess REC-010 as of February 28 using only knowledge available February 20; do not assume a later recall announcement was already known.','截至2月28日仅使用2月20日可知信息评估 REC-010，不能假定稍后召回公告当时已知。','REC-010','recall_id product_id location_id on_hand in_transit sold returned'.split(),k='2027-02-20')

# S09: controlled stock, action gap, coverage and order consequences.
recall('For REC-011, report physically controlled quantities by product and location.','对 REC-011，分商品地点列出已实物控制数量。','REC-011','product_id location_id controlled_quantity'.split())
recall('For REC-012, report the remaining control gap at each location.','对 REC-012，列出各地点尚待控制的数量缺口。','REC-012','product_id location_id pending_control_quantity'.split())
recall('For REC-013, compute control coverage using on-hand plus transit as the denominator, excluding unreturned sales.','对 REC-013，以在库加在途为分母计算控制覆盖率，排除尚未退回的已售货物。','REC-013','product_id location_id controlled_quantity controllable_quantity coverage_ratio'.split())
recall('Which REC-014 locations still require control action? Include in-transit quantities, which are not controlled merely because a recall exists.','REC-014 哪些地点仍需控制行动？计入在途量，不能因已发召回就视为在途已受控。','REC-014','product_id location_id on_hand in_transit controlled_quantity pending_control_quantity'.split(),condition='pending_control')
recall('REC-050 is closed. Does it still produce an active recall assessment? Return the active assessment rows only; do not fabricate a new open recall.','REC-050 已关闭。是否仍应产生有效召回评估？仅返回有效评估行，不能编造新的未结召回。','REC-050','product_id location_id controllable_quantity controlled_quantity coverage_ratio'.split())
recall('For REC-016, show how returned quantities are included in stock and physical control without adding them twice to the coverage denominator.','对 REC-016，列示退货如何计入在库及实物控制，覆盖率分母不能再加一次退货。','REC-016','product_id location_id returned on_hand in_transit controlled_quantity controllable_quantity coverage_ratio'.split())
add('For REC-017, query the recorded control-coverage metric, then independently aggregate physical control and controllable quantities across locations; compare the product-level recorded and reconstructed ratios, never averaging location percentages.','对 REC-017 查询已记录控制覆盖率指标，再跨地点独立汇总实物控制量和可控制量；比较商品级记录与重算比例，不能平均地点百分比。','recall_metric',{'recall_id':'REC-017'},'snapshot_id product_id unit controlled_quantity controllable_quantity recorded_ratio reconstructed_ratio difference'.split(),['recall_snapshots','recalls','lot_links','movements','holds','inspections','reservations','orders','order_lines','lots','products'])
alloc('After active recall restrictions, jointly plan PRD-018’s open order lines and show shortages and source allocations.','考虑有效召回限制后，对 PRD-018 未结订单联合分配，列示缺口及来源批次。',['PRD-018'],'line_id order_id requested_quantity allocated_quantity shortage_quantity allocations'.split())
recall('For REC-045, preserve unknown control gaps and ratios when transfer provenance is incomplete; do not label unknown stock fully controlled.','对 REC-045，调拨来源不完整时控制缺口和比例保持未知，不能把未知货量判为已完全控制。','REC-045','product_id location_id on_hand in_transit controlled_quantity controllable_quantity pending_control_quantity coverage_ratio'.split())
recall('For REC-020, separate each location’s controlled stock, in-transit exposure, net sold and pending action; retain affected orders to support action planning.','对 REC-020，分地点列出已控制货、在途敞口、净售出和待控制缺口，并保留影响订单便于处置。','REC-020','product_id location_id affected_order_ids controlled_quantity in_transit sold pending_control_quantity coverage_ratio'.split())

# S10: fault-sensitive controls and bitemporal evidence.
add('List exact-duplicate semantic event IDs and their physical row counts, without counting them as distinct business events.','列出完全重复的语义事件标识及其物理行数，不能视作不同业务事件。','event_audit',{'mode':'duplicates'},'event_id physical_row_count payload_variant_count'.split(),['movements'])
add('List visible reversal events with their target event IDs.','列出可见撤销事件及其目标事件标识。','event_audit',{'mode':'reversals'},'event_id reversal_of event_date recorded_date'.split(),['movements'])
add('List actual events whose business date is no later than February 28 but which were recorded after February 28 and by March 5.','列出业务日期不晚于2月28日、但2月28日后且3月5日前才记录的实际事件。','event_audit',{'mode':'late'},'event_id lot_id event_date recorded_date'.split(),['movements'],k='2027-03-05')
inv('For PRD-042, reconstruct inventory after deduplicating events and return the actual quantities by lot/location.','对 PRD-042，事件去重后重建库存，按批次地点返回实际数量。',['PRD-042'],'lot_id location_id on_hand sold returned available'.split())
inv('For PRD-044, reconstruct inventory after the visible reversal cancels its target, rather than adding the reversal as a new quantity movement.','对 PRD-044，撤销目标事件后重建库存，不能把撤销当作新的数量流转相加。',['PRD-044'],'lot_id location_id on_hand sold returned available'.split())
inv('For PRD-041, compare February 28 balances at knowledge cutoffs February 28 and March 5 to isolate late reporting.','对 PRD-041 固定2月28日业务日期，比较知识截止2月28日和3月5日的库存以识别迟报影响。',['PRD-041'],'knowledge_date lot_id location_id on_hand sold available'.split(),condition='late_compare',k='2027-03-05')
add('List conflicting semantic event IDs and all their payload variant counts, separately from identical duplicates.','列出冲突语义事件及业务载荷变体数，不能和完全相同的重复混淆。','event_audit',{'mode':'conflicts'},'event_id physical_row_count payload_variant_count'.split(),['movements'])
inv('For PRD-043, list only inventory rows rendered unreliable by conflicting event payloads and preserve null quantitative fields.','对 PRD-043，仅列出因事件载荷冲突而不可信的库存行，数量字段保留为空。',['PRD-043'],'lot_id location_id on_hand available quality_status'.split(),condition='unknown')
inv('For PRD-045 and PRD-046, contrast missing-transfer provenance with negative source inventory; report every affected lot/location and unknown balances without dropping either product.','对比 PRD-045 的调拨来源缺失与 PRD-046 的源负库存，列出全部受影响批次地点及未知数量，不得漏掉任一商品。',['PRD-045','PRD-046'],'product_id lot_id location_id on_hand in_transit available quality_status'.split(),condition='unknown')
add('Audit all source tables for missing foreign keys, invalid units and same-day event sequence ties; report defect type and record ID, without treating declared duplicate event IDs as duplicate physical primary keys.','审计全部源表的外键缺失、单位不合法和同日事件序号冲突，返回缺陷类型与记录标识；语义事件重复不能误判成物理主键重复。','integrity',{},'defect_type table record_id field'.split(),['organizations','locations','products','lots','movements','orders','order_lines','lot_links'])

def load_sql(tables):
    con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
    for table,rows in tables.items():
        if not rows:continue
        columns=list(rows[0]);con.execute('CREATE TABLE "'+table+'" ('+','.join('"'+x+'" TEXT' for x in columns)+')')
        con.executemany('INSERT INTO "'+table+'" VALUES ('+','.join('?' for _ in columns)+')',[[r[x] for x in columns] for r in rows])
    return con
def keep(row,cond):
    if cond in (None,'knowledge_compare','business_compare','late_compare'):return True
    if cond=='not_passed':return row['inspection_status_code']!='passed'
    if cond=='returned':return row.get('returned') is not None and row['returned']>0
    if cond=='transit':return row.get('in_transit') is not None and row['in_transit']>0
    if cond=='quarantined':return row.get('quarantined') is not None and row['quarantined']>0
    if cond=='unavailable':return row.get('on_hand') is not None and row['on_hand']>0 and row['available']==0
    if cond=='unknown':return row.get('quality_status')=='unknown'
    if cond=='expired':return row['expired']
    if cond=='near_expiry':return row['near_expiry']
    if cond=='near_blocked':return row['near_expiry'] and row['on_hand'] is not None and row['on_hand']>0 and row['available']==0
    if cond in ('fefo','near_available'):return row['available'] is not None and row['available']>0 and (cond!='near_available' or row['near_expiry'])
    if cond.startswith('shelf_'):return row['available'] is not None and row['available']>0 and row['expiry_date']>=cond[6:]
    if cond=='shortage':return row.get('shortage_quantity') is not None and row['shortage_quantity']>0
    if cond=='full':return row['allocation_status_code']=='full'
    if cond=='pending_control':return row['pending_control_quantity'] is not None and row['pending_control_quantity']>0
    raise ValueError(cond)
def summarize(rows,kind):
    groups={}
    for r in rows:groups.setdefault(r['product_id'],[]).append(r)
    result=[]
    for product,rs in sorted(groups.items()):
        keys={'inventory':['on_hand','in_transit','quarantined','recall_blocked','reserved','available'],'allocation':['requested_quantity','allocated_quantity','shortage_quantity'],'plan':['demand_quantity','allocated_quantity','shortage_quantity','recommended_quantity'],'recall':['controlled_quantity','controllable_quantity','pending_control_quantity']}[kind]
        row={'product_id':product,'unit':rs[0].get('unit')}
        for field in keys:row[field]=None if any(r[field] is None for r in rs) else sum((r[field] for r in rs),ZERO)
        if kind=='recall':row['coverage_ratio']=None if row['controllable_quantity'] is None or row['controllable_quantity']<=0 else row['controlled_quantity']/row['controllable_quantity']
        result.append(row)
    return result

def resolve(ref,con,c):
    p=c['params'];a=c['as_of_date'];k=c['knowledge_date'];kind=c['kind']
    if kind=='sql':rows=[dict(r) for r in con.execute(p['sql'])]
    elif kind=='inventory':
        rows=[];dates=[(a,k)]
        if p['condition']=='knowledge_compare':dates=[(a,'2027-02-20'),(a,'2027-02-28')]
        if p['condition']=='late_compare':dates=[(a,'2027-02-28'),(a,'2027-03-05')]
        if p['condition']=='business_compare':dates=[('2027-02-20','2027-02-20'),('2027-02-28','2027-02-28')]
        for aa,kk in dates:
            inv=ref.inventory(aa,kk)[0]
            rows.extend(dict(r,as_of_date=aa,knowledge_date=kk) for r in inv if r['product_id'] in p['products'] and (not p['locations'] or r['location_id'] in p['locations']) and keep(r,p['condition']))
        if p['summary']:rows=summarize(rows,kind)
    elif kind=='allocation':
        rows=[r for r in ref.allocation(p['products'],a,k,p['orders']) if keep(r,p['condition'])]
        if p['summary']:rows=summarize(rows,kind)
    elif kind=='plan':
        rows=[r for r in ref.plan(p['products'],a,k,p['horizon']) if keep(r,p['condition'])]
        if p['summary']:rows=summarize(rows,kind)
    elif kind=='plan_compare':
        rows=[dict(r,knowledge_date=kk) for kk in p['cutoffs'] for r in ref.plan(p['products'],a,kk)]
    elif kind=='inventory_metric':
        reconstructed={(r['lot_id'],r['location_id']):r for r in ref.inventory(a,k)[0]}
        rows=[]
        for s in ref.tables['inventory_snapshots']:
            if s['product_id'] not in p['products'] or s['as_of_date']!=a or s['knowledge_date']!=k:continue
            value=reconstructed[(s['lot_id'],s['location_id'])]['available'];recorded=None if s['available']=='' else number(s['available'])
            rows.append({'snapshot_id':s['snapshot_id'],'lot_id':s['lot_id'],'location_id':s['location_id'],'recorded_available':recorded,'reconstructed_available':value,'difference':None if recorded is None or value is None else value-recorded})
    elif kind=='recall_metric':
        reconstructed={r['product_id']:r for r in summarize(ref.recall(p['recall_id'],a,k),'recall')};rows=[]
        for s in ref.tables['recall_snapshots']:
            if s['recall_id']!=p['recall_id'] or s['as_of_date']!=a or s['knowledge_date']!=k:continue
            value=reconstructed[s['product_id']];ratio=value['coverage_ratio'];recorded=None if s['coverage_ratio']=='' else number(s['coverage_ratio'])
            # Both ratios compared at declared six-decimal display precision.
            ratio=None if ratio is None else number(serialize(ratio))
            rows.append({'snapshot_id':s['snapshot_id'],'product_id':s['product_id'],'unit':s['unit'],'controlled_quantity':value['controlled_quantity'],'controllable_quantity':value['controllable_quantity'],'recorded_ratio':recorded,'reconstructed_ratio':ratio,'difference':None if recorded is None or ratio is None else ratio-recorded})
    elif kind=='recall':
        rows=[r for r in ref.recall(p['recall_id'],a,k) if keep(r,p['condition'])]
        if p['summary']:rows=summarize(rows,kind)
    elif kind in ('links','closure'):
        root=p['root'];mode=p.get('mode');rows=[]
        if kind=='closure':rows=[r for lid,r in sorted(ref.lots.items()) if lid in ref.closure(root,a,k)]
        else:
            for kk in (['2027-02-20','2027-02-28'] if mode=='knowledge_compare' else [k]):
                component=ref.closure(root,a,kk,both=True)
                for r in ref.links(a,kk):
                    if mode=='children' and r['parent_lot_id']!=root:continue
                    if mode=='parents' and r['child_lot_id']!=root:continue
                    if mode not in ('children','parents') and not(r['parent_lot_id'] in component and r['child_lot_id'] in component):continue
                    if mode=='split_mismatch' and not(r['link_type_code']=='split' and ref.lots[r['parent_lot_id']]['product_id']==ref.lots[r['child_lot_id']]['product_id'] and number(r['parent_quantity'])!=number(r['child_quantity'])):continue
                    rows.append(dict(r,knowledge_date=kk))
    elif kind=='event_audit':
        events=[r for r in ref.tables['movements'] if r['view_code']=='actual' and r['event_date']<=a and r['recorded_date']<=k];mode=p['mode']
        if mode=='reversals':rows=[r for r in events if r['event_type_code']=='reversal']
        elif mode=='late':rows=[r for r in events if r['event_date']<='2027-02-28'<r['recorded_date']]
        else:
            groups={}
            for r in events:groups.setdefault(r['event_id'],[]).append(r)
            rows=[]
            for eid,rs in groups.items():
                variants={tuple((key,value) for key,value in sorted(r.items()) if key not in ('movement_id','recorded_date')) for r in rs}
                if (mode=='duplicates' and len(rs)>1 and len(variants)==1) or (mode=='conflicts' and len(variants)>1):rows.append({'event_id':eid,'physical_row_count':len(rs),'payload_variant_count':len(variants)})
    elif kind=='integrity':
        schema=json.loads((ROOT/'tools/retail_gs1/schema-contract.json').read_text());rows=[]
        for table,s in schema['object_types'].items():
            for field,(target,pk) in s['foreign_keys'].items():
                ids={r[pk] for r in ref.tables[target]}
                for r in ref.tables[table]:
                    if r[field] and r[field] not in ids:rows.append({'defect_type':'missing_foreign_key','table':table,'record_id':r[s['primary_key']],'field':field})
        for r in ref.tables['movements']:
            if r['unit'] not in ('ea','件','case','箱'):rows.append({'defect_type':'invalid_unit','table':'movements','record_id':r['movement_id'],'field':'unit'})
        groups={}
        ev=ref.visible_events(a,k)[0]
        for r in ev:groups.setdefault((r['lot_id'],r['event_date'],r['event_sequence']),[]).append(r)
        for rs in groups.values():
            if len(rs)>1:
                for r in rs:rows.append({'defect_type':'event_sequence_tie','table':'movements','record_id':r['movement_id'],'field':'event_sequence'})
    else:raise ValueError(kind)
    rows=[{f:r[f] for f in c['fields']} for r in rows]
    # Numeric CSV source fields are strings; retain exact lexical values, grader uses Decimal.
    rows=serialize(rows)
    # Optional/unknown source values have one public representation: JSON null.
    rows=[{field:None if value=='' else value for field,value in row.items()} for row in rows]
    if c.get('row_order'):
        from grade import sort_key
        rows.sort(key=lambda row:sort_key(row,c['row_order']))
    else:rows.sort(key=lambda r:json.dumps(r,ensure_ascii=False,sort_keys=True))
    return rows

def schema_for(rows,fields):
    props={}
    for field in fields:
        values=[r[field] for r in rows if r[field] is not None]
        if values and isinstance(values[0],list):
            props[field]={'type':'array'}
        elif values and isinstance(values[0],bool):props[field]={'type':'boolean'}
        elif field.endswith('_quantity') or field in ('quantity','on_hand','in_transit','sold','returned','quarantined','recall_blocked','reserved','available','pack_multiplier','min_shelf_days','priority','event_sequence','coverage_ratio','physical_row_count','payload_variant_count','product_count','recorded_available','reconstructed_available','recorded_ratio','reconstructed_ratio','difference'):
            props[field]={'type':['string','number','null'],'x-comparison':'decimal_exact'}
        else:props[field]={'type':['string','null']}
    return {'type':'object','required':['rows'],'properties':{'rows':{'type':'array','items':{'type':'object','required':fields,'additionalProperties':False,'properties':props}}}}

def source_evidence(ref,c):
    """Source scope includes records excluded by the business constraints as evidence.

    This is a provenance index, not a hidden answer or a minimal proof guarantee.
    """
    serialized=json.dumps(c['params']);products=set(re.findall(r'PRD-\d{3}',serialized));lots=set(re.findall(r'LOT-\d{3}-[A-Z]',serialized));orders=set(re.findall(r'ORD-\d{3}-[A-Z]',serialized))
    if c['kind']=='links' and c['params'].get('mode') in ('connected','knowledge_compare','split_mismatch'):
        lots|=ref.closure(c['params']['root'],c['as_of_date'],c['knowledge_date'],both=True)
    if c['params'].get('recall_id'):
        recall=next(r for r in ref.tables['recalls'] if r['recall_id']==c['params']['recall_id']);lots|=ref.closure(recall['root_lot_id'],c['as_of_date'],c['knowledge_date'])
    for lot in list(lots):products.add(ref.lots[lot]['product_id'])
    for r in ref.tables['order_lines']:
        if r['order_id'] in orders:products.add(r['product_id'])
    lots|={lid for lid,row in ref.lots.items() if row['product_id'] in products}
    orders|={r['order_id'] for r in ref.tables['order_lines'] if r['product_id'] in products}
    schema=json.loads((ROOT/'tools/retail_gs1/schema-contract.json').read_text());out={}
    scoped=bool(products or lots or orders)
    for table in c['tables']:
        selected=[];pk=schema['object_types'][table]['primary_key']
        for r in ref.tables[table]:
            applicable=not scoped or table in ('organizations','locations')
            applicable|=r.get('product_id') in products or r.get('lot_id') in lots or r.get('order_id') in orders or r.get('root_lot_id') in lots or r.get('parent_lot_id') in lots or r.get('child_lot_id') in lots
            if r.get('line_id') in ref.lines:applicable|=ref.lines[r['line_id']]['product_id'] in products
            if applicable:selected.append(r[pk])
        out[table]=sorted(set(selected))
    return out

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');parser.add_argument('--revision-after-formal',action='store_true',help='Preserve original freeze.json and mark current revision untested; never rescore old runs');args=parser.parse_args()
    if len(CASES)!=100:raise ValueError(f'Expected100, got{len(CASES)}')
    if Counter(c['difficulty'] for c in CASES)!=Counter(basic=30,medium=40,complex=30):raise ValueError('difficulty split')
    for lang in ['en-us','zh-cn']:
        sample=ROOT/'samples'/('retail-gs1-'+lang);ref=Reference(sample/'data');con=load_sql(ref.tables)
        public=[];gold={};recipes={};readable=['# Independent reference answers','', 'Evaluator material. Never supplied to formal answerers or installed runtime.','']
        for c in CASES:
            rows=resolve(ref,con,c);contract=schema_for(rows,c['fields']);fields=', '.join(c['fields'])
            if c.get('row_order'):contract['properties']['rows']['x-order-by']=c['row_order']
            question=c['zh' if lang=='zh-cn' else 'en']
            suffix=(f" 默认业务日期 {c['as_of_date']}、知识截止 {c['knowledge_date']}；除非题目明确比较日期，均按此范围。返回完整 rows，字段：{fields}。数量与比例用十进制字符串；未知用 null，不能用0替代。" if lang=='zh-cn' else f" Use business date {c['as_of_date']} and knowledge cutoff {c['knowledge_date']} unless comparing dates explicitly. Return all rows with fields: {fields}. Decimal strings for quantities/ratios; unknown is null, never zero.")
            q={k:c[k] for k in ['id','scenario_id','difficulty','as_of_date','knowledge_date']};q.update(question=question+suffix,output_contract=contract)
            public.append(q);gold[c['id']]={'rows':rows,'evidence_tables':c['tables'],'source_evidence':source_evidence(ref,c),'evidence_scope':'Source records in the requested business scope, including excluded rows needed to verify boundaries; not a minimal proof.','oracle':'independent_source_rules','row_count':len(rows)};recipes[c['id']]={k:v for k,v in c.items() if k not in ['en','zh']}
            readable.extend([f"## {c['id']} · {c['scenario_id']} · {c['difficulty']}",'',question,'','```json',json.dumps({'rows':rows},ensure_ascii=False,indent=2),'```',''])
        coverage={'questions':100,'difficulty':dict(Counter(c['difficulty'] for c in CASES)),'scenarios':{f'S{i:02}':{'count':10,'question_ids':[c['id'] for c in CASES if c['scenario_id']==f'S{i:02}']} for i in range(1,11)},'empty_answer_questions':[qid for qid,g in gold.items() if not g['rows']],'formal_agent_rounds_executed':0,'oracle_implementation':'tools/retail_eval/oracle.py; no production imports','all_expected_rows':sum(g['row_count'] for g in gold.values())}
        if args.write:
            out=sample/'bkn-eval';out.mkdir(parents=True,exist_ok=True)
            for name,obj in [('questions.json',public),('response-contracts.json',{q['id']:q['output_contract'] for q in public}),('expected-results.json',gold),('oracle-recipes.json',recipes),('coverage.json',coverage)]:
                (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
            (out/'answers.md').write_text('\n'.join(readable)+'\n')
            if not args.revision_after_formal:
                hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob('*.json') if f.name!='freeze.json'}
                (out/'freeze.json').write_text(json.dumps({'files':hashes,'formal_agent_rounds_executed':0},indent=2)+'\n')
        print(json.dumps({'language':lang,**coverage},ensure_ascii=False))
if __name__=='__main__':main()
