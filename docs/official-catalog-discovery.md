# 官方目录发现（第一批）

状态：本地实现，尚未提交或联调。2026 年 10 月 9 日只读确认官方仓库根 `catalog.json` 返回 404；当前没有把草案示例发布成正式目录。

## 获取与缓存

实例服务固定读取 `openbkn-ai/bkn-samples` 的 main：先调用 GitHub Git Ref API 得到提交 SHA，再读取该 SHA 下的根 `catalog.json`。Studio 不直接访问 GitHub，实例请求也不携带用户的 OpenBKN Bearer Token。

首期仅接受 `sourceId=openbkn-official`、stable 和当前 v1beta1 目录 Schema。清单、说明、验收引用使用官方 raw.githubusercontent.com 仓库的完整提交 SHA URL。拒绝重定向、重复 JSON 键、重复 release、无效说明语言、非官方或未固定引用；限制请求超时、响应大小及目录条目数。

`POST /api/studio/samples/refresh` 发起扫描，返回更新后的目录与 sourceRefresh。实例内一分钟最多尝试一次；`GET /api/studio/samples` 只读内存/磁盘缓存，不每次触发外网请求。页面反馈 updated、unchanged、failed、not_refreshed 和刷新限频，并显示最后成功刷新时间。

缓存保存在状态目录的 `catalogs/official.json`，临时文件完成后原子替换。刷新失败不覆盖旧缓存，也不影响内置样例。重启后验证缓存结构再恢复。目录内容变化须提升 sequence；已发布 release 保留原固定引用，撤回保留条目。expiresAt 改为可选，官方受控源不必为续期频繁提交；显式设置的过期目录不作为新的成功刷新结果。

## 页面与版本说明

远程目录按 sampleId 聚合，与现有内置卡片合并；增加独立的 latestPublishedVersion 和 versions。每个版本可切换阅读说明，显示发布日期、撤回或当前安装器不支持的原因。说明按固定 URL 获取并核对 SHA-256，按语言回退。已安装版本优先使用原记录快照。

目录根文件不包含任何实例运行目录。作者本地目录布局是发布工具输入，消费者通过 URL 读取。实际发布前需要生成正式目录与固定引用；现有 `protocol/draft/examples` 的 .invalid 地址会被运行时拒绝。

## 当前限制

远程 v1beta1 版本暂不提供安装操作：现有安装器仍只执行镜像内置 v1alpha1 内容。发现、读取说明与通过平台验收是不同阶段；自报 verification URL 不等于验收通过。内置版本继续按现有流程安装，远程版本与成功版本分别显示。

完整动态安装还需真实样例包、固定内容的模型及平台验收、下载与导入实现，以及异步任务和历史迁移。此批没有新增第三方源设置、通用插件加载或签名体系。

仅完成语法、格式与 diff 检查，尚未运行测试、镜像构建、真实扫描联调或平台安装验收。多副本缓存协调仍按部署与安装服务任务处理。
