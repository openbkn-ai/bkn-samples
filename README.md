# BKN Samples

[中文](README_cn.md)

Official OpenBKN samples for exploring knowledge networks with data, object relationships and business scenarios. Install a sample through **One-click onboarding**, then connect an external agent through MCP to query and analyze its published model.

Each sample is an independent package with its own database, knowledge network and release versions. Functions, metrics and Skills are included where the sample declares them.

## Try a sample

Use an OpenBKN 0.2.x environment with the standard sample installation service enabled and an account authorized to install samples. The manufacturing, financial FIBO and retail GS1 samples require **OpenBKN 0.2.1 or later**; their current manifest compatibility range is `>=0.2.1 <0.3.0`.

1. Open **Studio → One-click onboarding** and select **Refresh samples**.
2. Choose a published sample, check its version and release notes, and select **Install**.
3. Wait for installation and verification to complete, then open its knowledge network.
4. Connect an external agent through MCP. Inspect the schema, query object instances and use the sample's declared functions, metrics or Skills as needed.
5. Use **Uninstall** to remove the sample. Installation history remains available; reinstall after cleanup completes.

For an offline candidate, use **Import offline package** to import its fixed `.tar.gz` package. If it declares a data image, that image must also be available to the target cluster. The FIBO packages use the product's shared MariaDB runtime and need no separate sample database image. CLI and Python setup are needed for sample development, not for the standard Studio installation flow.

## Sample directory

The OpenBKN 0.2.1 update covers **13 standard samples**: one Order Basics sample
and bilingual pairs for Supply Chain, World Cup, Manufacturing, Financial FIBO,
Retail GS1 and Energy SAREF4ENER. Energy source is integrated in this change. All
thirteen are built and checked through one candidate plan, rather than using only
the previous mainline inventory.

| Sample | Language | Scenarios | Availability |
| --- | --- | --- | --- |
| [Order Basics](samples/order-basics/) | Chinese | A small starting point for orders, products and object relationships | Existing release 0.1.2; 0.2.1 candidate 0.1.4, platform acceptance pending |
| [Supply Chain](samples/supply_ontology_hand/) | Chinese | Orders, forecasts, BOMs, inventory, procurement, shortages and delivery analysis | Existing release 0.1.4; 0.2.1 candidate 0.1.9, platform acceptance pending |
| [Supply Chain](samples/supply_ontology_en/) | English | Supply-chain analysis with English data, model definitions, functions, metrics and Skills | Existing release 0.1.1; 0.2.1 candidate 0.1.4, platform acceptance pending |
| [World Cup](samples/world-cup/) | Chinese model; English data | Tournament, team, player and match-event exploration, with 50 Chinese evaluation questions | Existing release 0.1.2; 0.2.1 candidate 0.1.6, platform acceptance pending |
| [World Cup](samples/world-cup-en/) | English | Object queries, joins, rankings and cross-tournament analysis, with 50 evaluation questions | Existing release 0.1.0; 0.2.1 candidate 0.1.2, platform acceptance pending |
| [Manufacturing Operations](samples/manufacturing-industry-en-us/) | English | Forecast-to-shipment manufacturing fulfillment, with 40 tables, 71 relations, and 100 bilingual evaluation questions | 0.2.1 candidate 0.1.3; self-contained, platform acceptance pending |
| [制造业端到端运营](samples/manufacturing-industry-zh-cn/) | Chinese | 从预测到发运的制造履约，含 40 张表、71 条关系和 100 道中英对照评测题 | 0.2.1 candidate 0.1.3; self-contained, platform acceptance pending |
| [Financial Portfolio Operations (FIBO)](samples/financial-fibo-en-us/) | English | Securities trading, settlement, positions, valuation, issuer concentration and receivable limits; 20 tables, 78,356 records and 100 evaluation questions | Existing release 0.2.5; 0.2.1 candidate 0.2.6, platform acceptance pending |
| [金融投资组合运营（FIBO）](samples/financial-fibo-zh-cn/) | Chinese | 证券交易、结算、持仓、估值、发行方集中度与未结算应收限额；20 张表、78,356 条记录和 100 道评测题 | Existing release 0.2.5; 0.2.1 candidate 0.2.6, platform acceptance pending |
| [Food Supply and Recall (GS1)](samples/retail-gs1-en-us/) | English | Receipt inspection, lot traceability, inventory, shared-stock fulfillment, March 2027 replenishment and recall; 15 tables, 2,911 records and 100 questions | Existing release 0.1.0; 0.2.1 candidate 0.1.1, platform acceptance pending |
| [食品供应链追溯与召回（GS1）](samples/retail-gs1-zh-cn/) | Chinese | 到货质检、批次追溯、库存、共享库存履约、2027年3月补货及召回；15张表、2,911条记录、100题 | Existing release 0.1.0; 0.2.1 candidate 0.1.1, platform acceptance pending |
| [Energy demand response (SAREF4ENER)](samples/energy-saref4ener-en-us/) | English | Eligibility, shared-capacity dispatch and metered settlement; 15 tables and 14,787 records | 0.2.1 candidate 0.1.5; self-contained, platform acceptance pending |
| [需求响应与柔性用能（SAREF4ENER）](samples/energy-saref4ener-zh-cn/) | Chinese | Localized model and aligned facts; 3 functions, 2 snapshot metrics and 1 investigation Skill | 0.2.1 candidate 0.1.5; self-contained, platform acceptance pending |


The [complete thirteen-package candidate set](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-candidates-0.2.1-complete-20261025-r2) includes every sample
above. Its [machine-readable plan](tools/publication/candidates-0.2.1.json) is checked
against source manifests in both directions: missing, duplicate or unregistered
samples fail the build. Fixed-source SHA-256 candidates are intended for offline
import into a 0.2.1 test environment after local checks. Real product installation,
MCP, function and business acceptance remain pending. The earlier nine-package
candidate set and historical assets remain unchanged.

Published 0.2.0 clients continue to use the root [official catalog](catalog.json).
The updated sample service selects directories by product version: [0.2.0](catalogs/0.2.0/catalog.json)
and [0.2.1](catalogs/0.2.1/catalog.json); see [directory selection](docs/product-version-catalogs.md).
The 0.2.1 directory currently retains existing FIBO/GS1 entries. None of the nine new
candidates is admitted to a stable directory yet. The OpenBKN 0.2.1 product is not
formally released; the candidates are intended for offline import into its test environments.

Manufacturing 0.1.3 and Energy 0.1.5 are now included as bilingual, content-only
shared-MariaDB candidates without sample-specific database images. Manufacturing
retains its 40 operational tables, 71 relations and IOF reference layer; Energy
retains its 15 tables, 3 functions, 2 snapshot metrics and investigation Skill.
See the [source integration record](docs/energy-saref4ener-readiness.md) for local
validation scope and historical recovery provenance.

The FIBO samples use selected MIT-licensed [FIBO sources](https://github.com/edmcouncil/fibo/tree/2d73435a4419b66b7c9f44cb9763e35fe8ac7890) as semantic references and fictional data, rather than claiming full-FIBO coverage. Fixed **[English 0.2.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.5)** and **[Chinese 0.2.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.2.5)** packages each provide 3 functions, 2 recorded-snapshot metrics and 1 investigation Skill and require **OpenBKN 0.2.1 or later** (`>=0.2.1 <0.3.0`). Version 0.2.5 corrects publication notes and execution-capability requirements; business content and question banks are unchanged. Import the fixed package offline; online availability follows the merged official catalog. Validation of 0.2.5 is limited to fresh installation, compatibility gates and package parity, without new model QA. Historical results remain **96/100 financial fields per language**, **4/4 specified post-fix tool paths (100% of those paths)** and **16/16 representative 0.2.4 technical checks (100% of those checks)**; they are not a new 0.2.5 full-bank accuracy score. See the [0.2.5 release acceptance and limits](docs/financial-fibo-release-0.2.5.zh-CN.md). Historical 0.2.4 and 0.1.x assets remain unchanged.

World Cup data is a locked historical snapshot covering men's editions through 2022 and women's editions through 2019. Detailed coverage varies by table. See each sample's README for its data scope, license and scenario assumptions.

The GS1 samples are two independently installable packages with fictional, aligned bilingual data, three functions, two dated snapshot metrics and one investigation Skill per language. They reference the Apache-2.0 [GS1 Web Vocabulary](https://github.com/gs1/WebVoc), with explicit local operational extensions. On local port 8081, the original single full pass scored **English 96/100 and Chinese 95/100**. After an event-deduplication repair and question-contract corrections, only the prior nonpassing cases were retested: **English 4/4 and Chinese 5/5**, all execution and evidence states complete. The revised full banks were not rerun; this is not a full-bank 100% claim. See the [acceptance report](docs/retail-gs1-acceptance.en-US.md). Source PR #186 is merged. Immutable [English 0.1.0](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-en-us-v0.1.0) and [Chinese 0.1.0](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-zh-cn-v0.1.0) assets are published; catalog PR #187 is merged. Offline import requires OpenBKN 0.2.1 or later; no legacy 020 bundled index was changed.

## Scenario evaluation

Samples with an evaluation suite keep questions, reference answers and baseline checks under `bkn-eval/`:

- [Supply Chain evaluation](samples/supply_ontology_hand/bkn-eval/README.md)
- [English Supply Chain evaluation](samples/supply_ontology_en/bkn-eval/README.md)
- [World Cup evaluation](samples/world-cup/bkn-eval/README.md): 50 Chinese questions with explicit output fields, ordering, frozen answers and grading scripts.
- [English World Cup evaluation](samples/world-cup-en/bkn-eval/README.md): 10 basic queries/statistics, 12 multi-table joins, 14 rankings/cross-tournament comparisons and 14 combined analyses.
- [English FIBO evaluation](samples/financial-fibo-en-us/bkn-eval/README.md) and [Chinese FIBO evaluation](samples/financial-fibo-zh-cn/bkn-eval/README.md): 100 questions per sample across 10 scenarios, with 30 easy/basic, 40 intermediate and 30 hard/complex questions; frozen full answers and financial regression controls.
- [English GS1 retail evaluation](samples/retail-gs1-en-us/bkn-eval/README.md) and [Chinese GS1 retail evaluation](samples/retail-gs1-zh-cn/bkn-eval/README.md): 100 questions each, PRD-mapped across 10 scenarios with 30 basic, 40 medium and 30 complex questions; original scores and the bounded nine-case retest are reported separately.

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

Add a manifest and standard hooks for a new sample, and update the directory table above; the installer discovers sample identities dynamically. Keep all user-facing sample content in its intended language. Declare only the components actually installed, verify the exact package and its declared runtime dependencies, and publish immutable release metadata before registering it in the corresponding product-version catalog.

Evaluation suites and tests stay in source control. Execution logs, temporary bindings, translation mappings and local work files do not belong in release packages.

Useful guides:

- [Development and versioning](docs/SAMPLE_DEVELOPMENT_GUIDE.md)
- [Package construction and publication](docs/candidate-publication.md)
- [Uninstall and reinstall](docs/sample-uninstall.md)
- [Sample service deployment](docs/sample-service-deployment.md)
- [Design and documentation index](docs/README.md)
