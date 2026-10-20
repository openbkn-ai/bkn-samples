# Food Supply Chain Traceability and Recall BKN

Complete properties are in kn/object_types. Foreign keys point from source property to target primary key; blanks create no edge. Standard alignment is in standard-sources.md; local extensions do not claim GS1 equivalence.

| Object | Name | Primary key |
|---|---|---|
| organizations | Organization | organization_id |
| locations | Business Location | location_id |
| products | Food Product | product_id |
| lots | Product Lot | lot_id |
| movements | Supply Event | movement_id |
| inspections | Quality Inspection | inspection_id |
| holds | Stock Hold | hold_id |
| orders | Customer Order | order_id |
| order_lines | Order Line | line_id |
| reservations | Stock Reservation | reservation_id |
| demand_forecasts | Demand Forecast | forecast_id |
| recalls | Product Recall | recall_id |
| lot_links | Lot Transformation | link_id |
| inventory_snapshots | Recorded Inventory | snapshot_id |
| recall_snapshots | Recorded Recall Control | snapshot_id |

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
