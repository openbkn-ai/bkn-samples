# 需求响应与柔性用能（SAREF4ENER 参考，中文）

以虚构负荷聚合商为场景，从企业客户、场所、可调设备和电表，追溯到响应事件、负荷预测与基线、设备申报与约束、多事件共享资源的调度、执行回执、电表读数和结算台账。包含 15 张数据表、本体、3 个原生函数和 2 个业务 Skill。业务需求与口径见 [PRD](docs/PRD.md)。

## 安装与体验

1. 登录 OpenBKN，进入首页的**一键体验**。
2. 刷新官方目录，选择**需求响应与柔性用能**并点击**安装**，要求 **OpenBKN >=0.2.1 <0.3.0**。
3. 等待安装和验证完成，打开对应知识网络。
4. 在智能问答、数据查询和图探索页面试用体验卡，或接入外部 Agent，通过 MCP 查询对象、调用已发布函数和使用 Skill。

无法访问官方目录时，从 [Releases](https://github.com/openbkn-ai/bkn-samples/releases) 下载本样例的 `package.tar.gz`，在一键体验中选择**导入离线包**后安装。

数据是虚构的合成数据，覆盖 2026 年 11 月至 2027 年 3 月，业务日期为 2027-02-28：十一月至二月已发生，三月为当天已知的计划。不代表真实电网调度或结算，不下发控制指令，也不付款。

## 能力

能用 Cypher 查到的不写函数，只为 Cypher 表达不了的计算保留函数。样例不使用指标，社区版即可完整使用。

- **Cypher 查询**：客户、场所、设备和电表，事件安排，申报与约束，已承诺分配，执行回执，读数版本，结算台账，以及 2027-02-28 的容量和结算快照。
- **原生函数**：`flexibility_assessment` 算某事件的可承诺容量和设备排除原因；`dispatch_plan` 按优先级和申报成本给出同一时段事件的新增方案、缺口和预计成本；`settlement_assessment` 算核实电量、交付比例、收入、客户补偿和与台账的差额。三个函数都可按更早某天已知的信息回看。
- **Skill**：按使用者组织为“容量与调度”（聚合商运营、企业能源经理）和“执行与结算”（响应值班员、结算专员），写明业务口径、何时用 Cypher、何时调用函数和回答格式。

## 体验卡

15 张体验卡从测试集中选题，覆盖资产、可承诺容量、场所上限、共享时段、执行、交付达标、台账核对和结算合计，由浅入深。卡片的数据查询和图探索 Cypher 用 `tools/acceptance/experience_set.py` 在安装后的平台上在线核验。

## 验收与维护

测试集见 [业务场景测试集 v1](bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md)，参考答案由独立脚本从交付数据计算，不随安装包交付。安装后让未读答案的智能体每题跑一轮；未达 100% 时记录失败原因，先改本体描述、Skill 或函数，不改题目和答案迁就结果。原有 100 题回放与数据核验见 [bkn-eval](bkn-eval/README.md)，可在仓库根运行：

```sh
python3 tools/energy_saref4ener/verify.py --sample zh-cn
python3 -m unittest tools.energy_saref4ener.test_engine tools.energy_saref4ener.test_adapter -v
```

本体与 SAREF4ENER 的对应见[本体规范](docs/bkn-modeling-spec.md)；来源为 ETSI [SAREF4ENER 2.1.1](https://saref.etsi.org/saref4ener/v2.1.1/) 及其导入的 [SAREF Core 4.1.1](https://saref.etsi.org/core/v4.1.1/)，BSD-3-Clause 许可，原始 Turtle 见 [saref-reference/](saref-reference/README.md)。客户、场所、调度方案和结算公式是本样例的业务扩展，不宣称 ETSI 认证或全局最优调度。

升级时先卸载旧样例，再安装新版本。卸载会清理样例数据和用户修改；删除离线包缓存不会卸载已安装资源。
