# 样例数据业务差异与异常索引

数据覆盖50个客户场所、150设备唯一电表、25个响应日期。每日期4个完全重叠事件，共享部分设备，体现优先级与场所上限。历史60事件、2027年3月未来40事件；未来无实际计量、回执或已入账结算。所有业务名称、状态、原因和单位均按语言表达，ID与代码稳定一致。

异常是定点业务事实，不是每表1至2条装饰数据；正常事件与失败/拒绝/缺证/更正/冲突/零承诺同时存在。

| 类型 | 精确记录/范围 |
|---|---|
| 约束上限缺失 | {"source_ids": ["CON-076"], "response_date": "2027-02-10", "device_id": "DEV-061"} |
| 最新预测质量无效 | {"source_ids": ["FOR-04-046", "FOR-04-046-R2"], "device_id": "DEV-046", "response_date": "2026-11-25"} |
| 同修订基线冲突 | {"source_ids": ["BAS-06-076", "BAS-06-076-CONFLICT"], "device_id": "DEV-076", "response_date": "2026-12-09"} |
| 计量读数缺失 | {"source_ids": ["REA-08-106"], "device_id": "DEV-106", "response_date": "2026-12-23"} |
| 相同读数重试去重 | {"source_ids": ["REA-09-136", "REA-09-136-RETRY"], "device_id": "DEV-136", "response_date": "2026-12-30"} |
| 晚到读数更正 | {"source_ids": ["REA-10-136", "REA-10-136-R2"], "device_id": "DEV-136", "response_date": "2027-01-06", "known_date": "2027-01-18"} |
| 截止日后基线重述 | {"source_ids": ["BAS-15-061", "BAS-15-061-R2"], "device_id": "DEV-061", "response_date": "2027-02-24", "known_date": "2027-03-03"} |
| 执行回执缺失 | {"event_id": "EVT-033", "allocation_id": "ALL-0283"} |
| 同区间超预约 | {"event_ids": ["EVT-057", "EVT-058", "EVT-059", "EVT-060"], "allocation_id": "ALL-0499", "device_id": "DEV-061", "response_date": "2027-02-24"} |
| 未来申报晚到撤回 | {"source_ids": ["OFF-2161", "OFF-2161-R2"], "event_id": "EVT-073", "known_date": "2027-03-05"} |
| 共享电表按比例归因 | {"response_date": "2026-11-04", "block_code": "peak_a", "shared_devices": [{"device_id": "DEV-016", "meter_id": "MTR-016", "reading_id": "REA-01-016", "allocation_ids": ["ALL-0004", "ALL-0010"], "event_ids": ["EVT-001", "EVT-002"], "total_committed_kwh": "12.250000", "observed_reduction_kwh": "9.800000"}, {"device_id": "DEV-017", "meter_id": "MTR-017", "reading_id": "REA-01-017", "allocation_ids": ["ALL-0005", "ALL-0011"], "event_ids": ["EVT-001", "EVT-002"], "total_committed_kwh": "12.250000", "observed_reduction_kwh": "9.800000"}, {"device_id": "DEV-018", "meter_id": "MTR-018", "reading_id": "REA-01-018", "allocation_ids": ["ALL-0006", "ALL-0012"], "event_ids": ["EVT-001", "EVT-002"], "total_committed_kwh": "12.250000", "observed_reduction_kwh": "9.800000"}]} |
| 阈值包含与半分舍入 | {"event_id": "EVT-001", "committed_kwh": "37.500000", "verified_kwh": "30.000000", "delivery_ratio": "0.800000", "minimum_ratio": "0.800000", "reward_cny_kwh": "1.200500", "unrounded_revenue_cny": "36.015000000000", "rounded_revenue_cny": "36.02"} |
| 用电上升不算削减 | {"device_id": "DEV-046", "reading_id": "REA-01-046", "response_date": "2026-11-04"} |
| 能力快照偏差 | {"snapshot_id": "CAP-017", "event_id": "EVT-017", "difference_kw": "7.000000"} |
| 已入账收入偏差 | {"event_id": "EVT-025", "settlement_id": "SET-025", "snapshot_id": "SSP-025", "difference_cny": "5.00"} |
| 能力快照偏差 | {"snapshot_id": "CAP-065", "event_id": "EVT-065", "difference_kw": "7.000000"} |
| 能力快照偏差 | {"snapshot_id": "CAP-091", "event_id": "EVT-091", "difference_kw": "7.000000"} |
| 同日已入账台账冲突 | {"event_id": "EVT-041", "source_ids": ["SET-041", "SET-041-CONFLICT"], "posted_date": "2027-01-15", "effect": "Reconciliation unknown; measured delivery and recomputed revenue remain independently known."} |

完整行数、精确ID与构造规则见dataset-scenarios.json。源值用于对照，不是官方电力市场结算或模型准确率证明。
