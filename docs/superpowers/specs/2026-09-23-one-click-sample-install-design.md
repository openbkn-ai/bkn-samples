# OpenBKN 样例一键安装设计

## 1. 背景

`bkn-samples` 已经提供两个可体验样例：

- `supply_ontology_hand`：12 张脱敏供应链 CSV、知识网络、业务函数、Skill 和评测资产；
- `world-cup`：27 张世界杯数据表、BKN 模板、Vega SQL 工具和一套六步安装脚本。

当前用户仍需自行准备数据库、加载数据、创建 Vega Catalog、扫描资源、导入和绑定 BKN、构建索引，并发布函数和 Skill。步骤多、依赖分散，且数据库网络地址、CLI 登录态和脚本运行环境容易配置错误。

本设计不新增 OpenBKN 原生样例管理能力，而是在仓库中增加一个统一的 Shell 入口。用户安装 OpenBKN CLI 后，通过一条命令得到完整、可查询、可供 Agent 使用的知识网络；如果尚未登录，安装器先引导完成 `openbkn auth login`。为避免 Catalog 数据库密码出现在进程参数中，安装器要求 CLI 提供从受限权限文件读取 connector config 的安全输入能力；除此之外不修改 OpenBKN 核心服务或 CLI 工作流。

## 2. 目标与非目标

### 2.1 目标

用户通过以下命令安装样例：

```bash
./install.sh supply-chain
./install.sh world-cup
./install.sh list
```

安装器应完成：

1. 检查本机工具，引导或验证 OpenBKN 管理员登录，并检查 CLI 与目标平台兼容性；
2. 启动一个自带 MariaDB、初始化器和样例数据的数据库容器；
3. 加载并校验样例数据；
4. 创建或复用 Vega Catalog，完成资源发现；
5. 导入 BKN 并绑定对象类资源；
6. 按平台能力构建关键字或向量索引；
7. 发布样例需要的 Toolbox、Function 和 Skill；
8. 运行数据查询与知识网络查询冒烟测试；
9. 在同一版本上可安全重复执行，失败后可直接重跑。

安装器支持两种数据运行时：

- **Kubernetes 模式**：在 OpenBKN 所在集群内部署样例数据库，作为默认和推荐模式；
- **Docker 模式**：在执行脚本的主机启动样例数据库，适合无集群权限但数据库地址能被 OpenBKN 访问的环境。

### 2.2 非目标

- 不新增 `openbkn sample` CLI 命令或平台样例管理 API；CLI 侧唯一前置增强是 connector config 文件输入能力；
- 不修改 OpenBKN 核心部署流程或复用平台控制数据库；
- 不承诺让 OpenBKN 访问 NAT、防火墙或私网之后的任意 Docker 主机；
- 不自动注册 LLM 或 Embedding 模型；没有 Embedding 时允许降级为关键字索引；
- 不把预生成的 `/var/lib/mysql` 数据目录打入镜像；
- 首版不提供 PostgreSQL 变体，也不在同一个容器内同时运行 MySQL 与 PostgreSQL；
- 首版只支持随 `bkn-samples` 仓库和镜像发布的样例，不支持从任意 URL 动态安装第三方样例包；
- 首版不提供完整卸载器，避免误删用户已使用或修改的平台资源。

## 3. 用户接口

### 3.1 基本命令

```bash
./install.sh <sample> [options]
./install.sh list
```

首批内置 sample：

| 用户名 | 仓库目录 | 知识网络 ID |
| --- | --- | --- |
| `supply-chain` | `samples/supply_ontology_hand` | `supply_ontology_hand` |
| `world-cup` | `samples/world-cup` | `worldcup_vega_catalog_bkn` |

sample 名、别名和资产路径由各目录的 `sample.yaml` 声明，根安装器不维护硬编码列表。`./install.sh list` 读取所有通过 schema 校验的 manifest 并展示可安装样例。

首版参数：

| 参数 | 说明 |
| --- | --- |
| `--runtime auto\|k8s\|docker` | 默认 `auto`；优先选择确认属于目标 OpenBKN 的 Kubernetes 集群 |
| `--catalog-host <host>` | Docker 模式必填；OpenBKN 集群访问数据库时使用的地址 |
| `--namespace <name>` | Kubernetes namespace，默认 `openbkn-samples` |
| `--base-url <url>` | 尚未登录时使用的平台地址；交互模式未提供时由安装器询问 |
| `--dry-run` | 输出计划和将使用的资源名称，不产生外部写入 |
| `--upgrade` | 允许从旧样例版本升级并更新由安装器管理的资源 |

不提供镜像名参数。安装器默认从 SWR 拉取固定名称：

```text
swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples:<version>
```

若本机已有同一固定版本的默认 SWR 镜像，Docker 模式直接复用该镜像，以支持受限网络中的离线安装；release tag 不可变，因此不会混入不同版本内容。否则，若 SWR 明确返回镜像不存在或连续拉取失败，安装器自动回退到同版本的 `ghcr.io/openbkn-ai/bkn-samples:<version>`。Docker 模式在 pull 失败后切换；Kubernetes 模式在检测到 `ImagePullBackOff` 后把 StatefulSet 改为 GHCR 同版本镜像并重试。用户不选择 registry，也不输入镜像地址。

仓库根目录的 `VERSION` 是安装器 bundle 发布版本和镜像 tag 的唯一版本源。`install.sh` 读取该版本并使用完全相同的镜像 tag，不使用浮动的 `latest`。开发者的 commit SHA tag 只供 CI 和维护调试使用，不进入公开用户接口。

根 `VERSION` 只表示安装器和镜像 bundle 版本。每个 manifest 另外声明 sample schema 版本与 data 版本；健康检查和升级决策比较 sample/data 版本及 manifest 摘要，不能因为 bundle 中其他 sample 更新就误判当前数据库需要升级。

### 3.2 前置条件

所有模式都要求：

- 已安装满足 sample manifest 版本范围的 `openbkn` CLI，且 `vega catalog` 支持从文件安全读取 connector config；
- Node.js 22.19+ 可用，并满足 sample manifest 声明的版本范围；
- Python 3.11+ 可用，供供应链现有平台工具在临时 virtualenv 中运行；
- `curl`、`jq` 和 Bash 4+ 可用。

登录不是用户必须预先完成的步骤。首版明确要求最终使用 OpenBKN 平台管理员身份，但不按用户名推断角色，也不实现细粒度权限矩阵。安装器直接执行 `openbkn --json auth whoami`，同时验证登录态和 token 刷新：

- 命令成功：展示目标平台和当前身份，继续安装；
- 未登录且有交互终端：使用 `--base-url` 或询问平台地址，再执行 `openbkn auth login <url> --device`，等待用户在浏览器完成授权；
- 未登录且无交互终端：不读取用户名、密码或 Token，只输出准确的登录命令并退出；
- 登录完成后：再次执行 `auth whoami`；后续出现 401/403 时按管理员身份或平台授权配置异常停止，不继续产生新的平台写入。

`--dry-run` 不发起登录，只报告是否需要登录以及建议命令。

Kubernetes 模式还要求 `kubectl` 可访问 OpenBKN 所在集群，并拥有创建、读取和更新 Namespace、Secret、PVC、StatefulSet 和 Service 所需的 Kubernetes RBAC 权限；OpenBKN 平台管理员身份不等于 Kubernetes 管理权限。Docker 模式要求 Docker Engine 和 Compose plugin 可用，并要求 OpenBKN 集群能反向访问 `--catalog-host` 及数据库端口。

## 4. 架构

```text
用户
  |
  v
install.sh ---------------------------------------------------+
  |                                                           |
  | 读取 VERSION、引导/检查登录、选择 runtime                 |
  |                                                           |
  +--> Kubernetes runtime          Docker runtime             |
  |    StatefulSet + Service       Compose sample container   |
  |    PVC + Secret                Volume + local secret      |
  |            \                     /                        |
  |             +-- bkn-samples image --+                    |
  |                 MariaDB + init                           |
  |                                                           |
  +--> 本机 openbkn CLI / 现有 sample 工具                    |
          Catalog -> Discover -> BKN -> Bind -> Index          |
          -> Toolbox/Function/Skill -> Smoke test              |
                                                              |
  +--> 安装结果与下一步提示 ----------------------------------+
```

### 4.1 统一安装器

根目录 `install.sh` 是唯一公开入口，负责参数解析、环境检查、阶段编排、日志、失败处理和最终报告。它不重新实现每个 sample 的业务逻辑，而是调用 sample 自己的适配脚本。

建议内部目录：

```text
installer/
├── lib/
│   ├── common.sh
│   ├── runtime_k8s.sh
│   ├── runtime_docker.sh
│   ├── openbkn.sh
│   └── sample.sh
├── manifests/
│   ├── k8s/
│   └── compose.yaml
└── schemas/
    └── sample.schema.json
```

`common.sh` 提供阶段执行、重试、日志脱敏、精确名称查找和 JSON 解析。runtime 模块只管理自包含样例数据库容器，不理解 BKN。`sample.sh` 读取、校验 manifest 并按标准生命周期调用 sample hook；根安装器不通过 `case` 语句识别具体样例。

### 4.2 自包含样例数据库

唯一 OCI 镜像基于固定版本的 MariaDB 构建。MariaDB 提供与现有世界杯脚本兼容的 MySQL 协议，也能承载供应链样例，因此首版不增加 PostgreSQL 构建矩阵。

每个已安装 sample 独占一个数据库容器和持久卷，使用独立数据库：

- `supply_demo_hand`；
- `worldcup`。

Kubernetes 模式在 `openbkn-samples` namespace 中为每个 sample 创建独立的 StatefulSet、ClusterIP Service、PVC 和 Secret。Docker 模式通过 Compose 创建一个等价的样例数据库容器和持久卷。两个 sample 使用同一个镜像，但通过内部环境变量 `BKN_SAMPLE_ID` 选择初始化内容；该变量由 `install.sh` 设置，不作为用户接口暴露。

数据库密码首次安装时随机生成：

- Kubernetes 模式保存在 Secret；
- Docker 模式保存在权限为 `0600` 的本地状态文件；
- 日志、命令摘要和最终报告均不得打印密码；
- 样例数据库不使用 OpenBKN 自身的 MariaDB 实例或账号。

### 4.3 镜像初始化与健康检查

唯一 OCI 镜像为：

```text
swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples:<version>
```

同版本镜像同时发布到 GHCR，供 SWR 不可用时自动回退。两个 registry 中的多架构 manifest 必须指向相同构建产物和内容摘要。

镜像包含：

- MariaDB 服务端和官方 entrypoint；
- 供应链的 12 张脱敏 CSV；
- 两个样例的数据加载脚本、schema 映射和校验工具；
- Python 运行时、数据库客户端和固定依赖；
- 世界杯数据集锁文件与许可证说明。

镜像不包含：

- 预生成的 MariaDB 数据目录；
- PostgreSQL 服务端；
- OpenBKN CLI、Token 或其他用户凭据；
- 世界杯 CSV 数据本体。

镜像不实现进程守护器，只增加一个故障恢复 wrapper。正常启动路径中，wrapper 完成卷归属和初始化状态检查后，以 `exec` 调用 MariaDB 官方 entrypoint；官方链路最终仍以 `mariadbd` 作为 PID 1。只有同一失败 attempt 被容器运行时自动重启时，wrapper 才进入不启动数据库的稳定失败等待状态。样例卷统一挂载到 `/var/lib/bkn-samples`，内部固定分为：

```text
/var/lib/bkn-samples/
├── owner.json                 # 卷归属、sample id 和最近初始化 attempt
├── ready.json                 # 最近一次完整初始化成功标记
├── mysql/                     # MariaDB datadir
├── cache/                     # 世界杯下载缓存
└── failed/                    # 最近一次失败 datadir，供诊断
```

wrapper 只允许操作带有匹配 `owner.json` 的卷；发现非空但没有归属标记、sample id 不匹配或归属文件损坏时立即退出，绝不删除或接管目录。每次用户执行安装命令时生成一个初始化 attempt ID，并由 StatefulSet 或 Compose 配置传给容器。首次使用空数据目录启动时，wrapper 原子写入包含该 attempt ID 的 `owner.json`，然后由官方 entrypoint 调用镜像内的 `/docker-entrypoint-initdb.d/10-bkn-sample-init.sh`：

1. 校验 `BKN_SAMPLE_ID`、数据库名和凭据；
2. 对供应链读取镜像内 CSV，对世界杯下载并校验锁定数据；
3. 在临时数据库中加载和校验数据；
4. 通过后切换为正式数据库；
5. 写入状态为 `ready` 的 `bkn_sample_meta`，并原子写入 `ready.json`。

首次初始化失败时，官方 entrypoint 以非零状态退出，`ready.json` 不存在。同一 workload 因 Kubernetes 或 Docker 重启而再次启动时，wrapper 发现 attempt ID 未变化，写出明确失败状态后进入稳定等待，不再次启动 MariaDB，避免 CrashLoop 不断重建和下载；readiness 始终失败，安装器据此返回原始初始化错误。用户重新执行 `install.sh` 后，安装器生成新的 attempt ID 并重建 Pod/container；wrapper 确认 `owner.json` 归属当前 sample 且数据从未 ready，才把未完成的 `mysql/` 原子移动到 `failed/<timestamp>/`，保留 `cache/` 和失败现场，再创建空 `mysql/` 重新进入官方初始化流程。同一卷只保留最近一次失败 datadir，避免显式重试无限占用空间。该恢复规则只适用于从未成功的首次初始化，不能用于自动回滚已 ready 的数据库。

容器 health check 同时检查 MariaDB 存活、`ready.json`、`bkn_sample_meta.status=ready`，以及表内 sample/data 版本与镜像 manifest 一致。OpenBKN bootstrap 只有在这些检查全部通过后才能继续。

成功产生 `ready.json` 后，wrapper 不再清理或重建 datadir；官方 initdb 脚本在已有数据目录上也不会再次运行，因此同版本容器重建不会重复导入。安装器通过镜像内的 `/opt/bkn-samples/bin/verify` 回读并校验状态。旧版本数据只有在用户指定 `install.sh --upgrade` 后，才由安装器在容器内显式执行 `/opt/bkn-samples/bin/upgrade`；检测到更高版本时拒绝降级。

### 4.4 OpenBKN 控制面操作

Catalog、BKN、Toolbox、Function 和 Skill 操作由宿主机的 `install.sh` 调用 `openbkn` CLI 完成，复用用户已有登录态和 token 刷新能力。样例数据库容器不接收 OpenBKN Token。

Catalog 连接配置由安装器写入 `0700` 临时目录中的 `0600` JSON 文件，并通过 CLI 的 `--connector-config-file` 传给 `catalog test-connection-config`、`catalog create` 和 `catalog update`。该参数与现有 `--connector-config` 互斥，读取 UTF-8 JSON object 后沿用相同的客户端校验。临时文件由 `trap` 在正常退出和可捕获信号时删除；安装器下次启动还会清理自己拥有的过期临时目录。不得把 connector config 放入命令参数、环境变量、shell trace 或错误摘要。安装器启动时通过实时 `--help` 检查该能力，不支持时直接失败并提示升级 CLI，不能静默回退到 `--connector-config <json>`。

供应链现有 Python 工具继续作为实现主体。安装器在仓库内创建临时 virtualenv 并安装锁定依赖，避免修改系统 Python。世界杯现有 `run.sh` 拆出或复用其平台阶段，使数据准备与平台 bootstrap 可以分别重跑。

现有 sample 工具中的精确 CLI/Node 版本判断由根安装器替代。每个 sample 在 manifest 中声明语义版本范围和必需能力；根安装器统一解析版本并通过实时 `--help` 验证能力，sample hook 不得再次硬编码单一 CLI 版本。

BKN 导入前由公共 helper 生成临时 payload，源文件保持不变：若平台存在默认 Embedding，将所有启用的 `vector_config.model_id` 重写为当前环境的模型 ID；若不存在默认 Embedding，则在发送请求前递归移除向量配置，并按 manifest 继续构建关键字索引。不得发送样例资产中遗留或为空的模型 ID，也不得依赖平台先报错再进行降级。

### 4.5 Sample 扩展契约

每个可安装样例必须提供 `samples/<slug>/sample.yaml`，并遵循版本化 JSON Schema `installer/schemas/sample.schema.json`。建议目录结构：

```text
samples/<slug>/
├── sample.yaml
├── data/                         # 可选：允许进入镜像的静态数据
├── dataset.lock                  # 可选：运行时下载数据的锁文件
├── db/
│   ├── init.sh                   # 必需：首次初始化
│   ├── verify.sh                 # 必需：数据验收
│   └── upgrade.sh                # 可选：显式版本升级
├── platform/
│   ├── install.sh                # 必需：Catalog/BKN/能力发布
│   └── verify.sh                 # 必需：平台侧验收
├── kn/                           # 可选：BKN 资产
└── skills/                       # 可选：Skill 资产
```

首版 manifest 合同：

```yaml
apiVersion: samples.openbkn.ai/v1alpha1
kind: Sample
metadata:
  name: world-cup
  aliases: [worldcup]
  displayName: 世界杯
spec:
  version: 1.0.0
  requires:
    cli: ">=0.1.5 <0.2.0"
    node: ">=22.19.0"
    features:
      - vega-catalog-connector-config-file
  database:
    engine: mariadb
    name: worldcup
    expectedTables: 27
  data:
    mode: runtime-download       # embedded | runtime-download
    version: 1.0.0
    lockFile: dataset.lock
  knowledgeNetwork:
    id: worldcup_vega_catalog_bkn
  hooks:
    dbInit: db/init.sh
    dbVerify: db/verify.sh
    dbUpgrade: db/upgrade.sh
    platformInstall: platform/install.sh
    platformVerify: platform/verify.sh
```

约束如下：

- `metadata.name` 是公开安装名，必须在仓库内唯一；alias 也不得冲突；
- `spec.version` 是该 sample 安装合同的版本，`spec.data.version` 是数据库内容版本；二者独立于根目录 bundle `VERSION`；
- `requires.cli` 和 `requires.node` 使用语义版本范围；`requires.features` 通过实时命令帮助或能力探测验证，不能仅凭版本号推断；
- `database.engine` 首版只接受 `mariadb`，字段保留是为了未来通过新合同版本扩展，而不是暗示当前支持 PostgreSQL；
- hook 路径必须位于当前 sample 目录，不能使用绝对路径或 `..`；
- 所有 hook 必须幂等，成功返回 0，失败返回非零，并把机器可读结果写到安装器指定的 JSON 文件；
- 数据库 hook 只在样例数据库容器内运行，不能接收 OpenBKN Token；
- 平台 hook 在宿主机运行，通过已有 `openbkn` 登录态操作，不得直接调用 `kubectl` 或 Docker；
- 公共环境变量、输入 JSON 和输出 JSON 的字段由 `v1alpha1` 合同固定，sample 不得依赖安装器内部函数；
- 新增 sample 不允许修改 `install.sh`、runtime 模块或通用 Kubernetes/Compose 模板；若现有合同无法表达需求，应先升级扩展合同并补兼容测试。

构建镜像时自动发现通过 schema 校验的 manifest，只复制 manifest 声明的数据和数据库 hook，并生成 `/opt/bkn-samples/manifest-index.json`。安装器在启动容器前比较仓库 manifest 摘要与镜像索引，防止脚本和镜像版本错配。平台 hook、BKN 和 Skill 保留在仓库 checkout 中，由宿主机执行。这样增加普通 MariaDB 样例只需新增一个 sample 目录；不需要复制一套安装器。

## 5. 数据策略

### 5.1 供应链

供应链 CSV 已脱敏且随仓库发布，构建时进入 OCI 镜像。镜像初始化器复用现有字段类型覆盖与加载顺序，加载完成后核对：

- 12 张表全部存在；
- 每张表行数与发布清单一致；
- 关键字段类型符合 `column_types.yaml`；
- 代表性 JOIN 和业务函数输入能够得到预期结果。

### 5.2 世界杯

世界杯数据在运行时下载。新增 `dataset.lock`，记录：

- 上游仓库；
- 固定 commit；
- 27 个文件的相对路径和 SHA-256；
- 数据集作者、许可证和署名文本。

镜像初始化器下载到持久缓存目录，逐文件校验后再开始数据库事务。缓存与 MariaDB 数据目录位于同一 sample PVC/volume 的不同子目录中。不得使用浮动的 `master`。下载或校验失败时不创建或覆盖数据库中的正式表。

为避免用户看到半加载状态，初始化器使用临时数据库完成加载与校验，全部通过后再切换为正式数据库。重跑时已验证的下载缓存可以复用。

## 6. 安装流程

### 阶段 0：认证引导与预检

在产生任何平台资源写入前完成：

1. 验证 sample 名和参数；
2. 读取 `VERSION`，先检查 SWR 同版本镜像，必要时确定 GHCR 回退；
3. 直接执行 `openbkn --json auth whoami`；未登录时按交互规则引导 `openbkn auth login <url> --device`，然后重新验证身份；
4. 验证 CLI/Node 语义版本范围、connector config 文件输入能力和平台版本；管理员身份作为首版运行前提，不执行细粒度权限探测；
5. 检查所选 runtime；
6. Kubernetes 模式确认当前 context 中存在 OpenBKN 服务，并验证所需 Kubernetes RBAC；
7. Docker 模式只校验 `--catalog-host`、端口和 Compose 配置，不在数据库启动前声称完成服务端连通测试；
8. 输出将创建或复用的资源清单。

`auto` 模式只有在当前 Kubernetes context 能识别出目标 OpenBKN 部署时才选择 Kubernetes；否则选择 Docker。无法证明集群归属时应失败并要求显式指定，而不是写入可能错误的集群。

### 阶段 1：准备数据服务

- 为目标 sample 创建或复用 namespace、Secret、PVC、StatefulSet 和 Service，或 Compose project；
- 启动固定版本的自包含样例数据库镜像；
- 等待 MariaDB 存活检查与样例数据就绪检查同时通过；
- 确认数据库连接只使用样例专用账号；
- 核对 `ready.json`、`bkn_sample_meta` 与当前 sample/data 版本一致；
- 数据服务 ready 后，通过 connector config 临时文件调用 Vega 服务端连接测试；测试成功前不创建或更新任何 OpenBKN 平台资源。

### 阶段 2：创建 Catalog 与发现资源

- 使用确定性 Catalog 名：`bkn-sample-<sample>`；
- 按精确名称查找已有 Catalog；
- 已有 Catalog 的 connector 地址或数据库名不匹配时立即停止，不接管同名资源；
- 复用阶段 1 已通过的服务端连接测试结果，创建或复用 Catalog 后启动完整发现任务并轮询完成；
- 验证供应链 12 张、世界杯 27 张目标表均已发现。

### 阶段 3：导入和绑定 BKN

- 校验本地 BKN 资产；
- 渲染 Vega resource ID 占位；
- 导入或更新确定性知识网络 ID；
- 绑定对象类与关系数据源；
- 校验绑定数量及关键对象查询。

同版本重跑只验证现状，不覆盖用户修改过的 BKN。只有显式 `--upgrade` 才允许把安装器管理的旧版本资源更新到当前版本；如果无法证明资源由本安装器创建，则停止并报告冲突。

### 阶段 4：索引与能力发布

- 有可用默认 Embedding 模型时，先把临时 BKN payload 中全部启用的向量配置改写为该模型 ID，再构建样例定义的向量索引；
- 无 Embedding 时，在导入请求发出前移除全部向量配置，构建关键字索引或跳过非必需向量能力，并明确报告降级；
- 按确定性名称创建或更新 Toolbox、Function 和 Skill；
- 启用工具并发布 Toolbox；
- 轮询异步任务至终态。

### 阶段 5：验收

至少验证：

- Catalog 连接健康；
- 预期表和行数存在；
- 每个关键对象类能够通过资源绑定查询；
- 一条跨表或关系查询返回预期结果；
- 样例 Function/Tool 可调用；
- 相关 Skill 已发布并可发现。

最终输出知识网络 ID、Catalog ID、已发布能力、索引降级情况和建议体验问题。只有以上必需检查全部通过才返回退出码 0。

## 7. 幂等、升级与失败恢复

### 7.1 状态标识

镜像初始化器在数据库维护 `bkn_sample_meta` 表，至少记录：

- `sample_id`；
- `sample_version`；
- `data_version`；
- 数据清单摘要；
- 完成时间。

Kubernetes ConfigMap 或 Docker 本地状态文件记录 runtime 资源与安装版本。平台资源仍以确定性名称和平台返回 ID 为权威，不依赖本地状态文件猜测 ID。

Catalog、BKN 等支持 tag 的资源增加以下安装器标识：

```text
bkn-samples
bkn-sample:<sample-id>
bkn-samples-version:<version>
```

对于不支持 tag 的 Toolbox、Function 和 Skill，安装状态记录其平台 ID 与发布内容摘要。重跑时优先回读平台内容并比较摘要：内容完全一致可以复用；内容不同则视为用户修改或名称冲突并停止。状态文件丢失时只能复用带安装器标识或与当前发布内容完全一致的资源，不能仅凭同名资源推断所有权。

### 7.2 重跑规则

- 同版本且校验通过：跳过已完成阶段，只运行健康检查和最终验收；
- 同版本但阶段未完成：从第一个未完成阶段继续；
- 发现更旧版本：要求 `--upgrade`；
- 发现更高版本：拒绝降级；
- 名称相同但配置或所有权不匹配：停止，不覆盖；
- 数据版本变化：在新临时库/表完成加载和校验后切换，避免破坏当前可查询版本。

### 7.3 失败处理

安装器不自动删除已经成功创建的平台资源，因为删除 Catalog 会级联影响 Resource 和 BKN 绑定。失败时：

1. 保留成功阶段；
2. 保留失败容器日志和 PVC/volume，停止反复重启，便于定位后重跑；
3. 输出失败阶段、原始错误、已创建资源和安全的重跑命令；
4. 返回非零退出码。

日志写入 `.bkn-samples/logs/<sample>-<timestamp>.log`，对密码、Token 和 connector secret 做脱敏。

## 8. 安全与许可

- 安装器复用或引导创建本机 OpenBKN 登录态，不自行接收 OpenBKN 用户名、密码或 Token，也不把长期 refresh token 复制到数据库容器；
- Catalog connector config 只通过 `0600` 临时文件传入 CLI，禁止出现在 argv、环境变量、shell trace、日志和最终输出；缺少文件输入能力时安装器拒绝运行；
- 样例 MariaDB 在 Kubernetes 模式仅暴露 ClusterIP；
- Docker 模式默认不声称平台可达，必须通过服务端连接测试后才能继续；
- 所有镜像基础层和依赖固定版本；SBOM 和 provenance 作为独立 release artifact 发布，不作为 OCI attestation 挂到 SWR 镜像索引；
- 供应链数据继续声明为脱敏历史回放，不能用于真实交付承诺或写回 ERP；
- 世界杯安装输出和缓存目录保留 Joshua C. Fjelstul 的署名及 CC-BY-SA 4.0 许可说明；
- 运行时下载的数据不重新打包进入 OpenBKN 发布镜像。

## 9. CI 与镜像发布

### 9.1 `ci.yml`

在 pull request 和 main push 上运行：

- ShellCheck；
- 供应链现有 Python 测试；
- `install.sh --dry-run` 契约测试；
- 未登录时的交互引导、非交互失败和 `--dry-run` 行为测试；
- 管理员运行前提、OpenBKN 身份与 Kubernetes RBAC 相互独立的错误提示测试；
- CLI/Node 语义版本范围和 connector config 文件输入能力探测；
- SWR 默认拉取、GHCR 自动回退和两端 digest 一致性检查；
- 所有 `sample.yaml` 的 JSON Schema、路径安全和名称唯一性检查；
- Kubernetes manifest 和 Compose 配置校验；
- 构建 OCI 镜像但不推送；
- 直接启动构建出的自包含镜像，等待样例数据就绪后核对供应链表数、行数和关键查询；
- 使用小型固定 fixture 测试世界杯下载失败、checksum 失败、缓存命中和加载逻辑；
- 验证 connector password 不出现在子进程 argv、环境变量、shell trace 或日志中，且临时文件权限为 `0600` 并在退出后删除。

PR CI 不下载完整世界杯数据，避免上游网络导致常规提交不稳定。

### 9.2 `release-image.yml`

在项目版本 tag 和手动发布时运行：

1. 验证 Git tag、`VERSION` 和安装器声明版本完全一致；
2. 下载并校验完整世界杯锁定数据，但不把数据加入镜像；
3. 分别构建 `linux/amd64` 与 `linux/arm64`；
4. 关闭 BuildKit 内嵌 attestation，使用 Docker schema 2 media type，把同一次构建的架构镜像分别推送到 GHCR 和 SWR；
5. 分别使用 Docker manifest list 组装两端的多架构 tag，并验证架构子镜像 digest 和最终 manifest digest 一致；
6. 生成独立的 SBOM、provenance 和镜像 digest release artifact；
7. 发布完整版本 tag；稳定正式版可同时更新 `latest`，但安装器始终使用完整版本 tag。

发布镜像：

```text
swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples:<version>
ghcr.io/openbkn-ai/bkn-samples:<version>
```

CI 内部仍可发布 `<commit-sha>-amd64` / `<commit-sha>-arm64` 架构 tag，用于合成 manifest 和排障，但这些 tag 不进入安装器用户接口。

## 10. 测试策略

### 10.1 单元测试

- 参数解析和 runtime 选择；
- 版本与镜像 tag 解析；
- 认证引导状态机和 registry 回退；
- 精确名称查找和冲突判断；
- secret 脱敏；
- 世界杯 lock 文件与 checksum；
- 阶段状态机和失败恢复。

外部命令通过 PATH 中的 fake `openbkn`、`kubectl` 和 `docker` 测试，单元测试不访问真实平台。

### 10.2 数据集成测试

- Compose 直接启动自包含样例数据库镜像；
- 供应链完成 12 表加载和代表性 JOIN；
- 世界杯 fixture 完成宽表建表与重复加载；
- 同版本容器重复启动不重复导入或产生重复行；
- 在 MariaDB 系统表已创建但 sample init 尚未完成时强制中断；同 attempt 重启必须稳定停在失败态，重新执行安装命令产生新 attempt 后保留缓存和最近一次失败现场，并从空 datadir 恢复；
- 非空但没有匹配 `owner.json` 的卷必须拒绝启动且不修改任何文件；
- 旧版本、损坏缓存和 checksum 不匹配均按预期失败。

### 10.3 扩展合同测试

- 使用一个最小 fixture sample 验证 manifest 驱动的发现、镜像初始化和平台 hook 调度；
- fixture 只新增 `samples/<slug>/`，不得修改 `install.sh`、runtime 模块或通用模板；
- manifest 字段缺失、alias 冲突、越界 hook 路径和不支持的数据库引擎必须在 CI 中失败；
- `./install.sh list` 的输出完全来自通过校验的 manifest；
- manifest 中 CLI/Node 版本范围格式错误或必需能力不存在时必须在平台写入前失败。

### 10.4 OpenBKN 端到端测试

完整 E2E 需要真实 OpenBKN，因此不作为普通 PR 必跑项。提供手动或定时 workflow，在一次性测试环境验证：

- K8s 模式首次安装；
- 同版本重跑；
- 从旧版升级；
- 无 Embedding 降级；
- 有 Embedding 时所有启用的向量配置使用当前环境模型 ID；无 Embedding 时导入 payload 不包含遗留或空的模型 ID；
- Catalog 扫描、BKN 查询、Function 调用和 Skill 发现；
- Docker 模式在可路由测试网络中的安装。

## 11. 验收标准

- 新安装的 OpenBKN 上，用户登录后执行一条安装命令即可完成样例交付；
- 供应链和世界杯两种样例均支持 Kubernetes 模式；
- Docker 模式在平台可访问数据库地址的前提下可用，并在不可达时于平台写入前失败；
- 同版本命令连续执行两次均成功，第二次不重复导入数据或创建同名资源；
- 供应链镜像内置数据，世界杯使用锁定 commit 运行时下载并校验；
- 用户无需选择或输入 OCI 镜像名；
- 默认从 SWR 拉取，SWR 不可用时自动回退同版本 GHCR 镜像；
- 用户未预先登录时，交互模式能引导完成 device login；非交互模式在任何平台资源写入前给出明确命令并退出；
- 首版以 OpenBKN 平台管理员身份运行；Kubernetes 模式另外验证 kubectl 身份具备所需 RBAC；
- Catalog 密码只通过受限权限临时文件传给支持安全文件输入的 CLI，不出现在进程参数、环境变量、日志和最终输出；
- 首次数据库初始化在系统表创建后中断时，下一次运行能够安全恢复；安装器绝不清理没有匹配归属标记的卷；
- amd64 与 arm64 镜像均由 GitHub Actions 构建发布；
- 增加第三个 MariaDB 样例时，只需新增符合扩展合同的 sample 目录，不修改安装器核心；
- Token、数据库密码不出现在日志和最终输出；
- 必需冒烟检查失败时命令返回非零，且报告明确的重跑入口。

## 12. 实施边界

实现应优先复用现有脚本，并按以下顺序交付：

1. 在 OpenBKN CLI 为 Catalog 连接测试、创建和更新增加互斥的 `--connector-config-file` 安全输入，并完成单元测试和发布；
2. 统一安装器框架、Sample 扩展合同、版本文件与供应链 Kubernetes 路径；
3. 世界杯 runtime 下载锁文件和 Kubernetes 路径；
4. Docker runtime；
5. PR CI、镜像发布和手动 E2E workflow；
6. 文档与发布验收。

每个阶段都必须保持 `install.sh` 的用户接口稳定。若实现过程中发现必须修改 OpenBKN 核心 API，停止扩展范围，先在独立设计中评审该平台变更。
