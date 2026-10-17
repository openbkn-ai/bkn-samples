# 制造业端到端运营样例

这是一个可导入的端到端制造业行业样例，用于追溯需求预测到计划、供应、生产、质量、成品入库和发运的完整链路。

**安装兼容性：**本样例要求 OpenBKN **0.2.1 或更高版本**。它以离线包方式交付，并刻意不登记到在线样例目录。

## 包含内容

- `kn/`：运营层 BKN 模型，含 **40 个 ObjectType**、**71 个 RelationType** 和 3 个概念分组。
- `data/`：40 张运营 CSV 表，共 **2,700 条记录**；每张表至少 50 条。
- `iof-reference/`：独立的固定 **IOF Core + Production Planning 112 类**参考层。其合成参考实例保留来源 IRI、标签和定义，不是运营交易数据。
- `bkn-eval/`：100 道中英对照题和 18 个确定性验收场景。
- `docs/`：业务 PRD、模型映射、数据分支设计、本体分层说明和能力需求。

## 场景与计划时间跨度

数据链路为：预测 → 生产计划 → 销售订单 → 物料收货与发放 → 工单与工艺 → 设备、人员与执行 → 质量规格与检验 → 成品入库 → 发运。

计划时间跨度为 **2026 年 11 月至 2027 年 3 月**。所有时间字段均为日期粒度（`YYYY-MM-DD`），包括销售交期、采购预计收货、收货、班次、执行、维护和生产交期；最晚计划生产交期为 `2027-03-30`。

50 个关联业务案例包括 22 个已发运完成、11 个物料不足、11 个质量不合格和 6 个生产进行中工单。每类结果所依据的业务事实见[数据分支设计](docs/dataset-scenarios_cn.md)。

## 标识符兼容性

OpenBKN 0.2.1 对 BKN 资源的 `id` 与 `name` 均限制为最多 40 个字符。网络、40 个对象类型、71 个关系类型和 3 个概念分组均满足该限制。关系 ID 使用稳定的端点缩写，例如 `material_issue_to_prod_mat_req`；每个关系映射中仍完整保留源和目标 CSV 字段。

## 中英文包约定

中英文包的 CSV 结构、记录数、稳定 ID、BKN 关系结构和评测题号一致；各包的业务显示值和状态值按语言本地化。跨语言比对请使用稳定 ID；不要根据实体名称判断异常原因。

## 建议阅读和运行顺序

1. 阅读[业务 PRD](docs/PRD_cn.md)，其中包含场景范围和 P0 验收需求。
2. 将 `kn/` 与 `data/` 一起查看：RelationType 的映射规则说明 CSV 中的外键关联字段。
3. 阅读 [IOF 与运营模型映射](docs/iof-operational-mapping_cn.md)和[本体分层说明](docs/ontology-layers_cn.md)，再使用 112 类参考层；不要将其当作交易数据。
4. 在本目录运行本地校验：

```bash
python3 tools/verify_industry_links.py
python3 iof-reference/tools/verify_reference_instances.py
python3 bkn-eval/run.py
openbkn bkn validate kn
```

这些检查验证 71 条运营关联、计划/BOM 谱系、事务推导的库存快照、逐条发运闸门、112 个 IOF 参考实例表和 18 个验收基线和 BKN 语法。

## 开源本体来源

112 类参考层基于已发布的 **IOF Core** 与 **IOF Production Planning** 模块。运营层 BKN 模型和 CSV 是本样例构造的虚构业务实现，不是 IOF 的官方发布物，也不是对其 OWL 文件的逐字复制。

- [IOF 本体开源仓库](https://github.com/iofoundry/ontology)
- [IOF Core 模块](https://spec.industrialontologies.org/portal/release/202603/core.html)
- [IOF Production Planning 模块](https://spec.industrialontologies.org/portal/release/202603/productionplanning/ProductionPlanningOntology.html)
- [IOF Core 源码声明的 MIT 许可证](https://github.com/iofoundry/Core/blob/main/Core.rdf)

本包采用的固定模块范围、精确来源 IRI、标签和定义见 [`iof-reference/README_cn.md`](iof-reference/README_cn.md)。

## 范围边界

样例回答已下达生产计划能否经发料、执行、最终质量、成品入库和发运完成履约。它刻意不涵盖派工优化、有限产能排程、批次谱系和根因处置；支持的证据与决策边界见[能力需求文档](docs/capability-requirements_cn.md)。
