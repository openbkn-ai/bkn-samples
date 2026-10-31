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

OpenBKN 0.2.1 offers **12 standard samples**: bilingual pairs for Supply Chain, World Cup, Manufacturing, Financial FIBO, Retail GS1 and Energy SAREF4ENER, all registered in the [0.2.1 catalog](catalogs/0.2.1/catalog.json). Order Basics is not offered on 0.2.1 and keeps its earlier release. Each 0.2.1 release title starts with `[OpenBKN 0.2.1]`.

| Sample | Language | Scenarios | Availability |
| --- | --- | --- | --- |
| [Order Basics](samples/order-basics/) | Chinese | A small starting point for orders, products and object relationships | Original 020: 0.1.2; not offered on 0.2.1 |
| [Supply Chain](samples/supply_ontology_hand/) | Chinese | PMC planning and purchasing: backlog, buildable and promisable quantities, shortages and follow-up | Original 020: [0.1.16](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.16); 0.2.1: [0.1.17](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.17) |
| [Supply Chain](samples/supply_ontology_en/) | English | The same PMC and purchasing scenarios in English | Original 020: [0.1.1](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-en-v0.1.1); 0.2.1: [0.1.11](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-en-v0.1.11) |
| [World Cup](samples/world-cup/) | Chinese model; English data | Tournaments, teams, players and match events | Original 020: 0.1.2; 0.2.1: [0.1.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-world-cup-v0.1.7) |
| [World Cup](samples/world-cup-en/) | English | Tournaments, teams, players and match events | Original 020: 0.1.0; 0.2.1: [0.1.3](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-world-cup-en-v0.1.3) |
| [Manufacturing Operations](samples/manufacturing-industry-en-us/) | English | Precision machining fulfilment: delivery, material, execution compliance, quality release, purchasing and maintenance | 0.2.1: [0.1.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-manufacturing-industry-en-us-v0.1.5) |
| [制造业端到端运营](samples/manufacturing-industry-zh-cn/) | Chinese | 精密加工订单履约：交付、物料、执行合规、质量放行、采购与维护 | 0.2.1: [0.1.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-manufacturing-industry-zh-cn-v0.1.5) |
| [Financial Portfolio Operations (FIBO)](samples/financial-fibo-en-us/) | English | Post-trade operations, valuation, concentration and limits | 0.2.1: [0.2.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.7) |
| [金融投资组合运营（FIBO）](samples/financial-fibo-zh-cn/) | Chinese | 交易后运营、估值、集中度与限额 | 0.2.1: [0.2.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.2.7) |
| [Food Supply and Recall (GS1)](samples/retail-gs1-en-us/) | English | Receipt quality, lot traceability, warehouse and store fulfilment, replenishment and recall | 0.2.1: [0.1.2](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-en-us-v0.1.2) |
| [食品供应链追溯与召回（GS1）](samples/retail-gs1-zh-cn/) | Chinese | 到货质检、批次追溯、仓库与门店履约、补货和召回 | 0.2.1: [0.1.2](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-zh-cn-v0.1.2) |
| [Energy demand response (SAREF4ENER)](samples/energy-saref4ener-en-us/) | English | Eligible capacity, shared-block dispatch, delivery verification and settlement | 0.2.1: [0.1.6](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-energy-saref4ener-en-us-v0.1.6) |
| [需求响应与柔性用能（SAREF4ENER）](samples/energy-saref4ener-zh-cn/) | Chinese | 可承诺容量、同时段调度、交付核实与结算 | 0.2.1: [0.1.6](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-energy-saref4ener-zh-cn-v0.1.6) |

Every 0.2.1 sample is organised around business roles with a business PRD, a 50-question business-scenario test set with independently computed reference answers, role-based Skills and 15 experience cards. Metrics are removed and only calculations that Cypher cannot express remain as functions, so the Community edition can use every sample. Each release was installed fresh on an OpenBKN 0.2.1 main build (arm64), its experience cards were checked online, and its `verification.json` records the evidence and limits.

Published 0.2.0 clients continue to use the root [official catalog](catalog.json). The updated sample service selects directories by product version: [0.2.0](catalogs/0.2.0/catalog.json) and [0.2.1](catalogs/0.2.1/catalog.json); see [directory selection](docs/product-version-catalogs.md). Earlier 0.2.1 releases are withdrawn in the catalogs and their assets removed; Git history keeps their sources.

World Cup data is a locked historical snapshot covering men's editions through 2022 and women's editions through 2019. See each sample's README for its data scope, license and scenario assumptions.

## Scenario evaluation

Each sample keeps its business-scenario test set under `bkn-eval/baselines/`, with a PRD-mapped question set (12 basic, 20 medium, 18 complex), a withheld answer set, the oracle that computes it from the delivered data, and the recorded MCP agent run.

An independent external agent answers the questions through MCP. Reference answers are withheld during evaluation, then used to check business values. Record the tested package and actual results for each evaluation.

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

[Supply shortage rule follow-up #190](docs/shortage-rule-190.md): retired; supply-chain 0.1.17 and supply-chain-en 0.1.11 no longer publish it.

See the [0.2.1 release record](docs/release-0.2.1-20261031.md) for the published set, the withdrawn versions and the deleted releases; the earlier plan is the [release retention and 021 promotion plan](docs/release-retention-20261030.md).
