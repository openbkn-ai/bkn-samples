# 一键体验首期交付与验收

2026-10-11。首期目标是作者发布独立样例版本，客户从目录或离线包首次安装并使用。安装导入包中已有内容，不调用 bkn create/creator 或生成式 Skill。

## 验收矩阵

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| 官方发布 | 英文 PR、AI 审批、固定包与镜像摘要、版本说明、不可改写的历史版本 | 各版本 sample.json / verification.json 与 catalog.json |
| 首页交互 | 来源仓库链接、集中操作区、刷新目录、离线包入口、可展开卡片、版本说明、安装确认与进度 | Studio #854、#855、#856、#857 |
| 数据与知识网络 | 供应链 12 张业务表、15 对象、21 关系、11 数据绑定；世界杯正式包安装成功 | [组件验收](phase6-component-acceptance.md)、[在线验收](phase6-online-acceptance.md) |
| 函数与指标 | 14 个函数通过 managed MCP 实际执行；8 个指标、8 个逻辑属性绑定、13 次指标查询通过 | [组件验收](phase6-component-acceptance.md) |
| 业务 Skill 与模型 | 四个 Skill 的主文档及十个引用文件与包一致；子 agent 经配置的模型自主检索、读取、调用业务能力，四个问答场景通过 | [智能问答验收](phase6-agent-acceptance.md) |
| 无目录缓存的离线安装 | 外网不可达且缓存为空，首页仍导入新样例包、展示本地说明并完成安装 | [第三样例验收](phase6-third-sample-acceptance.md) |
| 动态新增 | 固定 Studio 和服务镜像后，正式发布第三样例，刷新、全新在线安装及对象/关系查询通过 | [第三样例验收](phase6-third-sample-acceptance.md) |
| 历史与持久化 | 失败与成功逐次归档；同版本重试、跨版本记录及服务重建后保留 | [在线验收](phase6-online-acceptance.md)、[第三样例验收](phase6-third-sample-acceptance.md) |
| 产品部署 | 使用 openbkn-deploy 的标准入口和官方 Chart，样例服务位于现有集群，未新建平台实例 | [部署指南](sample-service-deployment.md)、[Chart 验收](phase6-chart-acceptance.md) |

## 作者下一步：供应链新版本

按 [中文开发指南](SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md) 更新供应链为 0.1.4，并按 [候选发布流程](candidate-publication.md) 执行：内容与版本说明 PR → 固定包 → 干净测试安装与真实调用 → 完整验收凭证 → 固定制品与目录 PR → 首页刷新及在线安装。

数据、知识网络结构、函数、指标、Skill 或接口契约发生交付变化，均随独立新版本发布。未改变的数据镜像可以复用原 digest。先核对包内声明与实际内容，再验证每项声明的能力；未声明的能力明确记录为不适用。

## 边界

目录由实例扫描并保留最后成功缓存，不是实时推送；新环境没有远程缓存。外网不可用可上传包，但 tar.gz 不包含容器镜像层，数据镜像需要可达或预先导入。

已安装同一样例的原地升级、数据迁移、用户修改合并和卸载不在首期交付范围。发布新版本不等于自动更新客户已有实例。验证仅覆盖本地 arm64 环境；amd64 镜像已构建，不宣称在真实 amd64 平台完成验收。
