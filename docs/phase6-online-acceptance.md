# 第六阶段：在线全新安装与历史验收

2026-10-11，在既有 `http://localhost:8081` 开发实例执行。没有启动第二个 OpenBKN 实例。

## 操作和结果

1. 将早期固定目录配置恢复为官方主线扫描；实际目录提交为 `5ad12adacdf3e68a90ffb0add36d4c0a196511ef`。
2. 备份世界杯旧安装记录、配置和离线缓存，清理该测试样例的数据源、知识网络和专属数据库资源。供应链 0.1.2 保持已安装。
3. 从 Studio 首页查看世界杯 0.1.1 说明、确认并点击开始安装。任务使用 `remoteRelease`，不是离线导入或内置安装。
4. database、discover、knowledge、capabilities、verify 五阶段全部成功；成功记录与 `state/history/world-cup/inst-world-cup-0.1.1.json` 完全一致。
5. 重建样例服务，管理员历史 API 返回的记录与重建前完全一致，两张卡片保持已安装。
6. 点击“打开知识网络”，进入 `worldcup_vega_catalog_bkn`，页面显示 27 个对象类、29 个关系类、4 个概念组。

| 固定身份 | 本次实际值 |
| --- | --- |
| sample / version | world-cup / 0.1.1 |
| 任务 | inst-world-cup |
| 开始时间 | 2026-10-11T01:50:42.642128Z |
| 成功时间 | 2026-10-11T01:51:27.246532Z |
| manifest SHA-256 | 8e1ad4ed90bbf581f9be26c8d0103e5d78ddaecf9fc59c3a6b49893a82033cae |
| package SHA-256 | 56ecb0641daada096220028d8b7145b099de601dcd0a54662dc33ed5f6f03eb2 |
| 数据镜像 | ghcr.io/openbkn-ai/bkn-samples@sha256:805317bc1ac93e58f4149e35a7a0a75057330d8888ca54526a354996f313fcd1 |
| 本地安装器镜像 | docker.io/openbkn-local/bkn-sample-studio@sha256:8a7261be98991cb07c942da6b362a9e6aebf57ad9a58740c40e11df5a98790f3 |

## 发现的问题和验收边界

官方远程条目在安装前不含已创建的知识网络 ID。Studio 原解析器因此过滤掉可安装卡片。候选修复允许未安装、在途及失败卡片暂缺 ID，仍要求已安装卡片拥有真实打开目标；12 项定向解析测试通过。此次首页验收使用该待评审候选，不能宣称修复已经合入 Studio 主线。

安装器使用包含 #94 的本地镜像，正式主线镜像和 Chart 已发布，但本次不是正式 Chart 安装或迁移验收。历史仅保存每个任务 / 版本的最新终态，同版本重试会更新记录；本次不证明逐次尝试的追加历史，也不能恢复此前丢失的记录。

证据保存在验收工作区 `artifacts/acceptance/history-real-install/`：管理员安装与历史 API 的无凭据 JSON、前后历史比较和首页截图。保护目录中的备份含运行配置，不提交到仓库。

仍需独立完成第三个样例动态发布、逐次尝试历史及产品部署、迁移、回退验收。
