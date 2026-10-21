# FIBO 0.2.5 发布修正版验收

0.2.5仅修正发布说明与能力要求，替代0.2.4申请官方目录登记。要求 **OpenBKN >=0.2.1 <0.3.0**。中英文是两个独立样例，每语20表、78,356条虚构记录、20对象、29关系、3概念分组、3函数、2快照指标、1个只读调查Skill。

## 审核阻塞与修复

- `65361ad884f7e89a`：0.2.4包内版本说明仍称未发布候选。标准客户端同时核对在线说明与包内文件摘要，不能仅替换在线文本。按用户确认发布新0.2.5包，使用明确的修正版说明，0.2.4已发布包、acceptance.json与SHA256SUMS保持原资产ID、摘要和字节数。
- `b00183941adff85a`：在线manifest继承旧版本能力要求，漏报execution.function和execution.skill。标准构建器现从实际包的offline-release.json整体读取requires；两语在线manifest、目录与离线描述符一致。

两语各111个运营交付文件与0.2.4包逐字节一致；数据、本体、函数、指标、Skill均未变化，题库与答案相对已合并源码无差异。样例版本身份、README、当前版本说明及离线描述符发生预期变化。原四个hook执行位保持0755，评测题和答案不进入安装包。

## 本轮验证范围

只验证精确包安全解压、原生BKN与20绑定校验、标准离线导入/全新安装、能力门槛与其他样例身份不变。不运行模型问答，不重跑100题、此前四条工具路径或0.2.4的八项原生技术交互。

两语各四种兼容门槛均符合预期：0.2.0拒绝，缺execution.function拒绝，缺execution.skill拒绝，0.2.1全能力接受。缺能力/低版本拒绝均在读取元数据与下载前发生。发布工具与客户端相关22项回归测试通过。

## 结果口径与环境边界

0.2.5没有新的问答准确率。历史单轮财务字段仍为英文96/100、中文96/100；原始严格字段94/100、93/100不改写。修复后指定历史工具路径4/4、0.2.4代表性技术检查16/16均保留为历史分母，不能作为0.2.5新增全量100%或独立盲测结果。

本轮使用既有修复后的8081 arm64环境，不变更平台镜像或配置。不能据此声称原版0.2.1、amd64执行或集群级断网已验收。数据库hook原始stdout不被现有运行时持久化；以精确包的数据库阶段成功、平台验证阶段实际checks及完整安装回执作证，不伪造stdout或重复执行hook。Skill仍只有SKILL.md，源文档相对引用不是挂载附件，其运行时解析仍未验证。

发布PR #188保持未合并。官方目录刷新与正式在线安装须在PR合并后验证，本轮离线安装与公开客户端下载验证不能提前宣称完成该步骤。

## 实际安装结果

中英文各一次标准卸载0.2.4、仅清理自身离线缓存、导入精确0.2.5包、全新安装，均五阶段成功；**2/2首次安装成功、0失败、0重试**。内部state保留五项检查均ok：ownership、20-object-types、29-relations、20-resource-bindings、20-live-object-queries；capabilitySummary保存3函数、2指标、1 Skill注册/校验结果，未再次执行函数。其他9样例完整卡片和安装回执未变，运行镜像与pod身份前后完全一致。

- en-us：`inst-financial-fibo-en-us-672a88213c7e43e888514dc4d1eb22ce`，attempt `195828d344994db697f311661a989c33`；UTC 2026-10-21T04:04:08.283179Z 至 2026-10-21T04:34:36.426757Z。
- zh-cn：`inst-financial-fibo-zh-cn-bb40874abe6d4788b3ff4fa0e7d8518b`，attempt `01d4bfd4302b4e2eb17775936b817746`；UTC 2026-10-21T04:34:39.997540Z 至 2026-10-21T04:36:23.947214Z。

英文回执跨度约30.5分钟，只是主机墙钟跨度，原因未确认，不据此推断连续执行时长或性能；中文约104秒。一次本地预检因超出本轮范围的附件断言而在平台调用前中断，该断言移除后继续；它不是安装失败或重试。

[源包一致性与能力门槛](financial-fibo-acceptance/release-0.2.5/source-package-parity.json)、[实际安装与运行快照](financial-fibo-acceptance/release-0.2.5/platform-install-summary.json)、[历史0.2.4资产未变](financial-fibo-acceptance/release-0.2.5/historical-024-assets-unchanged.json)。

## Published fixed assets and public client

- [EN 0.2.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.5): SHA-256 `bd191c446c34dbb0cc80d420fc74461e1f64563d8bc1527be4cefe48942390a3`, 996,159 bytes.
- [ZH 0.2.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.2.5): SHA-256 `2e86b89d70d79d8434396585ff92d9f5a82f366901f7eeada6aa07172fe4e3c9`, 994,875 bytes.

Source: `9d469ac08c20ca2c1f9c01c4cba0da8a94a432be`. Metadata: `57f878c314c7212298b833bc34f2b24e2b2b21be`, retained by `samples-financial-fibo-metadata-20261020-v025`. All six uploaded assets matched byte-for-byte after download. The standard public client read the real pinned metadata and Release assets, verified corrected release notes, missing-capability rejection, package/evidence digests, safe extraction, native BKN and all20bindings. Official online catalog installation remains pending merge.

Official publication validation passed16releases with all14baseline entries preserved; sequence15 adds only the two0.2.5entries. Version0.2.4 is not registered. Manifest-index build/check passed.

[Public client receipt](financial-fibo-acceptance/release-0.2.5/publication-client-verification.json), [six-asset roundtrip](financial-fibo-acceptance/release-0.2.5/release-asset-roundtrip.json), [publication receipts](financial-fibo-acceptance/release-0.2.5/published-releases.json).
