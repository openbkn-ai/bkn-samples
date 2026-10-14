# BKN Samples

[中文](README_cn.md)

Official OpenBKN samples for exploring knowledge networks with data, object relationships and business scenarios. Install a sample through **One-click onboarding**, then connect an external agent through MCP to query and analyze its published model.

Each sample is an independent package with its own database, knowledge network and release versions. Functions, metrics and Skills are included where the sample declares them.

## Try a sample

Use an OpenBKN 0.2.x environment with the standard sample installation service enabled and an account authorized to install samples.

1. Open **Studio → One-click onboarding** and select **Refresh samples**.
2. Choose a published sample, check its version and release notes, and select **Install**.
3. Wait for installation and verification to complete, then open its knowledge network.
4. Connect an external agent through MCP. Inspect the schema, query object instances and use the sample's declared functions, metrics or Skills as needed.
5. Use **Uninstall** to remove the sample. Installation history remains available; reinstall after cleanup completes.

For an offline candidate, use **Import offline package** to import its fixed `.tar.gz` package. The referenced data image must also be available to the target cluster. CLI and Python setup are needed for sample development, not for the standard Studio installation flow.

## Sample directory

| Sample | Language | Scenarios | Availability |
| --- | --- | --- | --- |
| [Order Basics](samples/order-basics/) | Chinese | A small starting point for orders, products and object relationships | Online catalog |
| [Supply Chain](samples/supply_ontology_hand/) | Chinese | Orders, forecasts, BOMs, inventory, procurement, shortages and delivery analysis | Online catalog |
| [Supply Chain](samples/supply_ontology_en/) | English | Supply-chain analysis with English data, model definitions, functions, metrics and Skills | Online catalog |
| [World Cup](samples/world-cup/) | Chinese model; English data | Tournament, team, player and match-event exploration, with 50 Chinese evaluation questions | Online catalog |
| [World Cup](samples/world-cup-en/) | English | Object queries, joins, rankings and cross-tournament analysis, with 50 evaluation questions | Online catalog |

All five samples are published in the [official catalog](catalog.json). Download their offline packages from [Releases](https://github.com/openbkn-ai/bkn-samples/releases). The catalog determines the available versions; sample package versions are independent of the platform version.

World Cup data is a locked historical snapshot covering men's editions through 2022 and women's editions through 2019. Detailed coverage varies by table. See each sample's README for its data scope, license and scenario assumptions.

## Scenario evaluation

Samples with an evaluation suite keep questions, reference answers and baseline checks under `bkn-eval/`:

- [Supply Chain evaluation](samples/supply_ontology_hand/bkn-eval/README.md)
- [English Supply Chain evaluation](samples/supply_ontology_en/bkn-eval/README.md)
- [World Cup evaluation](samples/world-cup/bkn-eval/README.md): 50 Chinese questions with explicit output fields, ordering, frozen answers and grading scripts.
- [English World Cup evaluation](samples/world-cup-en/bkn-eval/README.md): 10 basic queries/statistics, 12 multi-table joins, 14 rankings/cross-tournament comparisons and 14 combined analyses.

An independent external agent answers the questions through MCP. Reference answers are withheld during evaluation, then used to check business values, result fields and ordering. Record the tested data baseline, package and actual results for each evaluation.

## Develop and publish

Start with the [Sample Development Guide](docs/SAMPLE_DEVELOPMENT_GUIDE.md). For local development, use an [openbkn CLI](https://github.com/openbkn-ai/bkn-sdk) compatible with your platform and Python 3.11+ with the dependencies required by the sample's scripts.

```text
samples/<directory>/
├── sample.yaml                 # Identity, components and installation hooks
├── README.md                   # Usage, scenarios and data scope
├── dataset.lock                # Locked data provenance and checksums, where applicable
├── data/                       # Embedded sample data
├── kn/                         # BKN model or KN JSON
├── db/                         # Database initialization and verification
├── platform/                   # Managed installation and verification hooks
├── tools/                      # Functions or developer helpers, where declared
├── skills/                     # Business Skills, where declared
├── bkn-eval/                   # Questions, reference answers and baseline checks, where provided
└── releases/<version>/         # Release notes and published artifact metadata
```

Add a manifest and standard hooks for a new sample, and update the directory table above; the installer discovers sample identities dynamically. Keep all user-facing sample content in its intended language. Declare only the components actually installed, verify the exact package and fixed data image, and publish immutable release metadata before registering the version in `catalog.json`.

Evaluation suites and tests stay in source control. Execution logs, temporary bindings, translation mappings and local work files do not belong in release packages.

Useful guides:

- [Development and versioning](docs/SAMPLE_DEVELOPMENT_GUIDE.md)
- [Package construction and publication](docs/candidate-publication.md)
- [Uninstall and reinstall](docs/sample-uninstall.md)
- [Sample service deployment](docs/sample-service-deployment.md)
- [Design and documentation index](docs/README.md)
