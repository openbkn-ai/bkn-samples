# 供应链分类字段补丁发布验收（2026-10-27）

本次改进位于 bkn-samples，关联 [Foundry #2516](https://github.com/openbkn-ai/bkn-foundry/issues/2516)。没有增加平台分类能力、答案纠正、DSH 特判或第二套交期算法。

## 固定发布

| 样例 | 版本 | 最终制品 MF-01 |
| --- | --- | --- |
| [中文供应链](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.12) | 0.1.12 | 1/1 通过 |
| [英文供应链](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-en-v0.1.8) | 0.1.8 | 1/1 通过 |

- `supply-chain`：`sha256:a90125eaa669079d4ba8ff494c3a72dbbdddb4fb2cdb99f685b82946a4e9b456`。
- `supply-chain-en`：`sha256:6ba85cfeb73c93eb693c643adf9556c905cb43399b6d075f5f061663a1707275`。

固定源码：[7c6dbcd70b7ca806b7b23ebe03995107c1bfffe0](https://github.com/openbkn-ai/bkn-samples/commit/7c6dbcd70b7ca806b7b23ebe03995107c1bfffe0)。发布前草稿附件和发布后的公共客户端下载均核对同一份包、acceptance.json、SHA256SUMS，六个附件与验收文件字节一致。[公共客户端回执](supply-field-acceptance/20261027/public-client-verification.json)记录元数据、制品与兼容门槛核验。清单及 verification.json 固定在保留标签 `samples-supply-fields-metadata-20261027` 对应提交 `bc24fe1cd1109ddc99bbf99583d0a30979834e2c`。

## 改动与安装验证

#204 明确 `group_name`（存货类别/Stock Category）与 `group_type`（物料分类/Material Category）。实际首次安装另外暴露出三处样例问题，已针对性修复：

- 新增但未正式发布的补货草稿 Action ID 超出已有 8081 Backend 的 40 字符限制。缩短样例 ID 并同步所有引用，兼容当前主线的 128 字符上限；不改平台约束。
- 草稿输入参数的无效 `value: null` 在 Backend 读回时被省略，导致样例归属校验拒绝自己的定义。删除空常量，保留严格归属检查。
- Action PUT 成功时正文为空，注册脚本却解析 JSON，误报安装失败。仅允许原始 PUT 成功的空正文；列表读取、其他响应和失败退出仍严格校验。

两语最终包均在标准 API 中从卸载后的状态安装。首次任务与认证 HTTP 503、Safe Pod 替换重叠；失败记录保留，各用同一包和执行器标准重试一次后成功，不宣称首次即成功。五个安装阶段和七项检查全部通过：数据资源、对象查询、跨表查询、函数挂载、Skill、指标查询及指标归属。

中英文完整 tools/tests 各 336 项通过；最终源码的 contract、MariaDB、CodeQL、review/verify/verdict 均通过，review 无未解决意见。发布包兼容门槛拒绝 0.2.0 和缺少函数、Skill、共享数据库能力的调用者，并在读取元数据前拒绝。

## MF-01 与真实数据

使用 8081 已配置的 `deepseek-v4-flash`，模型管理 ID `2109170092993548288`；temperature=0、max_tokens=8192、thinking=disabled。临时只读模型工具循环仅提供题目、网络 ID 和真实 MCP 工具响应，不读取或提供金标、CSV、历史答案。最终回答后再按金标及独立的实际查询/函数回执核对。

| 最终回答事实 | 中文 | 英文 |
| --- | --- | --- |
| 标准生产交期 | 1 天，来源 product_fixedleadtime | 1 day, product_fixedleadtime |
| group_name | 库存商品-产成品 | Finished Goods |
| group_type | 406包装成品 | 406 packed product |

两次模型问答的交期、两个分类及附加事实均与实际源查询一致，Interaction 终态 completed、证据 complete。另分别调用实际发布的标准交期函数，返回 production、1 day、product_fixedleadtime，回执 completed/durable；这两次独立函数核验不加入 MF-01 问题分母。

两语各 12 张业务表、78,635 行与更新前备份逐行无序摘要一致；版本元数据表不计入业务行比较。其他 11 个样例的版本、状态、安装身份和 manifest 摘要未变。

较早未发布的 f62e413 候选也各测一题，原始回答单独保留，不移作或混算最终包成绩。未重跑核心 50 题，不声称通用模型准确率；模型供应方的不可变构建身份不可获得，也不是原 DSH Desktop 失败调用的复现。

## 交付边界与收尾

实测环境为已有补丁的 arm64 8081，Backend `0.2.1-main.20261016154814.sha3673f27`，样例执行器 `docker.io/bkn-local/bkn-sample-studio@sha256:e8f3e7a734973794c3362de0d002043161ea15a093e71dde611acc9a3850b3dd`。本任务未更换平台镜像或配置；不宣称 AMD64 执行、原版 0.2.1 全量认证或 Workshop 事件联调通过。

本次只向 0.2.1 目录追加两个独立补丁版本，保留原四项、0.2.0 目录、历史包、原候选批次和历史成绩。目录由 [PR #205](https://github.com/openbkn-ai/bkn-samples/pull/205) 登记；本记录未执行合并后的正式目录在线安装。目录生效前 #2516 保留待收尾，不新增平台修复项。 只读核对确认当前 8081 旧版样例服务尚不具备 ProductCatalog 路径，仍读取旧目录机制；合并后须更新到已有官方样例服务并验证正式入口，无需新增平台能力或协议。

已有网络不会因发布新包或安装重试而更新说明。维护者应先保留自定义，选择显式更新两个说明并读回，或按现有卸载/安装流程更换完整样例；卸载会清理该样例的数据与归属资源，不提供自动迁移或自定义合并。
