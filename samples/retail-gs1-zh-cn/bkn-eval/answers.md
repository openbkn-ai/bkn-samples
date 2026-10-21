# Independent reference answers

Evaluator material. Never supplied to formal answerers or installed runtime.

## Q001 · S01 · basic

PRD-001 的名称、基准单位及包装倍率是什么？

```json
{
  "rows": [
    {
      "product_id": "PRD-001",
      "name": "原味酸奶250克",
      "unit": "件",
      "pack_multiplier": "6"
    }
  ]
}
```

## Q002 · S01 · basic

PRD-002 由谁供货？返回供应商标识、名称及角色代码。

```json
{
  "rows": [
    {
      "product_id": "PRD-002",
      "organization_id": "ORG-002",
      "name": "杭州丰穗食品有限公司",
      "role_code": "supplier"
    }
  ]
}
```

## Q003 · S01 · basic

WH-001 仓库属于哪个组织，地点类型是什么？

```json
{
  "rows": [
    {
      "location_id": "WH-001",
      "name": "杭州中心配送中心",
      "location_type_code": "warehouse",
      "organization_id": "ORG-026",
      "organization_name": "杭州青禾商贸有限公司"
    }
  ]
}
```

## Q004 · S01 · basic

STORE-002 由哪个组织运营？

```json
{
  "rows": [
    {
      "location_id": "STORE-002",
      "name": "杭州东湖生活超市",
      "organization_id": "ORG-027",
      "organization_name": "杭州丰穗商贸有限公司"
    }
  ]
}
```

## Q005 · S01 · basic

LOT-003-A 的商品、生产日期和到期日期是什么？

```json
{
  "rows": [
    {
      "lot_id": "LOT-003-A",
      "product_id": "PRD-003",
      "produced_date": "2026-11-01",
      "expiry_date": "2027-02-20"
    }
  ]
}
```

## Q006 · S01 · basic

PRD-004 声明的最小剩余保质期是多少天？

```json
{
  "rows": [
    {
      "product_id": "PRD-004",
      "min_shelf_days": "3",
      "unit": "件"
    }
  ]
}
```

## Q007 · S01 · medium

将 PRD-001、PRD-002、PRD-003 各三箱换算成基准数量，按商品分别返回。

```json
{
  "rows": [
    {
      "product_id": "PRD-001",
      "unit": "件",
      "base_quantity": 18
    },
    {
      "product_id": "PRD-003",
      "unit": "件",
      "base_quantity": 18
    },
    {
      "product_id": "PRD-002",
      "unit": "件",
      "base_quantity": 36
    }
  ]
}
```

## Q008 · S01 · medium

列出 PRD-005 的全部批次、供应商名称及到期日期。

```json
{
  "rows": [
    {
      "lot_id": "LOT-005-A",
      "product_id": "PRD-005",
      "supplier_name": "杭州江湾食品有限公司",
      "expiry_date": "2027-02-20"
    },
    {
      "lot_id": "LOT-005-D",
      "product_id": "PRD-005",
      "supplier_name": "杭州江湾食品有限公司",
      "expiry_date": "2027-03-05"
    },
    {
      "lot_id": "LOT-005-B",
      "product_id": "PRD-005",
      "supplier_name": "杭州江湾食品有限公司",
      "expiry_date": "2027-03-10"
    },
    {
      "lot_id": "LOT-005-C",
      "product_id": "PRD-005",
      "supplier_name": "杭州江湾食品有限公司",
      "expiry_date": "2027-03-31"
    },
    {
      "lot_id": "LOT-005-P",
      "product_id": "PRD-005",
      "supplier_name": "杭州江湾食品有限公司",
      "expiry_date": "2027-03-31"
    }
  ]
}
```

## Q009 · S01 · medium

统计每个供应商角色组织负责的商品数，保留零商品供应商，不把地点当作供应商。

```json
{
  "rows": [
    {
      "organization_id": "ORG-012",
      "name": "南京丰穗食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-014",
      "name": "南京晴岭食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-015",
      "name": "南京江湾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-013",
      "name": "南京泉润食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-011",
      "name": "南京青禾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-017",
      "name": "宁波丰穗食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-019",
      "name": "宁波晴岭食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-020",
      "name": "宁波江湾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-018",
      "name": "宁波泉润食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-016",
      "name": "宁波青禾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-022",
      "name": "无锡丰穗食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-024",
      "name": "无锡晴岭食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-025",
      "name": "无锡江湾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-023",
      "name": "无锡泉润食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-021",
      "name": "无锡青禾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-002",
      "name": "杭州丰穗食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-004",
      "name": "杭州晴岭食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-005",
      "name": "杭州江湾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-003",
      "name": "杭州泉润食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-001",
      "name": "杭州青禾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-007",
      "name": "苏州丰穗食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-009",
      "name": "苏州晴岭食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-010",
      "name": "苏州江湾食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-008",
      "name": "苏州泉润食品有限公司",
      "product_count": 2
    },
    {
      "organization_id": "ORG-006",
      "name": "苏州青禾食品有限公司",
      "product_count": 2
    }
  ]
}
```

## Q010 · S01 · complex

审计全部批次→商品→供应商路径，仅列出缺失供应商或角色错误的记录。

```json
{
  "rows": []
}
```

## Q011 · S02 · basic

列出 LOT-001-A 的实际收货事件。

```json
{
  "rows": [
    {
      "movement_id": "MOV-00001",
      "event_id": "EV-00001",
      "event_date": "2026-11-03",
      "destination_location_id": "WH-001",
      "quantity": "121",
      "unit": "件"
    }
  ]
}
```

## Q012 · S02 · basic

列出观察日已知的 LOT-002-A 检验记录。

```json
{
  "rows": [
    {
      "inspection_id": "QC-002-A",
      "lot_id": "LOT-002-A",
      "inspection_date": "2026-11-03",
      "result_code": "passed",
      "reason": "验收合格"
    }
  ]
}
```

## Q013 · S02 · basic

按批次列出 WH-003 的 PRD-003 在库数量与当前检验代码。

```json
{
  "rows": [
    {
      "lot_id": "LOT-003-A",
      "location_id": "WH-003",
      "on_hand": "83.000000",
      "inspection_status_code": "passed"
    },
    {
      "lot_id": "LOT-003-B",
      "location_id": "WH-003",
      "on_hand": "93.000000",
      "inspection_status_code": "passed"
    },
    {
      "lot_id": "LOT-003-C",
      "location_id": "WH-003",
      "on_hand": "143.000000",
      "inspection_status_code": "passed"
    },
    {
      "lot_id": "LOT-003-D",
      "location_id": "WH-003",
      "on_hand": "63.000000",
      "inspection_status_code": "passed"
    }
  ]
}
```

## Q014 · S02 · basic

列出观察日 PRD-004 各批次仍有效的实物隔离记录。

```json
{
  "rows": [
    {
      "hold_id": "HOLD-004-Q",
      "lot_id": "LOT-004-B",
      "location_id": "WH-004",
      "quantity": "20",
      "reason": "召回预隔离"
    },
    {
      "hold_id": "HOLD-004-R",
      "lot_id": "LOT-004-C",
      "location_id": "STORE-004",
      "quantity": "5",
      "reason": "退货及包装复检"
    }
  ]
}
```

## Q015 · S02 · medium

PRD-011 哪些批次检验失败或待检？各地点实物隔离量是多少？

```json
{
  "rows": [
    {
      "lot_id": "LOT-011-C",
      "location_id": "STORE-011",
      "inspection_status_code": "failed",
      "on_hand": "26.000000",
      "quarantined": "26.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-011-C",
      "location_id": "WH-011",
      "inspection_status_code": "failed",
      "on_hand": "140.000000",
      "quarantined": "140.000000",
      "available": "0.000000"
    }
  ]
}
```

## Q016 · S02 · medium

勾稽 PRD-006 的在库、实物隔离及可用数量，保留可用量为零的地点。

```json
{
  "rows": [
    {
      "lot_id": "LOT-006-A",
      "location_id": "STORE-006",
      "on_hand": "25.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-006-B",
      "location_id": "STORE-006",
      "on_hand": "28.000000",
      "quarantined": "3.000000",
      "recall_blocked": "25.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-006-D",
      "location_id": "STORE-006",
      "on_hand": "25.000000",
      "quarantined": "0.000000",
      "recall_blocked": "25.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-006-A",
      "location_id": "WH-006",
      "on_hand": "86.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-006-B",
      "location_id": "WH-006",
      "on_hand": "96.000000",
      "quarantined": "20.000000",
      "recall_blocked": "76.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-006-D",
      "location_id": "WH-006",
      "on_hand": "61.000000",
      "quarantined": "0.000000",
      "recall_blocked": "61.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-006-C",
      "location_id": "WH-006",
      "on_hand": "146.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "30.000000",
      "available": "116.000000"
    },
    {
      "lot_id": "LOT-006-C",
      "location_id": "STORE-006",
      "on_hand": "28.000000",
      "quarantined": "5.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "23.000000"
    }
  ]
}
```

## Q017 · S02 · medium

找出 LOT-007-A 最新可见检验及受检地点，不能使用未来才可知的结果。

```json
{
  "rows": [
    {
      "inspection_id": "QC-007-A",
      "lot_id": "LOT-007-A",
      "location_id": "WH-007",
      "inspection_date": "2026-11-03",
      "known_date": "2026-11-03",
      "result_code": "passed"
    }
  ]
}
```

## Q018 · S02 · medium

仅列出 PRD-008 退货量大于零的批次地点库存行，并列示在库及实物隔离量；退货已计入在库不能再加一次。

```json
{
  "rows": [
    {
      "lot_id": "LOT-008-B",
      "location_id": "STORE-008",
      "on_hand": "26.000000",
      "returned": "3.000000",
      "quarantined": "3.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-008-C",
      "location_id": "STORE-008",
      "on_hand": "26.000000",
      "returned": "3.000000",
      "quarantined": "5.000000",
      "available": "21.000000"
    }
  ]
}
```

## Q019 · S02 · complex

对 PRD-009 分开列示检验状态、实物隔离、召回阻断和预留，解释为何不能承诺全部已收货库存。

```json
{
  "rows": [
    {
      "lot_id": "LOT-009-A",
      "location_id": "STORE-009",
      "inspection_status_code": "passed",
      "on_hand": "25.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-009-B",
      "location_id": "STORE-009",
      "inspection_status_code": "passed",
      "on_hand": "28.000000",
      "quarantined": "3.000000",
      "recall_blocked": "25.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-009-D",
      "location_id": "STORE-009",
      "inspection_status_code": "passed",
      "on_hand": "25.000000",
      "quarantined": "0.000000",
      "recall_blocked": "25.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-009-A",
      "location_id": "WH-009",
      "inspection_status_code": "passed",
      "on_hand": "82.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-009-B",
      "location_id": "WH-009",
      "inspection_status_code": "passed",
      "on_hand": "90.000000",
      "quarantined": "20.000000",
      "recall_blocked": "70.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-009-D",
      "location_id": "WH-009",
      "inspection_status_code": "passed",
      "on_hand": "64.000000",
      "quarantined": "0.000000",
      "recall_blocked": "64.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-009-C",
      "location_id": "WH-009",
      "inspection_status_code": "passed",
      "on_hand": "149.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "30.000000",
      "available": "119.000000"
    },
    {
      "lot_id": "LOT-009-C",
      "location_id": "STORE-009",
      "inspection_status_code": "passed",
      "on_hand": "28.000000",
      "quarantined": "5.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "23.000000"
    }
  ]
}
```

## Q020 · S02 · complex

对 PRD-010 在同一2月28日业务日期下，比较2月20日与2月28日可知的库存，返回两个知识日期及完整数量拆分。

```json
{
  "rows": [
    {
      "knowledge_date": "2027-02-20",
      "lot_id": "LOT-010-A",
      "location_id": "WH-010",
      "on_hand": "123.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-A",
      "location_id": "STORE-010",
      "on_hand": "24.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-B",
      "location_id": "STORE-010",
      "on_hand": "22.000000",
      "quarantined": "3.000000",
      "recall_blocked": "19.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-D",
      "location_id": "STORE-010",
      "on_hand": "24.000000",
      "quarantined": "0.000000",
      "recall_blocked": "24.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-A",
      "location_id": "WH-010",
      "on_hand": "83.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-B",
      "location_id": "WH-010",
      "on_hand": "91.000000",
      "quarantined": "20.000000",
      "recall_blocked": "71.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-D",
      "location_id": "WH-010",
      "on_hand": "60.000000",
      "quarantined": "0.000000",
      "recall_blocked": "60.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-C",
      "location_id": "WH-010",
      "on_hand": "150.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "30.000000",
      "available": "120.000000"
    },
    {
      "knowledge_date": "2027-02-20",
      "lot_id": "LOT-010-B",
      "location_id": "WH-010",
      "on_hand": "151.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "151.000000"
    },
    {
      "knowledge_date": "2027-02-20",
      "lot_id": "LOT-010-C",
      "location_id": "WH-010",
      "on_hand": "190.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "190.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-010-C",
      "location_id": "STORE-010",
      "on_hand": "27.000000",
      "quarantined": "5.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "22.000000"
    },
    {
      "knowledge_date": "2027-02-20",
      "lot_id": "LOT-010-D",
      "location_id": "WH-010",
      "on_hand": "80.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "80.000000"
    }
  ]
}
```

## Q021 · S03 · basic

列出观察日可见的 LOT-001-B 直接下游关联。

```json
{
  "rows": [
    {
      "link_id": "LINK-001",
      "parent_lot_id": "LOT-001-B",
      "child_lot_id": "LOT-001-D",
      "link_type_code": "split"
    }
  ]
}
```

## Q022 · S03 · basic

列出观察日可见的 LOT-002-D 直接上游批次。

```json
{
  "rows": [
    {
      "link_id": "LINK-002",
      "parent_lot_id": "LOT-002-B",
      "child_lot_id": "LOT-002-D",
      "link_type_code": "split"
    }
  ]
}
```

## Q023 · S03 · basic

列出 PRD-003 的已声明批次转换及输入输出数量，逐关联返回。

```json
{
  "rows": [
    {
      "link_id": "LINK-003",
      "parent_lot_id": "LOT-003-B",
      "child_lot_id": "LOT-003-D",
      "link_type_code": "split",
      "parent_quantity": "20",
      "child_quantity": "20",
      "unit": "件"
    }
  ]
}
```

## Q024 · S03 · medium

追踪 LOT-004-D 完整的上下游连通批次链，每条可见关联只返回一次。

```json
{
  "rows": [
    {
      "link_id": "LINK-004",
      "parent_lot_id": "LOT-004-B",
      "child_lot_id": "LOT-004-D",
      "link_type_code": "split"
    }
  ]
}
```

## Q025 · S03 · medium

列出 LOT-005-B 可达的所有下游批次（含根批次）、商品标识及到期日。

```json
{
  "rows": [
    {
      "lot_id": "LOT-005-D",
      "product_id": "PRD-005",
      "expiry_date": "2027-03-05"
    },
    {
      "lot_id": "LOT-005-B",
      "product_id": "PRD-005",
      "expiry_date": "2027-03-10"
    }
  ]
}
```

## Q026 · S03 · medium

检查 LOT-006-B 连通批次链，仅列出同商品拆分中声明输入输出数量不一致的关联。

```json
{
  "rows": []
}
```

## Q027 · S03 · medium

按业务日期、数值事件序号升序列出 LOT-007-B 的可见实际流转，事件标识用于同序号排序，保留调拨两端；无来源或目的地点时返回 null。

```json
{
  "rows": [
    {
      "event_id": "EV-00131",
      "event_type_code": "receive",
      "source_location_id": null,
      "destination_location_id": "WH-007",
      "event_date": "2027-02-02",
      "event_sequence": "10",
      "quantity": "157",
      "unit": "件"
    },
    {
      "event_id": "EV-00146",
      "event_type_code": "consume",
      "source_location_id": "WH-007",
      "destination_location_id": null,
      "event_date": "2027-02-21",
      "event_sequence": "15",
      "quantity": "20",
      "unit": "件"
    },
    {
      "event_id": "EV-00132",
      "event_type_code": "dispatch",
      "source_location_id": "WH-007",
      "destination_location_id": "STORE-007",
      "event_date": "2027-02-22",
      "event_sequence": "20",
      "quantity": "40",
      "unit": "件"
    },
    {
      "event_id": "EV-00133",
      "event_type_code": "arrive",
      "source_location_id": null,
      "destination_location_id": "STORE-007",
      "event_date": "2027-02-23",
      "event_sequence": "30",
      "quantity": "40",
      "unit": "件"
    },
    {
      "event_id": "EV-00134",
      "event_type_code": "sale",
      "source_location_id": "STORE-007",
      "destination_location_id": null,
      "event_date": "2027-02-24",
      "event_sequence": "40",
      "quantity": "16",
      "unit": "件"
    },
    {
      "event_id": "EV-00135",
      "event_type_code": "return",
      "source_location_id": null,
      "destination_location_id": "STORE-007",
      "event_date": "2027-02-25",
      "event_sequence": "50",
      "quantity": "3",
      "unit": "件"
    }
  ]
}
```

## Q028 · S03 · complex

对 LOT-047-D，沿可见批次关联追踪完整的上下游无向连通分量，包含不同商品和兄弟分支；每条边仅列一次，不能把输入单位直接视作输出单位。

```json
{
  "rows": [
    {
      "link_id": "LINK-047",
      "parent_lot_id": "LOT-047-B",
      "child_lot_id": "LOT-047-D",
      "link_type_code": "split",
      "parent_quantity": "20",
      "child_quantity": "20",
      "unit": "件"
    },
    {
      "link_id": "LINK-047-MULTI",
      "parent_lot_id": "LOT-048-B",
      "child_lot_id": "LOT-047-D",
      "link_type_code": "transform",
      "parent_quantity": "5",
      "child_quantity": "4",
      "unit": "件"
    },
    {
      "link_id": "LINK-048",
      "parent_lot_id": "LOT-048-B",
      "child_lot_id": "LOT-048-D",
      "link_type_code": "split",
      "parent_quantity": "20",
      "child_quantity": "20",
      "unit": "件"
    }
  ]
}
```

## Q029 · S03 · complex

对 REC-012 列出全部受影响下游批次及商品供应商，间接下游只计一次。

```json
{
  "rows": [
    {
      "lot_id": "LOT-012-D",
      "product_id": "PRD-012",
      "supplier_id": "ORG-012",
      "expiry_date": "2027-03-05"
    },
    {
      "lot_id": "LOT-012-B",
      "product_id": "PRD-012",
      "supplier_id": "ORG-012",
      "expiry_date": "2027-03-10"
    }
  ]
}
```

## Q030 · S03 · complex

固定业务日2月28日，比较 LOT-041-B 在2月20日及2月28日知识截止下的可见连通关联。

```json
{
  "rows": [
    {
      "knowledge_date": "2027-02-28",
      "link_id": "LINK-041",
      "parent_lot_id": "LOT-041-B",
      "child_lot_id": "LOT-041-D",
      "link_type_code": "split"
    }
  ]
}
```

## Q031 · S04 · basic

列出2月28日 PRD-001 按批次地点拆分的库存。

```json
{
  "rows": [
    {
      "lot_id": "LOT-001-A",
      "location_id": "STORE-001",
      "on_hand": "24.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-001-B",
      "location_id": "STORE-001",
      "on_hand": "27.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-001-D",
      "location_id": "STORE-001",
      "on_hand": "24.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-001-A",
      "location_id": "WH-001",
      "on_hand": "81.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-001-B",
      "location_id": "WH-001",
      "on_hand": "91.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-001-D",
      "location_id": "WH-001",
      "on_hand": "61.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-001-C",
      "location_id": "WH-001",
      "on_hand": "141.000000",
      "in_transit": "0.000000",
      "available": "111.000000"
    },
    {
      "lot_id": "LOT-001-C",
      "location_id": "STORE-001",
      "on_hand": "27.000000",
      "in_transit": "0.000000",
      "available": "22.000000"
    }
  ]
}
```

## Q032 · S04 · basic

PRD-005 哪些批次仍在途，目的地点在哪里？

```json
{
  "rows": [
    {
      "lot_id": "LOT-005-B",
      "location_id": "STORE-005",
      "in_transit": "5.000000"
    }
  ]
}
```

## Q033 · S04 · basic

仅列出 PRD-003 实物隔离数量大于零的批次地点行。

```json
{
  "rows": [
    {
      "lot_id": "LOT-003-B",
      "location_id": "STORE-003",
      "quarantined": "3.000000"
    },
    {
      "lot_id": "LOT-003-C",
      "location_id": "STORE-003",
      "quarantined": "5.000000"
    },
    {
      "lot_id": "LOT-003-B",
      "location_id": "WH-003",
      "quarantined": "20.000000"
    }
  ]
}
```

## Q034 · S04 · medium

对 PRD-004 查询已记录可用库存指标，并与相同日期的原子事实重算勾稽；按批次地点返回记录值、重算值及差异。

```json
{
  "rows": [
    {
      "snapshot_id": "IS-LOT-004-A-STORE-004",
      "lot_id": "LOT-004-A",
      "location_id": "STORE-004",
      "recorded_available": "0.000000",
      "reconstructed_available": "0.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-B-STORE-004",
      "lot_id": "LOT-004-B",
      "location_id": "STORE-004",
      "recorded_available": "0.000000",
      "reconstructed_available": "0.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-C-STORE-004",
      "lot_id": "LOT-004-C",
      "location_id": "STORE-004",
      "recorded_available": "22.000000",
      "reconstructed_available": "22.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-D-STORE-004",
      "lot_id": "LOT-004-D",
      "location_id": "STORE-004",
      "recorded_available": "0.000000",
      "reconstructed_available": "0.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-A-WH-004",
      "lot_id": "LOT-004-A",
      "location_id": "WH-004",
      "recorded_available": "0.000000",
      "reconstructed_available": "0.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-B-WH-004",
      "lot_id": "LOT-004-B",
      "location_id": "WH-004",
      "recorded_available": "0.000000",
      "reconstructed_available": "0.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-C-WH-004",
      "lot_id": "LOT-004-C",
      "location_id": "WH-004",
      "recorded_available": "114.000000",
      "reconstructed_available": "114.000000",
      "difference": "0.000000"
    },
    {
      "snapshot_id": "IS-LOT-004-D-WH-004",
      "lot_id": "LOT-004-D",
      "location_id": "WH-004",
      "recorded_available": "0.000000",
      "reconstructed_available": "0.000000",
      "difference": "0.000000"
    }
  ]
}
```

## Q035 · S04 · medium

仅列出 PRD-005 已在库但不可用的货，给出全部阻断数量分类。

```json
{
  "rows": [
    {
      "lot_id": "LOT-005-A",
      "location_id": "STORE-005",
      "on_hand": "23.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-005-B",
      "location_id": "STORE-005",
      "on_hand": "21.000000",
      "quarantined": "3.000000",
      "recall_blocked": "18.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-005-D",
      "location_id": "STORE-005",
      "on_hand": "23.000000",
      "quarantined": "0.000000",
      "recall_blocked": "23.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-005-A",
      "location_id": "WH-005",
      "on_hand": "85.000000",
      "quarantined": "0.000000",
      "recall_blocked": "0.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-005-B",
      "location_id": "WH-005",
      "on_hand": "95.000000",
      "quarantined": "20.000000",
      "recall_blocked": "75.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-005-D",
      "location_id": "WH-005",
      "on_hand": "60.000000",
      "quarantined": "0.000000",
      "recall_blocked": "60.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    }
  ]
}
```

## Q036 · S04 · medium

比较 PRD-006 在2月20日和2月28日的库存，分别使用当日已知信息。

```json
{
  "rows": [
    {
      "as_of_date": "2027-02-20",
      "lot_id": "LOT-006-A",
      "location_id": "WH-006",
      "on_hand": "126.000000",
      "in_transit": "0.000000",
      "available": "126.000000"
    },
    {
      "as_of_date": "2027-02-20",
      "lot_id": "LOT-006-B",
      "location_id": "WH-006",
      "on_hand": "156.000000",
      "in_transit": "0.000000",
      "available": "156.000000"
    },
    {
      "as_of_date": "2027-02-20",
      "lot_id": "LOT-006-C",
      "location_id": "WH-006",
      "on_hand": "186.000000",
      "in_transit": "0.000000",
      "available": "186.000000"
    },
    {
      "as_of_date": "2027-02-20",
      "lot_id": "LOT-006-D",
      "location_id": "WH-006",
      "on_hand": "81.000000",
      "in_transit": "0.000000",
      "available": "81.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-A",
      "location_id": "STORE-006",
      "on_hand": "25.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-B",
      "location_id": "STORE-006",
      "on_hand": "28.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-D",
      "location_id": "STORE-006",
      "on_hand": "25.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-A",
      "location_id": "WH-006",
      "on_hand": "86.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-B",
      "location_id": "WH-006",
      "on_hand": "96.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-D",
      "location_id": "WH-006",
      "on_hand": "61.000000",
      "in_transit": "0.000000",
      "available": "0.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-C",
      "location_id": "WH-006",
      "on_hand": "146.000000",
      "in_transit": "0.000000",
      "available": "116.000000"
    },
    {
      "as_of_date": "2027-02-28",
      "lot_id": "LOT-006-C",
      "location_id": "STORE-006",
      "on_hand": "28.000000",
      "in_transit": "0.000000",
      "available": "23.000000"
    }
  ]
}
```

## Q037 · S04 · medium

对 WH-007 与 STORE-007 的 PRD-007，列出累计净售出、退货、在库及在途量，不能重复计算调拨两端。

```json
{
  "rows": [
    {
      "lot_id": "LOT-007-A",
      "location_id": "STORE-007",
      "on_hand": "24.000000",
      "in_transit": "0.000000",
      "sold": "16.000000",
      "returned": "0.000000"
    },
    {
      "lot_id": "LOT-007-B",
      "location_id": "STORE-007",
      "on_hand": "27.000000",
      "in_transit": "0.000000",
      "sold": "13.000000",
      "returned": "3.000000"
    },
    {
      "lot_id": "LOT-007-C",
      "location_id": "STORE-007",
      "on_hand": "27.000000",
      "in_transit": "0.000000",
      "sold": "13.000000",
      "returned": "3.000000"
    },
    {
      "lot_id": "LOT-007-D",
      "location_id": "STORE-007",
      "on_hand": "24.000000",
      "in_transit": "0.000000",
      "sold": "16.000000",
      "returned": "0.000000"
    },
    {
      "lot_id": "LOT-007-A",
      "location_id": "WH-007",
      "on_hand": "80.000000",
      "in_transit": "0.000000",
      "sold": "0.000000",
      "returned": "0.000000"
    },
    {
      "lot_id": "LOT-007-B",
      "location_id": "WH-007",
      "on_hand": "97.000000",
      "in_transit": "0.000000",
      "sold": "0.000000",
      "returned": "0.000000"
    },
    {
      "lot_id": "LOT-007-C",
      "location_id": "WH-007",
      "on_hand": "147.000000",
      "in_transit": "0.000000",
      "sold": "0.000000",
      "returned": "0.000000"
    },
    {
      "lot_id": "LOT-007-D",
      "location_id": "WH-007",
      "on_hand": "62.000000",
      "in_transit": "0.000000",
      "sold": "0.000000",
      "returned": "0.000000"
    }
  ]
}
```

## Q038 · S04 · complex

对 PRD-045 到货缺少发运记录的情况，列出数量及可信状态，未知必须保留为空。

```json
{
  "rows": [
    {
      "lot_id": "LOT-045-A",
      "location_id": "STORE-020",
      "on_hand": "25.000000",
      "in_transit": "0.000000",
      "available": "0.000000",
      "quality_status": "known"
    },
    {
      "lot_id": "LOT-045-A",
      "location_id": "WH-020",
      "on_hand": "83.000000",
      "in_transit": "0.000000",
      "available": "0.000000",
      "quality_status": "known"
    },
    {
      "lot_id": "LOT-045-B",
      "location_id": "WH-020",
      "on_hand": "90.000000",
      "in_transit": "0.000000",
      "available": "0.000000",
      "quality_status": "known"
    },
    {
      "lot_id": "LOT-045-D",
      "location_id": "WH-020",
      "on_hand": "60.000000",
      "in_transit": "0.000000",
      "available": "0.000000",
      "quality_status": "known"
    },
    {
      "lot_id": "LOT-045-B",
      "location_id": "STORE-020",
      "on_hand": "23.000000",
      "in_transit": "5.000000",
      "available": "0.000000",
      "quality_status": "known"
    },
    {
      "lot_id": "LOT-045-C",
      "location_id": "WH-020",
      "on_hand": "141.000000",
      "in_transit": "0.000000",
      "available": "111.000000",
      "quality_status": "known"
    },
    {
      "lot_id": "LOT-045-C",
      "location_id": "STORE-020",
      "on_hand": null,
      "in_transit": null,
      "available": null,
      "quality_status": "unknown"
    },
    {
      "lot_id": "LOT-045-D",
      "location_id": "STORE-020",
      "on_hand": null,
      "in_transit": null,
      "available": null,
      "quality_status": "unknown"
    }
  ]
}
```

## Q039 · S04 · complex

找出 PRD-046 不可信的库存行，保留空数量，不能把源负库存改成零。

```json
{
  "rows": [
    {
      "lot_id": "LOT-046-C",
      "location_id": "STORE-021",
      "on_hand": null,
      "in_transit": null,
      "available": null,
      "quality_status": "unknown"
    }
  ]
}
```

## Q040 · S04 · complex

对 PRD-008 和 PRD-009 分商品汇总库存，不得跳过受阻行；若任一行未知，该商品合计为空。

```json
{
  "rows": [
    {
      "product_id": "PRD-008",
      "unit": "件",
      "on_hand": "488.000000",
      "in_transit": "0.000000",
      "quarantined": "28.000000",
      "recall_blocked": "187.000000",
      "reserved": "30.000000",
      "available": "139.000000"
    },
    {
      "product_id": "PRD-009",
      "unit": "件",
      "on_hand": "491.000000",
      "in_transit": "0.000000",
      "quarantined": "28.000000",
      "recall_blocked": "184.000000",
      "reserved": "30.000000",
      "available": "142.000000"
    }
  ]
}
```

## Q041 · S05 · basic

2月28日 PRD-010 哪些批次已过期？

```json
{
  "rows": [
    {
      "lot_id": "LOT-010-A",
      "location_id": "STORE-010",
      "expiry_date": "2027-02-20",
      "on_hand": "24.000000",
      "expired": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-010-A",
      "location_id": "WH-010",
      "expiry_date": "2027-02-20",
      "on_hand": "83.000000",
      "expired": true,
      "available": "0.000000"
    }
  ]
}
```

## Q042 · S05 · basic

PRD-011 哪些批次在观察日起14天内到期（含当天）？

```json
{
  "rows": [
    {
      "lot_id": "LOT-011-D",
      "location_id": "STORE-011",
      "expiry_date": "2027-03-05",
      "on_hand": "23.000000",
      "near_expiry": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-011-D",
      "location_id": "WH-011",
      "expiry_date": "2027-03-05",
      "on_hand": "61.000000",
      "near_expiry": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-011-B",
      "location_id": "STORE-011",
      "expiry_date": "2027-03-10",
      "on_hand": "26.000000",
      "near_expiry": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-011-B",
      "location_id": "WH-011",
      "expiry_date": "2027-03-10",
      "on_hand": "92.000000",
      "near_expiry": true,
      "available": "0.000000"
    }
  ]
}
```

## Q043 · S05 · basic

PRD-012 的剩余保质期要求及各批次到期日是什么？

```json
{
  "rows": [
    {
      "product_id": "PRD-012",
      "min_shelf_days": "3",
      "lot_id": "LOT-012-A",
      "expiry_date": "2027-02-20"
    },
    {
      "product_id": "PRD-012",
      "min_shelf_days": "3",
      "lot_id": "LOT-012-D",
      "expiry_date": "2027-03-05"
    },
    {
      "product_id": "PRD-012",
      "min_shelf_days": "3",
      "lot_id": "LOT-012-B",
      "expiry_date": "2027-03-10"
    },
    {
      "product_id": "PRD-012",
      "min_shelf_days": "3",
      "lot_id": "LOT-012-C",
      "expiry_date": "2027-03-31"
    },
    {
      "product_id": "PRD-012",
      "min_shelf_days": "3",
      "lot_id": "LOT-012-P",
      "expiry_date": "2027-03-31"
    }
  ]
}
```

## Q044 · S05 · medium

按FEFO顺序列出 WH-013 的 PRD-013 可用批次，先扣除隔离和预留。

```json
{
  "rows": [
    {
      "lot_id": "LOT-013-C",
      "expiry_date": "2027-03-31",
      "available": "112.000000"
    }
  ]
}
```

## Q045 · S05 · medium

PRD-014 哪些近效期在库货物还因其他原因不可用？

```json
{
  "rows": [
    {
      "lot_id": "LOT-014-D",
      "location_id": "STORE-014",
      "expiry_date": "2027-03-05",
      "on_hand": "23.000000",
      "quarantined": "0.000000",
      "recall_blocked": "23.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-014-D",
      "location_id": "WH-014",
      "expiry_date": "2027-03-05",
      "on_hand": "64.000000",
      "quarantined": "0.000000",
      "recall_blocked": "64.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-014-B",
      "location_id": "STORE-014",
      "expiry_date": "2027-03-10",
      "on_hand": "26.000000",
      "quarantined": "3.000000",
      "recall_blocked": "23.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-014-B",
      "location_id": "WH-014",
      "expiry_date": "2027-03-10",
      "on_hand": "95.000000",
      "quarantined": "20.000000",
      "recall_blocked": "75.000000",
      "reserved": "0.000000",
      "available": "0.000000"
    }
  ]
}
```

## Q046 · S05 · medium

截至3月10日、知识截止2月28日，报告 PRD-015 考虑过期后的实际库存，不能计入计划收货。

```json
{
  "rows": [
    {
      "lot_id": "LOT-015-B",
      "location_id": "STORE-015",
      "expiry_date": "2027-03-10",
      "on_hand": "23.000000",
      "expired": false,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-015-B",
      "location_id": "WH-015",
      "expiry_date": "2027-03-10",
      "on_hand": "96.000000",
      "expired": false,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-015-A",
      "location_id": "STORE-015",
      "expiry_date": "2027-02-20",
      "on_hand": "25.000000",
      "expired": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-015-A",
      "location_id": "WH-015",
      "expiry_date": "2027-02-20",
      "on_hand": "81.000000",
      "expired": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-015-D",
      "location_id": "STORE-015",
      "expiry_date": "2027-03-05",
      "on_hand": "25.000000",
      "expired": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-015-D",
      "location_id": "WH-015",
      "expiry_date": "2027-03-05",
      "on_hand": "60.000000",
      "expired": true,
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-015-C",
      "location_id": "WH-015",
      "expiry_date": "2027-03-31",
      "on_hand": "144.000000",
      "expired": false,
      "available": "144.000000"
    },
    {
      "lot_id": "LOT-015-C",
      "location_id": "STORE-015",
      "expiry_date": "2027-03-31",
      "on_hand": "28.000000",
      "expired": false,
      "available": "23.000000"
    }
  ]
}
```

## Q047 · S05 · medium

对 PRD-016，列出能满足3月5日发货且仍有7天保质期的批次，只保留正可用量并按FEFO排序。

```json
{
  "rows": [
    {
      "lot_id": "LOT-016-C",
      "location_id": "WH-016",
      "expiry_date": "2027-03-31",
      "available": "115.000000"
    },
    {
      "lot_id": "LOT-016-C",
      "location_id": "STORE-016",
      "expiry_date": "2027-03-31",
      "available": "22.000000"
    }
  ]
}
```

## Q048 · S05 · complex

对 PRD-017 未结订单，按各行真实交期和保质期要求共享分配库存。

```json
{
  "rows": [
    {
      "line_id": "LINE-017-A",
      "order_id": "ORD-017-A",
      "requested_quantity": "111.000000",
      "allocated_quantity": "111.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-017-C",
          "quantity": "111.000000"
        }
      ],
      "allocation_status_code": "full"
    },
    {
      "line_id": "LINE-017-B",
      "order_id": "ORD-017-B",
      "requested_quantity": "102.000000",
      "allocated_quantity": "35.000000",
      "shortage_quantity": "67.000000",
      "allocations": [
        {
          "lot_id": "LOT-017-C",
          "quantity": "35.000000"
        }
      ],
      "allocation_status_code": "partial"
    }
  ]
}
```

## Q049 · S05 · complex

对 PRD-018 规划3月需求，考虑库存到期并排除保质期不达标的计划收货。

```json
{
  "rows": [
    {
      "forecast_id": "FC-018-M3",
      "location_id": "WH-018",
      "demand_date": "2027-03-31",
      "demand_quantity": "83.000000",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "83.000000"
    },
    {
      "forecast_id": "FC-018-M2",
      "location_id": "WH-018",
      "demand_date": "2027-03-15",
      "demand_quantity": "83.000000",
      "eligible_supply_quantity": "61.000000",
      "allocated_quantity": "61.000000",
      "shortage_quantity": "22.000000"
    },
    {
      "forecast_id": "FC-018-M1",
      "location_id": "WH-018",
      "demand_date": "2027-03-05",
      "demand_quantity": "83.000000",
      "eligible_supply_quantity": "144.000000",
      "allocated_quantity": "83.000000",
      "shortage_quantity": "0.000000"
    }
  ]
}
```

## Q050 · S05 · complex

对 PRD-049 与 PRD-050，分商品地点列出近效期可用货量，不混单位，不能将有效召回货算为可用，并区分已关闭召回。

```json
{
  "rows": [
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-B",
      "location_id": "STORE-025",
      "unit": "件",
      "expiry_date": "2027-03-10",
      "available": "18.000000"
    },
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-D",
      "location_id": "STORE-025",
      "unit": "件",
      "expiry_date": "2027-03-05",
      "available": "23.000000"
    },
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-D",
      "location_id": "WH-025",
      "unit": "件",
      "expiry_date": "2027-03-05",
      "available": "60.000000"
    },
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-B",
      "location_id": "WH-025",
      "unit": "件",
      "expiry_date": "2027-03-10",
      "available": "75.000000"
    }
  ]
}
```

## Q051 · S06 · basic

列出未结 ORD-001-A 的订单行、需求量与保质期要求。

```json
{
  "rows": [
    {
      "line_id": "LINE-001-A",
      "order_id": "ORD-001-A",
      "product_id": "PRD-001",
      "quantity": "111",
      "unit": "件",
      "min_shelf_days": "3",
      "due_date": "2027-03-02",
      "priority": "1"
    }
  ]
}
```

## Q052 · S06 · basic

列出观察日 ORD-002-A 的有效预留。

```json
{
  "rows": [
    {
      "reservation_id": "RSV-002-A",
      "line_id": "LINE-002-A",
      "lot_id": "LOT-002-C",
      "location_id": "WH-002",
      "quantity": "20"
    }
  ]
}
```

## Q053 · S06 · medium

ORD-003-A 能否足量履约？考虑自身及其他订单预留、效期和质量约束。

```json
{
  "rows": [
    {
      "line_id": "LINE-003-A",
      "requested_quantity": "113.000000",
      "allocated_quantity": "113.000000",
      "shortage_quantity": "0.000000",
      "allocation_status_code": "full",
      "allocations": [
        {
          "lot_id": "LOT-003-C",
          "quantity": "113.000000"
        }
      ]
    }
  ]
}
```

## Q054 · S06 · medium

共享分配 PRD-004 的两个竞争订单，给出准确批次分配。

```json
{
  "rows": [
    {
      "line_id": "LINE-004-A",
      "order_id": "ORD-004-A",
      "allocated_quantity": "114.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-004-C",
          "quantity": "114.000000"
        }
      ]
    },
    {
      "line_id": "LINE-004-B",
      "order_id": "ORD-004-B",
      "allocated_quantity": "30.000000",
      "shortage_quantity": "74.000000",
      "allocations": [
        {
          "lot_id": "LOT-004-C",
          "quantity": "30.000000"
        }
      ]
    }
  ]
}
```

## Q055 · S06 · medium

PRD-005 未结订单行在FEFO分配后哪些仍有缺口？

```json
{
  "rows": [
    {
      "line_id": "LINE-005-B",
      "order_id": "ORD-005-B",
      "requested_quantity": "100.000000",
      "allocated_quantity": "30.000000",
      "shortage_quantity": "70.000000"
    }
  ]
}
```

## Q056 · S06 · medium

分配 PRD-049 未结积压订单，必须包含逾期 ORD-049-A；不能静默忽略逾期订单，保质期基准使用观察日和交期中较晚者。

```json
{
  "rows": [
    {
      "line_id": "LINE-049-A",
      "order_id": "ORD-049-A",
      "allocated_quantity": "111.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-049-C",
          "quantity": "111.000000"
        }
      ],
      "allocation_status_code": "full"
    },
    {
      "line_id": "LINE-049-B",
      "order_id": "ORD-049-B",
      "allocated_quantity": "34.000000",
      "shortage_quantity": "70.000000",
      "allocations": [
        {
          "lot_id": "LOT-049-C",
          "quantity": "34.000000"
        }
      ],
      "allocation_status_code": "partial"
    }
  ]
}
```

## Q057 · S06 · complex

对 PRD-007 全部竞争订单联合分配，并勾稽总需求、分配与缺口，库存不能用两次。

```json
{
  "rows": [
    {
      "product_id": "PRD-007",
      "requested_quantity": "219.000000",
      "allocated_quantity": "147.000000",
      "shortage_quantity": "72.000000"
    }
  ]
}
```

## Q058 · S06 · complex

若只调查 ORD-008-B，应保留被排除订单的预留占用，并只释放一次B自身预留后分配。

```json
{
  "rows": [
    {
      "line_id": "LINE-008-B",
      "requested_quantity": "103.000000",
      "allocated_quantity": "103.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-008-C",
          "quantity": "103.000000"
        }
      ]
    }
  ]
}
```

## Q059 · S06 · complex

对 PRD-043，报告冲突源事件造成的分配不确定性，不能承诺零库存或编造货量。

```json
{
  "rows": [
    {
      "line_id": "LINE-043-A",
      "requested_quantity": "113.000000",
      "allocated_quantity": "113.000000",
      "shortage_quantity": "0.000000",
      "allocation_status_code": "full",
      "allocations": [
        {
          "lot_id": "LOT-043-C",
          "quantity": "113.000000"
        }
      ]
    },
    {
      "line_id": "LINE-043-B",
      "requested_quantity": "103.000000",
      "allocated_quantity": "37.000000",
      "shortage_quantity": "66.000000",
      "allocation_status_code": "partial",
      "allocations": [
        {
          "lot_id": "LOT-043-C",
          "quantity": "37.000000"
        }
      ]
    }
  ]
}
```

## Q060 · S06 · complex

对 PRD-009 与 PRD-010 分商品、同商品跨订单共享分配，满足召回、质量、交期和FEFO约束。

```json
{
  "rows": [
    {
      "product_id": "PRD-009",
      "line_id": "LINE-009-A",
      "order_id": "ORD-009-A",
      "requested_quantity": "111.000000",
      "allocated_quantity": "111.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-009-C",
          "quantity": "111.000000"
        }
      ],
      "allocation_status_code": "full"
    },
    {
      "product_id": "PRD-010",
      "line_id": "LINE-010-A",
      "order_id": "ORD-010-A",
      "requested_quantity": "112.000000",
      "allocated_quantity": "112.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-010-C",
          "quantity": "112.000000"
        }
      ],
      "allocation_status_code": "full"
    },
    {
      "product_id": "PRD-009",
      "line_id": "LINE-009-B",
      "order_id": "ORD-009-B",
      "requested_quantity": "104.000000",
      "allocated_quantity": "38.000000",
      "shortage_quantity": "66.000000",
      "allocations": [
        {
          "lot_id": "LOT-009-C",
          "quantity": "38.000000"
        }
      ],
      "allocation_status_code": "partial"
    },
    {
      "product_id": "PRD-010",
      "line_id": "LINE-010-B",
      "order_id": "ORD-010-B",
      "requested_quantity": "100.000000",
      "allocated_quantity": "38.000000",
      "shortage_quantity": "62.000000",
      "allocations": [
        {
          "lot_id": "LOT-010-C",
          "quantity": "38.000000"
        }
      ],
      "allocation_status_code": "partial"
    }
  ]
}
```

## Q061 · S07 · basic

列出2月28日前已知的 PRD-001 三月计划需求。

```json
{
  "rows": [
    {
      "forecast_id": "FC-001-M1",
      "product_id": "PRD-001",
      "location_id": "WH-001",
      "demand_date": "2027-03-05",
      "quantity": "81",
      "unit": "件",
      "known_date": "2027-02-26"
    },
    {
      "forecast_id": "FC-001-M2",
      "product_id": "PRD-001",
      "location_id": "WH-001",
      "demand_date": "2027-03-15",
      "quantity": "81",
      "unit": "件",
      "known_date": "2027-02-26"
    },
    {
      "forecast_id": "FC-001-M3",
      "product_id": "PRD-001",
      "location_id": "WH-001",
      "demand_date": "2027-03-31",
      "quantity": "81",
      "unit": "件",
      "known_date": "2027-02-26"
    }
  ]
}
```

## Q062 · S07 · basic

列出2月28日已知且截至3月31日的 PRD-002 计划入库。

```json
{
  "rows": [
    {
      "event_id": "EV-00040",
      "lot_id": "LOT-002-P",
      "destination_location_id": "WH-002",
      "event_date": "2027-03-05",
      "quantity": "27",
      "unit": "件"
    }
  ]
}
```

## Q063 · S07 · medium

规划 PRD-003 三月补货，逐预测列示合格供给、分配、缺口及建议量。

```json
{
  "rows": [
    {
      "forecast_id": "FC-003-M3",
      "product_id": "PRD-003",
      "location_id": "WH-003",
      "demand_date": "2027-03-31",
      "demand_quantity": "83.000000",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "83.000000",
      "recommended_quantity": "83.000000"
    },
    {
      "forecast_id": "FC-003-M2",
      "product_id": "PRD-003",
      "location_id": "WH-003",
      "demand_date": "2027-03-15",
      "demand_quantity": "83.000000",
      "eligible_supply_quantity": "58.000000",
      "allocated_quantity": "58.000000",
      "shortage_quantity": "25.000000",
      "recommended_quantity": "25.000000"
    },
    {
      "forecast_id": "FC-003-M1",
      "product_id": "PRD-003",
      "location_id": "WH-003",
      "demand_date": "2027-03-05",
      "demand_quantity": "83.000000",
      "eligible_supply_quantity": "141.000000",
      "allocated_quantity": "83.000000",
      "shortage_quantity": "0.000000",
      "recommended_quantity": "0.000000"
    }
  ]
}
```

## Q064 · S07 · medium

计入合格计划收货后，PRD-004 哪些三月预测仍短缺？

```json
{
  "rows": [
    {
      "forecast_id": "FC-004-M3",
      "demand_date": "2027-03-31",
      "demand_quantity": "84.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "84.000000",
      "recommended_quantity": "84.000000"
    },
    {
      "forecast_id": "FC-004-M2",
      "demand_date": "2027-03-15",
      "demand_quantity": "84.000000",
      "allocated_quantity": "55.000000",
      "shortage_quantity": "29.000000",
      "recommended_quantity": "29.000000"
    }
  ]
}
```

## Q065 · S07 · medium

仅规划 PRD-005 到3月15日，排除更晚需求，以及需求日尚未合格的收货。

```json
{
  "rows": [
    {
      "forecast_id": "FC-005-M2",
      "demand_date": "2027-03-15",
      "eligible_supply_quantity": "56.000000",
      "allocated_quantity": "56.000000",
      "shortage_quantity": "29.000000"
    },
    {
      "forecast_id": "FC-005-M1",
      "demand_date": "2027-03-05",
      "eligible_supply_quantity": "141.000000",
      "allocated_quantity": "85.000000",
      "shortage_quantity": "0.000000"
    }
  ]
}
```

## Q066 · S07 · medium

分商品汇总 PRD-006 三月需求和补货缺口，任一预测分配未知时合计保持为空。

```json
{
  "rows": [
    {
      "product_id": "PRD-006",
      "demand_quantity": "258.000000",
      "allocated_quantity": "143.000000",
      "shortage_quantity": "115.000000",
      "recommended_quantity": "115.000000"
    }
  ]
}
```

## Q067 · S07 · complex

对 PRD-007，按顺序在三月各次预测间共享库存，逐批考虑效期，并先处理当日供给再分配当日需求。

```json
{
  "rows": [
    {
      "forecast_id": "FC-007-M3",
      "demand_date": "2027-03-31",
      "demand_quantity": "87.000000",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "87.000000"
    },
    {
      "forecast_id": "FC-007-M2",
      "demand_date": "2027-03-15",
      "demand_quantity": "87.000000",
      "eligible_supply_quantity": "30.000000",
      "allocated_quantity": "30.000000",
      "shortage_quantity": "57.000000"
    },
    {
      "forecast_id": "FC-007-M1",
      "demand_date": "2027-03-05",
      "demand_quantity": "87.000000",
      "eligible_supply_quantity": "117.000000",
      "allocated_quantity": "87.000000",
      "shortage_quantity": "0.000000"
    }
  ]
}
```

## Q068 · S07 · complex

对 PRD-008 和 PRD-009，分商品地点报告三月计划，考虑召回及检验不合格排除。

```json
{
  "rows": [
    {
      "product_id": "PRD-008",
      "location_id": "WH-008",
      "forecast_id": "FC-008-M3",
      "demand_date": "2027-03-31",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "88.000000",
      "recommended_quantity": "88.000000"
    },
    {
      "product_id": "PRD-009",
      "location_id": "WH-009",
      "forecast_id": "FC-009-M3",
      "demand_date": "2027-03-31",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "89.000000",
      "recommended_quantity": "89.000000"
    },
    {
      "product_id": "PRD-008",
      "location_id": "WH-008",
      "forecast_id": "FC-008-M2",
      "demand_date": "2027-03-15",
      "eligible_supply_quantity": "55.000000",
      "allocated_quantity": "55.000000",
      "shortage_quantity": "33.000000",
      "recommended_quantity": "33.000000"
    },
    {
      "product_id": "PRD-009",
      "location_id": "WH-009",
      "forecast_id": "FC-009-M2",
      "demand_date": "2027-03-15",
      "eligible_supply_quantity": "56.000000",
      "allocated_quantity": "56.000000",
      "shortage_quantity": "33.000000",
      "recommended_quantity": "33.000000"
    },
    {
      "product_id": "PRD-008",
      "location_id": "WH-008",
      "forecast_id": "FC-008-M1",
      "demand_date": "2027-03-05",
      "eligible_supply_quantity": "143.000000",
      "allocated_quantity": "88.000000",
      "shortage_quantity": "0.000000",
      "recommended_quantity": "0.000000"
    },
    {
      "product_id": "PRD-009",
      "location_id": "WH-009",
      "forecast_id": "FC-009-M1",
      "demand_date": "2027-03-05",
      "eligible_supply_quantity": "145.000000",
      "allocated_quantity": "89.000000",
      "shortage_quantity": "0.000000",
      "recommended_quantity": "0.000000"
    }
  ]
}
```

## Q069 · S07 · complex

对 PRD-007 固定业务日2月28日，比较知识截止2月28日及3月5日的三月计划，展示稍后可知的计划供给如何改变缺口。

```json
{
  "rows": [
    {
      "knowledge_date": "2027-02-28",
      "forecast_id": "FC-007-M3",
      "demand_date": "2027-03-31",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "87.000000",
      "recommended_quantity": "87.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "forecast_id": "FC-007-M3",
      "demand_date": "2027-03-31",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "87.000000",
      "recommended_quantity": "87.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "forecast_id": "FC-007-M2",
      "demand_date": "2027-03-15",
      "eligible_supply_quantity": "30.000000",
      "allocated_quantity": "30.000000",
      "shortage_quantity": "57.000000",
      "recommended_quantity": "57.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "forecast_id": "FC-007-M2",
      "demand_date": "2027-03-15",
      "eligible_supply_quantity": "58.000000",
      "allocated_quantity": "58.000000",
      "shortage_quantity": "29.000000",
      "recommended_quantity": "29.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "forecast_id": "FC-007-M1",
      "demand_date": "2027-03-05",
      "eligible_supply_quantity": "117.000000",
      "allocated_quantity": "87.000000",
      "shortage_quantity": "0.000000",
      "recommended_quantity": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "forecast_id": "FC-007-M1",
      "demand_date": "2027-03-05",
      "eligible_supply_quantity": "145.000000",
      "allocated_quantity": "87.000000",
      "shortage_quantity": "0.000000",
      "recommended_quantity": "0.000000"
    }
  ]
}
```

## Q070 · S07 · complex

对 PRD-045，期初库存不可信时三月建议应保持未知，不能静默以零期初量规划。

```json
{
  "rows": [
    {
      "forecast_id": "FC-045-M3",
      "demand_date": "2027-03-31",
      "demand_quantity": "80.000000",
      "eligible_supply_quantity": "0.000000",
      "allocated_quantity": "0.000000",
      "shortage_quantity": "80.000000",
      "recommended_quantity": "80.000000"
    },
    {
      "forecast_id": "FC-045-M2",
      "demand_date": "2027-03-15",
      "demand_quantity": "80.000000",
      "eligible_supply_quantity": "57.000000",
      "allocated_quantity": "57.000000",
      "shortage_quantity": "23.000000",
      "recommended_quantity": "23.000000"
    },
    {
      "forecast_id": "FC-045-M1",
      "demand_date": "2027-03-05",
      "demand_quantity": "80.000000",
      "eligible_supply_quantity": "137.000000",
      "allocated_quantity": "80.000000",
      "shortage_quantity": "0.000000",
      "recommended_quantity": "0.000000"
    }
  ]
}
```

## Q071 · S08 · basic

REC-001 的根批次、公告日期、原因和状态是什么？

```json
{
  "rows": [
    {
      "recall_id": "REC-001",
      "root_lot_id": "LOT-001-B",
      "announced_date": "2027-02-27",
      "reason": "供应商包装密封缺陷",
      "status_code": "open"
    }
  ]
}
```

## Q072 · S08 · basic

列出 REC-002 含下游的受影响批次及各批次商品。

```json
{
  "rows": [
    {
      "lot_id": "LOT-002-D",
      "product_id": "PRD-002",
      "expiry_date": "2027-03-05"
    },
    {
      "lot_id": "LOT-002-B",
      "product_id": "PRD-002",
      "expiry_date": "2027-03-10"
    }
  ]
}
```

## Q073 · S08 · medium

对 REC-003，分商品地点列出受影响在库和在途数量。

```json
{
  "rows": [
    {
      "recall_id": "REC-003",
      "product_id": "PRD-003",
      "location_id": "STORE-003",
      "affected_lot_ids": [
        "LOT-003-B",
        "LOT-003-D"
      ],
      "on_hand": "53.000000",
      "in_transit": "0.000000"
    },
    {
      "recall_id": "REC-003",
      "product_id": "PRD-003",
      "location_id": "WH-003",
      "affected_lot_ids": [
        "LOT-003-B",
        "LOT-003-D"
      ],
      "on_hand": "156.000000",
      "in_transit": "0.000000"
    }
  ]
}
```

## Q074 · S08 · medium

对 REC-004，按地点分别列出受影响净售出量和退货量。

```json
{
  "rows": [
    {
      "product_id": "PRD-004",
      "location_id": "STORE-004",
      "sold": "29.000000",
      "returned": "3.000000"
    },
    {
      "product_id": "PRD-004",
      "location_id": "WH-004",
      "sold": "0.000000",
      "returned": "0.000000"
    }
  ]
}
```

## Q075 · S08 · medium

REC-005 哪些目的地点仍有受影响在途货？

```json
{
  "rows": [
    {
      "product_id": "PRD-005",
      "location_id": "STORE-005",
      "affected_lot_ids": [
        "LOT-005-B",
        "LOT-005-D"
      ],
      "in_transit": "5.000000"
    }
  ]
}
```

## Q076 · S08 · medium

列出 REC-006 影响的订单标识，包含已售订单及受影响批次的未结预留订单。

```json
{
  "rows": [
    {
      "product_id": "PRD-006",
      "location_id": "STORE-006",
      "affected_order_ids": [
        "ORD-006-H"
      ]
    },
    {
      "product_id": "PRD-006",
      "location_id": "WH-006",
      "affected_order_ids": []
    }
  ]
}
```

## Q077 · S08 · complex

对 REC-007 勾稽实物在库、在途、净售出与退货，退货不能重复加总。

```json
{
  "rows": [
    {
      "product_id": "PRD-007",
      "location_id": "WH-007",
      "on_hand": "159.000000",
      "in_transit": "0.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "controllable_quantity": "159.000000"
    },
    {
      "product_id": "PRD-007",
      "location_id": "STORE-007",
      "on_hand": "51.000000",
      "in_transit": "0.000000",
      "sold": "29.000000",
      "returned": "3.000000",
      "controllable_quantity": "51.000000"
    }
  ]
}
```

## Q078 · S08 · complex

对 REC-048 沿全部下游转换追踪，不同商品分行，列出受影响批次和订单标识。

```json
{
  "rows": [
    {
      "product_id": "PRD-047",
      "location_id": "STORE-022",
      "unit": "件",
      "affected_lot_ids": [
        "LOT-047-D"
      ],
      "affected_order_ids": [
        "ORD-047-H"
      ],
      "on_hand": "23.000000",
      "in_transit": "0.000000"
    },
    {
      "product_id": "PRD-047",
      "location_id": "WH-022",
      "unit": "件",
      "affected_lot_ids": [
        "LOT-047-D"
      ],
      "affected_order_ids": [],
      "on_hand": "66.000000",
      "in_transit": "0.000000"
    },
    {
      "product_id": "PRD-048",
      "location_id": "STORE-023",
      "unit": "件",
      "affected_lot_ids": [
        "LOT-048-B",
        "LOT-048-D"
      ],
      "affected_order_ids": [
        "ORD-048-H"
      ],
      "on_hand": "53.000000",
      "in_transit": "0.000000"
    },
    {
      "product_id": "PRD-048",
      "location_id": "WH-023",
      "unit": "件",
      "affected_lot_ids": [
        "LOT-048-B",
        "LOT-048-D"
      ],
      "affected_order_ids": [],
      "on_hand": "151.000000",
      "in_transit": "0.000000"
    }
  ]
}
```

## Q079 · S08 · complex

对 REC-043，列出受影响批次及控制覆盖率；不能因不属于下游的同商品兄弟批次有冲突事件，就把受影响范围也判为未知。

```json
{
  "rows": [
    {
      "product_id": "PRD-043",
      "location_id": "WH-018",
      "affected_lot_ids": [
        "LOT-043-B",
        "LOT-043-D"
      ],
      "on_hand": "160.000000",
      "in_transit": "0.000000",
      "controllable_quantity": "160.000000",
      "coverage_ratio": "0.125000"
    },
    {
      "product_id": "PRD-043",
      "location_id": "STORE-018",
      "affected_lot_ids": [
        "LOT-043-B",
        "LOT-043-D"
      ],
      "on_hand": "51.000000",
      "in_transit": "0.000000",
      "controllable_quantity": "51.000000",
      "coverage_ratio": "0.058824"
    }
  ]
}
```

## Q080 · S08 · complex

截至2月28日仅使用2月20日可知信息评估 REC-010，不能假定稍后召回公告当时已知。

```json
{
  "rows": []
}
```

## Q081 · S09 · basic

对 REC-011，分商品地点列出已实物控制数量。

```json
{
  "rows": [
    {
      "product_id": "PRD-011",
      "location_id": "WH-011",
      "controlled_quantity": "20.000000"
    },
    {
      "product_id": "PRD-011",
      "location_id": "STORE-011",
      "controlled_quantity": "3.000000"
    }
  ]
}
```

## Q082 · S09 · basic

对 REC-012，列出各地点尚待控制的数量缺口。

```json
{
  "rows": [
    {
      "product_id": "PRD-012",
      "location_id": "STORE-012",
      "pending_control_quantity": "50.000000"
    },
    {
      "product_id": "PRD-012",
      "location_id": "WH-012",
      "pending_control_quantity": "135.000000"
    }
  ]
}
```

## Q083 · S09 · medium

对 REC-013，以在库加在途为分母计算控制覆盖率，排除尚未退回的已售货物。

```json
{
  "rows": [
    {
      "product_id": "PRD-013",
      "location_id": "WH-013",
      "controlled_quantity": "83.000000",
      "controllable_quantity": "157.000000",
      "coverage_ratio": "0.528662"
    },
    {
      "product_id": "PRD-013",
      "location_id": "STORE-013",
      "controlled_quantity": "27.000000",
      "controllable_quantity": "51.000000",
      "coverage_ratio": "0.529412"
    }
  ]
}
```

## Q084 · S09 · medium

REC-014 哪些地点仍需控制行动？计入在途量，不能因已发召回就视为在途已受控。

```json
{
  "rows": [
    {
      "product_id": "PRD-014",
      "location_id": "WH-014",
      "on_hand": "159.000000",
      "in_transit": "0.000000",
      "controlled_quantity": "20.000000",
      "pending_control_quantity": "139.000000"
    },
    {
      "product_id": "PRD-014",
      "location_id": "STORE-014",
      "on_hand": "49.000000",
      "in_transit": "0.000000",
      "controlled_quantity": "3.000000",
      "pending_control_quantity": "46.000000"
    }
  ]
}
```

## Q085 · S09 · medium

REC-050 已关闭。是否仍应产生有效召回评估？仅返回有效评估行，不能编造新的未结召回。

```json
{
  "rows": []
}
```

## Q086 · S09 · medium

对 REC-016，列示退货如何计入在库及实物控制，覆盖率分母不能再加一次退货。

```json
{
  "rows": [
    {
      "product_id": "PRD-016",
      "location_id": "WH-016",
      "returned": "0.000000",
      "on_hand": "158.000000",
      "in_transit": "0.000000",
      "controlled_quantity": "20.000000",
      "controllable_quantity": "158.000000",
      "coverage_ratio": "0.126582"
    },
    {
      "product_id": "PRD-016",
      "location_id": "STORE-016",
      "returned": "3.000000",
      "on_hand": "51.000000",
      "in_transit": "0.000000",
      "controlled_quantity": "3.000000",
      "controllable_quantity": "51.000000",
      "coverage_ratio": "0.058824"
    }
  ]
}
```

## Q087 · S09 · complex

对 REC-017 查询已记录控制覆盖率指标，再跨地点独立汇总实物控制量和可控制量；比较商品级记录与重算比例，不能平均地点百分比。

```json
{
  "rows": [
    {
      "snapshot_id": "RC-017-PRD-017",
      "product_id": "PRD-017",
      "unit": "件",
      "controlled_quantity": "23.000000",
      "controllable_quantity": "209.000000",
      "recorded_ratio": "0.110048",
      "reconstructed_ratio": "0.110048",
      "difference": "0.000000"
    }
  ]
}
```

## Q088 · S09 · complex

考虑有效召回限制后，对 PRD-018 未结订单联合分配，列示缺口及来源批次。

```json
{
  "rows": [
    {
      "line_id": "LINE-018-A",
      "order_id": "ORD-018-A",
      "requested_quantity": "112.000000",
      "allocated_quantity": "112.000000",
      "shortage_quantity": "0.000000",
      "allocations": [
        {
          "lot_id": "LOT-018-C",
          "quantity": "112.000000"
        }
      ]
    },
    {
      "line_id": "LINE-018-B",
      "order_id": "ORD-018-B",
      "requested_quantity": "103.000000",
      "allocated_quantity": "35.000000",
      "shortage_quantity": "68.000000",
      "allocations": [
        {
          "lot_id": "LOT-018-C",
          "quantity": "35.000000"
        }
      ]
    }
  ]
}
```

## Q089 · S09 · complex

对 REC-045，调拨来源不完整时控制缺口和比例保持未知，不能把未知货量判为已完全控制。

```json
{
  "rows": [
    {
      "product_id": "PRD-045",
      "location_id": "WH-020",
      "on_hand": "150.000000",
      "in_transit": "0.000000",
      "controlled_quantity": "20.000000",
      "controllable_quantity": "150.000000",
      "pending_control_quantity": "130.000000",
      "coverage_ratio": "0.133333"
    },
    {
      "product_id": "PRD-045",
      "location_id": "STORE-020",
      "on_hand": null,
      "in_transit": null,
      "controlled_quantity": null,
      "controllable_quantity": null,
      "pending_control_quantity": null,
      "coverage_ratio": null
    }
  ]
}
```

## Q090 · S09 · complex

对 REC-020，分地点列出已控制货、在途敞口、净售出和待控制缺口，并保留影响订单便于处置。

```json
{
  "rows": [
    {
      "product_id": "PRD-020",
      "location_id": "STORE-020",
      "affected_order_ids": [
        "ORD-020-H"
      ],
      "controlled_quantity": "3.000000",
      "in_transit": "5.000000",
      "sold": "31.000000",
      "pending_control_quantity": "46.000000",
      "coverage_ratio": "0.061224"
    },
    {
      "product_id": "PRD-020",
      "location_id": "WH-020",
      "affected_order_ids": [],
      "controlled_quantity": "20.000000",
      "in_transit": "0.000000",
      "sold": "0.000000",
      "pending_control_quantity": "132.000000",
      "coverage_ratio": "0.131579"
    }
  ]
}
```

## Q091 · S10 · basic

列出完全重复的语义事件标识及其物理行数，不能视作不同业务事件。

```json
{
  "rows": [
    {
      "event_id": "EV-00875",
      "physical_row_count": 2,
      "payload_variant_count": 1
    }
  ]
}
```

## Q092 · S10 · basic

列出可见撤销事件及其目标事件标识。

```json
{
  "rows": [
    {
      "event_id": "EV-00922",
      "reversal_of": "EV-00921",
      "event_date": "2027-02-27",
      "recorded_date": "2027-02-27"
    }
  ]
}
```

## Q093 · S10 · basic

列出业务日期不晚于2月28日、但2月28日后且3月5日前才记录的实际事件。

```json
{
  "rows": [
    {
      "event_id": "EV-00855",
      "lot_id": "LOT-041-C",
      "event_date": "2027-02-26",
      "recorded_date": "2027-03-02"
    }
  ]
}
```

## Q094 · S10 · medium

对 PRD-042，事件去重后重建库存，按批次地点返回实际数量。

```json
{
  "rows": [
    {
      "lot_id": "LOT-042-A",
      "location_id": "STORE-017",
      "on_hand": "25.000000",
      "sold": "15.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-042-B",
      "location_id": "STORE-017",
      "on_hand": "28.000000",
      "sold": "12.000000",
      "returned": "3.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-042-D",
      "location_id": "STORE-017",
      "on_hand": "25.000000",
      "sold": "15.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-042-A",
      "location_id": "WH-017",
      "on_hand": "80.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-042-B",
      "location_id": "WH-017",
      "on_hand": "96.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-042-D",
      "location_id": "WH-017",
      "on_hand": "62.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-042-C",
      "location_id": "WH-017",
      "on_hand": "149.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "119.000000"
    },
    {
      "lot_id": "LOT-042-C",
      "location_id": "STORE-017",
      "on_hand": "28.000000",
      "sold": "12.000000",
      "returned": "3.000000",
      "available": "23.000000"
    }
  ]
}
```

## Q095 · S10 · medium

对 PRD-044，撤销目标事件后重建库存，不能把撤销当作新的数量流转相加。

```json
{
  "rows": [
    {
      "lot_id": "LOT-044-A",
      "location_id": "STORE-019",
      "on_hand": "23.000000",
      "sold": "17.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-B",
      "location_id": "STORE-019",
      "on_hand": "26.000000",
      "sold": "14.000000",
      "returned": "3.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-C",
      "location_id": "STORE-019",
      "on_hand": "26.000000",
      "sold": "14.000000",
      "returned": "3.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-D",
      "location_id": "STORE-019",
      "on_hand": "23.000000",
      "sold": "17.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-A",
      "location_id": "WH-019",
      "on_hand": "82.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-B",
      "location_id": "WH-019",
      "on_hand": "98.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-C",
      "location_id": "WH-019",
      "on_hand": "140.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    },
    {
      "lot_id": "LOT-044-D",
      "location_id": "WH-019",
      "on_hand": "64.000000",
      "sold": "0.000000",
      "returned": "0.000000",
      "available": "0.000000"
    }
  ]
}
```

## Q096 · S10 · medium

对 PRD-041 固定2月28日业务日期，比较知识截止2月28日和3月5日的库存以识别迟报影响。

```json
{
  "rows": [
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-A",
      "location_id": "STORE-016",
      "on_hand": "23.000000",
      "sold": "17.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-B",
      "location_id": "STORE-016",
      "on_hand": "26.000000",
      "sold": "14.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-D",
      "location_id": "STORE-016",
      "on_hand": "23.000000",
      "sold": "17.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-A",
      "location_id": "WH-016",
      "on_hand": "86.000000",
      "sold": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-B",
      "location_id": "WH-016",
      "on_hand": "95.000000",
      "sold": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-D",
      "location_id": "WH-016",
      "on_hand": "61.000000",
      "sold": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-A",
      "location_id": "STORE-016",
      "on_hand": "23.000000",
      "sold": "17.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-B",
      "location_id": "STORE-016",
      "on_hand": "26.000000",
      "sold": "14.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-D",
      "location_id": "STORE-016",
      "on_hand": "23.000000",
      "sold": "17.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-A",
      "location_id": "WH-016",
      "on_hand": "86.000000",
      "sold": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-B",
      "location_id": "WH-016",
      "on_hand": "95.000000",
      "sold": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-D",
      "location_id": "WH-016",
      "on_hand": "61.000000",
      "sold": "0.000000",
      "available": "0.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-C",
      "location_id": "WH-016",
      "on_hand": "148.000000",
      "sold": "0.000000",
      "available": "118.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-C",
      "location_id": "WH-016",
      "on_hand": "148.000000",
      "sold": "0.000000",
      "available": "118.000000"
    },
    {
      "knowledge_date": "2027-03-05",
      "lot_id": "LOT-041-C",
      "location_id": "STORE-016",
      "on_hand": "19.000000",
      "sold": "21.000000",
      "available": "14.000000"
    },
    {
      "knowledge_date": "2027-02-28",
      "lot_id": "LOT-041-C",
      "location_id": "STORE-016",
      "on_hand": "26.000000",
      "sold": "14.000000",
      "available": "21.000000"
    }
  ]
}
```

## Q097 · S10 · medium

列出冲突语义事件及业务载荷变体数，不能和完全相同的重复混淆。

```json
{
  "rows": [
    {
      "event_id": "EV-00897",
      "physical_row_count": 2,
      "payload_variant_count": 2
    }
  ]
}
```

## Q098 · S10 · medium

对 PRD-043，仅列出因事件载荷冲突而不可信的库存行，数量字段保留为空。

```json
{
  "rows": [
    {
      "lot_id": "LOT-043-C",
      "location_id": "STORE-018",
      "on_hand": null,
      "available": null,
      "quality_status": "unknown"
    }
  ]
}
```

## Q099 · S10 · complex

对比 PRD-045 的调拨来源缺失与 PRD-046 的源负库存，列出全部受影响批次地点及未知数量，不得漏掉任一商品。

```json
{
  "rows": [
    {
      "product_id": "PRD-045",
      "lot_id": "LOT-045-C",
      "location_id": "STORE-020",
      "on_hand": null,
      "in_transit": null,
      "available": null,
      "quality_status": "unknown"
    },
    {
      "product_id": "PRD-045",
      "lot_id": "LOT-045-D",
      "location_id": "STORE-020",
      "on_hand": null,
      "in_transit": null,
      "available": null,
      "quality_status": "unknown"
    },
    {
      "product_id": "PRD-046",
      "lot_id": "LOT-046-C",
      "location_id": "STORE-021",
      "on_hand": null,
      "in_transit": null,
      "available": null,
      "quality_status": "unknown"
    }
  ]
}
```

## Q100 · S10 · complex

审计全部源表的外键缺失、单位不合法和同日事件序号冲突，返回缺陷类型与记录标识；语义事件重复不能误判成物理主键重复。

```json
{
  "rows": []
}
```

