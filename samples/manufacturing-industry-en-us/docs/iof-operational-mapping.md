# IOF-to-operational mapping

The operational network is a BKN extension layer, not a second copy of IOF. The following mappings are executable design rules: every listed operational record uses its business key as the BKN key; the stated source IRI is its semantic anchor; unlisted items are explicit operational extensions.

| Operational ObjectType | IOF source class / status | Field mapping and conversion rule |
|---|---|---|
| `products` | `MaterialProduct` — `https://spec.industrialontologies.org/ontology/construct/MaterialProduct` | `product_id` is the local instance key; `product_code`, name, type, and unit are operational attributes. |
| `production_orders` | `ProductionOrder` — `https://spec.industrialontologies.org/ontology/construct/ProductionOrder` | `production_order_id` is the local key; product, quantity, due date, and status operationalize the IOF objective specification. |
| `manufacturing_operations` | `ManufacturingOperation` — `https://spec.industrialontologies.org/ontology/construct/ManufacturingOperation` | `operation_id` is the local key; work center and status are operational planning attributes. |
| `process_steps` | `ProcessStep` — `https://spec.industrialontologies.org/ontology/construct/ProcessStep` | `process_step_id` is the local key; `required_capability_id` is a BKN requirement extension. |
| `production_machines` | `ProductionMachine` — `https://spec.industrialontologies.org/ontology/construct/ProductionMachine` | `machine_id` is the local key; site, work center, and status are operational attributes. |
| `equipment_capabilities` | `Capability` — `https://spec.industrialontologies.org/ontology/construct/Capability` | `capability_id` is the local key; category is a local catalog classification. |
| `customers`, `suppliers`, `operators` | IOF business/agent concepts where available | Customer/supplier/operator IDs are local master-data keys; commercial and employment fields are extensions. |
| Remaining 31 ObjectTypes | BKN operational extension | BOM, routing, order lines, inventory, execution, inspection results, shifts, qualifications, and maintenance are needed for importable ERP/MES operations. Their foreign keys are declared as the 71 BKN RelationTypes. |

Core relationship mapping: `production_orders.product_id → products.product_id`; `manufacturing_operations.production_order_id → production_orders.production_order_id`; `process_steps.operation_id → manufacturing_operations.operation_id`; `process_steps.required_capability_id → equipment_capabilities.capability_id`; `production_execution_records.process_step_id → process_steps.process_step_id`; `quality_inspection_lots.production_order_id → production_orders.production_order_id`. These mappings are checked by `tools/verify_industry_links.py`.
