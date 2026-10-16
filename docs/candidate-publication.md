# 候选包构建与正式发布

在线使用轻量 `package.tar.gz`；完整离线使用另外构建的 `offline-package.tar.gz`，包含 OCI 镜像层和节点导入工具，见 [完整离线安装](offline-installation.md)。旧 URL-only 包不再作为完整离线包接收。两种入口使用相同的版本、包摘要、数据镜像与安装流程。样例版本独立于 OpenBKN 平台版本。

## 1. 修改样例并提交 PR

修改 `samples/<directory>/` 的 `sample.yaml`、数据、模型及声明的 hooks，增加 `releases/<version>/release-notes.zh-CN.md` 或英文说明。数据、知识网络、函数、指标、Skill、接口任一变化均发布整个样例的新版本。不要覆盖旧版本。

详细内容更新与验收要求见 [开发指南](SAMPLE_DEVELOPMENT_GUIDE.md)。BKN 目录可用 `openbkn bkn validate <directory>/kn` 校验；KN JSON 使用现有导入接口及真实查询验收，不能将 JSON 文件路径传给目录校验命令。

PR 使用英文标题和描述，完成规范检查与 AI 审核后合并。最终候选从审核过的干净提交构建。新增文件须进入 Git 索引；未跟踪的 hooks 和模型不会进入包。

## 2. 准备数据镜像并构建固定包

数据变化需要发布新的数据镜像，并固定 digest；数据未变可复用已经验证的镜像。镜像内须包含对应样例的数据库 hooks 和锁定数据。支持的目标架构为 amd64、arm64。

供应链与世界杯的数据镜像由主线的 `publish-sample-studio.yml` 构建（服务及数据镜像使用同一主线构建版本）；在 Actions 对应源提交的运行中取得数据镜像 tag，再用 `docker buildx imagetools inspect ghcr.io/openbkn-ai/bkn-samples:<build-version>` 读取 digest。不要使用可变 tag 代替 digest。`publish-sample-data.yml` 按 `sample.yaml` 的 `metadata.name` 动态解析样例目录，不使用固定名称白名单。传入 sample ID、版本以及 Dockerfile 的构建上下文：`sample` 表示相对样例目录，`repository` 表示相对仓库根目录。样例目录名可以与 sample ID 不同。修改数据后，必须等待包含该修改的官方数据镜像发布成功。

```sh
PYTHONPATH=. python3 tools/publication/build_candidate.py samples/<directory> \
  --version <version> --output /absolute/path/outside/bkn-samples \
  --data-image-ref ghcr.io/openbkn-ai/bkn-samples@sha256:<digest> \
  --image-layout /tmp/sample-oci
```

上述完整离线构建需先用 `skopeo copy --all --preserve-digests` 导出本地 OCI layout，生成 `<directory>/<version>/offline-package.tar.gz` 与 `build.json`。在线轻量 `package.tar.gz` 不传两个镜像参数，单独构建。构建只打包，不执行样例代码，也不代表安装成功。`build.json` 记录源提交、工作区状态、逐文件摘要和包摘要，属于作者报告，不是实例安装清单。

归档只包含已跟踪、允许交付的文件和当前版本说明，拒绝符号链接及冲突；归档时间和顺序固定。相同输入可复现同一摘要。使用新的输出目录，不覆盖候选或已发布制品。

完整离线 tar.gz 包含固定镜像的全部层和本地导入工具，安装与重试禁止拉取。已安装 OpenBKN 和 Kubernetes 是前置条件，不将整个产品重复装入每个样例包。

## 3. 在测试环境验收精确候选

Studio 首页 → 一键体验 → 导入离线包，选择包含镜像层的 offline.v2 完整包；先从包内向每个可调度节点导入镜像，再检查版本说明并安装。验收必须断开外网，从样例镜像无缓存开始，覆盖缺失镜像失败、包内本地导入、重试、卸载及重装。对相同包和数据镜像记录全新安装的实际结果：

- 数据库表、锁定数据及代表值；
- 知识网络对象、关系和真实数据源绑定；
- 声明的函数调用、指标计算及绑定、Skill 内容和引用；
- 代表业务场景、安装版本与逐次安装记录。

失败不发布目录；修复后重新构建未发布候选并重新验收。安装器拒绝冲突资源，不会替作者迁移客户已有数据。不支持原地升级、迁移或合并用户修改；具备归属记录的安装可卸载后重装，新版本仍需真实安装验收，见 [卸载与重装](sample-uninstall.md)。

## 4. 发布固定制品和元数据

验收通过后上传精确候选包到官方 GitHub Release，核对上传资产摘要。在 `releases/<version>/` 增加 `sample.json` 和 `verification.json`，绑定固定包、镜像、说明摘要、实际安装结果及限制。参考 [供应链 0.1.3](../samples/supply_ontology_hand/releases/0.1.3/sample.json)。

`verification.json` 必须绑定实际样例版本、包摘要、数据镜像、全新安装结果，并明确提供 `database`、`knowledge`、`capabilities`、`scenario` 四项通过检查。样例没有可选函数、指标或 Skill 时，能力检查说明未声明并确认该阶段通过，不能漏写。`evidence` 要指向当前版本的真实记录与查询结果；不能复用旧版本的安装证明。

先提交元数据形成完整官方提交 SHA，再将 `catalog.json` 的元数据 URL 固定到该 SHA。 该提交须在主线历史或保留的发布 tag 中可达；不要只依赖随后会删除的 PR 分支。若同一个 PR 中先提交元数据、再提交目录并采用 squash 合并，应保留元数据提交的发布 tag，确保后续 CI 可以取得并校验固定 SHA。递增目录 sequence，保留旧版本；撤回保留历史条目。目录变更同样经过英文 PR 和 AI 审核。

```sh
git show origin/main:catalog.json > /tmp/baseline-catalog.json
python3 tools/publication/validate.py . --official \
  --baseline-catalog /tmp/baseline-catalog.json
```

规范检查证明结构、来源和固定引用正确；不能替代真实安装及业务验收。

## 5. 在实例确认发布结果

合并目录 PR 后，在首页点击刷新样例，确认新版本、release notes 和可安装状态。目录不是实时推送：实例读取官方目录并保留成功缓存，刷新失败时使用已有缓存并提示失败。没有缓存的新环境不能凭空获得远程目录；仍可使用离线包入口。内置样例不等于远程目录缓存。

最后用正式远程包完成安装、打开知识网络及实际查询，并记录持久状态在服务重建后保留。部署入口见 [样例服务部署](sample-service-deployment.md)，产品 Chart 位于 `openbkn-ai/openbkn-deploy`。

## 独立数据镜像发布入口

先合并包含样例 Dockerfile、该版本说明及动态发布入口的 PR，再从 main 发起构建。例如英文供应链 Dockerfile 使用仓库根目录上下文：

```sh
gh workflow run publish-sample-data.yml --ref main \
  -f sample=supply-chain-en -f version=0.1.1 -f build_context=repository
```

该工作流生成 amd64/arm64 镜像，拒绝覆盖现有版本 tag。记录成功构建的源 SHA 及 digest，之后才能构建绑定该 digest 的候选包。不要将共享数据镜像未包含某个 sample 的情况误当成“已有可复用镜像”。

## 发布结束前的必做检查

删除已卸载样例的离线缓存包，再刷新官方目录。必须还能找到本次发布的在线身份、版本、说明和可安装状态。随后从在线入口安装并验证实际内容，完成卸载及历史检查。若删除离线包后卡片消失，说明在线交付尚未完成；不能只因源码、数据镜像或安装器已经合并而关闭发布工作项。
