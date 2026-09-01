# OpenBKN Hand Import Guide

[中文版 (Chinese)](./openbkn-hand-import-guide_cn.md)

**Version:** v0.3  
**Status:** Published in [bkn-samples](https://github.com/openbkn-ai/bkn-samples); steps 3–5 are scriptable; P0 acceptance checklist in Appendix D  
**Package:** `samples/supply_ontology_hand/` ([openbkn-ai/bkn-samples](https://github.com/openbkn-ai/bkn-samples))  
**Knowledge network:** Supply Chain Ontology — Hand Edition (ID: `supply_ontology_hand`)

This document is the **single operational entry point** for the hand experience pack. Follow steps 1–7 in order to: import the knowledge network → load sample data → catalog scan → bind object types → run scenario tests. Scripts live under `tools/`; sample CSVs under `data/`.

---

## Audience and prerequisites

**Audience:** Customers and ecosystem partners (self-service OpenBKN evaluation). Implementation teams may assist, but the doc is written for self-contained execution.

**Before you start:**

| Item | Description |
|------|-------------|
| OpenBKN platform | Deployed and Web UI accessible; see [Feishu install guide](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde) |
| openbkn CLI | **Required for steps 4–5**; install and auth in §1.2–1.4 ([bkn-sdk](https://github.com/openbkn-ai/bkn-sdk)) |
| Account permissions | Import knowledge networks; manage data sources and Catalogs |
| Target database | PostgreSQL or MySQL (your instance, for sample data load) |
| This package | Full `samples/supply_ontology_hand/` directory |
| Python 3.11+ | Run load, catalog, bind, and smoke scripts under `tools/` |

**Key files in the package:**

- Knowledge network model: `kn/supply_ontology_hand.json`
- Sample data: `data/` (12 CSV files)
- Config template: `tools/config.example.yaml` → copy to `config.yaml` and edit
- Canonical scenario design (Chinese): `docs/场景驱动的供应链动态能力设计.md`
- Eval set / import verification: `docs/业务问答测试集.md` · `docs/Agent导入验证清单.md`

---

## Third-party environment customization

The pack is meant for customers/partners deploying **in their own environment**. Rule: **change config, not contract assets**.

### Must customize (`tools/config.yaml`)

| Section | Typical fields | Notes |
|---------|----------------|-------|
| `database` | `engine`, `host`, `port`, `database`, `user`, `password` | Step 3 load; DB must exist (`CREATE DATABASE` first) |
| `database.schema` | Usually `public` for PostgreSQL | Ignore for MySQL |
| `vega.catalog_host` | Often `host.docker.internal` in Docker/K8s | OpenBKN **connects to DB**; may differ from `database.host` (local load, often `127.0.0.1`) |
| `vega.catalog_name` | Custom name; avoid collisions | Used when step 4 creates Catalog |
| `vega.catalog_id` | Fill after step 4 or via `--write-config` | Required for step 5 bind |

When handing off to an agent or implementer, provide at least: `engine`, `host`, `port`, `database` (empty DB created), `user`, `password`; if OpenBKN runs in containers, also specify `catalog_host`.

### Do not change (unless you know how to sync)

| Asset | Reason |
|-------|--------|
| `data/*.csv` file stems | Must match Catalog table names and `object_table_map.yaml` |
| `tools/mapping/object_table_map.yaml` | OT ↔ table ↔ primary key mapping |
| `kn_id` in `kn/supply_ontology_hand.json` | Must be ≤32 chars; arbitrary changes may break import |
| `openbkn.kn_id` in `config.yaml` | Must match imported KN (default `supply_ontology_hand`) |

### Usually no change needed

| Asset | Notes |
|-------|-------|
| `load_sample_data.py` / `setup_catalog.py` / `bind_kn_resources.py` | Adapt via `config.yaml` only |
| `data/` contents | Built-in anonymized samples |

> `config.yaml` contains DB passwords — **do not commit** (`tools/.gitignore` excludes it).

---

## Step 1: Platform readiness

Confirm OpenBKN platform and local CLI before importing the KN. Steps 4–5 use `openbkn` CLI — **complete CLI install and auth first**.

### 1.1 Install OpenBKN platform (Web)

Follow the official deployment guide and log in to the Web console:

- **Platform install:** [OpenBKN platform install (Feishu)](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde)

**Manual checks:**

- [ ] Web console login works
- [ ] LLM / small-model chat works (Agent / model factory)

> Step 2 can use Web UI; steps 4–5 require CLI below.

### 1.2 Install openbkn CLI

CLI from [@openbkn-ai/bkn-sdk](https://github.com/openbkn-ai/bkn-sdk); requires **Node.js 22+**.

```bash
npm install -g @openbkn/bkn-sdk
openbkn --help
```

Or run without global install:

```bash
npx @openbkn/bkn-sdk --help
```

Success: `openbkn --help` lists command groups (`auth`, `vega`, `bkn`, etc.).

### 1.3 Authentication (`openbkn auth login`)

Credentials stored in `~/.bkn/` (override with `BKN_CONFIG_DIR`). **Do not put platform URL/token in `config.yaml`** — use `auth login`.

Replace `<platform-url>` with your base URL (e.g. `https://openbkn.example.com` or `http://localhost`), **no path suffix**.

**Option A — Browser (recommended):**

```bash
openbkn auth login <platform-url>
```

**Option B — Device code (headless / remote):**

```bash
openbkn auth login <platform-url> --device
# or: openbkn auth login <platform-url> --no-browser
```

**Option C — Username/password:**

```bash
openbkn auth login <platform-url> -u <username> -p <password>
```

**Option D — Existing token:**

```bash
openbkn auth login <platform-url> --token "<access-token>"
```

**Self-signed HTTPS:**

```bash
openbkn auth login -k <platform-url>
```

### 1.4 Verify CLI session

```bash
openbkn auth status
openbkn auth whoami
```

**Expected:** `hasToken: true`, not expired; `whoami` shows user.

| Command | Purpose |
|---------|---------|
| `openbkn auth list` | List saved sessions |
| `openbkn auth use <url>` | Switch active platform |
| `openbkn auth token` | Print token (do not leak) |
| `openbkn auth logout` | Clear token |

**Step 1 checklist:**

- [ ] Web console OK
- [ ] `openbkn --help` works
- [ ] `openbkn auth status` authenticated

---

## Step 2: Import knowledge network (UI / script / agent)

**Import file:** `kn/supply_ontology_hand.json`  
**Expected:** ID `supply_ontology_hand`, name `供应链本体知识网络-手工版` (Supply Chain Ontology — Hand Edition)

### Option A — Web UI

1. Knowledge networks → Import / upload JSON
2. Select the file above
3. Verify in the list after import

### Option B — Script (recommended)

```bash
cd tools
openbkn auth status
python3 import_kn.py
openbkn --json bkn get supply_ontology_hand
```

`import_kn.py` reads `../kn/supply_ontology_hand.json` by default, calls import API via `openbkn call`, and verifies with `bkn get`.

**Equivalent one-liner:**

```bash
openbkn --json call -X POST /api/ontology-manager/v1/knowledge-networks \
  -d "$(cat ../kn/supply_ontology_hand.json)"
openbkn --json bkn get supply_ontology_hand
```

> If the platform reports a name conflict, remove or rename the existing KN, or use UI overwrite (platform-dependent).

### Option C — Agent prompt

```text
You are an OpenBKN implementation assistant. With openbkn auth login done, run "Step 2: Import KN" for the experience pack.

Working directory: <package-root>
KN file: <package-root>/kn/supply_ontology_hand.json
Target kn_id: supply_ontology_hand
Target name: 供应链本体知识网络-手工版

Steps:
1. openbkn auth status
2. In <package-root>/tools: python3 import_kn.py (or equivalent openbkn call POST)
3. openbkn --json bkn get supply_ontology_hand
4. Report kn_id and name; on failure give stderr and UI fallback

Do not change kn_id in JSON; do not commit config.yaml.
```

### Acceptance

| Field | Expected |
|-------|----------|
| Name | `供应链本体知识网络-手工版` |
| ID | `supply_ontology_hand` (≤32 chars; do not lengthen) |

---

## Step 3: Load sample data (script)

Load `data/` CSVs into your database.

1. Copy `tools/config.example.yaml` → `tools/config.yaml`
2. Edit **`database`** section (no `vega.catalog_id` needed yet; platform auth is via step 1)

**Required `database` fields:**

| Field | Required | Notes |
|-------|----------|-------|
| `engine` | Yes | `postgres` or `mysql` |
| `host` / `port` | Yes | PG usually 5432; MySQL 3306 |
| `database` | Yes | Target DB name (must exist) |
| `user` / `password` | Yes | CREATE/DROP/INSERT rights; **`password` required** for OpenBKN connector |
| `schema` | PG recommended | Usually `public`; ignore for MySQL |

**Create empty database first:**

```sql
-- PostgreSQL
CREATE DATABASE supply_demo_hand;

-- MySQL
CREATE DATABASE supply_demo_hand CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Run:**

```bash
cd tools
cp config.example.yaml config.yaml
python3 -m pip install -r requirements.txt
python3 load_sample_data.py --config config.yaml
```

**Behavior:** `sample_dir` defaults to `../data`; `mode: recreate` drops and rebuilds 12 tables; load order in Appendix A.

**Acceptance:**

- [ ] 12 tables visible with data
- [ ] No fatal errors; row counts reasonable

---

## Step 4: Catalog attach and scan (script / agent)

Create a **Catalog / data source** pointing at the step 3 database, enable, discover 12 tables, write `catalog_id` to `config.yaml`.

**Prerequisites:** Step 3 done; `openbkn auth status` OK; OpenBKN can reach DB (often `vega.catalog_host: host.docker.internal` when platform is in Docker).

**`vega` section in `config.yaml`:**

| Field | Notes |
|-------|-------|
| `catalog_name` | e.g. `supply-demo-hand` |
| `catalog_host` | Host OpenBKN uses to reach DB |
| `catalog_id` | Empty first time; `--write-config` fills it |
| `connector_type` | `postgresql` or `mysql` |

> For Docker/K8s, set a real PostgreSQL password and put the same value in `database.password`.

```bash
cd tools
openbkn auth status
python3 setup_catalog.py --config config.yaml --write-config
```

**Acceptance:**

- [ ] `verification.ok: true`, `found_count: 12`
- [ ] `vega.catalog_id` in `config.yaml`

**UI fallback if script fails:** Create data source in Web UI, enable, discover, copy `catalog_id` to `config.yaml`.

---

## Step 5: Bind object types (script / agent)

Bind OTs to Catalog resources (`data_source.type=resource`).

```bash
cd tools
openbkn auth status
python3 bind_kn_resources.py --config config.yaml --dry-run
python3 bind_kn_resources.py --config config.yaml
openbkn --json bkn object-type query supply_ontology_hand supply_ontology_hand_product --body '{"limit":3}'
```

**Notes:**

- Mapping: `tools/mapping/object_table_map.yaml`
- `bind: false` OTs (e.g. `supply_ontology_hand_mon_task`) are skipped
- Optional: `bkn build` for search/vector index
- Query should return non-empty instances

**UI fallback:** Manually bind each OT in the console to the scanned table; verify primary keys per Appendix B.

---

## Step 6: Scenario extension (optional)

Does not block P0. See [场景驱动的供应链动态能力设计](./场景驱动的供应链动态能力设计.md) for S1–S6 (this KN + CSV snapshots; do not use `supplychain_hd0202` counts).

| Priority | Content |
|----------|---------|
| **P0** | Steps 1–5 done; Q1–Q4 in step 7 not failing on “no data / unbound” |
| **P1** | Metrics, S1 backward scheduling, Action re-bind in your environment |

**Safety:** Do not auto-run `initiate_po` or other write Actions without human confirmation.

---

## Step 7: Comparison testing

Full Q&A gold set: [业务问答测试集](./业务问答测试集.md). Post-import checklist: [Agent导入验证清单](./Agent导入验证清单.md). Power layer (step 8): [动力层落地说明书](./动力层落地说明书.md).

**Minimum smoke (must match this pack’s CSV — not 431 / Kunshan warehouses):**

| # | Question | Expected |
|---|----------|----------|
| Q1 | How many finished products do we have? | **30** |
| Q2 | Basic info for product `382-000005` | Name includes 北斗导航农机驾驶仪 |
| Q3 | How many sales orders for `382-000005`? | **40**; SO linkage works |
| Q4 | Finished-goods available qty for `382-000005`? | ≈ **534** (Suzhou + Urumqi + Harbin FG) |
| Q5 | Backward kit plan for `382-000005`, due `2026-05-14` | Written report; L1 `791-000007` / `791-000015` avail = 0; no auto PO |

```bash
cd tools
python3 smoke_test.py --config config.yaml
python3 power_layer.py all --kn-id supply_ontology_hand
```

Smoke checks KN name, OT row counts, and `join_checks` hit rates. `power_layer.py` creates metrics, binds object logic properties, and verifies CSV snapshots. Step 8 details: [动力层落地说明书](./动力层落地说明书.md). Q5 quality is manual.

---

## Appendix A: Tables and load order

| Order | CSV | Table | Notes |
|-------|-----|-------|-------|
| 1 | `erp_material.csv` | `erp_material` | Materials |
| 2 | `hd_product_view.csv` | `hd_product_view` | Products |
| 3 | `erp_material_bom.csv` | `erp_material_bom` | BOM |
| 4 | `erp_real_time_inventory.csv` | `erp_real_time_inventory` | Inventory |
| 5 | `erp_supplier.csv` | `erp_supplier` | Suppliers |
| 6 | `erp_mds_forecast.csv` | `erp_mds_forecast` | Forecast |
| 7 | `erp_mrp_plan_order.csv` | `erp_mrp_plan_order` | MRP |
| 8 | `erp_purchase_request.csv` | `erp_purchase_request` | PR |
| 9 | `erp_purchase_order.csv` | `erp_purchase_order` | PO |
| 10 | `erp_production_work_order.csv` | `erp_production_work_order` | Work orders |
| 11 | `customer_entity.csv` | `customer_entity` | Customers |
| 12 | `sales_order.csv` | `sales_order` | Sales orders |

---

## Appendix B: Object mapping summary

Full mapping: `tools/mapping/object_table_map.yaml`.

| OT | Table | Primary keys | Notes |
|----|-------|--------------|-------|
| Product | `hd_product_view` | `material_code` | |
| Material | `erp_material` | `material_code` | |
| BOM | `erp_material_bom` | `bom_version`, `bom_material_code`, `seq_no` | |
| Inventory | `erp_real_time_inventory` | `id` | |
| Supplier | `erp_supplier` | `supplier_code` | |
| Forecast | `erp_mds_forecast` | `id` | |
| MRP | `erp_mrp_plan_order` | `billno` | |
| PR | `erp_purchase_request` | `entry_id` | |
| PO | `erp_purchase_order` | `entry_id` | |
| Work order | `erp_production_work_order` | `entry_id` | OT `…_mps` |
| Sales order | `sales_order` | `sales_order_id` | |
| Monitor task | — | — | No sample table |
| (no OT) | `customer_entity` | — | Load only |

**P0 join checks (after bind):**

| Relation | Expectation |
|----------|-------------|
| SO → product | 100% hit on `product_code` |
| Product → forecast | Seed products have forecast |
| BOM → material | No orphan material codes |
| PO → supplier | Supplier codes resolve |
| PO → PR | `srcbillentryid` → `entry_id` (~95%+ in sample data) |

---

## Appendix C: Troubleshooting

| Symptom | Cause | Action |
|---------|-------|--------|
| No token / expired | Not logged in | `openbkn auth login <url>` |
| TLS error | Self-signed cert | `openbkn auth login -k <url>` |
| 401 on step 4/5 | Wrong active platform | `openbkn auth list` → `auth use` |
| Invalid KN ID | ID > 32 chars | Use `supply_ontology_hand` |
| Import name exists | KN name collision | Remove conflict or UI import |
| Load connection failed | DB missing / wrong creds | `CREATE DATABASE`; check `config.yaml` |
| Catalog incomplete connector | Missing `password` | Set PG password; fill `database.password` |
| Discover missing tables | Scan not finished | Run `python3 tools/setup_catalog.py --config tools/config.yaml --write-config`; it polls the discovery task before verifying tables. |
| Query empty after bind | Wrong table/PK | Check Appendix B; UI re-bind |
| Script bind failed | CLI version / permissions | Step 5 UI fallback |

---

## Appendix D: P0 / P1 acceptance

### P0 (required)

- [ ] Steps 1–7 runnable from this guide
- [ ] `load_sample_data.py` loads 12 tables (PostgreSQL preferred in production)
- [ ] KN import OK; `supply_ontology_hand` visible
- [ ] Core OT queries non-empty after bind
- [ ] `smoke_test.py` passes
- [ ] At least 3 of Q1–Q4 pass in Agent UI

### P1 (enhancement)

- [ ] Metrics / logic properties (e.g. effective warehouse stock)
- [ ] Q5 backward scheduling answer quality
- [ ] Actions re-bound in your environment

| Field | Value |
|-------|-------|
| Environment | (fill in) |
| Date | (fill in) |
| Verifier | (fill in) |
| P0 result | ☐ Pass / ☐ Retest |
