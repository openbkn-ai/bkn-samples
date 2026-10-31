# 制造业端到端运营（IOF 参考，中文）

以虚构的精密加工企业为场景：深圳、苏州两个工厂为十家客户加工泵壳、阀体、叶轮和法兰，从销售订单、需求预测和生产计划，追溯到物料需求、采购来料、发料、生产执行、检验、成品入库、发运和设备维护。包含 40 张数据表、本体和 2 个业务 Skill。业务需求与口径见 [PRD](docs/PRD.md)。

## 安装与体验

1. 登录 OpenBKN，进入首页的**一键体验**。
2. 刷新官方目录，选择**制造业端到端运营**并点击**安装**，要求 **OpenBKN >=0.2.1 <0.3.0**。
3. 等待安装和验证完成，打开对应知识网络。
4. 在智能问答、数据查询和图探索页面试用体验卡，或接入外部 Agent，通过 MCP 查询对象和使用 Skill。

无法访问官方目录时，从 [Releases](https://github.com/openbkn-ai/bkn-samples/releases) 下载本样例的 `package.tar.gz`，在一键体验中选择**导入离线包**后安装。

数据是虚构的合成数据，覆盖 2026 年 11 月至 2027 年 3 月，业务日期为 2027-02-28：十一月至二月已发生，三月工单是计划。不代表真实企业运营，不下单、不排产也不发货。

## 能力

全部问题都能用 Cypher 查到，样例不提供函数，也不使用指标，社区版即可完整使用。

- **Cypher 查询**：产品、BOM 版本、工艺路线、设备能力与人员资质，订单、发运与欠交，预测与计划，物料需求与发料，采购与来料，执行记录与排班，检验结果与规格，库存与维护。
- **Skill**：按使用者组织为“订单交付与物料采购”（订单交付经理、采购与物料经理）和“生产与质量”（生产主管、质量经理），写明业务口径、Cypher 写法和回答格式。

## 体验卡

15 张体验卡从测试集中选题，覆盖 BOM 与工艺、人员资质、延误与补做、缺料与阻塞、报废、执行合规、检验拒收与漏检、维护逾期、订单追溯和库存，由浅入深。卡片的数据查询和图探索 Cypher 用 `tools/acceptance/experience_set.py` 在安装后的平台上在线核验。

## 数据与验收

数据由 [`tools/manufacturing_industry/generate_data.py`](../../tools/manufacturing_industry/generate_data.py) 按一个连贯的业务故事确定性生成，中英文包只在文字上不同：设备、人员、物料、供应商和库存在工单之间共享，并刻意放入分批与延误发运、报废少交、检验拒收与补做、质量漏检、执行不合规、待检发料、采购短交与拒收、BOM 草稿和逾期维护等例外，见测试集说明。

测试集见 [业务场景测试集 v1](bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md)，参考答案由独立脚本从交付数据计算，不随安装包交付。安装后让未读答案的智能体每题跑一轮；未达 100% 时记录失败原因，先改本体描述或 Skill，不改题目和答案迁就结果。在本目录运行本地校验：

```bash
python3 tools/verify_industry_links.py
python3 iof-reference/tools/verify_reference_instances.py
python3 bkn-eval/run.py
openbkn bkn validate kn
```

## 开源本体来源

`iof-reference/` 是独立的 **IOF Core + Production Planning 112 类**参考层，合成参考实例保留来源 IRI、标签和定义，不是运营交易数据；与运营模型的对应见 [IOF 与运营模型映射](docs/iof-operational-mapping_cn.md)和[本体分层说明](docs/ontology-layers_cn.md)。运营层模型和 CSV 是本样例构造的虚构业务实现，不是 IOF 官方发布物。

- [IOF 本体开源仓库](https://github.com/iofoundry/ontology)
- [IOF Core 模块](https://spec.industrialontologies.org/portal/release/202603/core.html)
- [IOF Production Planning 模块](https://spec.industrialontologies.org/portal/release/202603/productionplanning/ProductionPlanningOntology.html)
- [IOF Core 源码声明的 MIT 许可证](https://github.com/iofoundry/Core/blob/main/Core.rdf)

升级时先卸载旧样例，再安装新版本。卸载会清理样例数据和用户修改；删除离线包缓存不会卸载已安装资源。
