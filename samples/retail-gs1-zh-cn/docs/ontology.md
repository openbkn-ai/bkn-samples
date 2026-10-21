# 食品供应链追溯与召回 BKN

完整属性定义见kn/object_types；外键从源属性连到目标主键，空值不产生边。标准映射见standard-sources.md，本地扩展不声称GS1等价。

| Object | Name | Primary key |
|---|---|---|
| organizations | 组织 | organization_id |
| locations | 业务地点 | location_id |
| products | 食品商品 | product_id |
| lots | 商品批次 | lot_id |
| movements | 供应链事件 | movement_id |
| inspections | 质量检验 | inspection_id |
| holds | 库存隔离 | hold_id |
| orders | 客户订单 | order_id |
| order_lines | 订单明细 | line_id |
| reservations | 库存预留 | reservation_id |
| demand_forecasts | 需求预测 | forecast_id |
| recalls | 商品召回 | recall_id |
| lot_links | 批次转换 | link_id |
| inventory_snapshots | 已记录库存 | snapshot_id |
| recall_snapshots | 已记录召回控制 | snapshot_id |

| Relation | Source | Target | Join |
|---|---|---|---|
| locations_by_organization_id | locations | organizations | organization_id = organization_id |
| products_by_supplier_id | products | organizations | supplier_id = organization_id |
| lots_by_product_id | lots | products | product_id = product_id |
| lots_by_supplier_id | lots | organizations | supplier_id = organization_id |
| movements_by_lot_id | movements | lots | lot_id = lot_id |
| movements_by_source_location_id | movements | locations | source_location_id = location_id |
| movements_by_destination_location_id | movements | locations | destination_location_id = location_id |
| movements_by_order_id | movements | orders | order_id = order_id |
| inspections_by_lot_id | inspections | lots | lot_id = lot_id |
| inspections_by_location_id | inspections | locations | location_id = location_id |
| holds_by_lot_id | holds | lots | lot_id = lot_id |
| holds_by_location_id | holds | locations | location_id = location_id |
| holds_by_recall_id | holds | recalls | recall_id = recall_id |
| orders_by_customer_id | orders | organizations | customer_id = organization_id |
| orders_by_location_id | orders | locations | location_id = location_id |
| order_lines_by_order_id | order_lines | orders | order_id = order_id |
| order_lines_by_product_id | order_lines | products | product_id = product_id |
| reservations_by_line_id | reservations | order_lines | line_id = line_id |
| reservations_by_lot_id | reservations | lots | lot_id = lot_id |
| reservations_by_location_id | reservations | locations | location_id = location_id |
| demand_forecasts_by_product_id | demand_forecasts | products | product_id = product_id |
| demand_forecasts_by_location_id | demand_forecasts | locations | location_id = location_id |
| recalls_by_root_lot_id | recalls | lots | root_lot_id = lot_id |
| lot_links_by_parent_lot_id | lot_links | lots | parent_lot_id = lot_id |
| lot_links_by_child_lot_id | lot_links | lots | child_lot_id = lot_id |
| inventory_snapshots_by_product_id | inventory_snapshots | products | product_id = product_id |
| inventory_snapshots_by_lot_id | inventory_snapshots | lots | lot_id = lot_id |
| inventory_snapshots_by_location_id | inventory_snapshots | locations | location_id = location_id |
| recall_snapshots_by_recall_id | recall_snapshots | recalls | recall_id = recall_id |
| recall_snapshots_by_product_id | recall_snapshots | products | product_id = product_id |
