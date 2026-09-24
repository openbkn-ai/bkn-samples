# BKN Samples

[中文版 (Chinese)](./README_cn.md)

Official OpenBKN experience samples: knowledge network models, sample data, and step-by-step import tools.

## One-command install

After logging in with an OpenBKN administrator account, install a sample from a repository checkout:

```bash
./install.sh list
./install.sh supply-chain --runtime k8s
./install.sh world-cup --runtime k8s
```

For a Docker runtime outside the OpenBKN cluster, provide the host address that Vega can reach. The installer uses a per-sample default port (`13306` for supply-chain and `13307` for world-cup):

```bash
./install.sh supply-chain --runtime docker --catalog-host 10.0.0.8
```

If no local session exists, the installer guides an interactive `openbkn auth login <url> --device`; non-interactive runs print the exact login command and stop. Use `--dry-run` to inspect the plan without writes.

The installer requires an `openbkn` release whose `vega catalog create`, `update`, and `test-connection-config` commands support `--connector-config-file`. It never falls back to passing the database password in command-line JSON.

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
