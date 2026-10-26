# BKN industry modelling specification: energy demand response

Uses native network.bkn, object_types, relation_types and concept_groups. All15operational objects have CSV data and stable primary keys;15relations correspond exactly to explicit foreign keys;3groups separate assets/metering, flexibility/planning and execution/settlement. Dates are date, values are decimal, blank numerics mean unknown rather than zero. All object, relation and property display names are at most40characters.

SAREF4ENER v2.1.1 and directly imported SAREF Core v4.1.1 provide semantic references only. Named source inventories, anonymous-class counts and original licences are in saref-reference. The80explicit upstream class declarations do not imply80populated operational tables. The76namespace-owned classes include control modes outside this sample; no complete OWL inference, universal control-mode coverage or fallback pseudo-object is claimed. The operational mapping is a local extension without owl:equivalentClass; the original selected-mapping.json was not retained in the recovered source. Simplified offers do not implement the complete upstream multi-timeseries FlexOffer; dispatch allocations are not transmitted device-control instructions.

Each device has exactly one nonoverlapping meter. Forecasts, baselines and readings join by device/meter,date,block, not date alone. Resolve revision and knowledge cutoff before aggregation. Cross-event device/site/meter budgets require business functions, not naive graph-edge sums. Recorded capacity/settlement snapshots are not live recalculations.

## Objects and associations

| Object | Primary key | Records | Foreign-key targets |
|---|---|---:|---|
| Customer (`customers`) | customer_id | 50 | — |
| Energy Site (`sites`) | site_id | 50 | customer_id→customers.customer_id |
| Flexible Device (`devices`) | device_id | 150 | site_id→sites.site_id |
| Device Meter (`meters`) | meter_id | 150 | device_id→devices.device_id |
| Response Event (`response_events`) | event_id | 100 | — |
| Load Forecast (`load_forecasts`) | forecast_id | 3751 | device_id→devices.device_id |
| Approved Baseline (`baselines`) | baseline_id | 3752 | device_id→devices.device_id |
| Flexibility Offer (`flexibility_offers`) | offer_id | 3001 | event_id→response_events.event_id, device_id→devices.device_id |
| Device Constraint (`device_constraints`) | constraint_id | 76 | device_id→devices.device_id |
| Dispatch Allocation (`dispatch_allocations`) | allocation_id | 894 | event_id→response_events.event_id, device_id→devices.device_id |
| Execution Receipt (`execution_logs`) | execution_id | 341 | allocation_id→dispatch_allocations.allocation_id |
| Meter Reading (`meter_readings`) | reading_id | 2251 | meter_id→meters.meter_id |
| Settlement Ledger (`settlements`) | settlement_id | 61 | event_id→response_events.event_id |
| Capacity Snapshot (`capacity_snapshots`) | snapshot_id | 100 | event_id→response_events.event_id |
| Settlement Snapshot (`settlement_snapshots`) | snapshot_id | 60 | event_id→response_events.event_id |

[OpenBKN BKN specification](https://github.com/openbkn-ai/bkn-foundry/tree/main/adp/bkn/bkn-backend/server/bkn-specification); object/property/relation/group constraints were checked against SPECIFICATION.md.


This directory omits bkn_spec and uses the specification's permanent2.x compatibility convention, matching existing retail samples rather than3.0-only syntax. Local OpenBKN CLI0.1.5 native validation passed:15objects,15relations,3groups,0errors and0warnings. Syntax validation is not platform installation or metric/function execution acceptance.
