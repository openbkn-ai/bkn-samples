# Supply Chain

Explore orders, forecasts, BOMs, stock, procurement, shortages and delivery risk with fictional sample data. The sample includes 12 tables, a knowledge network, metrics, native functions and business Skills.

## Install and explore

1. Sign in to OpenBKN and open **One-click onboarding** from the homepage.
2. Refresh the official catalog, select **Supply Chain (EN)** and click **Install**.
3. Wait for installation and verification to complete, then open the knowledge network.
4. Connect an external agent through MCP to query objects, call published functions and use Skills.

If the official catalog is unreachable, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases), choose **Import offline package**, then install it. The referenced data image must also be available to the target cluster; ask the administrator to prepare it for restricted networks.

Users do not need to configure Python, the CLI or database connections. See the [installation and acceptance guide](docs/import-guide.en-US.md) and [FAQ](docs/faq.md).

## Scenarios and acceptance

The fixture uses fictional people and companies, engineering specifications and stable business identifiers. Explore stock coverage, shortages, shared demand allocation and delivery risk with explicit business dates. Keep identifiers as strings, including leading zeroes. These historical scenarios do not promise real-world delivery or create purchase orders.

After installation, verify objects, metrics, functions and Skills through MCP. Use [BKN-Eval](bkn-eval/README.md) for the core 50 questions and run the four calendar-month checks separately. Evaluation questions and reference answers are maintained in the source repository and excluded from installable packages.

To install a new version, uninstall the existing sample first. Uninstallation removes sample data and user edits. Deleting a cached offline package does not uninstall platform resources.

Developers can inspect `sample.yaml`, `db/`, `platform/` and [tools/](tools/README.md). Standard installation hooks run these scripts; users do not execute them individually.

## Material assurance / 材料保障

Candidate 0.1.6 adds Material_Assurance and Replenishment_Draft (16 native Functions total). Explicitly choose customer_delivery or new_production; drafts never persist or execute purchases. See [contract and acceptance boundaries](docs/material-assurance.md). Original historical receipts and target-product acceptance remain pending.

## Read-only shortage rule / 只读缺料规则

Candidate 0.1.7 adds Material_Shortage_Rule (17 native Functions total). It requires resolved, trusted event projection configuration and returns candidates/closure suggestions only. Workshop owns IDs, writes and scheduling. See [adapter contract and pending integration](docs/shortage-rule.md).
