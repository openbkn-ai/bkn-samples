# Supply Chain

Explore order backlog, order acceptance, BOMs, stock, purchase follow-up and lead times with fictional historical sample data. The sample includes 12 tables, an ontology, native functions and business Skills. Business requirements and rules are in the [PRD](docs/PRD.en-US.md).

## Install and explore

1. Sign in to OpenBKN and open **One-click onboarding** from the homepage.
2. Refresh the official catalog, select **Supply Chain (EN)** and click **Install**.
3. Wait for installation and verification to complete, then open the knowledge network.
4. Try the experience cards on the Q&A, data query and graph pages, or connect an external agent through MCP to query objects, call published functions and use Skills.

If the official catalog is unreachable, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases), choose **Import offline package** in one-click onboarding, then install it. The referenced data image must also be available to the target cluster; ask the administrator to prepare it for restricted networks.

Users do not need to configure Python, the CLI or database connections. See the [installation and acceptance guide](docs/import-guide.en-US.md) and [FAQ](docs/faq.md).

The sample is a historical replay. It does not represent live stock or real delivery commitments, and it never creates purchase orders or writes to an ERP.

## Capabilities

Anything Cypher can answer has no function; functions are kept only for calculations Cypher cannot express. The sample uses no metrics, so the Community edition can use all of it.

- **Cypher queries**: master data, stock totals, backlog and overdue orders, forecasts, open and overdue purchases, BOM lists (one query from the product returns the whole BOM, filtered by level and parent), where-used, common parts and document trace. The platform does not support variable-length paths or `UNWIND`; the Skills give the patterns to use instead.
- **Native functions**:
  - Buildable quantity and available to promise: nets the BOM level by level by the PRD rules, can add open purchases due by a date, and returns buildable quantity, available to promise and the blocking materials for one or several products.
  - Demand coverage and shortages: evaluates several demands in order against one shared stock pool and returns coverage and the shortage list.
- **Skills**: organized for the two users, PMC planning and purchase follow-up, stating the business rules, when to use Cypher, when to call a function, and how to answer.

## Experience cards

About 15 experience cards are taken from the test set, one or two per scenario, from simple to complex: lookups first (backlog, stock), then relations (where-used, document trace), then reasoning (how much to accept, what blocks it, whom to chase). The cards' data query and graph Cypher are checked online after installation with `tools/acceptance/experience_set.py`.

## Acceptance and maintenance

See the [v4 business-scenario test set](bkn-eval/baselines/2026-10-30-business-scenarios-v4/README.md). Reference answers are computed by an independent script from the delivered data and are not shipped in the package. After installation, an agent that has not read the answers runs each question once; below 100%, record why each failed and fix the ontology descriptions, Skills or functions first, never the questions or answers.

To install a new version, uninstall the existing sample first. Uninstallation removes sample data and user edits; deleting a cached offline package does not uninstall installed resources.

Developers can inspect `sample.yaml`, `db/`, `platform/` and [tools/](tools/README.md). Standard installation hooks run these scripts; customers and partners do not execute them individually.
