# Backward Plan Test Fixtures

The in-memory fixtures in [test_backward_plan.py](../../test_backward_plan.py) use `build_snapshot(rows)` to construct a `Snapshot`. They do not read CSV files, business evaluation answers or remote services.

## Input records

- Forecast: `id`, `material_number`, `enddate`, `qty`.
- BOM: `bom_material_code`, `material_code`, `parent_material_code`, `bom_level`, `standard_usage` and alternate-position fields.
- Material: `material_code`, `materialattr`, `purchase_fixedleadtime`, `product_fixedleadtime`.
- Inventory: material, warehouse, available quantity and stock status.
- Procurement: material, ordered/received quantities, close status and arrival date.

Material types use `Purchased`, `Subcontracted` and `Manufactured`. Alternate rows use `Alternate`. Dates are explicit; tests pass `today` to avoid dependence on the system clock. Warehouse fixtures include production-scope locations and an excluded quarantine location.

Assertions cover exact forecast identifiers, product/quantity/deadline validation, calendar-day planning, scoped stock, incoming PO evidence, alternate applicability, shared allocation, delayed supply, summary/full-tree output and the 5,000-node limit. Returned nodes retain material, parent, level, usage, requirements, dates, supply and risk evidence.

Keep synthetic inputs and independently calculated assertions in the tests. These fixtures contain no business evaluation answers.
