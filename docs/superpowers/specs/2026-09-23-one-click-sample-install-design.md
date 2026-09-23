# OpenBKN 样例一键安装设计

## 1. 背景

`bkn-samples` 已经提供两个可体验样例：

- `supply_ontology_hand`：12 张脱敏供应链 CSV、知识网络、业务函数、Skill 和评测资产；
- `world-cup`：27 张世界杯数据表、BKN 模板、Vega SQL 工具和一套六步安装脚本。

当前用户仍需自行准备数据库、加载数据、创建 Vega Catalog、扫描资源、导入和绑定 BKN、构建索引，并发布函数和 Skill。步骤多、依赖分散，且数据库网络地址、CLI 登录态和脚本运行环境容易配置错误。

本设计在不修改 OpenBKN 核心服务和 CLI 的前提下，为仓库增加一个统一的 Shell 入口。用户已安装 OpenBKN 并完成一次 `openbkn auth login` 后，通过一条命令得到完整、可查询、可供 Agent 使用的知识网络。

## 2. 目标与非目标

### 2.1 目标

用户通过以下命令安装样例：

```bash
./install.sh supply-chain
./install.sh world-cup
```

安装器应完成：

1. 检查本机工具、OpenBKN 登录态和目标平台版本；
2. 准备一个 OpenBKN 集群可访问的 MariaDB 样例数据库；
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

- 不新增 `openbkn sample` CLI 命令或平台样例管理 API；
- 不修改 OpenBKN 核心部署流程或复用平台控制数据库；
- 不承诺让 OpenBKN 访问 NAT、防火墙或私网之后的任意 Docker 主机；
- 不自动注册 LLM 或 Embedding 模型；没有 Embedding 时允许降级为关键字索引；
- 不把预生成的 `/var/lib/mysql` 数据目录打入镜像；
- 首版不提供完整卸载器，避免误删用户已使用或修改的平台资源。

## 3. 用户接口

### 3.1 基本命令

```bash
./install.sh <sample> [options]
```

支持的 sample 名：

| 用户名 | 仓库目录 | 知识网络 ID |
| --- | --- | --- |
| `supply-chain` | `samples/supply_ontology_hand` | `supply_ontology_hand` |
| `world-cup` | `samples/world-cup` | `worldcup_vega_catalog_bkn` |

首版参数：

| 参数 | 说明 |
| --- | --- |
| `--runtime auto\|k8s\|docker` | 默认 `auto`；优先选择确认属于目标 OpenBKN 的 Kubernetes 集群 |
| `--catalog-host <host>` | Docker 模式必填；OpenBKN 集群访问数据库时使用的地址 |
| `--namespace <name>` | Kubernetes namespace，默认 `openbkn-samples` |
| `--dry-run` | 输出计划和将使用的资源名称，不产生外部写入 |
| `--upgrade` | 允许从旧样例版本升级并更新由安装器管理的资源 |

不提供镜像名参数。安装器固定使用：

```text
ghcr.io/openbkn-ai/bkn-samples:<version>
```

仓库根目录的 `VERSION` 是唯一版本源。`install.sh` 读取该版本并使用完全相同的镜像 tag，不使用浮动的 `latest`。开发者的 commit SHA tag 只供 CI 和维护调试使用，不进入公开用户接口。

### 3.2 前置条件

所有模式都要求：

- 已安装 `openbkn` CLI；
- 用户已运行 `openbkn auth login`，当前身份拥有 Catalog、BKN、Toolbox、Function 和 Skill 所需权限；
- `curl`、`jq` 和 Bash 4+ 可用。

Kubernetes 模式还要求 `kubectl` 可访问 OpenBKN 所在集群。Docker 模式要求 Docker Engine 和 Compose plugin 可用，并要求 OpenBKN 集群能反向访问 `--catalog-host` 及数据库端口。

## 4. 架构

```text
用户
  |
  v
install.sh ---------------------------------------------------+
  |                                                           |
  | 读取 VERSION、检查登录态、选择 runtime                    |
  |                                                           |
  +--> Kubernetes runtime          Docker runtime             |
  |    StatefulSet + Service       Compose MariaDB            |
  |    Loader Job                  Loader container           |
  |            \                     /                        |
  |             +---- MariaDB -----+                         |
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
│   └── openbkn.sh
├── manifests/
│   ├── k8s/
│   └── compose.yaml
└── samples/
    ├── supply-chain.sh
    └── world-cup.sh
```

`common.sh` 提供阶段执行、重试、日志脱敏、精确名称查找和 JSON 解析。runtime 模块只管理数据库与 Loader，不理解 BKN。sample 适配器负责各自的数据集、BKN 和能力发布流程。

### 4.2 数据库

使用固定版本的官方 MariaDB 镜像。两个样例使用独立数据库：

- `supply_demo_hand`；
- `worldcup`。

Kubernetes 模式在 `openbkn-samples` namespace 中创建一个共享的 MariaDB StatefulSet、ClusterIP Service、PVC 和 Secret。Docker 模式通过 Compose 创建等价服务和持久卷。

数据库密码首次安装时随机生成：

- Kubernetes 模式保存在 Secret；
- Docker 模式保存在权限为 `0600` 的本地状态文件；
- 日志、命令摘要和最终报告均不得打印密码；
- MariaDB 不使用 OpenBKN 自身的 MariaDB 实例或账号。

### 4.3 数据镜像

唯一 OCI 镜像为：

```text
ghcr.io/openbkn-ai/bkn-samples:<version>
```

镜像包含：

- 供应链的 12 张脱敏 CSV；
- 两个样例的数据加载脚本、schema 映射和校验工具；
- Python 运行时、数据库客户端和固定依赖；
- 世界杯数据集锁文件与许可证说明。

镜像不包含：

- MariaDB 数据目录；
- OpenBKN Token 或其他用户凭据；
- 世界杯 CSV 数据本体。

同一镜像在 Kubernetes 中作为一次性 Loader Job 运行，在 Docker 中作为一次性 Loader container 运行。完成加载和校验后退出，不作为常驻服务。

### 4.4 OpenBKN 控制面操作

Catalog、BKN、Toolbox、Function 和 Skill 操作由宿主机的 `install.sh` 调用 `openbkn` CLI 完成，复用用户已有登录态和 token 刷新能力。数据库容器和 Loader 不接收 OpenBKN Token。

供应链现有 Python 工具继续作为实现主体。安装器在仓库内创建临时 virtualenv 并安装锁定依赖，避免修改系统 Python。世界杯现有 `run.sh` 拆出或复用其平台阶段，使数据准备与平台 bootstrap 可以分别重跑。

## 5. 数据策略

### 5.1 供应链

供应链 CSV 已脱敏且随仓库发布，构建时进入 OCI 镜像。Loader 复用现有字段类型覆盖与加载顺序，加载完成后核对：

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

Loader 下载到持久缓存卷，逐文件校验后再开始数据库事务。不得使用浮动的 `master`。下载或校验失败时不创建或覆盖数据库中的正式表。

为避免用户看到半加载状态，Loader 使用临时表或临时数据库完成加载与校验，全部通过后再切换为正式表。重跑时已验证的下载缓存可以复用。

## 6. 安装流程

### 阶段 0：只读预检

在产生任何外部写入前完成：

1. 验证 sample 名和参数；
2. 读取 `VERSION` 并确认对应 OCI 镜像可拉取；
3. 执行 `openbkn auth status`；
4. 检查平台版本和当前账号能力；
5. 检查所选 runtime；
6. Kubernetes 模式确认当前 context 中存在 OpenBKN 服务；
7. Docker 模式由 Vega 服务端测试 `--catalog-host` 的可达性；
8. 输出将创建或复用的资源清单。

`auto` 模式只有在当前 Kubernetes context 能识别出目标 OpenBKN 部署时才选择 Kubernetes；否则选择 Docker。无法证明集群归属时应失败并要求显式指定，而不是写入可能错误的集群。

### 阶段 1：准备数据服务

- 创建或复用 namespace、Secret、PVC、StatefulSet 和 Service，或 Compose project；
- 等待 MariaDB health check 通过；
- 确认数据库连接只使用样例专用账号；
- 启动 Loader 并等待其成功退出。

### 阶段 2：创建 Catalog 与发现资源

- 使用确定性 Catalog 名：`bkn-sample-<sample>`；
- 按精确名称查找已有 Catalog；
- 已有 Catalog 的 connector 地址或数据库名不匹配时立即停止，不接管同名资源；
- 测试连接后启动完整发现任务并轮询完成；
- 验证供应链 12 张、世界杯 27 张目标表均已发现。

### 阶段 3：导入和绑定 BKN

- 校验本地 BKN 资产；
- 渲染 Vega resource ID 占位；
- 导入或更新确定性知识网络 ID；
- 绑定对象类与关系数据源；
- 校验绑定数量及关键对象查询。

同版本重跑只验证现状，不覆盖用户修改过的 BKN。只有显式 `--upgrade` 才允许把安装器管理的旧版本资源更新到当前版本；如果无法证明资源由本安装器创建，则停止并报告冲突。

### 阶段 4：索引与能力发布

- 有可用 Embedding 模型时构建样例定义的向量索引；
- 无 Embedding 时构建关键字索引或跳过非必需向量能力，并明确报告降级；
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

Loader 在数据库维护 `bkn_sample_meta` 表，至少记录：

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
2. 删除一次性 Loader Job/container 和临时凭据；
3. 输出失败阶段、原始错误、已创建资源和安全的重跑命令；
4. 返回非零退出码。

日志写入 `.bkn-samples/logs/<sample>-<timestamp>.log`，对密码、Token 和 connector secret 做脱敏。

## 8. 安全与许可

- 安装器只读取当前用户的 OpenBKN 登录态，不复制长期 refresh token 到数据库容器；
- MariaDB 在 Kubernetes 模式仅暴露 ClusterIP；
- Docker 模式默认不声称平台可达，必须通过服务端连接测试后才能继续；
- 所有镜像基础层和依赖固定版本，发布时生成 SBOM 和 provenance；
- 供应链数据继续声明为脱敏历史回放，不能用于真实交付承诺或写回 ERP；
- 世界杯安装输出和缓存目录保留 Joshua C. Fjelstul 的署名及 CC-BY-SA 4.0 许可说明；
- 运行时下载的数据不重新打包进入 OpenBKN 发布镜像。

## 9. CI 与镜像发布

### 9.1 `ci.yml`

在 pull request 和 main push 上运行：

- ShellCheck；
- 供应链现有 Python 测试；
- `install.sh --dry-run` 契约测试；
- Kubernetes manifest 和 Compose 配置校验；
- 构建 OCI 镜像但不推送；
- 启动临时 MariaDB，加载供应链数据并核对表数、行数和关键查询；
- 使用小型固定 fixture 测试世界杯下载失败、checksum 失败、缓存命中和加载逻辑。

PR CI 不下载完整世界杯数据，避免上游网络导致常规提交不稳定。

### 9.2 `release-image.yml`

在项目版本 tag 和手动发布时运行：

1. 验证 Git tag、`VERSION` 和安装器声明版本完全一致；
2. 下载并校验完整世界杯锁定数据，但不把数据加入镜像；
3. 分别构建 `linux/amd64` 与 `linux/arm64`；
4. 推送架构 tag 和多架构 manifest；
5. 生成 SBOM、provenance 和镜像 digest；
6. 发布完整版本 tag；稳定正式版可同时更新 `latest`，但安装器始终使用完整版本 tag。

发布镜像：

```text
ghcr.io/openbkn-ai/bkn-samples:<version>
ghcr.io/openbkn-ai/bkn-samples:<commit-sha>-amd64
ghcr.io/openbkn-ai/bkn-samples:<commit-sha>-arm64
```

## 10. 测试策略

### 10.1 单元测试

- 参数解析和 runtime 选择；
- 版本与镜像 tag 解析；
- 精确名称查找和冲突判断；
- secret 脱敏；
- 世界杯 lock 文件与 checksum；
- 阶段状态机和失败恢复。

外部命令通过 PATH 中的 fake `openbkn`、`kubectl` 和 `docker` 测试，单元测试不访问真实平台。

### 10.2 数据集成测试

- Compose 启动 MariaDB；
- 供应链完成 12 表加载和代表性 JOIN；
- 世界杯 fixture 完成宽表建表与重复加载；
- Loader 重复运行不产生重复行；
- 旧版本、损坏缓存和 checksum 不匹配均按预期失败。

### 10.3 OpenBKN 端到端测试

完整 E2E 需要真实 OpenBKN，因此不作为普通 PR 必跑项。提供手动或定时 workflow，在一次性测试环境验证：

- K8s 模式首次安装；
- 同版本重跑；
- 从旧版升级；
- 无 Embedding 降级；
- Catalog 扫描、BKN 查询、Function 调用和 Skill 发现；
- Docker 模式在可路由测试网络中的安装。

## 11. 验收标准

- 新安装的 OpenBKN 上，用户登录后执行一条安装命令即可完成样例交付；
- 供应链和世界杯两种样例均支持 Kubernetes 模式；
- Docker 模式在平台可访问数据库地址的前提下可用，并在不可达时于平台写入前失败；
- 同版本命令连续执行两次均成功，第二次不重复导入数据或创建同名资源；
- 供应链镜像内置数据，世界杯使用锁定 commit 运行时下载并校验；
- 用户无需选择或输入 OCI 镜像名；
- amd64 与 arm64 镜像均由 GitHub Actions 构建发布；
- Token、数据库密码不出现在日志和最终输出；
- 必需冒烟检查失败时命令返回非零，且报告明确的重跑入口。

## 12. 实施边界

实现应优先复用现有脚本，并按以下顺序交付：

1. 统一安装器框架、版本文件与供应链 Kubernetes 路径；
2. 世界杯 runtime 下载锁文件和 Kubernetes 路径；
3. Docker runtime；
4. PR CI、镜像发布和手动 E2E workflow；
5. 文档与发布验收。

每个阶段都必须保持 `install.sh` 的用户接口稳定。若实现过程中发现必须修改 OpenBKN 核心 API，停止扩展范围，先在独立设计中评审该平台变更。
