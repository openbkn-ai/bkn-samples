# BKN Samples

[中文](README_cn.md)

Official OpenBKN samples for exploring knowledge networks with data, object relationships and business scenarios. Install a sample through **One-click onboarding**, then connect an external agent through MCP to query and analyze its published model.

Each sample is an independent package with its own database, knowledge network and release versions. Functions, metrics and Skills are included where the sample declares them.

## Try a sample

Use an OpenBKN 0.2.x environment with the standard sample installation service enabled and an account authorized to install samples. The manufacturing and both financial FIBO samples require **OpenBKN 0.2.1 or later**; their current manifest compatibility range is `>=0.2.1 <0.3.0`.

1. Open **Studio → One-click onboarding** and select **Refresh samples**.
2. Choose a published sample, check its version and release notes, and select **Install**.
3. Wait for installation and verification to complete, then open its knowledge network.
4. Connect an external agent through MCP. Inspect the schema, query object instances and use the sample's declared functions, metrics or Skills as needed.
5. Use **Uninstall** to remove the sample. Installation history remains available; reinstall after cleanup completes.

For an offline candidate, use **Import offline package** to import its fixed `.tar.gz` package. If it declares a data image, that image must also be available to the target cluster. The FIBO packages use the product's shared MariaDB runtime and need no separate sample database image. CLI and Python setup are needed for sample development, not for the standard Studio installation flow.

## Sample directory

| Sample | Language | Scenarios | Availability |
| --- | --- | --- | --- |
| [Order Basics](samples/order-basics/) | Chinese | A small starting point for orders, products and object relationships | Online catalog |
| [Supply Chain](samples/supply_ontology_hand/) | Chinese | Orders, forecasts, BOMs, inventory, procurement, shortages and delivery analysis | Online catalog |
| [Supply Chain](samples/supply_ontology_en/) | English | Supply-chain analysis with English data, model definitions, functions, metrics and Skills | Online catalog |
| [World Cup](samples/world-cup/) | Chinese model; English data | Tournament, team, player and match-event exploration, with 50 Chinese evaluation questions | Online catalog |
| [World Cup](samples/world-cup-en/) | English | Object queries, joins, rankings and cross-tournament analysis, with 50 evaluation questions | Online catalog |
| [Manufacturing Operations](samples/manufacturing-industry-en-us/) | English | Forecast-to-shipment manufacturing fulfillment, with 40 tables, 71 relations, and 100 bilingual evaluation questions | Offline release only; requires OpenBKN ≥ 0.2.1 |
| [制造业端到端运营](samples/manufacturing-industry-zh-cn/) | Chinese | 从预测到发运的制造履约，含 40 张表、71 条关系和 100 道中英对照评测题 | 仅离线发布；要求 OpenBKN ≥ 0.2.1 |
| [Financial Portfolio Operations (FIBO)](samples/financial-fibo-en-us/) | English | Securities trading, settlement, positions, valuation, issuer concentration and receivable limits; 20 tables, 78,356 records and 100 evaluation questions | Released 0.1.3; requires OpenBKN ≥ 0.2.1 |
| [金融投资组合运营（FIBO）](samples/financial-fibo-zh-cn/) | Chinese | 证券交易、结算、持仓、估值、发行方集中度与未结算应收限额；20 张表、78,356 条记录和 100 道评测题 | 已发布 0.1.4；要求 OpenBKN ≥ 0.2.1 |

The [official catalog](catalog.json) determines downloadable versions for the published samples.

The two manufacturing samples are intentionally kept out of the official catalog and legacy `020` discovery. Import their fixed offline package only after loading its matching data image into the target cluster; they install independently and can coexist because they use separate databases and knowledge-network IDs.

The FIBO samples are independently installable English and Chinese packages with separate databases and knowledge-network IDs. They use selected MIT-licensed [FIBO sources](https://github.com/edmcouncil/fibo/tree/2d73435a4419b66b7c9f44cb9763e35fe8ac7890) as semantic references and fictional operational data, rather than claiming full-FIBO coverage. Both completed local installation and 100 actual model questions; see the [acceptance summary and limits](docs/financial-fibo-repair-acceptance.zh-CN.md). Fixed [English 0.1.3](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.1.3) and [Chinese 0.1.4](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.1.4) Releases include the package, acceptance evidence and checksums. Use the official catalog for online discovery, or download the same package for offline import.

World Cup data is a locked historical snapshot covering men's editions through 2022 and women's editions through 2019. Detailed coverage varies by table. See each sample's README for its data scope, license and scenario assumptions.

## Scenario evaluation

Samples with an evaluation suite keep questions, reference answers and baseline checks under `bkn-eval/`:

- [Supply Chain evaluation](samples/supply_ontology_hand/bkn-eval/README.md)
- [English Supply Chain evaluation](samples/supply_ontology_en/bkn-eval/README.md)
- [World Cup evaluation](samples/world-cup/bkn-eval/README.md): 50 Chinese questions with explicit output fields, ordering, frozen answers and grading scripts.
- [English World Cup evaluation](samples/world-cup-en/bkn-eval/README.md): 10 basic queries/statistics, 12 multi-table joins, 14 rankings/cross-tournament comparisons and 14 combined analyses.
- [English FIBO evaluation](samples/financial-fibo-en-us/bkn-eval/README.md) and [Chinese FIBO evaluation](samples/financial-fibo-zh-cn/bkn-eval/README.md): 100 questions per sample across 10 scenarios, with 30 easy/basic, 40 intermediate and 30 hard/complex questions; frozen full answers and financial regression controls.

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
