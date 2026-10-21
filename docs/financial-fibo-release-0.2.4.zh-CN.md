# FIBO 0.2.4 固定包发布验收

中英文两个独立固定包从已合并PR #183的提交 `763f318348f1901f42b6733872a12e1610f2d2a8` 构建，要求 **OpenBKN 0.2.1及以上**（`>=0.2.1 <0.3.0`）。每语言20表、78,356条虚构记录、20对象、29关系、3分组、3函数、2快照指标、1只读调查Skill。两个包均已在8081标准卸载、清理各自离线缓存、精确导入、全新安装后完成有界技术检查；未变更平台镜像/配置、数据或金标准。其他9个样例完整卡片及安装身份保持不变。

## 验收结果按实际范围报告

| 验证范围 | 英文 | 中文 | 可作出的结论 |
|---|---:|---:|---|
| 当前固定包最终技术检查 | 8/8（100%） | 8/8（100%） | 指定的绑定、数据库、三函数、双指标及Skill正文检查通过，共16/16；不是模型准确率 |
| 原公开题单轮财务字段 | 96/100 | 96/100 | 原分母和8个失败保持不变，不改写全量100% |
| 原公开题未作等价归一的字段 | 94/100 | 93/100 | 原始严格字段结果，未因发布改分 |
| 之前平台修复后指定四条工具路径 | EN FIN-010/088通过 | ZH FIN-015/071通过 | 合计4/4（该四项100%），不是新增全量或盲测 |

本轮正式问答题数、模型调用数均为0，没有重跑100题或那四题。两个技术交互均execution=completed；finish初始assembling，经有界查询确认evidence=complete。首次失败、重试和证据维度均不并入模型题目分数。

## 安装实际过程

英文首次在knowledge阶段返回 `BknBackend.ConceptGroup.InternalError.InsertOpenSearchDataFailed` / `WriteDatasetDocument HTTP500`；数据库与发现阶段已成功。对同安装记录执行唯一一次标准retry后，五阶段全部成功，未改变包或平台。根因仍未确认，不能因重试成功称其必为瞬态故障，更不能称首次安装100%。中文首次全新安装五阶段全部成功，无重试。原始失败及恢复详情绑定在各Release的acceptance.json和verification.json中。

## 精确制品与功能检查

- 英文：[0.2.4 Release](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.4)，包摘要 `sha256:6c4eb89b9755b5af335845502838682a5ce89293d6e4ea135ba338d665789a56`，995,597字节。
- 中文：[0.2.4 Release](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.2.4)，包摘要 `sha256:f99c88eadabcae64752039cca4ea9da3ad4a26d7fdab3bd0303a6bf23e59e519`，994,468字节。
- 每语116个交付文件与固定源码字节核对，四个hook均0755；评测题、答案及本地验证目录未进入安装包。全部20个resource binding不同且资源名与对应表一致。
- 78,356条带类型数据由精确包安装阶段的dbInit/dbVerify全行检查证明，没有额外重复全表MCP读取。三函数各执行一次PF-046、actual、业务日/知识日2027-02-28：结算32行、估值8行、限额5行。与包内同一内核的比较是来源/实现一致性检查，不能冒充独立金融oracle；另用冻结标量断言应收2002.41 USD、阈值500 USD、超额1502.41 USD。
- 真实快照指标分别取CE-046-4应收2002.41和IE-046-1-4集中度0.254176。Skill挂载正文与源码一致，但仅有SKILL.md，没有附件；其中相对路径 `../../docs/business-capability-contract.md` 是源码文档参考，未验证挂载环境解析。本轮小范围调用依赖函数schema和Skill正文，不声称附件或相对引用可用。

## 环境与发布边界

8081实际Vega EE为 `0.2.1-main.20261020181403.sha7bb933f`（依赖#2288）；控制面为 `0.2.1-main.20261021005935.shaba89095`（#2301）。AOI/retrieval仍使用c24-fix2-reviewed2本地镜像，样例安装器是已有main-contract-fixes-r2版本；执行器为先前控制面重建后的官方python-basic37b2b3b。详细镜像快照在Release验收证据中，只采集运行前快照，本任务未修改平台部署。`>=0.2.1`是声明下限，复现需同时核对这些已修复构建；不能据此声称原版0.2.1或全部后续构建均已验收。

仅实测arm64；未做amd64运行认证或集群级断外网验证。使用产品共享MariaDB，无样例独立数据库镜像。原100题没有逐ID自动证明全部源证据和自然语言结论，本次同源技术对比不能补成盲测准确率。

Release提供原验收包、acceptance.json和SHA256SUMS；固定资产不覆盖历史版本。归档中README/版本说明保留固定源码的准备阶段措辞，当前可用性以Release和官方目录为准。发布PR只提议登记两个0.2.4版本，保留其他目录条目；PR合并后仍须刷新8081官方目录并验证正式在线安装，本次离线验收不提前宣称该步通过。旧020内置发现索引不修改。

标准构建器本次发现会继承旧manifest的sizeBytes，导致新包在线下载后被拒绝；已改为当前build.json测得字节数，并给既有测试增加实际文件大小断言。该修复只影响元数据构造，不更改已验收归档；安装器254项检查（1项跳过）通过。

[源包对应](financial-fibo-acceptance/release-0.2.4/source-package-parity.json)、[历史评分来源](financial-fibo-acceptance/release-0.2.4/historical-evaluation-provenance.json)、[英文技术结果](financial-fibo-acceptance/release-0.2.4/en-us-native-summary.json)、[中文技术结果](financial-fibo-acceptance/release-0.2.4/zh-cn-native-summary.json)、[其他样例不变](financial-fibo-acceptance/release-0.2.4/other-nine-identity-parity.json)供复核。原评分和本轮结果分别保存，不选择最好一次合并分数。

公开标准客户端已读取保留标签下的完整提交SHA元数据，并从真实Release URL下载两包、安全解压、验证原生本体及全部20绑定。0.2.0在读取元数据前被拒绝，0.2.1通过声明兼容检查；包、acceptance和SHA256SUMS摘要均匹配。此步骤不安装到8081，也不代表官方目录已合并。[公开客户端回执](financial-fibo-acceptance/release-0.2.4/publication-client-verification.json)、[上传后回下载字节核对](financial-fibo-acceptance/release-0.2.4/release-asset-roundtrip.json)、[Release发布回执](financial-fibo-acceptance/release-0.2.4/published-releases.json)。

## PR #188 审核修正

审核确认旧基线manifest漏报execution.function、execution.skill，实际已发布离线包的offline-release.json已包含这两项。构建器改为整体读取实际包的requires；两个0.2.4在线manifest及目录同步补齐，包、安装证据及其摘要不变。7项相关测试通过，并对两语分别验证缺少任一执行能力时在元数据读取/下载前拒绝。[定向公开客户端回执](financial-fibo-acceptance/release-0.2.4/publication-client-requires-fix.json)记录新固定引用，原回执保留为发布时历史。

另一项阻塞尚未解决：包内版本说明仍为源码候选措辞，标准客户端要求在线版本说明与包内文件摘要一致，不能仅替换在线文本。0.2.4已发布资产保持不可变；用户随后确认改发0.2.5修正版；0.2.4不再申请目录登记，资产不变，当前处理见[0.2.5发布报告](financial-fibo-release-0.2.5.zh-CN.md)，PR保持未合并。
