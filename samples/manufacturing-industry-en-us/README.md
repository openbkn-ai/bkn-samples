# Manufacturing operations (IOF reference, English)

A fictional precision machining company: two plants, Shenzhen and Suzhou, machine pump housings, valve bodies, impellers and flanges for ten customers, traced from sales orders, demand forecasts and production plans to material requirements, purchasing and receipts, material issues, production execution, inspection, finished goods receipts, shipments and machine maintenance. Includes 40 data tables, the ontology and 2 business Skills. Business needs and rules are in the [PRD](docs/PRD.md).

## Install and try

1. Sign in to OpenBKN and open **Quick start** on the home page.
2. Refresh the official catalog, choose **Manufacturing Operations** and click **Install**; it needs **OpenBKN >=0.2.1 <0.3.0**.
3. Wait for installation and verification to finish, then open the knowledge network.
4. Try the experience cards in smart Q&A, data query and graph exploration, or connect an external agent over MCP to query objects and use the Skills.

Without access to the official catalog, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases) and install it with **Import offline package** in Quick start.

All data are fictional and synthetic, covering November 2026 to March 2027 with business date 2027-02-28: November to February have happened and March work orders are the plan. Nothing here represents a real company; nothing is ordered, scheduled or shipped.

## Capabilities

Every question can be answered with Cypher, so the sample ships no functions and no metrics, and the Community edition can use all of it.

- **Cypher queries**: products, BOM revisions, routings, machine capabilities and operator qualifications, orders, shipments and units owed, forecasts and plans, material requirements and issues, purchasing and receipts, executions and shifts, inspection results and specifications, inventory and maintenance.
- **Skills**: organised by user as "Orders and materials" (order fulfilment manager, purchasing and materials manager) and "Production and quality" (production lead, quality manager), stating the business rules, Cypher patterns and how to answer.

## Experience cards

15 experience cards are taken from the test set, covering BOMs and routings, operator qualifications, late and remade orders, shortages and blocking, scrap, execution compliance, rejected lots and escapes, overdue maintenance, order traces and stock, from simple to involved. The cards' data-query and graph Cypher are checked online after installation with `tools/acceptance/experience_set.py`.

## Data and acceptance

The data are generated deterministically from one business story by [`tools/manufacturing_industry/generate_data.py`](../../tools/manufacturing_industry/generate_data.py), and the two language packages differ only in translated text. Machines, operators, materials, suppliers and stock are shared across work orders, with deliberate exceptions: split and late shipments, scrap shortfalls, rejected and remade work orders, a quality escape, non-compliant executions, an issue from a receipt in inspection, short and rejected purchases, a draft BOM and overdue maintenance; see the test set README.

The test set is the [business-scenario test set v1](bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md); reference answers are computed from the delivered data by an independent script and are not shipped in the package. After installation, an agent that has not seen the answers runs every question once; below 100%, record why it failed and change the ontology description or a Skill first, never the questions or answers. Run the local checks in this directory:

```bash
python3 tools/verify_industry_links.py
python3 iof-reference/tools/verify_reference_instances.py
python3 bkn-eval/run.py
openbkn bkn validate kn
```

## Open ontology sources

`iof-reference/` is a separate **IOF Core + Production Planning 112-class** reference layer whose synthetic reference instances keep the source IRI, label and definition and are not operational records; its correspondence to the operational model is in the [IOF operational mapping](docs/iof-operational-mapping.md) and [ontology layers](docs/ontology-layers.md). The operational model and CSV files are this sample's fictional business implementation, not an official IOF release.

- [IOF ontology repository](https://github.com/iofoundry/ontology)
- [IOF Core module](https://spec.industrialontologies.org/portal/release/202603/core.html)
- [IOF Production Planning module](https://spec.industrialontologies.org/portal/release/202603/productionplanning/ProductionPlanningOntology.html)
- [MIT license declared in the IOF Core source](https://github.com/iofoundry/Core/blob/main/Core.rdf)

To upgrade, uninstall the old sample before installing the new version. Uninstalling removes the sample's data and user changes; deleting the offline package cache does not uninstall installed resources.
