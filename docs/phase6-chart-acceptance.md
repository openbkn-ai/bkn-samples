# 第六阶段：官方 Chart 部署与回退验收

2026-10-11，复用 localhost:8081 / kind-bkn-dev，不启动第二个 OpenBKN 实例。

## 固定发布身份

| 项目 | 实际版本 / 摘要 |
| --- | --- |
| samples 主线 | `99d0341cdac6e7c81c7d1f8eb392655eeddabe44`（#97） |
| 样例服务 Chart | `0.1.0-main.20261011023813.sha99d0341` |
| Chart OCI digest | `sha256:1952eabd7377a3cc47e3ca23560ed9ed80fcd779f8280b3d61998ed269cf11c8` |
| 服务镜像 digest | `sha256:77db15d19f7063bf78baf2cddfad2363ba3c06b82f988bf56557c4263d72824b` |
| Studio 主线 | `45b720dc1a653bf037bf98c45bb291452c8544bd`（#857） |
| Studio Chart / 镜像 tag | `0.2.0-main.20261011103803.sha45b720d` |
| 回退检查的服务 Chart | `0.1.0-main.20261011020912.sha52cfc41` |
| 回退检查的镜像 digest | `sha256:b973a83ea549d243a40bcd20f4be478f5391769b92b1f5521a79d1925a141eb8` |

两仓均使用 GitHub 主线流水线发布的 OCI Chart 和镜像，不是本地重建候选。平台仍为原有 0.2.0 主线测试实例；本项不替代全套平台发行验收。

## 实际结果

- 私下备份状态，原 `bkn-sample-studio-state` PVC 保留。以 `existingClaim` 将原手工部署接入正式 Chart，Helm 4 使用 `--take-ownership`。Studio 的旧 `kubectl set image` 字段冲突使用 `--force-conflicts` 交回 Helm。
- 新版服务返回的供应链 0.1.2、世界杯 0.1.1 成功版本、时间和网络入口与迁移前一致；两份历史 API 完全一致。世界杯保留旧成功、中断失败、重试成功三条记录。
- 切换到上一官方服务版本后，成功版本和状态文件摘要均不变。该旧版 API 不返回 `attemptId`，并错误地将世界杯旧历史标为完整；因此回退仅验证无写入读取兼容，不能承诺旧版历史展示正确。
- `helm rollback ... 1` 恢复新版后，两份历史 API 再次与迁移前完全一致，全部状态 JSON 摘要与回退前一致。回退期间未发起新安装或重试。
- 新版再重建一次 Pod，供应链、世界杯的状态及历史 API 仍与迁移前完全一致。

## 卸载保护修复

部署核对发现 Chart 的 Namespace 缺少保留策略：卸载服务会级联删除样例数据库所在命名空间。此 PR 为 `openbkn-samples` 增加 `helm.sh/resource-policy: keep`，与状态 PVC 的保留规则一致。

`helm lint`、模板的 Namespace / Recreate / existingClaim 断言通过。将实际渲染的 Namespace 保留元数据用于临时 Chart，安装后卸载：Namespace 保留，普通 ConfigMap 删除；随后清理临时命名空间。没有卸载生产样例服务或删除样例数据库。该修复尚待本 PR 合并发布，当前 #97 发布的 Chart 不含修复，不应直接卸载。

证据位于验收工作区 `artifacts/acceptance/chart-delivery/`：无凭据的前后 API、Helm revisions 和状态摘要。保护备份不提交。操作步骤见 [服务部署说明](sample-service-deployment.md)。

仍需固定客户端与安装器后发布第三个独立样例的动态新增验收，以及 Foundry 整体部署入口的集成核对。当前 standalone Chart 验收不能代替后者；不宣称第六阶段全部完成。
