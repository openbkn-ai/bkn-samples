# OpenBKN 手工体验导入说明书

**版本：** v0.3  
**状态：** 已发布至 [bkn-samples](https://github.com/openbkn-ai/bkn-samples)；步骤 3～5 可脚本化执行；P0 环境验收见附录 D  
**交付包：** `samples/supply_ontology_hand/`（仓库 [openbkn-ai/bkn-samples](https://github.com/openbkn-ai/bkn-samples)）  
**知识网络：** `供应链本体知识网络-手工版`（ID: `supply_ontology_hand`）

本文档是手工体验包的**唯一操作入口**。按步骤 1～7 顺序执行，即可完成：导入知识网络 → 灌入体验样例数据 → 挂接扫描 → 绑定 → 场景对比测试。工具脚本位于 `tools/`，样例 CSV 位于 `data/`。

---

## 适用对象与准备清单

**适用对象：** 客户与生态伙伴（自助体验 OpenBKN）；实施同学可带跑，但文档按自助闭环编写。

**开始前请准备：**

| 项 | 说明 |
|----|------|
| OpenBKN 平台 | 已部署并可登录 Web；安装见 [飞书文档](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde) |
| openbkn CLI | **步骤 4～5 必需**；安装与认证见说明书 §1.2～1.4（[bkn-sdk](https://github.com/openbkn-ai/bkn-sdk)） |
| 账号权限 | 可导入知识网络、管理数据源与 Catalog |
| 目标数据库 | PostgreSQL 或 MySQL（自备实例，用于灌入体验样例数据） |
| 本体验包 | `samples/supply_ontology_hand/` 完整目录 |
| Python 3.11+ | 运行 `tools/` 下灌库、Catalog 扫描、绑定与冒烟脚本 |

**包内关键文件：**

- 知识网络模型：`kn/supply_ontology_hand.json`
- 体验样例数据：`data/`（12 张 CSV）
- 工具配置模板：`tools/config.example.yaml` → 复制为 `config.yaml` 后按环境修改
- 场景能力设计（主文档）：`docs/场景驱动的供应链动态能力设计.md`  
- 业务问答测试集 / 导入验证：`docs/业务问答测试集.md` · `docs/Agent导入验证清单.md`
- 动力层（步骤 8）：`docs/动力层落地说明书.md` · `tools/power_layer.py`

---

## 第三方环境定制说明

体验包面向客户 / 生态伙伴**在自己环境**自助部署。原则：**改配置，不改包内契约资产**。

### 必须按环境修改（`tools/config.yaml`）

| 配置段 | 常见改项 | 说明 |
|--------|----------|------|
| `database` | `engine`、`host`、`port`、`database`、`user`、`password` | 步骤 3 灌库连接；库名可自定，须预先 `CREATE DATABASE` |
| `database.schema` | PostgreSQL 通常 `public` | MySQL 可忽略 |
| `vega.catalog_host` | Docker/K8s 部署时常为 `host.docker.internal` | OpenBKN **连库**用；与 `database.host`（本机灌库，常 `127.0.0.1`）可不同 |
| `vega.catalog_name` | 可自定，避免与他人 Catalog 重名 | 步骤 4 脚本创建 Catalog 时使用 |
| `vega.catalog_id` | 步骤 4 成功后填入或 `--write-config` 自动回写 | 步骤 5 绑定必需 |

交给 Agent 或实施同学时，至少提供：`engine`、`host`、`port`、`database`（已建空库）、`user`、`password`；若 OpenBKN 在容器内，另说明 `catalog_host`。

### 建议不要修改（除非你知道如何同步）

| 资产 | 原因 |
|------|------|
| `data/*.csv` 文件名（表 stem） | 须与 Catalog 扫描表名、`object_table_map.yaml` 一致 |
| `tools/mapping/object_table_map.yaml` | 对象类 ↔ 表 ↔ 主键映射；改表名须同步改此文件 |
| `kn/supply_ontology_hand.json` 中的 `kn_id` | 须 ≤32 字符；随意改可能导致导入失败 |
| `config.yaml` 中的 `openbkn.kn_id` | 须与步骤 2 导入后的 KN ID 一致（默认 `supply_ontology_hand`） |

### 一般无需修改

| 资产 | 说明 |
|------|------|
| `load_sample_data.py` / `setup_catalog.py` / `bind_kn_resources.py` | 通过 `config.yaml` 适配环境即可 |
| `data/` 数据内容 | 体验包自带脱敏样例，直接灌库 |

> `config.yaml` 含数据库密码，**勿提交版本库**（`tools/.gitignore` 已忽略）。

---

## 步骤 1：平台就绪检查

在导入知识网络之前，确认 OpenBKN 平台与本机 CLI 均已就绪。步骤 4～5 的 Catalog 扫描、绑定脚本通过 `openbkn` CLI 调用平台 API，**须先完成本节 CLI 安装与认证**。

### 1.1 安装 OpenBKN 平台（Web）

按官方部署文档完成平台安装，并能通过浏览器登录 Web 控制台：

- **平台安装参考：** [OpenBKN 平台安装（飞书文档）](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde)

**人工检查项：**

- [ ] 能登录 OpenBKN Web 控制台
- [ ] 大小模型可正常对话（Agent / 模型工厂可用）
- [ ] 目标环境已配置默认 embedding 模型（脚本导入会自动读取）

> 步骤 2 导入知识网络可在 Web UI 完成；步骤 4～5 依赖 CLI，见下文。

### 1.2 安装 openbkn CLI

CLI 来自官方 SDK 仓库 [@openbkn-ai/bkn-sdk](https://github.com/openbkn-ai/bkn-sdk)，需 **Node.js 22+**。

```bash
npm install -g @openbkn/bkn-sdk
openbkn --help
```

也可用临时运行（不全局安装）：

```bash
npx @openbkn/bkn-sdk --help
```

验证安装成功：`openbkn --help` 能输出命令组列表（含 `auth`、`vega`、`bkn` 等）。

### 1.3 认证（`openbkn auth login`）

CLI 凭据保存在本机 `~/.bkn/`（可用环境变量 `BKN_CONFIG_DIR` 改目录）。**体验包不在 `config.yaml` 里配置 OpenBKN 平台 URL / Token**，统一用 `auth login` 写入会话。

将 `<platform-url>` 替换为实际平台根地址（示例：`https://openbkn.example.com` 或本机 `http://localhost`），**不要**附带路径后缀。

**方式 A — 浏览器登录（推荐，有桌面环境）：**

```bash
openbkn auth login <platform-url>
```

终端会给出验证链接与用户码，并尝试打开浏览器；在浏览器中登录并批准即可。

**方式 B — 无浏览器 / 远程机器（device code）：**

```bash
openbkn auth login <platform-url> --device
# 或：openbkn auth login <platform-url> --no-browser
```

在任意能打开浏览器的机器上访问 printed URL，输入 user code 完成授权。

**方式 C — 用户名密码（headless / CI）：**

```bash
openbkn auth login <platform-url> -u <username> -p <password>
```

未传的 `-u` / `-p` 会在终端提示输入。

**方式 D — 直接附加已有 Token：**

```bash
openbkn auth login <platform-url> --token "<access-token>"
```

适用于 CI 或已由管理员签发 Token 的场景（无 refresh，到期需重新 login）。

**自签名 HTTPS 平台：**

```bash
openbkn auth login -k <platform-url>
```

`-k` 对该平台关闭 TLS 校验（仅影响该平台请求）；登录成功后，后续命令一般无需再带 `-k`。

### 1.4 验证 CLI 会话

```bash
openbkn auth status
openbkn auth whoami
```

**期望结果：**

- `auth status`：显示 `baseUrl`、已配置 Token（如 `hasToken: true`）、未过期
- `auth whoami`：显示当前用户名 / 用户 ID

**常用会话命令（排错时可查）：**

| 命令 | 用途 |
|------|------|
| `openbkn auth list` | 列出已保存的平台会话 |
| `openbkn auth use <url>` | 切换当前活跃平台 |
| `openbkn auth token` | 打印 access token（勿泄露） |
| `openbkn auth logout` | 清除当前平台 Token |

**步骤 1 验收清单：**

- [ ] 平台 Web 控制台可登录
- [ ] `openbkn` 已安装且 `openbkn --help` 正常
- [ ] `openbkn auth status` 显示已认证，`whoami` 有当前用户

> 本包不替代官方安装手册；平台或 CLI 未就绪时，请先完成 [平台安装](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde) 与 [bkn-sdk](https://github.com/openbkn-ai/bkn-sdk) 文档中的部署说明，再继续步骤 2。

---

## 步骤 2：导入知识网络（UI / 脚本 / Agent）

**导入文件：** `kn/supply_ontology_hand.json`  
**期望结果：** 网络 ID `supply_ontology_hand`，名称 `供应链本体知识网络-手工版`

### 方式 A — Web UI（手工）

**操作面：** OpenBKN Web UI（知识网络管理）

> 当前 Sample JSON 可能包含制作环境遗留的 embedding 模型 ID，直接上传原始 JSON 可能报「小模型获取失败」。生态伙伴优先使用下方脚本方式；若必须手工导入，应先使用目标环境可用的 embedding 模型处理便携 JSON。

1. 进入「知识网络」→「导入 / 上传 JSON」
2. 选择上述 JSON 文件并提交
3. 导入完成后在列表中验收

### 方式 B — 脚本（推荐）

**前置：** 已完成步骤 1（`openbkn auth status` 正常）。

```bash
cd tools
openbkn auth status
openbkn --json model small get-default --type embedding
python3 import_kn.py --resolve-embedding
openbkn --json bkn get supply_ontology_hand
```

`import_kn.py` 默认读取 `../kn/supply_ontology_hand.json`。`--resolve-embedding` 会先读取目标环境的默认 embedding 模型，并替换 JSON 中原环境遗留的模型 ID，再通过 `openbkn call` 调用平台导入 API，最后校验 `bkn get` 可读到目标 ID。

这是推荐方式。不要省略 `--resolve-embedding`：Sample JSON 不能假设生态伙伴的平台与制作 Sample 的平台使用同一个 embedding 模型 ID。

**关于直接调用 API：** 不建议直接把原始 JSON 通过 `openbkn call` POST 导入，因为其中可能包含原环境的 embedding 模型 ID。若必须直接调用 API，应先在目标平台选择可用的 embedding 模型，或使用已清除环境模型引用的便携 JSON。

> 若平台返回「名称已存在」，说明同名校验冲突：删除或重命名平台上已有 KN 后重试，或改用 UI 覆盖导入（视平台版本而定）。

### 方式 C — 交给 Agent（提示词）

将下列提示词复制到 Cursor / 其他 Agent（请把 `<体验包根目录>` 换为实际路径）：

```text
你是 OpenBKN 实施助手。请在已完成 openbkn auth login 的前提下，为体验包执行「步骤 2：导入知识网络」。

工作目录：<体验包根目录>
KN 文件：<体验包根目录>/kn/supply_ontology_hand.json
目标 kn_id：supply_ontology_hand
目标名称：供应链本体知识网络-手工版

请依次：
1. 运行 openbkn auth status，确认已认证
2. 在 <体验包根目录>/tools 先运行 `openbkn --json model small get-default --type embedding`，再执行 `python3 import_kn.py --resolve-embedding`
3. 运行 openbkn --json bkn get supply_ontology_hand 验收
4. 回报 kn_id、名称是否与上一致；失败则给出 stderr 与 UI 降级建议

约束：勿修改 JSON 内 kn_id；勿提交 config.yaml。
```

### 验收标准

| 项 | 期望值 |
|----|--------|
| 网络名称 | `供应链本体知识网络-手工版` |
| 网络 ID | `supply_ontology_hand` |

**重要：网络 ID 长度限制**

- OpenBKN 要求知识网络 ID **≤ 32 字符**
- 本体验包已校验 ID 为 `supply_ontology_hand`（22 字符），可直接使用
- 若自行修改 ID 或加长前缀，可能触发「ID 参数无效」导入失败；请勿随意加长

---

## 步骤 3：灌入样例数据（脚本）

**操作面：** 命令行脚本（将 `data/` 体验样例数据写入自备数据库）

**配置文件：**

1. 复制 `tools/config.example.yaml` → `tools/config.yaml`（含密钥，勿提交版本库）
2. 编辑 `config.yaml` 中的 **`database` 段**（本步骤仅灌库，**不必**填写 `vega.catalog_id`；OpenBKN 平台地址通过步骤 1 的 `openbkn auth login` 认证，不在此文件配置）

**用户必填项（`database` 段）：**

| 字段 | 是否必填 | 说明 |
|------|----------|------|
| `engine` | 是 | `postgres` 或 `mysql` |
| `host` | 是 | 数据库实例地址 |
| `port` | 是 | PostgreSQL 通常 `5432`；MySQL 通常 `3306` |
| `database` | 是 | **目标库名**（可自定义，见下文「库名与覆盖策略」） |
| `user` / `password` | 是 | 须对该库具备建表、删表、插入权限；**OpenBKN 连接器要求 `password` 字段必填**（Docker 网段连库须设真实密码，见下文） |
| `schema` | PostgreSQL 建议填 | 通常 `public`；**MySQL 可忽略**（无 PG 式 schema） |

**先建空库（脚本不建库）：**

在运行灌库脚本前，请在目标实例上**预先创建**空库（库名与 `config.yaml` 中 `database` 一致）。示例：

```sql
-- PostgreSQL
CREATE DATABASE supply_demo_hand;

-- MySQL
CREATE DATABASE supply_demo_hand CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**库名与覆盖策略：**

| 情况 | 脚本行为 | 建议 |
|------|----------|------|
| 库名已存在（空库） | 正常连接，按 `load_order` 建 12 张表并灌入 | 推荐：专用体验库，如 `supply_demo_hand` |
| 库名已存在，且已有同名 12 表 | 默认 `mode: recreate`：**先 `DROP TABLE` 再重建**，原表数据被覆盖 | 勿指向生产/共用库 |
| 库名已存在，仅有其他名字的表 | 只处理体验包 12 表，**不影响**其他表 | 可用，但建议仍用专用库 |
| 库不存在 | 连接失败 | 先执行上方 `CREATE DATABASE` |
| 想换库名 | 修改 `config.yaml` 的 `database` 即可；**步骤 4 Catalog 须指向同一库** | 示例名 `supply_demo_hand` 非强制 |

> `config.example.yaml` 中的库名、账号均为示例。自助体验或交给 Agent 执行时，请明确提供：`engine`、`host`、`port`、`database`（已建空库）、`user`、`password`。

**执行脚本：**

```bash
cd tools
cp config.example.yaml config.yaml
python3 -m pip install -r requirements.txt
python3 load_sample_data.py --config config.yaml
```

**脚本行为（概要）：**

- 读取 `config.yaml` 中的 `sample_dir`（默认指向 `../data`）
- 默认 `mode: recreate`：对 12 张体验表执行 `DROP TABLE IF EXISTS` → 建表 → 插入（**无二次确认**）
- 按附录 A 的灌库顺序建表并导入 CSV
- 表名与 CSV 文件名 stem 一致（如 `erp_material`），便于步骤 4 扫描匹配
- 输出每张表的灌入行数；失败时按配置停止或跳过

**验收标准：**

- [ ] 12 张业务表在目标库中可见且有数据
- [ ] 控制台无致命错误；行数报告与 CSV 大致一致

> 灌库顺序见附录 A；MySQL / PostgreSQL 连接参数见 `config.example.yaml`。

---

## 步骤 4：挂接与扫描（脚本 / Agent）

**操作面：** 命令行脚本（推荐）或 OpenBKN Web UI（降级）

本步骤在 OpenBKN 上建立指向步骤 3 灌库数据库的 **Catalog / 数据源**，**Enable** 连接并 **Discover** 扫描 12 张体验表。完成后将 `catalog_id` 写入 `config.yaml`，供步骤 5 绑定使用。

**依赖：**

- 步骤 3 已完成（目标库中 12 表有数据）
- 本机已 `openbkn auth login` 且 `openbkn auth status` 正常
- OpenBKN 平台能访问 PostgreSQL/MySQL（`vega.catalog_host` 必须填写从平台容器/集群可解析、可连接的数据库主机；不得假定 `host.docker.internal` 在远程 POC 或伙伴环境存在。本机灌库使用 `database.host`。）

**配置文件（`tools/config.yaml`）：**

除 `database` 段外，填写或确认 `vega` 段：

| 字段 | 说明 |
|------|------|
| `catalog_name` | 新建 Catalog 名称（默认可用 `supply-demo-hand`） |
| `catalog_host` | OpenBKN **连库用**主机名；必须由部署者验证平台网络可达，不能照抄 `host.docker.internal` |
| `catalog_id` | 首次留空；脚本成功后可 `--write-config` 自动回写 |
| `connector_type` | PostgreSQL 填 `postgresql`；MySQL 填 `mysql` |

> OpenBKN 在 Docker/K8s 内通过 `catalog_host`（如 `host.docker.internal`）连库时，PostgreSQL 通常走 **192.168.65.x / 172.x 网段**，`pg_hba` 默认要求密码认证。请：
> 1. 在 PostgreSQL 侧为用户设置密码（示例）：
>    ```sql
>    ALTER USER your_user WITH PASSWORD 'your_password';
>    ```
> 2. 将同一密码写入 `config.yaml` 的 `database.password`（脚本会原样传给 Catalog 连接器，**不可省略 `password` 字段**）。

**执行脚本（推荐）：**

```bash
cd tools
openbkn auth status
python3 setup_catalog.py --config config.yaml --write-config
```

**脚本行为（概要）：**

1. 按 `database` + `vega.catalog_host` 组装连接器配置  
2. 若 `catalog_id` 为空：按 `catalog_name` 查找已有 Catalog，否则 `vega catalog create`  
3. `vega catalog enable` → `test-connection` → 触发异步 `discover` 并轮询任务终态
4. 校验 Catalog 中可见附录 A 的 **12 张表**  
5. `--write-config` 时将 `catalog_id` 写回 `config.yaml`

**验收标准：**

- [ ] 脚本输出 `verification.ok: true`，且 `found_count: 12`
- [ ] `config.yaml` 中 `vega.catalog_id` 已填写（或手工从输出复制）

**若 verification 报缺表（discover 尚未完成）：**

```bash
openbkn --json vega catalog discover <catalog_id>
# 记下返回的 task id，再查询：openbkn --json vega discover-task get <task_id>
python3 setup_catalog.py --config config.yaml --write-config
```

**CLI 手工验收（可选）：**

```bash
openbkn --json vega catalog resources <catalog_id> --category table --limit -1
```

**UI 降级路径：脚本失败 → 控制台手建**

若 CLI / 脚本因版本、网络或权限失败，脚本会提示：**请按说明书步骤 4 UI 挂接扫描**。此时在 Web UI 中：

1. 新建**物理 Catalog / 数据源**，连接信息与 `config.yaml` 一致（注意 `catalog_host`）
2. **Enable** 数据源连接
3. 执行 **Discover / 扫描表**
4. 确认 12 张表可见，并将 `catalog_id` 填入 `config.yaml`

---

## 步骤 5：绑定（脚本 / Agent）

**目标：** 将知识网络对象类（OT）绑定到步骤 4 Catalog 中扫描到的物理表（`data_source.type=resource`）。

### 方式 A — 脚本（推荐）

**依赖：**

- 步骤 2 已导入 KN（`supply_ontology_hand`）
- 步骤 4 已完成扫描，且 `config.yaml` 中已填写 `vega.catalog_id`
- 映射表：`tools/mapping/object_table_map.yaml`（对象类 ↔ 表名 ↔ 主键）

**执行：**

```bash
cd tools
openbkn auth status
python3 bind_kn_resources.py --config config.yaml --dry-run
python3 bind_kn_resources.py --config config.yaml
openbkn --json bkn object-type query supply_ontology_hand supply_ontology_hand_product --body '{"limit":3}'
```

**脚本行为（概要）：**

- 读取 `vega.catalog_id`，在 Catalog 中按表名查找 resource（`resource find --exact`，失败则 `resource list` 回退匹配）
- 对 `object_table_map.yaml` 中 `bind: true` 的对象类，GET 当前 OT 定义后合并 `data_source: {"type":"resource","id":"<resource_id>"}` 并 UPDATE
- `--dry-run` 仅打印 `对象类ID\t表名\tresource_id`，不调用 update
- `bind: false` 的对象类（如 `supply_ontology_hand_mon_task`）跳过
- 绑定完成后建议执行 `bkn build`（若环境需要检索 / 向量索引）
- 验收：对核心 OT 执行 `object-type query --limit 3` 应返回非空实例

### 方式 B — 交给 Agent（提示词）

```text
你是 OpenBKN 实施助手。请为供应链手工体验包执行「步骤 5：对象类绑定」。

工作目录：<体验包根目录>/tools
配置文件：<体验包根目录>/tools/config.yaml（已含 openbkn.kn_id 与 vega.catalog_id）
映射文件：<体验包根目录>/tools/mapping/object_table_map.yaml

请依次：
1. openbkn auth status
2. python3 bind_kn_resources.py --config config.yaml --dry-run
   - 确认 bind:true 的 OT 均解析到 resource_id（表名见 object_table_map.yaml）
3. python3 bind_kn_resources.py --config config.yaml
4. 验收：openbkn --json bkn object-type query supply_ontology_hand supply_ontology_hand_product --body '{"limit":3}'
   以及 supply_ontology_hand_salesorder、supply_ontology_hand_bom 等非空
5. 可选：python3 smoke_test.py --config config.yaml

若脚本失败：提示用户走 UI 手绑（见说明书步骤 5 降级路径），并贴出 openbkn 报错原文。
约束：勿修改 object_table_map.yaml 与 KN JSON；勿创建 Catalog（步骤 4 已完成）。
```

### UI 降级路径：脚本失败 → 控制台手绑

若 CLI / 脚本因版本差异或权限问题失败，脚本会退出非 0 并提示：**请按说明书步骤 5 UI 手绑**。此时：

1. 在 OpenBKN 控制台打开知识网络 `supply_ontology_hand`
2. 逐个对象类进入「数据源绑定」，手动选择步骤 4 扫描到的物理表
3. 核对主键与关键字段与附录 B 映射摘要一致
4. 保存后重新执行 query 验收

> 绑定脚本**不负责**创建物理数据源连接（该步骤在步骤 4 完成）。

---

## 步骤 6：场景扩展（可选）

本步骤为**体验增强**，不阻塞 P0 走通。核心事实绑定（步骤 1～5）完成后，即可先进行步骤 7 的基础问法测试。

**权威场景说明（扩展阅读）：**

- 同目录文档：[agent-scenario-kn-capability-design_cn.md](./agent-scenario-kn-capability-design_cn.md)
- **§2 场景地图**：S1～S6 能力形态一览（Skill / Metric / Action 分工）
- **§3 标杆场景 S1**：生产计划倒排 · 齐套诊断（输入、对象关系、规则与输出门槛）
- 体验包默认知识网络 ID 为 **`supply_ontology_hand`**（场景文档正文中的 `supplychain_hd0202` 须按文首「体验包说明」替换）
- 对象类 ID 以手工版 JSON 中 `supply_ontology_hand_*` 前缀为准

**P0 / P1 分工：**

| 优先级 | 内容 |
|--------|------|
| **P0** | 步骤 1～5 事实绑定完成；步骤 7 中 Q1～Q4 类问法不因「无数据 / 未绑定」失败 |
| **P1** | Metric / 逻辑属性（如有效仓可用库存）；S1 倒排要点（交期 / 缺口 / A·B 类延迟）；Action 在本环境重绑 |

**扩展内容（按需，均为 P1）：**

| 类型 | 说明 |
|------|------|
| Metric / 逻辑属性 | 对齐 §3 S1 倒排等问法所需指标 |
| Action | **须在本环境重新绑定工具箱**；手工版 JSON 已清空原环境 box/tool |
| Skill | 可选增强（须 `skill register` 到平台）；本期不强制 |

**安全约束：**

- **`initiate_po`（发起采购）禁止无人值守自动执行** — 仅允许在人工确认后的演示环境中操作
- 其他写操作类 Action 同样建议「确认后再执行」

---

## 步骤 7：对比测试

在 Agent / 对话界面中验证知识网络「可用、可答、可联查」。完整题目与 CSV 金标准见 [业务问答测试集](./业务问答测试集.md)；导入后分步勾选见 [Agent 导入验证清单](./Agent导入验证清单.md)。

**步骤 8（动力层）** 不在 1～7 内，完成后执行：

```bash
cd tools
python3 power_layer.py all --kn-id supply_ontology_hand
```

详见 [动力层落地说明书](./动力层落地说明书.md)。

**最小冒烟（须与 CSV 一致，不要用另一张网的 431 / 昆山仓）：**

| # | 问法 | 期望要点 | 实际 | 通过 |
|---|------|----------|------|------|
| Q1 | 我们现在有多少种成品？ | **30** | | ☐ |
| Q2 | 查产品 `382-000005` 的基本信息 | 名称含「北斗导航农机驾驶仪」 | | ☐ |
| Q3 | `382-000005` 有多少张销售订单？ | **40**；关系可联 | | ☐ |
| Q4 | `382-000005` 成品仓可用库存多少？ | 约 **534**（苏州+乌鲁木齐+哈尔滨成品仓） | | ☐ |
| Q5 | 对 `382-000005` 做齐套倒排，需求日 `2026-05-14` | 书面报告；一层 `791-000007` / `791-000015` 可用为 0；禁止自动下 PO | | ☐ |

> 产品码取自 `data/hd_product_view.csv` 首行；需求日对应销售订单 `SO0000002` 承诺交期。生产可用仓为苏州/乌鲁木齐/哈尔滨 7 仓（见库存对象注释）。

**判定原则：**

- P0：Q1～Q4 数字/联查正确；指标已创建（见验证清单 §2）
- P1：Q5 产出含交期 / 缺口要点的倒排报告（见 [动态能力设计](./场景驱动的供应链动态能力设计.md) §4）

**自动化辅助（不替代 Agent 质量评估）：**

```bash
cd tools
python3 smoke_test.py --config config.yaml
```

脚本检查：KN 名称、`bind: true` 的 OT 查询非空、`object_table_map.yaml` 中 `join_checks` 命中率。Q5 的回答质量须人工勾选上表。

---

## 附录 A：表清单与灌库顺序

体验样例数据共 **12 张 CSV**，灌库时建议按业务链顺序执行（与 `load_sample_data.py` 中 `load_order` 一致）：

| 顺序 | CSV 文件 | 表名（stem） | 说明 |
|------|----------|--------------|------|
| 1 | `erp_material.csv` | `erp_material` | 物料主数据 |
| 2 | `hd_product_view.csv` | `hd_product_view` | 产品 |
| 3 | `erp_material_bom.csv` | `erp_material_bom` | BOM |
| 4 | `erp_real_time_inventory.csv` | `erp_real_time_inventory` | 实时库存 |
| 5 | `erp_supplier.csv` | `erp_supplier` | 供应商 |
| 6 | `erp_mds_forecast.csv` | `erp_mds_forecast` | MDS 需求预测 |
| 7 | `erp_mrp_plan_order.csv` | `erp_mrp_plan_order` | MRP 计划订单 |
| 8 | `erp_purchase_request.csv` | `erp_purchase_request` | 采购申请 |
| 9 | `erp_purchase_order.csv` | `erp_purchase_order` | 采购订单 |
| 10 | `erp_production_work_order.csv` | `erp_production_work_order` | 生产工单 |
| 11 | `customer_entity.csv` | `customer_entity` | 客户 |
| 12 | `sales_order.csv` | `sales_order` | 销售订单 |

> 表名必须与 CSV stem 一致，否则步骤 4 扫描后难以与映射表匹配。

---

## 附录 B：对象映射摘要

对象类与物理表的完整映射见 `tools/mapping/object_table_map.yaml`。摘要：

| 对象类（OT） | 物理表 | 主键（物理列） | 备注 |
|--------------|--------|----------------|------|
| 产品 | `hd_product_view` | `material_code` | OT 属性 `material_number` → 该列 |
| 物料 | `erp_material` | `material_code` | |
| BOM | `erp_material_bom` | `bom_version`, `bom_material_code`, `seq_no` | |
| 库存 | `erp_real_time_inventory` | `id` | |
| 供应商 | `erp_supplier` | `supplier_code` | |
| 需求预测 | `erp_mds_forecast` | `id` | |
| MRP | `erp_mrp_plan_order` | `billno` | |
| 采购申请 | `erp_purchase_request` | `entry_id` | |
| 采购订单 | `erp_purchase_order` | `entry_id` | |
| 生产工单 | `erp_production_work_order` | `entry_id` | 对应 OT `…_mps` |
| 销售订单 | `sales_order` | `sales_order_id` | |
| 监控任务 | — | — | 无样例表，跳过实例绑定 |
| （无 OT） | `customer_entity` | — | 仅灌库，不绑定 |

**P0 联接抽检（绑定后验证）：**

| 关系 | 期望 |
|------|------|
| 销售订单 → 产品 | `product_code` 与产品编码命中率 100% |
| 产品 → 需求预测 | 种子产品均有预测记录 |
| BOM → 物料 | 无孤儿物料码 |
| PO → 供应商 | 供应商码可命中 |
| PO → PR | `srcbillentryid` → `entry_id` 可关联 |

---

## 附录 C：故障排查

| 现象 | 可能原因 | 处理建议 |
|------|----------|----------|
| `openbkn auth status` 无 Token / 已过期 | 未 login 或会话失效 | 重新 `openbkn auth login <platform-url>`（见步骤 1.3） |
| CLI 报 TLS / 证书错误 | 自签名 HTTPS | `openbkn auth login -k <platform-url>` |
| 步骤 4/5 报 401 / 未认证 | 活跃平台不对 | `openbkn auth list` → `openbkn auth use <url>` |
| 导入 KN 报「ID 参数无效」 | 网络 ID 超过 32 字符 | 使用本包预设 ID `supply_ontology_hand`，勿随意加长 |
| 导入 KN 报名称已存在 | 平台已有同名 KN | 删除冲突 KN 或改用 UI；勿改 JSON 内 `id` |
| 导入时报「小模型获取失败」或 `get model request failed` | JSON 携带了其他环境的 embedding 模型 ID；或目标环境没有默认 embedding 模型 | 确认 `openbkn --json model small get-default --type embedding` 有返回；使用 `python3 import_kn.py --resolve-embedding` 重试；不要直接 POST 原始 JSON |
| `import_kn.py` 提示 `unrecognized arguments: --resolve-embedding` | 使用了旧版 Sample | 从 bkn-samples 主线重新下载 Sample，或升级 `tools/import_kn.py` 后再执行 |
| `import_kn.py` / call 导入失败 | 未 auth 或 API 路径随版本变化 | 先 `openbkn auth status`；确认使用 `--resolve-embedding`；仍失败再走步骤 2 UI |
| 灌库连接失败 | 库不存在 / 地址 / 账号 / 防火墙 | 确认已 `CREATE DATABASE`；检查 `config.yaml`；用客户端直连验证 |
| 灌库报 Unknown database | 目标库未创建 | 先建空库，库名与 `database` 字段一致 |
| 误指向共用库 | `recreate` 覆盖同名 12 表 | 改用专用库名；勿对生产库执行灌库 |
| 创建 Catalog 报 Connector initialization failed / config is incomplete | 连接器 JSON 缺 `password` 或 PG 用户未设密码 | 见步骤 4「密码设置」；填 `database.password` 后重跑 `setup_catalog.py` |
| 扫描后 verification 缺表 | discover 尚未完成 | 运行 `python3 setup_catalog.py --config config.yaml --write-config`；脚本会轮询 discovery task 后再校验 |
| Catalog 扫描不到表 | 数据源未 enable、库名 / schema 不对 | 确认 Catalog 连接与步骤 3 同一库名；重新 discover |
| MySQL 下 schema 无效 | MySQL 无 PostgreSQL 式 schema；`database.schema` 会被忽略 | 配置中 `schema` 可留空或忽略；Catalog 绑定库名即可，勿填 `database.public` 形式 |
| 绑定后 query 为空 | 表名与映射不一致、PK 未配置 | 核对附录 B；必要时走 UI 手绑 |
| 有效仓库白名单 | 库存 OT 有过滤条件 | 确认样例数据中仓库编码在允许范围内 |
| 脚本绑定失败 | CLI 版本 / 权限差异 | 见步骤 5「脚本失败 → UI 手绑」降级路径 |
| Agent 回答「未绑定」 | 步骤 5 未完成或 build 未执行 | 重跑绑定；检查 OT data_source |

---

## 附录 D：P0 / P1 验收清单

实施或自助体验完成后，在**客户 OpenBKN + 自备数据库**环境中逐项勾选。工具与说明书已齐备；下列 P0 项须在真实环境走通后方可冻结。

### P0（必须）

- [ ] **1.** 单文件说明书步骤 1～7 可按序走通
- [ ] **2.** `load_sample_data.py` 灌入 12 表成功（至少一种引擎；SQLite 已由 `tools/tests` 覆盖，**生产优先 PostgreSQL**）
- [ ] **3.** KN JSON 导入成功，`supply_ontology_hand` 在控制台可见
- [ ] **4.** 绑定后核心 OT `object-type query` 非空（如 product / sales_order / bom）
- [ ] **5.** `join_checks` 全绿：`python3 smoke_test.py --config config.yaml` 返回通过（KN 名称、OT 行数、联接命中率）
- [ ] **6.** 步骤 7 问法表 Q1～Q4 中至少 **3 条**不因「无数据 / 未绑定」失败

### P1（体验增强，不阻塞体验包冻结）

- [ ] **Metric** — 有效仓可用库存等逻辑属性 / Metric 可查（若平台支持）
- [ ] **S1 倒排要点** — Q5 齐套/倒排类问法能产出含交期 / 缺口 / A·B 类延迟要点的回答（见场景文档 §3）
- [ ] **Action 重绑** — 写操作类 Action 在本环境完成工具箱重绑；`initiate_po` 等仅「确认后」演示

**验证记录（实施同学填写，勿虚构「已在环境 X 验证」除非现场实测）：**

| 项 | 值 |
|----|-----|
| 验证环境 | （待填） |
| 验证日期 | （待填） |
| 验证人 | （待填） |
| P0 结论 | ☐ 通过 / ☐ 待重测 |
