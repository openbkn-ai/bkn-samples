# 样例发布协议草案

状态：C1/P1 的第一批评审材料，协议尚未冻结。

本协议用于发现和发布样例。它描述样例身份、独立版本、release notes、制品与内容引用、兼容要求和安装 profile。包内路径只用于定位交付内容；客户实例自行决定工作目录、执行方式和持久化安装历史。

## 文件

| 文件 | 用途 |
| --- | --- |
| [catalog.schema.json](schemas/catalog.schema.json) | 源目录与各样例的版本条目 |
| [sample.schema.json](schemas/sample.schema.json) | 单个样例版本的发布清单 |
| [examples/catalog.json](examples/catalog.json) | 供应链两个版本的目录示意 |
| [供应链 1.0.0](examples/supply-chain/releases/1.0.0/sample.json) | 保留 KN JSON 格式的示例 |
| [供应链 1.1.0](examples/supply-chain/releases/1.1.0/sample.json) | 后续版本和独立说明的示例 |
| [作者校验器](../../tools/publication/validate.py) | 离线元数据、引用与本地说明摘要检查 |
| [候选包构建](../../docs/candidate-publication.md) | 真实内容归档、文件摘要与未验收构建报告；不发布目录 |

示例使用 `.invalid` 地址。样例版本、平台范围、日期和包摘要用于协议讨论；没有对应安装包、镜像或平台验收证明。清单和本地 release notes 的摘要按真实文件字节计算。校验这些示例不能将其变成已验证发布。

## 身份、版本与说明

- `sourceId` 标识发布源；`sampleId` 标识样例；`(sourceId, sampleId, version)` 标识独立 release。
- 样例版本使用 `MAJOR.MINOR.PATCH`，与协议版本、目录修订、平台和 SDK 版本分开管理。
- 每个 release 必须有非空 release notes 和默认语言。目录与清单必须引用相同语言集和摘要。
- 已发布版本保留原清单、制品摘要、说明及验收引用。修复内容发布新版本；撤回保留目录条目并设置 `withdrawn` 和原因。
- 安装计划固定清单摘要、版本及说明；成功验收才记录实际安装版本。失败的新安装不覆盖以前的成功记录。安装历史和说明快照属于实例接口。

清单作为独立文件放在归档之外：先构建含交付内容和说明的归档，计算归档摘要，再生成清单，最后计算清单摘要并生成目录，避免自引用摘要。

## 首期范围与演进

首期只使用官方 bkn-samples 源和现有安装链路，提供目录扫描、版本选择、说明与安装记录。协议版本用于后续演进。暂不建设插件市场、动态适配器加载、第三方源管理、通用数据提供器或复杂签名体系。来源控制由仓库 PR、CI、发布权限及固定制品摘要落实。

官方目录发现的本地实现与约束见 [发现接口说明](../../docs/official-catalog-discovery.md)。正式目录拟位于仓库根 `catalog.json`；当前未发布。expiresAt 为可选字段，显式到期时拒绝刷新覆盖缓存。

`contents` 中每份内容有 release 内唯一的 `contentId`。绑定和体验入口引用它；`artifactId + directory` 定位包内内容。不同归档可以使用相同目录名。函数包与技能包也有独立内容身份。

`bkn-directory` 指向既有 `network.bkn`；原生 BKN 的业务对象、关系、行动、能力及 CHECKSUM 沿用 OpenBKN 规范与实际解析器。`kn-json` 指向现有平台 KN 导出 JSON；供应链不要求先转换成 BKN。外层 Schema 不重新定义任何业务模型。发布前必须固定对应模型校验器、导入适配器及其 revision，并验证服务器真正支持的模型。

首期 Schema 只接受上述两种格式和固定 `openbkn.ai/sample-install.v1`。实例对不支持的格式、profile 或能力返回不兼容。新增格式在出现真实需求时再评审版本与实现。作者元数据能解析不表示实例具备执行能力。

数据依赖先沿用现有 MariaDB 声明：引擎、数据库名、制品引用和预期表数；空依赖数组允许无数据库样例。绑定先使用现有对象到表的映射，其他数据类型出现实际需求时再修订协议。

核心字段由作者 Schema 严格检查，`extensions` 保留为可选元数据空间。首期发布使用空扩展和一个固定安装 profile，不通过扩展改变执行行为。实例明确拒绝不支持的必需行为。通用扩展配置与适配器协商不列入首期交付。

## 作者校验

需要 Python 3.9+ 和作者工具依赖：

```sh
python -m pip install -r tools/publication/requirements.txt
python tools/publication/validate.py protocol/draft/examples
```

作者工具接受一个本地目录，其中包含 `catalog.json` 和 `<sampleId>/releases/<version>/sample.json`。这是工具输入布局；协议消费者按目录 URL 获取清单，无需使用相同文件布局。

正式发布时传入从可信基线提取的上一份目录：

```sh
python tools/publication/validate.py candidate-root --baseline trusted-previous-root
```

工具拒绝重复 JSON 键、重复身份、版本/说明不一致、摘要不符、未知引用、穿越路径及本地说明的符号链接；传入基线时拒绝删除历史 release 或修改其固定引用。没有基线时不能判断历史版本是否被改写。基线由发布流程取得，不能让 PR 作者自选。

工具不联网、不下载制品、不执行作者代码，也不验证归档内容、BKN/KN 模型、对象绑定是否完整或服务器安装结果。草案 fixtures 可随评审调整，不能作为正式版本不可改写的基线。

## 后续批次

1. C1：固定首期字段、两种已知格式和一个安装 profile，收敛发布契约。
2. D0/C2：确定实际实例能力，冻结预检、安装和历史接口。
3. P1：目录生成、完整制品校验、可信基线和官方源发布权限。
4. S1/P2/P3：供应链真实候选包、固定摘要的平台验收与正式发布。
5. R/U：实例扫描和持久安装记录，Studio 首页版本选择、release notes 与安装历史。
