# Manufacturing business scenarios and acceptance questions

| ID | Business scenario | Acceptance question | Expected result |
|---|---|---|
| MFG-01 | Demand to production | Which sales-order line drives `WO-1001`? | `SOL-001` from `SO-2026-001` for 120 `PROD-PUMP-HOUSING`. |
| MFG-02 | Material coverage | Is the required aluminum quantity issued to the work order? | `MR-001`: 122 EA required and 122 EA issued. |
| MFG-03 | Process completion | Are all process steps of `WO-1001` executed? | Yes: `STEP-1001-10-A` and `STEP-1001-20-A` each have a completed execution record. |
| MFG-04 | Equipment capability | Does each executing machine declare the required step capability? | Yes: CNC mill has `CAP-CNC-MILL`; CMM has `CAP-CMM-INSPECT`. |
| MFG-05 | Operator qualification | Is the assigned operator qualified for both executed capabilities? | Yes: `OPR-001` holds qualified records for CNC milling and CMM inspection. |
| MFG-06 | Shift and work-center consistency | Do executions occur in the assigned shift and at the operation work center? | Yes: both records fall within Day Shift A and use the operation work center. |
| MFG-07 | Final quality | Is the final inspection accepted and within the bore-diameter limits? | Yes: `QIL-001` is accepted; 50.01 is inside [49.95, 50.05]. |
| MFG-08 | Finished-goods availability | What finished-goods balance results for the completed order product? | `IB-FG-HOUSING`: 120 EA on hand, 0 allocated. |
| MFG-09 | Preventive maintenance | Is a preventive maintenance work order planned for the CNC mill? | Yes: `MWO-001` is planned from `MP-001` for `MACH-CNC-01`. |
| MFG-10 | Source-model traceability | Do all fixed IOF classes have a reference instance with provenance? | Yes: 112 CSVs, all with source IRI, label, definition, and synthetic-reference marker. |
| MFG-11 | Operational data scale | Is the dataset large enough to exercise relations beyond a single record? | Yes: 40 operational tables, 2,700 records in total, and at least 50 records in every table. |
| MFG-12 | Normal-completion population | How many independent batches complete with final quality accepted? | 22 batches have an accepted final inspection lot. |
| MFG-13 | Material-shortage population | How many batches are blocked by material shortage, and what is their coverage? | 11 batches; each has 90 EA issued against 122 EA required. |
| MFG-14 | Quality-failure population | How many batches fail final quality, and what is the failed value? | 11 batches; each measures 50.09 against an upper limit of 50.05. |
| MFG-15 | In-production population | How many batches remain in production and what is their final-quality state? | 6 released batches remain in production; every final inspection lot is pending. |
| MFG-16 | Planning horizon | Do demand forecasts and production plans extend to the agreed planning horizon? | Yes: forecast periods and production due dates span November 2026 through March 2027; the latest due date is 2027-03-30. |
| MFG-17 | End-to-end fulfillment | Does a completed work order reach a shipment, and do exception branches stop before shipment? | Yes: 22 accepted finished-goods receipts have completed shipments; 11 material shortages are blocked, 11 quality failures are rejected, and 6 in-production cases are pending. |
