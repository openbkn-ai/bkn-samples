# Installation and Acceptance

## Online installation

1. Sign in to OpenBKN and open **One-click onboarding** from the homepage.
2. Refresh the official catalog, select **Supply Chain (EN)** and click **Install** for the intended version.
3. Wait for data preparation, resource scanning, model import and binding, capability publication and verification to complete.
4. Open the knowledge network and inspect its objects and relationships.

The installation service loads data and publishes capabilities automatically. Users do not create databases, copy configuration files or run individual scripts.

## Offline package import

Download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases). Choose **Import offline package** in one-click onboarding, upload the package, then install the imported version.

The package references a fixed data image; it does not contain the image itself. The target cluster must be able to pull it. For restricted networks, ask the administrator to prepare the image in the target environment first.

## Capabilities and MCP acceptance

Connect an external agent through MCP. Verify that it can discover the knowledge network, metrics, Native Function Toolbox and Skills. Query orders and stock, then invoke functions with their declared business parameters. Check warehouse scopes, allocation policies and leading-zero forecast lookup. Installation success alone does not prove the business path.

The native implementations in `tools/fn/` are published by installation hooks. Callers do not construct `resolved_context`, pass credentials or supply inventory snapshots. Runtime functions read their bound BKN objects; local CSV calculations cannot replace actual MCP results.

## Core 50-question evaluation

Use the source repository's [BKN-Eval](../bkn-eval/README.md) for the core 50 questions. An independent external agent answers through MCP without seeing reference answers, CSVs or implementation source. Compare required fields, ordering and business values after completion, using the exact installed version and data baseline.

Run the four complete-calendar-month questions separately. Verify the published Monthly Sales Skill, half-open Asia/Shanghai boundaries, May 31 inclusion, identical filters and agent arithmetic. Keep execution evidence locally outside the committed sample.

## Failure and reinstallation

Read installation failure details, resolve the cause and retry the same installation record. If the original manifest no longer matches, retain the error and version information for the administrator; do not overwrite the failed record with a manual import of another version.

Before installing a new version, uninstall the old sample and wait for cleanup to finish. Uninstallation deletes sample data and user edits. Removing a cached package does not uninstall resources. Contact the administrator if uninstallation is unavailable or cleanup fails.

See the [FAQ](faq.md) for common questions.
