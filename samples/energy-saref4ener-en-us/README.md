# Demand response and flexible energy (SAREF4ENER reference, English)

A fictional load aggregator, traced from enterprise customers, sites, controllable devices and meters to response events, load forecasts and baselines, device offers and constraints, dispatch across events that share resources, execution receipts, meter readings and the settlement ledger. Includes 15 data tables, the ontology, 3 native functions and 2 business Skills. Business needs and rules are in the [PRD](docs/PRD.md).

## Install and try

1. Sign in to OpenBKN and open **Quick start** on the home page.
2. Refresh the official catalog, choose **Demand response and flexible energy** and click **Install**; it needs **OpenBKN >=0.2.1 <0.3.0**.
3. Wait for installation and verification to finish, then open the knowledge network.
4. Try the experience cards in smart Q&A, data query and graph exploration, or connect an external agent over MCP to query objects, call the published functions and use the Skills.

Without access to the official catalog, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases) and install it with **Import offline package** in Quick start.

All data are fictional and synthetic, covering November 2026 to March 2027 with business date 2027-02-28: November to February have happened, and March is the plan known that day. Nothing here represents real grid dispatch or settlement; no control instruction is sent and nothing is paid.

## Capabilities

Anything Cypher can query has no function; functions stay only for calculations Cypher cannot express. The sample uses no metrics, so the Community edition can use all of it.

- **Cypher queries**: customers, sites, devices and meters, event schedules, offers and constraints, committed allocations, execution receipts, reading versions, the settlement ledger, and the 2027-02-28 capacity and settlement snapshots.
- **Native functions**: `flexibility_assessment` works out an event's eligible capacity and why devices are excluded; `dispatch_plan` gives the new allocation, shortfall and estimated cost for events in one block by priority and offer cost; `settlement_assessment` works out verified energy, delivery ratio, revenue, customer compensation and the ledger difference. All three can look back at what was known on an earlier day.
- **Skills**: organised by user as "Capacity and dispatch" (aggregator operations, site energy managers) and "Delivery and settlement" (response duty officers, settlement clerks), stating the business rules, when to use Cypher, when to call a function and how to answer.

## Experience cards

15 experience cards are taken from the test set, covering assets, eligible capacity, site caps, shared blocks, execution, delivery thresholds, ledger reconciliation and settlement totals, from simple to involved. The cards' data-query and graph Cypher are checked online after installation with `tools/acceptance/experience_set.py`.

## Acceptance and maintenance

The test set is the [business-scenario test set v1](bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md); reference answers are computed from the delivered data by an independent script and are not shipped in the package. After installation, an agent that has not seen the answers runs every question once; below 100%, record why it failed and change the ontology description, a Skill or a function first, never the questions or answers. The earlier 100-question replay and data checks are in [bkn-eval](bkn-eval/README.md); from the repository root run:

```sh
python3 tools/energy_saref4ener/verify.py --sample en-us
python3 -m unittest tools.energy_saref4ener.test_engine tools.energy_saref4ener.test_adapter -v
```

The ontology's correspondence to SAREF4ENER is in the [BKN specification](docs/bkn-modeling-spec.md); sources are ETSI [SAREF4ENER 2.1.1](https://saref.etsi.org/saref4ener/v2.1.1/) and its import [SAREF Core 4.1.1](https://saref.etsi.org/core/v4.1.1/) under BSD-3-Clause, with the original Turtle in [saref-reference/](saref-reference/README.md). Customers, sites, dispatch plans and settlement formulas are this sample's business extensions; neither ETSI certification nor globally optimal dispatch is claimed.

To upgrade, uninstall the old sample before installing the new version. Uninstalling removes the sample's data and user changes; deleting the offline package cache does not uninstall installed resources.
