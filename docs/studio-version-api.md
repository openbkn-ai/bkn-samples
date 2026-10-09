# Studio 版本信息兼容接口

状态：未提交候选，已在 localhost:8081 完成页面联调与异步安装、中断重试验收。适用于现有 v1alpha1 安装镜像；不等同于独立多版本发布协议。

## 首批能力

- 目录仍读取镜像内置索引，当前仅有根 VERSION 指定的一个版本。
- 每个样例可随镜像交付 `releases/<version>/release-notes.<locale>.md`；构建索引保存内容与 SHA-256，旧样例缺失说明时不声明该能力。
- 供应链与世界杯添加当前内置 `0.1.0` 的中英文说明，描述现有内容与限制，不自报动态发布验收已完成。
- 新安装记录保存目标版本、清单摘要、说明快照及真实时间；旧记录缺失的字段不补造。

## 路由

所有路由继续由 bkn-safe 鉴权。下列服务端路径以 `/api` 开头，Studio request 基址已包含该前缀。

| 方法与路径 | 返回或约束 |
| --- | --- |
| `GET /api/studio/samples` | 增加每卡 `manifestSha256`、`versions[{version,hasReleaseNotes}]`、成功时的 `installedAt`；保留 installedVersion |
| `GET /api/studio/samples/<sample>/versions/<version>/release-notes?locale=zh-CN` | `{sample,version,resolvedLocale,content,digest}`；匹配语言不存在时回退到说明默认语言；优先读取原安装快照 |
| `GET /api/studio/samples/<sample>/installations` | `{items,historyComplete:false}`；当前最多一条，不能还原曾被旧服务覆盖的记录 |
| `POST /api/studio/samples/<sample>/installations` | 支持 `{version,manifestSha256}`，与当前可安装目录核对；不符返回 409 version_changed；保留旧空 body 调用 |
| 既有安装读取与重试 | 记录视图增加 startedAt、finishedAt；重试拒绝不同版本，新记录还核对原清单摘要 |

说明摘要使用 `sha256:<64hex>`；兼容字段 manifestSha256 沿用旧索引的裸 64hex。后者仅覆盖旧清单、数据库 hooks 及本次加入的说明文件，**不等同于完整制品摘要**。正式发布按 publication draft 另行实现完整内容核对。

创建和重试成功接受后均返回 HTTP 202 和现有安装任务视图（status:installing、id、版本与阶段）。先在 PVC 原子写入状态，再启动后台线程；失败预检仍同步返回 4xx。Studio 使用 30 秒请求超时并读取既有任务查询接口，不再等待安装结束。重复进行中请求返回 409，不产生第二个执行任务；尚未引入幂等键机制。

部署必须维持单副本 Recreate。服务启动时将遗留 installing 标记 failed / install_interrupted，保留阶段、版本、说明和资源引用，管理员可按原清单与数据镜像重试；不自动重放安装。调用凭据仅保留在当前工作线程内存，不写入任务文件。多副本协调和完整尝试历史尚未实现。

新增记录的说明快照在后续目录变化时继续可查。旧记录没有摘要时，只能沿旧机制核对版本，无法证明同版本的全部原始制品一致；迁移需单独处理。当前列表尚不支持远程仓库扫描，刷新按钮是“重新加载”。

## Studio 接入

卡片展开时加载说明和现有记录，收起后保留摘要。说明使用项目既有 MarkdownText 渲染；接口支持说明但读取失败时阻止安装提交。安装携带当前版本和摘要；旧服务器没有 manifestSha256 时继续使用旧请求。

已安装样例默认查询 installedVersion 的说明，不把目录当前版本当成成功安装版本。版本选择、动态官方目录、多版本包与完整历史仍待后续实现。

## 检查状态

30 个安装器定向测试、21 个受影响首页测试通过。真实页面创建与重试均返回 202，分别耗时 19–69 / 25 毫秒。容器硬中断后标记失败，管理员从页面重试原任务成功，版本、说明及制品引用保持一致。证据在工作区 artifacts/acceptance/studio-async；复用已有资源，不能替代固定候选首次全新安装或正式发布验收。
