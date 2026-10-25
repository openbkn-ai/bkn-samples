# 能源需求响应运营（SAREF4ENER参考，中文）

固定源码候选样例，版本0.1.4，目标兼容OpenBKN **>=0.2.1 <0.3.0**。以虚构负荷聚合商为场景，贯通资源准入、可承诺能力、多事件分配、执行计量及结算调查。业务起点是[PRD](docs/PRD.md)，精确口径集中于[业务计算契约](docs/business-capability-contract.md)。

每语15张关联数据表、14,787条记录，每表至少50条；原生BKN为15个业务对象、15条关系、3个概念分组。中文企业、场所、设备、状态和原因使用中文，稳定ID、代码及kW/kWh/CNY等单位代码保留英文。默认观察日2027-02-28，历史覆盖2026年11月起，已公告计划和预测至2027-03-31；日期只到天，以具名区段及持续小时数表达响应。

## 包含哪些内容

| 业务内容 | 文件 |
|---|---|
| 谁要作什么决定、10个验收场景与100题的对应 | [PRD](docs/PRD.md) |
| BKN模型、来源语义映射与本地扩展 | [本体规范](docs/bkn-modeling-spec.md)、[kn/](kn/network.bkn) |
| 全部对象的实例、类型/主外键与锁 | [data/](data/)、[model-contract.json](model-contract.json)、[dataset.lock](dataset.lock) |
| 业务差异、已知异常及精确记录ID | [数据场景](docs/dataset-scenarios.md) |
| 3函数：能力评估、分配建议、实际交付/结算核验 | [energy.py](tools/energy.py)、[契约](docs/business-capability-contract.md) |
| 2指标：单个日期快照的可响应功率、交付比例 | [指标定义](tools/assets/metrics-create.json) |
| 1只读调查Skill，引用文件在其references内实物交付 | [Skill](skills/energy-response-investigation-zh-cn/SKILL.md) |
| 100题、逐题答案/来源/解释及场景映射 | [题目](bkn-eval/questions.json)、[答案](bkn-eval/answers.md)、[机器金标](bkn-eval/expected-results.json) |

## 开源来源与模型边界

官方[SAREF4ENER 2.1.1](https://saref.etsi.org/saref4ener/v2.1.1/)及其直接导入[SAREF Core 4.1.1](https://saref.etsi.org/core/v4.1.1/)是语义参考，实际下载的Turtle、BSD-3-Clause许可、SHA256、完整具名类/属性清单与映射保留在[saref-reference/](saref-reference/README.md)。SAREF4ENER源有80个显式具名类（76个为自身命名空间），Core有32个（29个为自身）；完整来源清单与15个运行时业务对象分别说明其覆盖范围。

本地结算公式、客户/场所及调度提案是明确声明的业务扩展。使用兼容的BKN 2.x结构及原生验证器；未转换全部OWL公理，不宣称ETSI认证、完整电网调度或全局最优。数据全部虚构，资产和客户均不能用于实际控制或付款。

## 在仓库内本地验证

需要Python3.11+、已安装的openbkn CLI及其本地依赖。在仓库根运行：

```sh
python3 tools/energy_saref4ener/verify.py --sample zh-cn
python3 -m unittest tools.energy_saref4ener.test_engine tools.energy_saref4ener.test_adapter -v
```

也可运行本目录的 `python3 bkn-eval/run.py`。回放调用实际交付的计算实现，对照从历史终态记录恢复、附来源摘要的结构化参考；原独立金标文件未完整保留，不能将恢复参考冒充原文件。另有独立手工边界及托管数据适配器检查，不新增逐题函数。100题分为基础/简单30、中等40、困难/复杂30，每场景10题；业务日和知识截止日显式声明，带 reference_scope 的题同时比较两种视图。

实际结果见[本地验收报告](../../docs/energy-saref4ener-readiness.md)。报告保留首轮差异和定向修复，不把结构化字段通过率称为自然语言模型准确率。

## 安装准备与本轮边界

`sample.yaml`、共享MariaDB初始化/核验、原生本体绑定、指标/函数/Skill注册与归属保护hooks已提供；仅声明实际交付的组件。安装时消费包内数据和资源，不需要creator或读取题库。未来发布前仍须按标准流程对固定包作实际平台验收。

本样例作为固定源码候选交付，尚未登记正式目录。整合报告覆盖源码、本地数据库及回归检查；固定包的平台安装、能力运行及实际问答须另留与精确包绑定的回执，不能以本README作为平台成功证明。两个快照指标是已记录来源值，不替代实时重算；不完整资料保留null与证据。源公开许可条件保留，样例自定义代码与虚构数据采用仓库MIT许可。
