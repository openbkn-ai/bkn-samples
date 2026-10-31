# Food Supply Chain Traceability and Recall

A fictional food retailer's lot traceability, inventory fulfilment and recall sample: 25 warehouses and 25 stores, covering receipt inspection, transfers, sales and returns, quarantine, expiry, order allocation, March replenishment and recall control. The sample includes 15 tables, an ontology, 3 native functions and 2 business Skills. Business requirements and rules are in the [PRD](docs/PRD.en-US.md).

## Install and explore

1. Sign in to OpenBKN and open **One-click onboarding** from the homepage.
2. Refresh the official catalog, select **Food Supply Chain Traceability and Recall** and click **Install**; it requires **OpenBKN >=0.2.1 <0.3.0**.
3. Wait for installation and verification to complete, then open the knowledge network.
4. Try the experience cards on the Q&A, data query and graph pages, or connect an external agent through MCP to query objects, call published functions and use Skills.

If the official catalog is unreachable, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases), choose **Import offline package** in one-click onboarding, then install it.

The data is synthetic and covers November 2026 to March 2027, with business date 2027-02-28; March forecasts and planned receipts are the plan. Every conclusion is advice only; nothing places orders, ships or issues recall notices.

## Capabilities

Anything Cypher can answer has no function; functions are kept only for calculations Cypher cannot express. The sample uses no metrics, so the Community edition can use all of it.

- **Cypher queries**: products, organizations, locations, lots, inspections, movements, orders and reservations, forecasts, recalls, lot splits and transformations. The February 28 inventory and recall snapshots match recomputation from the source events and can be read directly.
- **Native functions**: `inventory_asof` replays stock for a day and what was known that day; `fulfillment_plan` allocates orders or works out replenishment against the March forecast; `recall_assessment` traces a recall from its root lot to downstream lots and works out control by location.
- **Skills**: organized for the users, "Inventory and fulfilment" (warehouse, store) and "Quality and recall" (quality lead), stating the business rules, when to use Cypher, when to call a function, and how to answer.

## Experience cards

The experience cards are taken from the test set and cover products, inspection, stock and its reasons, expiry, orders, replenishment, lot flow, recall reach and control, and data trust, from simple to complex. The cards' data query and graph Cypher are checked online after installation with `tools/acceptance/experience_set.py`.

## Acceptance and maintenance

See the [business-scenario test set v1](bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md). Reference answers are computed independently of the sample's functions and are not shipped in the package. After installation, an agent that has not read the answers runs each question once; below 100%, record why each failed and fix the ontology descriptions, Skills or functions first, never the questions or answers. The original 100-question bank is in [bkn-eval](bkn-eval/README.md).

For the ontology and standard sources see the [ontology notes](docs/ontology.md), [business contract](docs/business-contract.md) and [GS1 sources and license](docs/standard-sources.md).

To install a new version, uninstall the existing sample first. Uninstallation removes sample data and user edits; deleting a cached offline package does not uninstall installed resources.
