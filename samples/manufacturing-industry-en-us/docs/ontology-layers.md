# Ontology and operating-data layers

This package has two BKN networks that serve different purposes.

| Layer | Location | Coverage | Purpose |
|---|---|---:|---|
| IOF reference model | `iof-reference/kn/` | 112 ObjectTypes, 85 named OWL object properties | Complete structural projection of the fixed IOF Core and Production Planning sources. Seven properties with precise in-module endpoints are BKN RelationTypes; the other 78 are retained in the OWL property inventory. |
| Manufacturing operations model | `kn/` | 40 ObjectTypes, 71 RelationTypes | Importable end-to-end sample data for demand, supply, inventory, production, quality, workforce, and maintenance. |

The operational model maps its central concepts to the IOF layer: `products`, `production_orders`, `manufacturing_operations`, `process_steps`, `production_machines`, and `equipment_capabilities` correspond to IOF Product, ProductionOrder, ManufacturingOperation, ProcessStep, ProductionMachine, and Capability. Its other ObjectTypes are explicit operational extensions that make the industry flow importable and queryable.

The 40 tables are therefore not a replacement for the 112 IOF classes. They are the populated, end-to-end business layer that uses the reference model.
