# OpenBKN 样例产品资料

## 设计与实施

- [一键体验总体设计](DESIGN.md)：协议、跨仓库职责、在线／离线安装及资源归属。
- [0.2.0 总体实施进度](RELEASE_0.2.0_STATUS.md)：各阶段交付状态、待完成项与已知边界。
- [发布协议与 Schema](../protocol/draft/README.md)：目录、版本清单及原生模型引用。

## 使用与开发

- [中文开发与版本更新指南](SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md)
- [Sample Development Guide](SAMPLE_DEVELOPMENT_GUIDE.md)
- [按产品版本选择样例目录](product-version-catalogs.md)：产品版本、目录、固定包及缓存隔离。
- [0.2.1 本地验证与候选边界](acceptance/samples-0.2.1/README.md)：11 个源码样例中的 9 个候选包，制造业双语待补齐。
- [固定包构建与发布](candidate-publication.md)
- [完整离线安装](offline-installation.md)：自包含包、节点本地镜像导入、禁拉取与断网验收。
- [卸载与重装](sample-uninstall.md)
- [服务部署](sample-service-deployment.md)
- [供应链问题分类与准确率验收方案](supply-sample-optimization-triage.zh-CN.md)：issue 分类、评测基线差异及新版发布门禁。
- [供应链历史数据追溯与本次评测基线](supply-sample-history-forensics.zh-CN.md)：8 月底 POC 数据证据、变更时间线及完整 CSV 基线。
- [供应链优化实施记录](supply-sample-implementation-status.zh-CN.md)：本轮修复、真实 BKN 验证及剩余发布门禁。

样例内容、独立版本说明和正式验收凭证位于 `samples/<directory>/releases/<version>/`。根目录 [catalog.json](../catalog.json) 保留给已发布的 0.2.0 客户端；新服务按产品版本选择 [0.2.0 目录](../catalogs/0.2.0/catalog.json)或 [0.2.1 目录](../catalogs/0.2.1/catalog.json)。源码样例总数为 11，本轮候选包为 9，候选不代表平台验收通过。
