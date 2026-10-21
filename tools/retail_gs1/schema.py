"""Canonical source schema; generated assets carry exactly these field names."""
TABLES = {
 'organizations': ('organization_id', 'organization_id name role role_code'),
 'locations': ('location_id','location_id name location_type location_type_code organization_id'),
 'products': ('product_id','product_id name category unit pack_multiplier supplier_id min_shelf_days'),
 'lots': ('lot_id','lot_id product_id supplier_id produced_date expiry_date supplier_lot'),
 'movements': ('movement_id','movement_id event_id lot_id event_type event_type_code source_location_id destination_location_id transfer_id order_id quantity unit event_date event_sequence recorded_date view_kind view_code reversal_of'),
 'inspections': ('inspection_id','inspection_id lot_id location_id inspection_date known_date result result_code reason'),
 'holds': ('hold_id','hold_id lot_id location_id quantity return_overlap_quantity effective_from effective_to known_date reason recall_id'),
 'orders': ('order_id','order_id customer_id location_id order_date due_date known_date priority status status_code'),
 'order_lines': ('line_id','line_id order_id product_id quantity unit min_shelf_days'),
 'reservations': ('reservation_id','reservation_id line_id lot_id location_id quantity effective_from effective_to known_date'),
 'demand_forecasts': ('forecast_id','forecast_id product_id location_id demand_date quantity unit known_date view_kind view_code'),
 'recalls': ('recall_id','recall_id root_lot_id announced_date known_date reason status status_code'),
 'lot_links': ('link_id','link_id parent_lot_id child_lot_id link_type link_type_code parent_quantity child_quantity unit effective_date known_date'),
 'inventory_snapshots': ('snapshot_id','snapshot_id product_id lot_id location_id as_of_date knowledge_date unit on_hand in_transit quarantined reserved available'),
 'recall_snapshots': ('snapshot_id','snapshot_id recall_id product_id as_of_date knowledge_date unit controlled_quantity controllable_quantity coverage_ratio'),
}
NUMERIC = set('pack_multiplier min_shelf_days quantity return_overlap_quantity priority event_sequence parent_quantity child_quantity on_hand in_transit quarantined reserved available controlled_quantity controllable_quantity coverage_ratio'.split())
DATES = set('produced_date expiry_date event_date recorded_date inspection_date known_date effective_from effective_to order_date due_date demand_date announced_date effective_date as_of_date knowledge_date'.split())
FKS = {
 'locations': {'organization_id':['organizations','organization_id']},
 'products': {'supplier_id':['organizations','organization_id']},
 'lots': {'product_id':['products','product_id'],'supplier_id':['organizations','organization_id']},
 'movements': {'lot_id':['lots','lot_id'],'source_location_id':['locations','location_id'],'destination_location_id':['locations','location_id'],'order_id':['orders','order_id']},
 'inspections': {'lot_id':['lots','lot_id'],'location_id':['locations','location_id']},
 'holds': {'lot_id':['lots','lot_id'],'location_id':['locations','location_id'],'recall_id':['recalls','recall_id']},
 'orders': {'customer_id':['organizations','organization_id'],'location_id':['locations','location_id']},
 'order_lines': {'order_id':['orders','order_id'],'product_id':['products','product_id']},
 'reservations': {'line_id':['order_lines','line_id'],'lot_id':['lots','lot_id'],'location_id':['locations','location_id']},
 'demand_forecasts': {'product_id':['products','product_id'],'location_id':['locations','location_id']},
 'recalls': {'root_lot_id':['lots','lot_id']},
 'lot_links': {'parent_lot_id':['lots','lot_id'],'child_lot_id':['lots','lot_id']},
 'inventory_snapshots': {'product_id':['products','product_id'],'lot_id':['lots','lot_id'],'location_id':['locations','location_id']},
 'recall_snapshots': {'recall_id':['recalls','recall_id'],'product_id':['products','product_id']},
}
LABELS = {
 'organizations':['Organization','组织'], 'locations':['Business Location','业务地点'], 'products':['Food Product','食品商品'], 'lots':['Product Lot','商品批次'],
 'movements':['Supply Event','供应链事件'],'inspections':['Quality Inspection','质量检验'],'holds':['Stock Hold','库存隔离'], 'orders':['Customer Order','客户订单'],
 'order_lines':['Order Line','订单明细'],'reservations':['Stock Reservation','库存预留'],'demand_forecasts':['Demand Forecast','需求预测'], 'recalls':['Product Recall','商品召回'],
 'lot_links':['Lot Transformation','批次转换'],'inventory_snapshots':['Recorded Inventory','已记录库存'],'recall_snapshots':['Recorded Recall Control','已记录召回控制'],
}
