# BKN Samples

[中文版 (Chinese)](./README_cn.md)

Official OpenBKN experience samples: knowledge network models, sample data, and step-by-step import tools.

## Prerequisites

- [OpenBKN platform install (Feishu guide)](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde)
- [openbkn CLI (bkn-sdk)](https://github.com/openbkn-ai/bkn-sdk)
- Python 3.11+ (for `tools/` scripts inside each sample)

## Samples

| Sample | KN ID | Description |
|--------|-------|-------------|
| [supply_ontology_hand](samples/supply_ontology_hand/) | `supply_ontology_hand` | Supply chain ontology hand edition: CSV load → Catalog scan → OT bind → Agent scenarios |
| [world-cup](samples/world-cup/) | `worldcup_vega_catalog_bkn` | 27 public World Cup CSVs (CC-BY-SA) → MySQL → Vega catalog → BKN push + index build → published `vega_sql_execute` tool. Single `./run.sh`, six idempotent steps |

> More samples coming (e.g. `supply-chain-skill`).

## Layout

Each sample is a **self-contained package**:

```
samples/<slug>/
├── README.md              # English (default)
├── README_cn.md           # 中文
├── kn/
├── data/
├── tools/
└── docs/
    ├── openbkn-hand-import-guide.md
    ├── openbkn-hand-import-guide_cn.md
    ├── agent-scenario-kn-capability-design.md
    └── agent-scenario-kn-capability-design_cn.md
```

**Doc naming:** English base filename; Chinese adds `_cn` (e.g. `openbkn-hand-import-guide_cn.md`).

## Contributing

Add a new sample under `samples/<slug>/` with README (EN + `_cn`), data, tools, docs, and update the table above.

Sample changes must follow the [PR review rules](docs/review/sample-pr-review-rules.md). Include the PR template evidence; publication requires verification of the exact candidate artifacts.

## Dynamic sample publication

The [publication protocol draft](protocol/draft/README.md) defines independent sample versions, release notes and content references. See the [cross-repository implementation plan](protocol/draft/implementation-plan.md). The draft examples are illustrative; the root `catalog.json` lists published fixed releases. See the [Sample Development Guide](docs/SAMPLE_DEVELOPMENT_GUIDE.md) and [中文开发与版本更新指南](docs/SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md) for new samples and versions, and [service deployment](docs/sample-service-deployment.md) for the existing platform cluster.
