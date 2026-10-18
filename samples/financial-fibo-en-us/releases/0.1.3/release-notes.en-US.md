# 0.1.3 local revalidation candidate

Requires OpenBKN >=0.2.1 <0.3.0. Local offline acceptance only; not published.

Correct expanded cardinalities, explicit February trade cohort and selected-position scope. Specify trade-date FX eligibility and final grouped rounding. Offline evidence uses generic Decimal arithmetic for half-cent boundaries. Native BKN includes a reusable business analysis contract and localized controlled values for actual queries, cumulative settlement and complete lists.

Retains 20 objects, 29 relations and 78,356 business records per language. No per-question runtime functions, metrics or Skills. All 100 questions participate in fresh acceptance; no reference exclusions are carried forward.

Clarify booked gross_amount, local unsettled notionals and USD translation as separate measures. Historical position/valuation audits explicitly cover all actual snapshot dates. Business data and oracle result rows are unchanged from 0.1.2; booking-rounding and historical-scope controls added.

Full 100-question reference audit: breach traces contain breaches only; breach overview includes every limit identity plus total excess; the next-limit question names its version series. Every question participates in live revalidation.
