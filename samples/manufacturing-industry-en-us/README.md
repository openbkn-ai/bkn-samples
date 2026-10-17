# Manufacturing Operations Sample

This is an importable end-to-end manufacturing sample for tracing demand forecast through plan, supply, production, quality, finished-goods receipt, and shipment.

**Installation compatibility:** this sample requires OpenBKN **0.2.1 or later**. It is distributed as an offline package and is intentionally not registered in the online sample catalog.

## What is included

- `kn/`: the operational BKN model with **40 ObjectTypes**, **71 RelationTypes**, and 3 concept groups.
- `data/`: 40 operational CSV tables with **2,700 records** in total; every table contains at least 50 records.
- `iof-reference/`: a separate, fixed **112-class IOF Core + Production Planning** reference layer. Its synthetic reference instances preserve source IRI, label, and definition; it is not operational transaction data.
- `bkn-eval/`: 100 bilingual questions and 18 deterministic acceptance scenarios.
- `docs/`: business PRD, model mapping, data-branch design, ontology-layer rationale, and capability requirements.

## Scenario and planning horizon

The data chain is forecast → production plan → sales order → material receipt and issue → work order and routing → equipment, people, and execution → quality specification and inspection → finished-goods receipt → shipment.

The planning horizon is **November 2026 through March 2027**. All temporal fields are date-only (`YYYY-MM-DD`): sales delivery, procurement receipt, goods receipt, shift, execution, maintenance, and production due dates. The latest planned production due date is `2027-03-30`.

Fifty connected business cases cover 22 shipped completions, 11 material shortages, 11 quality failures, and 6 work orders in production. Read [the branch design](docs/dataset-scenarios.md) for the evidence represented by each outcome.

## Identifier compatibility

OpenBKN 0.2.1 limits BKN resource `id` and `name` values to 40 characters. The network, all 40 object types, 71 relation types, and 3 concept groups satisfy that limit. Relation IDs use stable abbreviated endpoint names such as `material_issue_to_prod_mat_req`; the source and target CSV fields remain fully explicit in each relation mapping.

## English and Chinese packages

The English and Chinese packages have the same CSV schemas, row counts, stable IDs, BKN relation structure, and evaluation IDs. Business display values and status values are localized in each package. Use stable IDs for cross-language comparison; do not infer an exception from an entity name.

## Start here

1. Read the [business PRD](docs/PRD.md), which includes scenario scope and P0 acceptance needs.
2. Inspect `kn/` and `data/` together: relation mapping rules identify the foreign-key fields used by the CSVs.
3. Review the [IOF-to-operational mapping](docs/iof-operational-mapping.md) and [ontology-layer rationale](docs/ontology-layers.md) before treating the 112-class reference layer as transactional data.
4. Run the local checks from this directory:

```bash
python3 tools/verify_industry_links.py
python3 iof-reference/tools/verify_reference_instances.py
python3 bkn-eval/run.py
openbkn bkn validate kn
```

The checks validate 71 operational relations, plan/BOM provenance, transaction-derived inventory snapshots, every shipment gate, 112 IOF reference-instance tables, and the 18 acceptance baselines, and BKN syntax.

## Open-source ontology source

The 112-class reference layer is derived from the released **IOF Core** and **IOF Production Planning** modules. The operational BKN model and CSV records are a local, fictional implementation for this sample; they are not an official IOF release or a verbatim copy of its OWL files.

- [IOF ontology source repository](https://github.com/iofoundry/ontology)
- [IOF Core module](https://spec.industrialontologies.org/portal/release/202603/core.html)
- [IOF Production Planning module](https://spec.industrialontologies.org/portal/release/202603/productionplanning/ProductionPlanningOntology.html)
- [MIT license declared by the IOF Core source](https://github.com/iofoundry/Core/blob/main/Core.rdf)

The exact source IRIs, labels, definitions, and the fixed module boundary used by this package are documented in [`iof-reference/README.md`](iof-reference/README.md).

## Scope boundary

The sample answers whether a released production plan can be fulfilled through material issue, execution, final quality, finished-goods receipt, and shipment. It deliberately excludes dispatch optimization, finite-capacity scheduling, lot genealogy, and root-cause workflows. See [capability requirements](docs/capability-requirements.md) for the supported evidence and decision boundary.
