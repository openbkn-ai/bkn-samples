# 样例候选包与正式发布

## 1. 准备源码和版本说明

样例以 `sample.yaml` 声明身份、数据库、组件和现有安装／验证 hooks。数据、知识网络、函数、指标、接口及 Skill 任一变化都发布整个 sample 的新版本。更新锁文件和 `releases/<新版本>/release-notes.*.md`，将交付文件加入 Git 索引，通过英文 PR 审核后从固定提交构建。不要在安装器中添加样例名称分支。

## 2. 构建在线和离线候选

```sh
PYTHONPATH=. python3 tools/publication/prepare_shared_release.py \
  samples/world-cup-en --version NEW_VERSION --output /absolute/path/to/candidates
```

工具复用此前审核过的发布清单，生成在线 `package.tar.gz`、完整离线 `offline-package.tar.gz` 和候选 `sample.json`。它不发布制品、不生成成功验收证明，也不更新官方目录。当前交付要求数据内置，已有知识网络格式、内容分组、绑定和体验入口保持原标准。

新清单要求 `database.shared`，数据依赖指向 archive。数据库运行环境由产品提供，不再构建或发布样例专属数据库镜像。旧运行服务因不支持新能力而拒绝该版本；先安装产品补丁。历史包和元数据不改写。

## 3. 验收固定候选

通过 Studio 首页安装精确候选。在已运行产品的环境中阻断外网，确认无需样例镜像缓存或节点操作，覆盖导入、安装、重试、卸载及重装：

- 数据库表、锁定数据及代表值；
- 知识网络对象、关系和真实数据源绑定；
- 声明的函数调用、指标计算及绑定、Skill 内容和引用；
- 业务查询、版本、逐次历史，以及卸载后其他样例仍可使用。

卸载应不依赖官方目录或原包。验证内部服务不可用时有界失败并可继续清理。验收失败不发布；修改候选后重新构建、重新验收，不支持原地升级、迁移或合并用户修改。

## 4. 发布及更新目录

通过验收后，将两种精确包上传为新版本 Release 附件，并核对上传摘要。提交 `sample.json` 和真实的 `verification.json`；后者绑定 sampleId、version、packageDigest、`databaseRuntime: shared-mariadb`、全新安装结果及 `database`、`knowledge`、`capabilities`、`scenario` 四项检查。未声明的可选能力要说明不适用，不能伪造调用成功。

元数据先形成可保留的完整提交 SHA，再通过 PR 更新 `catalog.json` 的固定引用、版本说明和递增 sequence。保留旧条目，不覆盖旧版本资产或证明。发布提交须在主线或保留 tag 中可达。

```sh
git show origin/main:catalog.json > /tmp/baseline-catalog.json
python3 tools/publication/validate.py . --official \
  --baseline-catalog /tmp/baseline-catalog.json
```

最后在实例刷新目录，通过正式在线包再验证安装和使用。规范检查不能代替实际内容验收。参见[离线交付](offline-installation.md)、[服务部署](sample-service-deployment.md)和[卸载重装](sample-uninstall.md)。
