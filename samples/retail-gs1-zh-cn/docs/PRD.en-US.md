# Food distribution, inventory fulfillment and recall PRD

Status: implementation baseline, not an acceptance certificate. Two standalone samples: retail-gs1-en-us and retail-gs1-zh-cn. Data/IDs have equivalent meanings, localized display values and paired question/gold banks.

## Business users and decisions

Quality owners need to identify affected lots, warehouse/store locations, shipments, sold units and orders, then distinguish already controlled stock from still-exposed stock. Distribution planners must allocate shared inventory without selling quarantined, expired or recalled goods. Store managers need usable stock, expiry risks and future replenishment gaps. Every result declares business date, knowledge cutoff, unit, evidence IDs and uncertainty.

The closed loop covers supplier receipt, inspection, warehouse/store movements, transit, sale, return, isolation/release, expiry, reservation, order fulfillment, known demand forecasts, replenishment recommendations, lot transformation and recall. It does not execute procurement, shipment, payment or recall notifications; does not train forecasts, optimize routes or claim compliance certification.

## Time and quantity rules

Data spans 2026-11-01 through 2027-03-31; default observation date 2027-02-28. Explicit business date, knowledge date and actual/planned scope are mandatory. Planned supply never becomes realized inventory. Public presentation is day-only; source event timestamp/sequence, when present, is retained for provenance. Same-day chronology is explicit, never inferred from ID ordering.

Identical semantic event IDs count once; conflicting payloads invalidate affected balances. Visible reversals remove their target effects. Late reports are visible only by knowledge cutoff. Missing essential flows and negative inventory produce issues and unknown balances rather than silent zeroes. Case quantities use the declared product conversion exactly once. Never sum incompatible products or units. Dispatch removes source stock and creates destination transit; arrival converts transit to received stock. Returns are physically quarantined.

Available stock excludes overlapping physical quarantine, active recalls, expired units and valid reservations without double deduction. Inspection failure/pending blocks sale. A line must meet remaining shelf-life at its due date. Shared FEFO allocation sorts expiry/lot after quality and location constraints; orders sort ascending priority, due date, order ID and line ID. A line may consume its own reservation exactly once while reservations for excluded/other lines remain protected. Unused own reservations are released after the line is processed.

Recall traverses declared downstream lot links and keeps direct/indirect evidence. Cross-product transformations establish traceability, not equality between raw-material and finished-product counts; only declared same-unit splits conserve quantities. Sold, returned, on-hand, transit, controlled, pending control and unknown are distinguished; returns already included in on-hand are not added again. Coverage is controlled/controllable only for a complete positive denominator, otherwise null.

Forecasts are explicit synthetic business inputs, not a model-accuracy claim. Replenishment advances through demand dates until 2027-03-31, admits only timely known eligible planned supply, expires stock and consumes FEFO buckets; shortages are read-only suggestions. See business-contract.md for the executable field-level semantics.

## Scenario-to-test agreement

| Scenario | Business question and output | IDs | Basic/medium/complex |
|---|---|---|---|
| S01 Product, organization, location | Units, packaging and responsible suppliers | Q001–010 | 6/3/1 |
| S02 Receipt and inspection | Receipt, inspection and quarantined/available quantities | Q011–020 | 4/4/2 |
| S03 Lot traceability | Upstream/downstream paths, transformations and affected sets | Q021–030 | 3/4/3 |
| S04 Inventory and transit | On-hand, transit, quarantine, reservation, availability, issues | Q031–040 | 3/4/3 |
| S05 Expiry | Near-expiry risks, eligibility and FEFO evidence | Q041–050 | 3/4/3 |
| S06 Order fulfillment | Shared-stock allocations, line shortages and reasons | Q051–060 | 2/4/4 |
| S07 Future replenishment | Known supply/demand, expiry and shortages through March | Q061–070 | 2/4/4 |
| S08 Recall reach | Affected stock, locations, orders, sales, returns and unknowns | Q071–080 | 2/4/4 |
| S09 Recall action | Physical control, remaining exposure and qualified coverage | Q081–090 | 2/4/4 |
| S10 Data trust | Duplicate/conflict/reversal/late-report effects and cutoff changes | Q091–100 | 3/5/2 |

Exactly 100 questions per language, 30 basic, 40 medium, 30 complex. Every question has a scenario ID, scope, output contract and evidence. Each scenario exercises relationships/evidence; complex questions combine at least two business constraints. Changing identifiers in a single lookup template does not make a sufficient bank. PRD owns the business scenario matrix; no separate duplicative scenario requirements document.

## Minimal capabilities and ontology boundary

Three general functions: inventory_asof (dated reconstruction and trace), fulfillment_plan (orders and replenishment modes), recall_assessment (reach and physical control). One investigation Skill determines scope, chooses capabilities, checks completeness/issues and provides evidence-supported suggestions. Two metrics are individual recorded snapshots: available inventory quantity and recall-control coverage. They require date, knowledge, product/unit and location or recall qualification; they do not replace live reconstruction.

Functions accept business scopes, never question IDs, and never load questions/gold. Output scope, rows, issues, evidence and completeness. Decimal quantities/ratios use six decimal places; unknown remains null. Simple master-data lookups use native object queries.

GS1 Web Vocabulary v1.16 commit f8f407bf717233c871dca2f62f4e45b0940e8cad is Apache-2.0. Organization/Place/FoodBeverageTobaccoProduct provide conceptual references, not equivalentClass assertions. EPCIS/CBV inform events; their specifications and official examples are not redistributed. Orders, forecasts, inspections, reservations and recall controls are declared local operational extensions. All 15 object classes are populated and linked, with 30 direct foreign-key relations and 3 concept groups. Stable synthetic IDs are not registered GTIN/GLN. Normal master tables have at least 50 meaningful records; fact volumes follow scenario complexity. Chinese business values are localized, stable machine codes are separate.

## Delivery and validation

Complete deterministic development checks before formal evaluation: BKN/schema, data hashes, foreign keys, temporal/unit/quantity invariants, intentional quality exceptions, bilingual parity, capability registration, actual function/metric/Skill queries, package self-containment and installation fidelity. Development checks are not extra Q&A rounds.

Freeze package/data/questions/grader before one formal evaluation through installed live tools by isolated subagents without gold access. Store first responses, tool traces and lifecycle result. All 100 questions per language remain in the denominator, including failures. Score business correctness separately from evidence capture. 100% is the target, not an assumed result. Preserve failures; do not silently retry, alter gold or start another round without user direction.

Deliver bilingual docs, BKN, synthetic data, capabilities, 100-question banks, local offline archives and actual 8081 evidence. No commit/push/release/catalog update is authorized by this implementation task. README reports actual state and prerequisites; packaging alone is not acceptance.
