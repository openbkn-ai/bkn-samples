# Metric queries and acceptance

The sample provides 11 standard Object Metrics V1 object-set aggregates. Create drafts, validate them, then publish. Every query pins `metric_id` and `version`. Definitions are in `metrics-create.json`; native V1 queries are in `metrics-query-examples.json`.

Object-set aggregates summarize collections and are not object-instance logical properties. `power_layer.py verify-ownership` checks the published version, owner object type and existence of that object type. It does not bind collection totals as instance properties. Function logical properties are unchanged.

```sh
python tools/power_layer.py all --kn-id supply_ontology_en
```

Open forecast queries explicitly filter the published `closestatus_title` analysis dimension. Inventory warehouse scopes are query inputs. All filters use standard V1 `filter` trees and typed property references.

`metrics-analysis-examples.json` retains complete calendar months and month comparisons: query each complete Asia/Shanghai month using inclusive lower and exclusive upper boundaries, then calculate adjacent-month differences. Proportions are calculated from actual complete grouped results. Acceptance checks every group, month and CSV baseline; missing, partial or empty responses fail. These client calculations are not extra published metrics.

```sh
python tools/power_layer.py verify --kn-id supply_ontology_en --query-file tools/assets/metrics-analysis-examples.json
```
