# OpenBKN 0.2.1 发布记录（2026-10-31）

## 已发布

12 个样例在 OpenBKN 0.2.1 主线构建（backend 0.2.1-main sha9156ec5，arm64）上全新安装验收后发布，并登记在 [0.2.1 目录](../catalogs/0.2.1/catalog.json)。Release 标题以 `[OpenBKN 0.2.1]` 开头；标签保持 `sample-<样例>-v<版本>`，因为已部署的安装器只接受这种下载地址。每个 Release 附 `package.tar.gz` 和 `acceptance.json`（安装记录与体验卡核验结果），仓库中的 `releases/<版本>/verification.json` 记录摘要、检查项和边界。

| 样例 | 版本 |
|---|---|
| supply-chain | [0.1.17](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.17) |
| supply-chain-en | [0.1.11](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-en-v0.1.11) |
| world-cup | [0.1.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-world-cup-v0.1.7) |
| world-cup-en | [0.1.3](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-world-cup-en-v0.1.3) |
| manufacturing-industry-zh-cn | [0.1.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-manufacturing-industry-zh-cn-v0.1.5) |
| manufacturing-industry-en-us | [0.1.5](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-manufacturing-industry-en-us-v0.1.5) |
| financial-fibo-zh-cn | [0.2.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.2.7) |
| financial-fibo-en-us | [0.2.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.7) |
| retail-gs1-zh-cn | [0.1.2](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-zh-cn-v0.1.2) |
| retail-gs1-en-us | [0.1.2](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-en-us-v0.1.2) |
| energy-saref4ener-zh-cn | [0.1.6](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-energy-saref4ener-zh-cn-v0.1.6) |
| energy-saref4ener-en-us | [0.1.6](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-energy-saref4ener-en-us-v0.1.6) |

## 撤回并删除

以下此前面向 0.2.1 的版本已在 0.2.1 目录（零售与 FIBO 也在根目录）标为撤回，条目和固定元数据保留；Release 及附件删除前已在维护机本地归档。Git 源码历史保留。

- `sample-supply-chain-v0.1.14`
- `sample-supply-chain-en-v0.1.10`
- `sample-financial-fibo-zh-cn-v0.2.5`
- `sample-financial-fibo-en-us-v0.2.5`
- `sample-retail-gs1-zh-cn-v0.1.0`
- `sample-retail-gs1-en-us-v0.1.0`
- `sample-candidates-0.2.1-complete-20261025-r1`
- `sample-candidates-0.2.1-complete-20261025-r2`

`sample-candidates-0.2.1-complete-20261025-r1`／`r2` 是早期 13 包候选集，其中的能源、制造业已由上表的正式版本取代。

## 边界

- 只在 arm64 的 0.2.1 主线环境验收，没有 AMD64 运行或正式 0.2.1 产品认证。
- 九个版本在同一安装包上跑过 50 题业务场景测试（50/50）；中文供应链和两个 FIBO 的最终包在跑题之后有变化，重新全新安装并核验体验卡，没有对该确切包再问模型问题。各自的 `verification.json` 写明了这一点。
