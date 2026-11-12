# 0.1.4：计算函数改为行动

基于 0.1.3。按日期回放库存、订单配货与补货、召回控制评估三个计算不再挂载到知识网络，改为三个工具调用类行动（`retail_gs1_zh_cn_inventory_asof`、`retail_gs1_zh_cn_fulfillment_plan`、`retail_gs1_zh_cn_recall_assessment`），配合 OpenBKN 0.2.2 的行动模型。对象、关系、业务数据、计算逻辑和 Skill 的业务范围不变。

行动的每个输入都必须传：商品、业务日期、知识截止日、召回，以及地点、批次、订单和追溯范围、配货或补货方式、补货截至日期是每次计算的假设，Agent 每次执行都显式传入，执行记录里能看到这次按什么假设算。用户没限定的范围传空列表或空字符串；函数把空字符串当作不设。

Agent 用 `get_action_info` 取参数定义、`execute_action` 执行、`get_action_execution` 取结果。需要 OpenBKN 0.2.2 及以上，且平台包含 openbkn-ai/bkn-foundry#3125（函数类行动的会话上下文）。

现有安装继续使用原版本；更换版本须按标准卸载、安装流程进行，卸载会清理样例数据及归属资源。本版本不提供原地迁移。
