# BKN行业建模规范：能源需求响应

本样例遵循OpenBKN原生BKN规范的network.bkn、object_types、relation_types和concept_groups结构。15个运营对象均有CSV与稳定主键；15条关系逐一对应显式外键；三个分组为资产与计量、柔性与计划、执行与结算。全部日期使用date，十进制使用decimal；空数值是未知，不是零。对象、关系及属性显示名均不超过40字符。

SAREF4ENER v2.1.1仅作需求响应语义参考，直接导入SAREF Core v4.1.1。来源文件完整具名inventory、匿名限制表达式树与版权许可位于saref-reference；来源80个显式类并非本样例80张业务表。上游76个自有类覆盖多种控制方式，本样例不实现全量OWL推理或全部控制模式，亦无回退伪对象。selected-mapping.json明确每个业务对象的来源参考或本地扩展，不断言owl:equivalentClass。特别地，本地柔性申报未实现上游多时序完整FlexOffer，分配表不是已发送设备控制指令。

每设备唯一电表；通过设备、日期、时段组成逻辑键关联预测/基线/计量，不能按日期单列错误拼接。业务查询需按revision和known_date解决可见版本。跨事件共享设备/场所/电表预算由业务函数处理，不用简单多边累加替代。capacity_snapshots和settlement_snapshots是已记录快照，不能替代重算。

## 数据对象与关联

| 对象 | 主键 | 记录数 | 外键目标 |
|---|---|---:|---|
| 用能客户 (`customers`) | customer_id | 50 | — |
| 用能场所 (`sites`) | site_id | 50 | customer_id→customers.customer_id |
| 柔性设备 (`devices`) | device_id | 150 | site_id→sites.site_id |
| 设备电表 (`meters`) | meter_id | 150 | device_id→devices.device_id |
| 响应事件 (`response_events`) | event_id | 100 | — |
| 负荷预测 (`load_forecasts`) | forecast_id | 3751 | device_id→devices.device_id |
| 核定基线 (`baselines`) | baseline_id | 3752 | device_id→devices.device_id |
| 柔性申报 (`flexibility_offers`) | offer_id | 3001 | event_id→response_events.event_id, device_id→devices.device_id |
| 设备约束 (`device_constraints`) | constraint_id | 76 | device_id→devices.device_id |
| 响应分配 (`dispatch_allocations`) | allocation_id | 894 | event_id→response_events.event_id, device_id→devices.device_id |
| 执行回执 (`execution_logs`) | execution_id | 341 | allocation_id→dispatch_allocations.allocation_id |
| 计量读数 (`meter_readings`) | reading_id | 2251 | meter_id→meters.meter_id |
| 结算台账 (`settlements`) | settlement_id | 61 | event_id→response_events.event_id |
| 能力快照 (`capacity_snapshots`) | snapshot_id | 100 | event_id→response_events.event_id |
| 结算快照 (`settlement_snapshots`) | snapshot_id | 60 | event_id→response_events.event_id |

[OpenBKN BKN规范](https://github.com/openbkn-ai/bkn-foundry/tree/main/adp/bkn/bkn-backend/server/bkn-specification)；本地核对使用该规范SPECIFICATION.md的对象/属性/关系/分组约束。


本目录未声明bkn_spec，按规范的2.x永久兼容约定解析，与现有retail样例结构一致，未使用3.0专有语法。本地OpenBKN CLI 0.1.5验证通过：15对象、15关系、3分组，0错误、0警告。该语法检查不代表平台安装或指标/函数执行已验收。
