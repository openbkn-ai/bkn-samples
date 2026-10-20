# Independent reference answers

Evaluator material. Never supplied to formal answerers or installed runtime.

## Q001 · S01 · basic

What are PRD-001’s name, unit and packaging multiplier?

```json
{
  "rows": [
    {
      "product_id": "PRD-001",
      "name": "Original Yogurt 250 g",
      "unit": "ea",
      "pack_multiplier": "6"
    }
  ]
}
```

## Q002 · S01 · basic

Who supplies PRD-002? Return supplier identity and role.

```json
{
  "rows": [
    {
      "product_id": "PRD-002",
      "organization_id": "ORG-002",
      "name": "Hangzhou Harvest Foods Ltd",
      "role_code": "supplier"
    }
  ]
}
```

## Q003 · S01 · basic

Who owns warehouse WH-001 and what type of location is it?

```json
{
  "rows": [
    {
      "location_id": "WH-001",
      "name": "Hangzhou Central Distribution Center",
      "location_type_code": "warehouse",
      "organization_id": "ORG-026",
      "organization_name": "Hangzhou Greenfield Retail Ltd"
    }
  ]
}
```

## Q004 · S01 · basic

What is STORE-002’s operating organization?

```json
{
  "rows": [
    {
      "location_id": "STORE-002",
      "name": "Hangzhou East Lake Grocery",
      "organization_id": "ORG-027",
      "organization_name": "Hangzhou Harvest Retail Ltd"
    }
  ]
}
```

## Q005 · S01 · basic

What are LOT-003-A’s product, production date and expiry date?

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

What minimum shelf life is declared for PRD-004?

```json
{
  "rows": [
    {
      "product_id": "PRD-004",
      "min_shelf_days": "3",
      "unit": "ea"
    }
  ]
}
```

## Q007 · S01 · medium

Convert three cases of each of PRD-001, PRD-002 and PRD-003 to base quantities, keeping products separate.

```json
{
  "rows": [
    {
      "product_id": "PRD-001",
      "unit": "ea",
      "base_quantity": 18
    },
    {
      "product_id": "PRD-003",
      "unit": "ea",
      "base_quantity": 18
    },
    {
      "product_id": "PRD-002",
      "unit": "ea",
      "base_quantity": 36
    }
  ]
}
```

## Q008 · S01 · medium

List all lots of PRD-005 with supplier names and expiry dates.

```json
{
  "rows": [
    {
      "lot_id": "LOT-005-A",
      "product_id": "PRD-005",
      "supplier_name": "Hangzhou Riverbend Foods Ltd",
      "expiry_date": "2027-02-20"
    },
    {
      "lot_id": "LOT-005-D",
      "product_id": "PRD-005",
      "supplier_name": "Hangzhou Riverbend Foods Ltd",
      "expiry_date": "2027-03-05"
    },
    {
      "lot_id": "LOT-005-B",
      "product_id": "PRD-005",
      "supplier_name": "Hangzhou Riverbend Foods Ltd",
      "expiry_date": "2027-03-10"
    },
    {
      "lot_id": "LOT-005-C",
      "product_id": "PRD-005",
      "supplier_name": "Hangzhou Riverbend Foods Ltd",
      "expiry_date": "2027-03-31"
    },
    {
      "lot_id": "LOT-005-P",
      "product_id": "PRD-005",
      "supplier_name": "Hangzhou Riverbend Foods Ltd",
      "expiry_date": "2027-03-31"
    }
  ]
}
```

## Q009 · S01 · medium

Count products assigned to each supplier-role organization; include suppliers with no product and do not count locations as suppliers.

```json
{
  "rows": [
    {
      "organization_id": "ORG-001",
      "name": "Hangzhou Greenfield Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-002",
      "name": "Hangzhou Harvest Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-005",
      "name": "Hangzhou Riverbend Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-003",
      "name": "Hangzhou Springwell Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-004",
      "name": "Hangzhou Sunridge Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-011",
      "name": "Nanjing Greenfield Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-012",
      "name": "Nanjing Harvest Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-015",
      "name": "Nanjing Riverbend Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-013",
      "name": "Nanjing Springwell Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-014",
      "name": "Nanjing Sunridge Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-016",
      "name": "Ningbo Greenfield Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-017",
      "name": "Ningbo Harvest Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-020",
      "name": "Ningbo Riverbend Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-018",
      "name": "Ningbo Springwell Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-019",
      "name": "Ningbo Sunridge Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-006",
      "name": "Suzhou Greenfield Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-007",
      "name": "Suzhou Harvest Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-010",
      "name": "Suzhou Riverbend Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-008",
      "name": "Suzhou Springwell Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-009",
      "name": "Suzhou Sunridge Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-021",
      "name": "Wuxi Greenfield Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-022",
      "name": "Wuxi Harvest Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-025",
      "name": "Wuxi Riverbend Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-023",
      "name": "Wuxi Springwell Foods Ltd",
      "product_count": 2
    },
    {
      "organization_id": "ORG-024",
      "name": "Wuxi Sunridge Foods Ltd",
      "product_count": 2
    }
  ]
}
```

## Q010 · S01 · complex

Audit every lot-to-product-to-supplier path and list only missing or wrongly assigned supplier roles.

```json
{
  "rows": []
}
```

## Q011 · S02 · basic

List received actual events for LOT-001-A.

```json
{
  "rows": [
    {
      "movement_id": "MOV-00001",
      "event_id": "EV-00001",
      "event_date": "2026-11-03",
      "destination_location_id": "WH-001",
      "quantity": "121",
      "unit": "ea"
    }
  ]
}
```

## Q012 · S02 · basic

List inspections of LOT-002-A known by the observation date.

```json
{
  "rows": [
    {
      "inspection_id": "QC-002-A",
      "lot_id": "LOT-002-A",
      "inspection_date": "2026-11-03",
      "result_code": "passed",
      "reason": "Receiving test passed"
    }
  ]
}
```

## Q013 · S02 · basic

For PRD-003 at WH-003, list on-hand quantities and current inspection codes by lot.

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

List active physical holds for PRD-004 lots at the observation date.

```json
{
  "rows": [
    {
      "hold_id": "HOLD-004-Q",
      "lot_id": "LOT-004-B",
      "location_id": "WH-004",
      "quantity": "20",
      "reason": "Recall precautionary hold"
    },
    {
      "hold_id": "HOLD-004-R",
      "lot_id": "LOT-004-C",
      "location_id": "STORE-004",
      "quantity": "5",
      "reason": "Returns and packaging retest"
    }
  ]
}
```

## Q015 · S02 · medium

Which PRD-011 lots have failed or pending inspection, and how much is physically quarantined at each location?

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

Reconcile on-hand, physical quarantine and available quantities for PRD-006, retaining locations with zero available stock.

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

For LOT-007-A, identify the latest visible inspection and the inspected location; do not use a future-known result.

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

Show only PRD-008 lot/location stock rows with returned quantity greater than zero alongside physical quarantine, demonstrating that returns already included in on-hand are not added again.

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

For PRD-009, separate inspection quarantine, recall block and reservations to explain why received stock cannot all be promised.

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

For PRD-010, compare inventory known on February 20 with February 28 at the same February 28 business date. Return both knowledge dates and the full stock split.

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

List direct child links of LOT-001-B visible at the observation date.

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

List direct parents of LOT-002-D visible at the observation date.

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

List PRD-003’s declared lot transformations with input and output quantities; keep each link separate.

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
      "unit": "ea"
    }
  ]
}
```

## Q024 · S03 · medium

Trace the complete connected upstream and downstream component of LOT-004-D, listing each visible link once.

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

List all downstream lots reachable from LOT-005-B, including the root, with product IDs and expiry dates.

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

For LOT-006-B’s connected component, identify same-product split links whose declared input and output quantities differ.

```json
{
  "rows": []
}
```

## Q027 · S03 · medium

List the visible actual event journey of LOT-007-B in ascending business-date and numeric event-sequence order (event ID breaks ties), including both sides of transfers. Return null for absent source/destination locations.

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
      "unit": "ea"
    },
    {
      "event_id": "EV-00146",
      "event_type_code": "consume",
      "source_location_id": "WH-007",
      "destination_location_id": null,
      "event_date": "2027-02-21",
      "event_sequence": "15",
      "quantity": "20",
      "unit": "ea"
    },
    {
      "event_id": "EV-00132",
      "event_type_code": "dispatch",
      "source_location_id": "WH-007",
      "destination_location_id": "STORE-007",
      "event_date": "2027-02-22",
      "event_sequence": "20",
      "quantity": "40",
      "unit": "ea"
    },
    {
      "event_id": "EV-00133",
      "event_type_code": "arrive",
      "source_location_id": null,
      "destination_location_id": "STORE-007",
      "event_date": "2027-02-23",
      "event_sequence": "30",
      "quantity": "40",
      "unit": "ea"
    },
    {
      "event_id": "EV-00134",
      "event_type_code": "sale",
      "source_location_id": "STORE-007",
      "destination_location_id": null,
      "event_date": "2027-02-24",
      "event_sequence": "40",
      "quantity": "16",
      "unit": "ea"
    },
    {
      "event_id": "EV-00135",
      "event_type_code": "return",
      "source_location_id": null,
      "destination_location_id": "STORE-007",
      "event_date": "2027-02-25",
      "event_sequence": "50",
      "quantity": "3",
      "unit": "ea"
    }
  ]
}
```

## Q028 · S03 · complex

For LOT-047-D, trace the complete upstream and downstream undirected connected component of visible lot links, including different products and sibling branches. List every edge once and do not equate input units with output units.

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
      "unit": "ea"
    },
    {
      "link_id": "LINK-047-MULTI",
      "parent_lot_id": "LOT-048-B",
      "child_lot_id": "LOT-047-D",
      "link_type_code": "transform",
      "parent_quantity": "5",
      "child_quantity": "4",
      "unit": "ea"
    },
    {
      "link_id": "LINK-048",
      "parent_lot_id": "LOT-048-B",
      "child_lot_id": "LOT-048-D",
      "link_type_code": "split",
      "parent_quantity": "20",
      "child_quantity": "20",
      "unit": "ea"
    }
  ]
}
```

## Q029 · S03 · complex

For recall REC-012, list all affected descendant lots and each product’s supplier; include indirect descendants exactly once.

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

For LOT-041-B, compare the visible connected links at knowledge cutoffs February 20 and February 28, holding business date February 28 fixed.

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

List PRD-001 inventory by lot and location at February 28.

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

Which PRD-005 lots remain in transit, and toward which destinations?

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

List only PRD-003 lot/location rows whose physical quarantine quantity is greater than zero.

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

For PRD-004, query the recorded available-inventory metric and reconcile it with atomic reconstruction at the same dates; report recorded and reconstructed available quantities and their difference by lot/location.

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

Show only PRD-005 stock that is on hand but unavailable, with all blocking quantity categories.

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

Compare PRD-006 stock at February 20 and February 28, using knowledge available on each date.

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

For PRD-007 at WH-007 and STORE-007, show cumulative sold, returned, on-hand and in-transit quantities without double counting transfer legs.

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

For PRD-045, show stock balances and quality status after an arrival with missing dispatch; preserve unknown values.

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

For PRD-046, identify unreliable stock rows, keeping null balances rather than converting negative source balances to zero.

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

For PRD-008 and PRD-009, return per-product stock totals while excluding no blocked rows; if any row is unknown, that product total must be null.

```json
{
  "rows": [
    {
      "product_id": "PRD-008",
      "unit": "ea",
      "on_hand": "488.000000",
      "in_transit": "0.000000",
      "quarantined": "28.000000",
      "recall_blocked": "187.000000",
      "reserved": "30.000000",
      "available": "139.000000"
    },
    {
      "product_id": "PRD-009",
      "unit": "ea",
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

Which PRD-010 lots are already expired on February 28?

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

Which PRD-011 lots expire within 14 days, including the observation date?

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

What is PRD-012’s shelf-life requirement and each lot’s expiry date?

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

List PRD-013 available lots at WH-013 in FEFO order, after quarantine and reservations.

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

Which PRD-014 near-expiry stock is physically on hand but blocked for another reason?

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

As of March 10 with knowledge cutoff February 28, report PRD-015 actual stock after expiry; do not credit planned receipts.

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

For PRD-016, list stock that will satisfy a March 5 shipment with seven remaining shelf days; keep only positive available quantities and use FEFO.

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

For PRD-017 open orders, allocate stock jointly using each line’s actual due date and shelf-life requirement.

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

For PRD-018, plan March demand after stock expires and exclude planned receipts whose lots do not satisfy shelf life.

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

For PRD-049 and PRD-050, list near-expiry available stock by product and location; do not mix units or include actively recalled stock as available, and distinguish a closed recall.

```json
{
  "rows": [
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-B",
      "location_id": "STORE-025",
      "unit": "ea",
      "expiry_date": "2027-03-10",
      "available": "18.000000"
    },
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-D",
      "location_id": "STORE-025",
      "unit": "ea",
      "expiry_date": "2027-03-05",
      "available": "23.000000"
    },
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-D",
      "location_id": "WH-025",
      "unit": "ea",
      "expiry_date": "2027-03-05",
      "available": "60.000000"
    },
    {
      "product_id": "PRD-050",
      "lot_id": "LOT-050-B",
      "location_id": "WH-025",
      "unit": "ea",
      "expiry_date": "2027-03-10",
      "available": "75.000000"
    }
  ]
}
```

## Q051 · S06 · basic

List open ORD-001-A order lines and their requested quantities and shelf-life requirements.

```json
{
  "rows": [
    {
      "line_id": "LINE-001-A",
      "order_id": "ORD-001-A",
      "product_id": "PRD-001",
      "quantity": "111",
      "unit": "ea",
      "min_shelf_days": "3",
      "due_date": "2027-03-02",
      "priority": "1"
    }
  ]
}
```

## Q052 · S06 · basic

List reservations for ORD-002-A that are active at the observation date.

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

Can ORD-003-A be filled? Respect its own reservations, other orders’ reservations, expiry and quality.

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

Jointly allocate PRD-004’s two competing orders; report exact lot allocations.

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

Which PRD-005 open order lines have a shortage after FEFO allocation?

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

Allocate PRD-049’s open backlog, including overdue ORD-049-A. Do not silently discard the overdue order; assess shelf life at the later of today and its due date.

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

For PRD-007, allocate all competing lines jointly and reconcile total demand, allocation and shortage without spending stock twice.

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

If only ORD-008-B is investigated, keep excluded orders’ reservations unavailable and allocate B using its own reservation exactly once.

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

For PRD-043, report allocation uncertainty caused by conflicting source events instead of promising zero or invented stock.

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

Allocate PRD-009 and PRD-010 independently by product but jointly across each product’s orders, respecting recall, quality, due dates and FEFO.

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

List March planned forecasts for PRD-001 known by February 28.

```json
{
  "rows": [
    {
      "forecast_id": "FC-001-M1",
      "product_id": "PRD-001",
      "location_id": "WH-001",
      "demand_date": "2027-03-05",
      "quantity": "81",
      "unit": "ea",
      "known_date": "2027-02-26"
    },
    {
      "forecast_id": "FC-001-M2",
      "product_id": "PRD-001",
      "location_id": "WH-001",
      "demand_date": "2027-03-15",
      "quantity": "81",
      "unit": "ea",
      "known_date": "2027-02-26"
    },
    {
      "forecast_id": "FC-001-M3",
      "product_id": "PRD-001",
      "location_id": "WH-001",
      "demand_date": "2027-03-31",
      "quantity": "81",
      "unit": "ea",
      "known_date": "2027-02-26"
    }
  ]
}
```

## Q062 · S07 · basic

List PRD-002’s planned incoming receipts known at February 28 through March 31.

```json
{
  "rows": [
    {
      "event_id": "EV-00040",
      "lot_id": "LOT-002-P",
      "destination_location_id": "WH-002",
      "event_date": "2027-03-05",
      "quantity": "27",
      "unit": "ea"
    }
  ]
}
```

## Q063 · S07 · medium

Plan PRD-003’s March replenishment: show each forecast, eligible supply, allocation, shortage and recommended quantity.

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

Which PRD-004 March forecasts have shortages after qualified planned receipts?

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

Plan PRD-005 only through March 15; exclude later demand and receipts not yet eligible by each demand date.

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

Summarize PRD-006 March demand and replenishment need by product, preserving an unknown total if any forecast allocation is unknown.

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

For PRD-007, use stock once across sequential March forecasts, age each lot and apply supply before the day’s demand.

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

For PRD-008 and PRD-009, report March plans separately by product/location, including recall or inspection exclusions.

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

For PRD-007, compare the March plan at knowledge cutoffs February 28 and March 5, holding the February 28 business date fixed; show how later-known planned supply changes shortages.

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

For PRD-045, preserve unknown March recommendations when opening stock is unreliable; do not silently use zero opening stock.

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

What is REC-001’s root lot, announcement date, reason and status?

```json
{
  "rows": [
    {
      "recall_id": "REC-001",
      "root_lot_id": "LOT-001-B",
      "announced_date": "2027-02-27",
      "reason": "Supplier seal integrity defect",
      "status_code": "open"
    }
  ]
}
```

## Q072 · S08 · basic

List affected lots of REC-002, including descendants and each lot’s product.

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

For REC-003, show affected stock and in-transit quantities by product and location.

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

For REC-004, list net sold and returned affected quantities separately at each location.

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

Which locations have affected stock still in transit under REC-005?

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

List customer order IDs affected by REC-006, including fulfilled sales and open reservations of affected lots.

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

For REC-007, reconcile physical stock, transit, net sold and returns without counting returned quantities twice.

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

For REC-048, retain different products in separate rows while following every downstream conversion; list affected lots and order IDs.

```json
{
  "rows": [
    {
      "product_id": "PRD-047",
      "location_id": "STORE-022",
      "unit": "ea",
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
      "unit": "ea",
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
      "unit": "ea",
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
      "unit": "ea",
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

For REC-043, show affected lots and control coverage; do not invalidate descendants merely because a non-descendant sibling lot has a conflicting event.

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

Assess REC-010 as of February 28 using only knowledge available February 20; do not assume a later recall announcement was already known.

```json
{
  "rows": []
}
```

## Q081 · S09 · basic

For REC-011, report physically controlled quantities by product and location.

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

For REC-012, report the remaining control gap at each location.

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

For REC-013, compute control coverage using on-hand plus transit as the denominator, excluding unreturned sales.

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

Which REC-014 locations still require control action? Include in-transit quantities, which are not controlled merely because a recall exists.

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

REC-050 is closed. Does it still produce an active recall assessment? Return the active assessment rows only; do not fabricate a new open recall.

```json
{
  "rows": []
}
```

## Q086 · S09 · medium

For REC-016, show how returned quantities are included in stock and physical control without adding them twice to the coverage denominator.

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

For REC-017, query the recorded control-coverage metric, then independently aggregate physical control and controllable quantities across locations; compare the product-level recorded and reconstructed ratios, never averaging location percentages.

```json
{
  "rows": [
    {
      "snapshot_id": "RC-017-PRD-017",
      "product_id": "PRD-017",
      "unit": "ea",
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

After active recall restrictions, jointly plan PRD-018’s open order lines and show shortages and source allocations.

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

For REC-045, preserve unknown control gaps and ratios when transfer provenance is incomplete; do not label unknown stock fully controlled.

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

For REC-020, separate each location’s controlled stock, in-transit exposure, net sold and pending action; retain affected orders to support action planning.

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

List exact-duplicate semantic event IDs and their physical row counts, without counting them as distinct business events.

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

List visible reversal events with their target event IDs.

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

List actual events whose business date is no later than February 28 but which were recorded after February 28 and by March 5.

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

For PRD-042, reconstruct inventory after deduplicating events and return the actual quantities by lot/location.

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

For PRD-044, reconstruct inventory after the visible reversal cancels its target, rather than adding the reversal as a new quantity movement.

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

For PRD-041, compare February 28 balances at knowledge cutoffs February 28 and March 5 to isolate late reporting.

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

List conflicting semantic event IDs and all their payload variant counts, separately from identical duplicates.

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

For PRD-043, list only inventory rows rendered unreliable by conflicting event payloads and preserve null quantitative fields.

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

For PRD-045 and PRD-046, contrast missing-transfer provenance with negative source inventory; report every affected lot/location and unknown balances without dropping either product.

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

Audit all source tables for missing foreign keys, invalid units and same-day event sequence ties; report defect type and record ID, without treating declared duplicate event IDs as duplicate physical primary keys.

```json
{
  "rows": []
}
```

