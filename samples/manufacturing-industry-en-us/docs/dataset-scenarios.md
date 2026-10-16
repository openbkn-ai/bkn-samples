# Sample-data design and business branches

Every operational table now has 50–150 records. Fifty business batches use synchronously expanded stable IDs, so order, work order, operation, execution, quality, and maintenance relationships remain connected; repeated branch types retain distinct batch IDs to exercise non-singleton queries.

The demand forecast and production-planning horizon runs from November 2026 through March 2027. Each batch has synchronized order, receipt, shift, execution, maintenance, and due-date facts; the latest production due date is 2027-03-30.

Each case now also connects a forecast to a production-plan line, records material issue against the work-order requirement, applies a reusable quality specification, records the finished-goods receipt, and resolves the shipment state. A shipment is completed only for an accepted inspection and accepted finished-goods receipt.

| Branch | Core work order | Business state | Validates |
|---|---|---|---|
| Normal completion (22 batches) | `WO-1001`, `WO-1001-OK2`, `WO-1001-B001` through `B020` | Fully issued material, two completed conformant steps, accepted final inspection | Positive completion decision and multi-record traceability |
| Material shortage (11 batches) | `WO-1001-MAT`, `WO-1001-B021` through `B030` | 122 EA required, 90 EA issued; blocked order, unstarted execution, pending inspection | Coverage, blocking reason, and pending handling |
| Quality failure (11 batches) | `WO-1001-QFAIL`, `WO-1001-B031` through `B040` | Completed execution but rejected final inspection; 50.09 exceeds upper limit 50.05 | Quality-gate failure distinct from completion status |
| In production (6 batches) | `WO-1001-B041` through `B046` | Machining completed, final inspection in progress, pending quality | Work-in-progress and pending-quality handling |

The data does not attribute blocked or failed states to unmodeled causes. The material branch is explained only by insufficient issue coverage; the quality branch only by rejected inspection and out-of-limit measurement.

These four branches are evaluated at two explicit dates: the released plan snapshot on 2026-10-20 and the transaction-derived inventory snapshot on 2027-03-31. Finite-capacity scheduling, lot genealogy, and maintenance conflicts remain outside this sample boundary.
