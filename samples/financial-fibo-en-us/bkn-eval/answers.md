# 100 questions and complete answers

Answers bind the locked data and contain every returned row. Amount units follow currency columns and question context; concentrations are ratios from 0 to 1. `NULL` means missing/unknown, not zero. SQL evidence is in `questions.json`; structured gold is in `expected-results.json`.

## FIN-001 · easy_basic

Who issues INS-001, and what is the issuer name?

Evidence returns 1 row(s). First result: instrument_id=INS-001; name=Alder Technology Ordinary Share; issuer_id=ISS-001; issuer_name=Alder Technology Holdings. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| instrument_id | name | issuer_id | issuer_name |
|---|---|---|---|
| INS-001 | Alder Technology Ordinary Share | ISS-001 | Alder Technology Holdings |

## FIN-002 · easy_basic

What asset class and price basis does INS-002 use?

Evidence returns 1 row(s). First result: instrument_id=INS-002; asset_class=bond; price_basis=dirty_per_100; price_multiplier=0.01; currency=CNY. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| instrument_id | asset_class | price_basis | price_multiplier | currency |
|---|---|---|---|---|
| INS-002 | bond | dirty_per_100 | 0.01 | CNY |

## FIN-003 · easy_basic

What is PF-049’s name and base currency?

Evidence returns 1 row(s). First result: portfolio_id=PF-049; name=Iris Utilities Core Portfolio; base_currency=USD. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| portfolio_id | name | base_currency |
|---|---|---|
| PF-049 | Iris Utilities Core Portfolio | USD |

## FIN-004 · intermediate

Trace INS-015 through its complete security identity to its issuer: return instrument_id, synthetic_code, scheme, instrument_name, issuer_id and issuer_name.

Evidence returns 1 row(s). First result: instrument_id=INS-015; synthetic_code=DEMO-SEC-00015; scheme=local_security_code; instrument_name=Harbor Technology Ordinary Share; issuer_id=ISS-008; issuer_name=Harbor Technology Holdings. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| instrument_id | synthetic_code | scheme | instrument_name | issuer_id | issuer_name |
|---|---|---|---|---|---|
| INS-015 | DEMO-SEC-00015 | local_security_code | Harbor Technology Ordinary Share | ISS-008 | Harbor Technology Holdings |

## FIN-005 · intermediate

What synthetic identifier belongs to issuer ISS-023?

Evidence returns 1 row(s). First result: entity_id=ISS-023; name=Cedar Industrials Holdings; synthetic_code=DEMO-ENTITY-ISS-023; scheme=synthetic_entity_code; is_synthetic=true. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| entity_id | name | synthetic_code | scheme | is_synthetic |
|---|---|---|---|---|
| ISS-023 | Cedar Industrials Holdings | DEMO-ENTITY-ISS-023 | synthetic_entity_code | true |

## FIN-006 · intermediate

Which account_id, portfolio_id, manager_id and manager_name (legal_entities.name of the portfolio manager) are associated with PF-010?

Evidence returns 1 row(s). First result: account_id=ACC-010; portfolio_id=PF-010; manager_id=MGR-010; manager_name=Juniper Technology Asset Management. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| account_id | portfolio_id | manager_id | manager_name |
|---|---|---|---|
| ACC-010 | PF-010 | MGR-010 | Juniper Technology Asset Management |

## FIN-007 · intermediate

Which two instruments share issuer ISS-008, and how do their pricing units differ?

Evidence returns 2 row(s). First result: instrument_id=INS-015; name=Harbor Technology Ordinary Share; asset_class=equity; unit=share; price_basis=per_share; price_multiplier=1.0. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| instrument_id | name | asset_class | unit | price_basis | price_multiplier |
|---|---|---|---|---|---|
| INS-015 | Harbor Technology Ordinary Share | equity | share | per_share | 1.0 |
| INS-016 | Harbor Technology 2030 Note | bond | face_unit | dirty_per_100 | 0.01 |

## FIN-008 · hard_complex

Which portfolios share issuer ISS-008 at the current snapshot, and through which instruments?

Evidence returns 32 row(s). First result: portfolio_id=PF-001; instrument_id=INS-015; asset_class=equity. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| portfolio_id | instrument_id | asset_class |
|---|---|---|
| PF-001 | INS-015 | equity |
| PF-001 | INS-016 | bond |
| PF-008 | INS-015 | equity |
| PF-008 | INS-016 | bond |
| PF-029 | INS-015 | equity |
| PF-029 | INS-016 | bond |
| PF-041 | INS-015 | equity |
| PF-041 | INS-016 | bond |
| PF-051 | INS-015 | equity |
| PF-051 | INS-016 | bond |
| PF-058 | INS-015 | equity |
| PF-058 | INS-016 | bond |
| PF-079 | INS-015 | equity |
| PF-079 | INS-016 | bond |
| PF-091 | INS-015 | equity |
| PF-091 | INS-016 | bond |
| PF-101 | INS-015 | equity |
| PF-101 | INS-016 | bond |
| PF-108 | INS-015 | equity |
| PF-108 | INS-016 | bond |
| PF-129 | INS-015 | equity |
| PF-129 | INS-016 | bond |
| PF-141 | INS-015 | equity |
| PF-141 | INS-016 | bond |
| PF-151 | INS-015 | equity |
| PF-151 | INS-016 | bond |
| PF-158 | INS-015 | equity |
| PF-158 | INS-016 | bond |
| PF-179 | INS-015 | equity |
| PF-179 | INS-016 | bond |
| PF-191 | INS-015 | equity |
| PF-191 | INS-016 | bond |

## FIN-009 · hard_complex

Does each instrument resolve to one security code, an issuer-role entity, and one synthetic entity identifier? Audit the complete identity path.

Evidence returns 1 row(s). First result: instruments_checked=100; identity_exceptions=0. Missing issuer roles are explicitly counted with IS NULL, avoiding SQL three-valued-logic omissions.

| instruments_checked | identity_exceptions |
|---|---|
| 100 | 0 |

## FIN-010 · hard_complex

Audit the current position-to-portfolio-to-manager and position-to-instrument-to-issuer paths; report distinct roles and any incorrect role assignments.

Evidence returns 1 row(s). First result: positions=1600; issuers=50; managers=50; role_errors=0. Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.

| positions | issuers | managers | role_errors |
|---|---|---|---|
| 1600 | 50 | 50 | 0 |

## FIN-011 · easy_basic

What side, quantity and currency were executed in TR-001-1-4?

Evidence returns 1 row(s). First result: trade_id=TR-001-1-4; side=buy; trade_quantity=170.0; currency=CNY. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | side | trade_quantity | currency |
|---|---|---|---|
| TR-001-1-4 | buy | 170.0 | CNY |

## FIN-012 · easy_basic

What is the execution price and gross amount of TR-001-2-4?

Evidence returns 1 row(s). First result: trade_id=TR-001-2-4; execution_price=100.0; gross_amount=3596.0; currency=CNY. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | execution_price | gross_amount | currency |
|---|---|---|---|
| TR-001-2-4 | 100.0 | 3596.0 | CNY |

## FIN-013 · easy_basic

Which order created TR-019-2-4?

Evidence returns 1 row(s). First result: trade_id=TR-019-2-4; order_id=ORD-019-2-4; trade_date=2027-02-26. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | order_id | trade_date |
|---|---|---|
| TR-019-2-4 | ORD-019-2-4 | 2027-02-26 |

## FIN-014 · intermediate

Trace TR-030-4-4 to account, portfolio and counterparty.

Evidence returns 1 row(s). First result: trade_id=TR-030-4-4; portfolio_id=PF-030; account_id=ACC-030; counterparty_id=CP-030. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | portfolio_id | account_id | counterparty_id |
|---|---|---|---|
| TR-030-4-4 | PF-030 | ACC-030 | CP-030 |

## FIN-015 · intermediate

List all actual trades executed for PF-041 in February 2027, with instrument, side, quantity, amount and currency.

Evidence returns 8 row(s). First result: trade_id=TR-041-1-4; instrument_id=INS-081; side=buy; trade_quantity=96.0; gross_amount=1977.6; currency=USD. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | instrument_id | side | trade_quantity | gross_amount | currency |
|---|---|---|---|---|---|
| TR-041-1-4 | INS-081 | buy | 96.0 | 1977.6 | USD |
| TR-041-2-4 | INS-082 | sell | 2184.0 | 2265.9 | USD |
| TR-041-3-4 | INS-095 | sell | 18.0 | 432.0 | EUR |
| TR-041-4-4 | INS-096 | sell | 454.0 | 464.22 | EUR |
| TR-041-5-4 | INS-015 | sell | 22.0 | 484.0 | USD |
| TR-041-6-4 | INS-016 | sell | 500.0 | 503.75 | USD |
| TR-041-7-4 | INS-039 | sell | 24.0 | 537.6 | USD |
| TR-041-8-4 | INS-040 | sell | 484.0 | 502.15 | USD |

## FIN-016 · intermediate

Explain the bond quote conversion for TR-010-2-4.

Evidence returns 1 row(s). First result: trade_id=TR-010-2-4; trade_quantity=3458.0; execution_price=104.0; price_multiplier=0.01; reconstructed_gross=3596.32; gross_amount=3596.32. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | trade_quantity | execution_price | price_multiplier | reconstructed_gross | gross_amount |
|---|---|---|---|---|---|
| TR-010-2-4 | 3458.0 | 104.0 | 0.01 | 3596.32 | 3596.32 |

## FIN-017 · intermediate

Are March trades for PF-049 actual or planned, and when were they known?

Evidence returns 8 row(s). First result: trade_id=TR-049-1-5; trade_date=2027-03-17; trade_status=planned; known_date=2027-02-28. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| trade_id | trade_date | trade_status | known_date |
|---|---|---|---|
| TR-049-1-5 | 2027-03-17 | planned | 2027-02-28 |
| TR-049-2-5 | 2027-03-19 | planned | 2027-02-28 |
| TR-049-3-5 | 2027-03-22 | planned | 2027-02-28 |
| TR-049-4-5 | 2027-03-08 | planned | 2027-02-28 |
| TR-049-5-5 | 2027-03-10 | planned | 2027-02-28 |
| TR-049-6-5 | 2027-03-12 | planned | 2027-02-28 |
| TR-049-7-5 | 2027-03-15 | planned | 2027-02-28 |
| TR-049-8-5 | 2027-03-16 | planned | 2027-02-28 |

## FIN-018 · hard_complex

Reconcile order and executed quantities for all actual trades.

Evidence returns 1 row(s). First result: actual_trades=6400; quantity_mismatches=0. Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.

| actual_trades | quantity_mismatches |
|---|---|
| 6400 | 0 |

## FIN-019 · hard_complex

For actual buys and sells, select the latest actual USD fixing with as_of_date, published_date and known_date no later than each trade date. Group by currency and side; report trade count, the sum of booked gross_amount (local currency, already rounded per trade to 2dp), and USD total. Translate that booked gross_amount at the eligible rate, then round only the grouped USD sum; do not replace booked amounts with unrounded quantity-price products.

Evidence returns 6 row(s). First result: currency=CNY; side=buy; trades=340; fixing_records=19; local_gross=1266440.0; usd_gross=176305.09; maximum_fixing_age=4. The fixing is the latest published curve observation available by each execution date, not the month-end fixing; USD totals permit cross-currency comparison.

| currency | side | trades | fixing_records | local_gross | usd_gross | maximum_fixing_age |
|---|---|---|---|---|---|---|
| CNY | buy | 340 | 19 | 1266440.0 | 176305.09 | 4 |
| CNY | sell | 1836 | 24 | 6720780.24 | 935639.37 | 4 |
| EUR | buy | 320 | 19 | 173888.8 | 185615.08 | 4 |
| EUR | sell | 1728 | 24 | 843407.19 | 900605.59 | 4 |
| USD | buy | 340 | 19 | 194047.6 | 194047.6 | 4 |
| USD | sell | 1836 | 24 | 958891.59 | 958891.59 | 4 |

## FIN-020 · hard_complex

For each trade-month cohort, currency and actual/planned view, reconcile trade count, signed booked contractual amount (sell +gross_amount, buy -gross_amount) and the remaining sell notional in that same local currency. For the latter accumulate eligible settlement transfers to that month end, then sum open sell quantity times execution quote times multiplier, rounding the local group total to 2dp. Do not translate this report to USD or carry other trade-month cohorts into a group.

Evidence returns 15 row(s). First result: month=2026-11; trade_status=executed; currency=CNY; trades=544; signed_contractual_amount=635854.04; open_sell_receivable_local=0.0. Each fill contributes contractual amount once despite several events. Event transfers accumulate only through that trade month-end, without consuming later recovery forecasts.

| month | trade_status | currency | trades | signed_contractual_amount | open_sell_receivable_local |
|---|---|---|---|---|---|
| 2026-11 | executed | CNY | 544 | 635854.04 | 0.0 |
| 2026-11 | executed | EUR | 512 | 77952.1 | 0.0 |
| 2026-11 | executed | USD | 544 | 88347.44 | 0.0 |
| 2026-12 | executed | CNY | 544 | 1902397.68 | 0.0 |
| 2026-12 | executed | EUR | 512 | 230307.58 | 0.0 |
| 2026-12 | executed | USD | 544 | 262669.18 | 0.0 |
| 2027-01 | executed | CNY | 544 | 1016055.64 | 0.0 |
| 2027-01 | executed | EUR | 512 | 132041.88 | 0.0 |
| 2027-01 | executed | USD | 544 | 149530.54 | 0.0 |
| 2027-02 | executed | CNY | 544 | 1900032.88 | 430130.34 |
| 2027-02 | executed | EUR | 512 | 229216.83 | 50752.22 |
| 2027-02 | executed | USD | 544 | 264296.83 | 57582.74 |
| 2027-03 | planned | CNY | 544 | 1014873.24 | 70131.22 |
| 2027-03 | planned | EUR | 512 | 131662.15 | 9691.02 |
| 2027-03 | planned | USD | 544 | 149964.69 | 8475.53 |

## FIN-021 · easy_basic

What is the settlement due date for TR-019-2-4?

Evidence returns 1 row(s). First result: trade_id=TR-019-2-4; instruction_id=SI-019-2-4; due_date=2027-03-02; required_quantity=3560.0. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| trade_id | instruction_id | due_date | required_quantity |
|---|---|---|---|
| TR-019-2-4 | SI-019-2-4 | 2027-03-02 | 3560.0 |

## FIN-022 · easy_basic

What is the failure reason of SE-030-2-4?

Evidence returns 1 row(s). First result: event_id=SE-030-2-4; event_date=2027-02-24; event_status=failed; failure_reason=cash_mismatch; settled_quantity=0.0. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| event_id | event_date | event_status | failure_reason | settled_quantity |
|---|---|---|---|---|
| SE-030-2-4 | 2027-02-24 | failed | cash_mismatch | 0.0 |

## FIN-023 · easy_basic

What amount of quantity was settled in SE-020-2-4?

Evidence returns 1 row(s). First result: event_id=SE-020-2-4; event_status=partial; settled_quantity=242.0. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| event_id | event_status | settled_quantity |
|---|---|---|
| SE-020-2-4 | partial | 242.0 |

## FIN-024 · intermediate

Is SI-019-2-4 overdue on 2027-02-28? Explain using due date and state.

Evidence returns 1 row(s). First result: instruction_id=SI-019-2-4; due_date=2027-03-02; event_status=pending; overdue=0. A due date after 2027-02-28 means not yet due; pending is not synonymous with failed or overdue.

| instruction_id | due_date | event_status | overdue |
|---|---|---|---|
| SI-019-2-4 | 2027-03-02 | pending | 0 |

## FIN-025 · intermediate

How much remains unsettled on partial instruction SI-020-2-4?

Evidence returns 1 row(s). First result: instruction_id=SI-020-2-4; required_quantity=484.0; settled_quantity=242.0; remaining_quantity=242.0; due_date=2027-02-24. Remaining quantity is required quantity minus cumulative transfers, not minus the quantity on an arbitrary event.

| instruction_id | required_quantity | settled_quantity | remaining_quantity | due_date |
|---|---|---|---|---|
| SI-020-2-4 | 484.0 | 242.0 | 242.0 | 2027-02-24 |

## FIN-026 · intermediate

Which broker and instrument are implicated by SE-029-4-4?

Evidence returns 1 row(s). First result: event_id=SE-029-4-4; failure_reason=insufficient_securities; counterparty_id=CP-029; counterparty_name=Iris Industrials Securities; instrument_id=INS-072; trade_id=TR-029-4-4. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| event_id | failure_reason | counterparty_id | counterparty_name | instrument_id | trade_id |
|---|---|---|---|---|---|
| SE-029-4-4 | insufficient_securities | CP-029 | Iris Industrials Securities | INS-072 | TR-029-4-4 |

## FIN-027 · intermediate

For February 2027 actual trades of PF-001, PF-019, PF-020 and PF-029, compare settled, pending, partial and failed instruction counts and remaining quantities as of 2027-02-28. Accumulate actual event transfers known by that date.

Evidence returns 7 row(s). First result: portfolio_id=PF-001; event_status=settled; instructions=8; remaining_quantity=0.0. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| portfolio_id | event_status | instructions | remaining_quantity |
|---|---|---|---|
| PF-001 | settled | 8 | 0.0 |
| PF-019 | pending | 4 | 4976.0 |
| PF-019 | settled | 4 | 0.0 |
| PF-020 | partial | 4 | 4067.0 |
| PF-020 | settled | 4 | 0.0 |
| PF-029 | failed | 4 | 5100.0 |
| PF-029 | settled | 4 | 0.0 |

## FIN-028 · hard_complex

Count February overdue unsettled instructions separately from unsettled instructions not yet due. Return due_state using the complete computed classification: overdue (due_date before 2027-02-28), not_due (otherwise), for instructions with cumulative settled_quantity below required_quantity.

Evidence returns 2 row(s). First result: due_state=not_due; instructions=80. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| due_state | instructions |
|---|---|
| not_due | 80 |
| overdue | 224 |

## FIN-029 · hard_complex

How many failed February instructions arise from each failure reason and side?

Evidence returns 2 row(s). First result: failure_reason=cash_mismatch; side=sell; instructions=80. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| failure_reason | side | instructions |
|---|---|---|
| cash_mismatch | sell | 80 |
| insufficient_securities | sell | 64 |

## FIN-030 · hard_complex

Reconcile required, settled and remaining quantities by instrument unit for actual trades.

Evidence returns 2 row(s). First result: unit=face_unit; required_quantity=5078988.0; settled_quantity=4544445.0; remaining_quantity=534543.0. Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.

| unit | required_quantity | settled_quantity | remaining_quantity |
|---|---|---|---|
| face_unit | 5078988.0 | 4544445.0 | 534543.0 |
| share | 201486.0 | 201486.0 | 0.0 |

## FIN-031 · easy_basic

What are the two quantity bases of POS-019-2-4?

Evidence returns 1 row(s). First result: position_id=POS-019-2-4; trade_basis_quantity=60550.0; settled_basis_quantity=64110.0; unsettled_delta=-3560.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | trade_basis_quantity | settled_basis_quantity | unsettled_delta |
|---|---|---|---|
| POS-019-2-4 | 60550.0 | 64110.0 | -3560.0 |

## FIN-032 · easy_basic

What quantity opened OP-001-1?

Evidence returns 1 row(s). First result: opening_id=OP-001-1; opening_date=2026-11-01; quantity=3426.0; cost_unit_price=21.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| opening_id | opening_date | quantity | cost_unit_price |
|---|---|---|---|
| OP-001-1 | 2026-11-01 | 3426.0 | 21.0 |

## FIN-033 · easy_basic

Which date and view does POS-050-4-5 represent?

Evidence returns 1 row(s). First result: position_id=POS-050-4-5; as_of_date=2027-03-31; view_kind=planned; known_date=2027-02-28. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | as_of_date | view_kind | known_date |
|---|---|---|---|
| POS-050-4-5 | 2027-03-31 | planned | 2027-02-28 |

## FIN-034 · intermediate

Trace POS-030-4-4 to instrument and portfolio.

Evidence returns 1 row(s). First result: position_id=POS-030-4-4; portfolio_id=PF-030; instrument_id=INS-074. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | portfolio_id | instrument_id |
|---|---|---|
| POS-030-4-4 | PF-030 | INS-074 |

## FIN-035 · intermediate

Do the quantity bases reconcile for PF-020 at the current date?

Evidence returns 8 row(s). First result: position_id=POS-020-1-4; trade_basis_quantity=548.0; settled_basis_quantity=548.0; unsettled_delta=0.0; reconciliation_error=0.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | trade_basis_quantity | settled_basis_quantity | unsettled_delta | reconciliation_error |
|---|---|---|---|---|
| POS-020-1-4 | 548.0 | 548.0 | 0.0 | 0.0 |
| POS-020-2-4 | 8257.0 | 8499.0 | -242.0 | 0.0 |
| POS-020-3-4 | 425.0 | 425.0 | 0.0 | 0.0 |
| POS-020-4-4 | 7746.0 | 7973.0 | -227.0 | 0.0 |
| POS-020-5-4 | 2185.0 | 2185.0 | 0.0 | 0.0 |
| POS-020-6-4 | 59954.0 | 61717.0 | -1763.0 | 0.0 |
| POS-020-7-4 | 2353.0 | 2353.0 | 0.0 | 0.0 |
| POS-020-8-4 | 62401.0 | 64236.0 | -1835.0 | 0.0 |

## FIN-036 · intermediate

Compare the current sell-side unsettled deltas of positions POS-001-2-4 and POS-029-2-4; explain the sign and distinguish these positions from portfolio totals.

Evidence returns 2 row(s). First result: portfolio_id=PF-001; position_id=POS-001-2-4; unsettled_delta=0.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| portfolio_id | position_id | unsettled_delta |
|---|---|---|
| PF-001 | POS-001-2-4 | 0.0 |
| PF-029 | POS-029-2-4 | -500.0 |

## FIN-037 · intermediate

Show the five snapshots of opening position OP-049-1 and their view kinds.

Evidence returns 5 row(s). First result: position_id=POS-049-1-1; as_of_date=2026-11-30; view_kind=actual; trade_basis_quantity=2836.0; settled_basis_quantity=2836.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | as_of_date | view_kind | trade_basis_quantity | settled_basis_quantity |
|---|---|---|---|---|
| POS-049-1-1 | 2026-11-30 | actual | 2836.0 | 2836.0 |
| POS-049-1-2 | 2026-12-31 | actual | 2974.0 | 2974.0 |
| POS-049-1-3 | 2027-01-31 | actual | 2905.0 | 2905.0 |
| POS-049-1-4 | 2027-02-28 | actual | 3043.0 | 3043.0 |
| POS-049-1-5 | 2027-03-31 | planned | 2974.0 | 2974.0 |

## FIN-038 · hard_complex

Reconstruct POS-020-2-4 trade-date quantity from opening plus signed actual trades.

Evidence returns 1 row(s). First result: position_id=POS-020-2-4; trade_basis_quantity=8257.0; reconstructed=8257.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | trade_basis_quantity | reconstructed |
|---|---|---|
| POS-020-2-4 | 8257.0 | 8257.0 |

## FIN-039 · hard_complex

Reconstruct POS-029-4-4 settled quantity from opening and settlement events.

Evidence returns 1 row(s). First result: position_id=POS-029-4-4; settled_basis_quantity=8445.0; reconstructed=8445.0. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| position_id | settled_basis_quantity | reconstructed |
|---|---|---|
| POS-029-4-4 | 8445.0 | 8445.0 |

## FIN-040 · hard_complex

Across the full actual position-snapshot history from November 2026 through February 2027, count dated position records, quantity reconciliation failures and records with nonzero unsettled delta. Include all historical actual snapshots, not only the current snapshot; exclude March plans.

Evidence returns 1 row(s). First result: actual_positions=6400; reconciliation_failures=0; open_unsettled_positions=304. Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.

| actual_positions | reconciliation_failures | open_unsettled_positions |
|---|---|---|
| 6400 | 0 | 304 |

## FIN-041 · easy_basic

What is PX-001-4’s date, source and approval?

Evidence returns 1 row(s). First result: price_id=PX-001-4; price_date=2027-02-26; pricing_source=demo_pricing; approval=approved. An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| price_id | price_date | pricing_source | approval |
|---|---|---|---|
| PX-001-4 | 2027-02-26 | demo_pricing | approved |

## FIN-042 · easy_basic

Why is VAL-035-1-4 blocked?

Evidence returns 1 row(s). First result: valuation_id=VAL-035-1-4; valuation_status=blocked; reason=stale; price_id=PX-069-4; market_value_base=unknown (NULL). An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| valuation_id | valuation_status | reason | price_id | market_value_base |
|---|---|---|---|---|
| VAL-035-1-4 | blocked | stale | PX-069-4 | NULL |

## FIN-043 · easy_basic

Is the February price for INS-073 present?

Evidence returns 1 row(s). First result: instrument_id=INS-073; price_count=0. Quote age is calendar-day difference; a ten-day-old quote fails the three-day freshness limit even if approved.

| instrument_id | price_count |
|---|---|
| INS-073 | 0 |

## FIN-044 · intermediate

How old is the price used by VAL-035-1-4? Return valuation_id, as_of_date, price_date, age_days and valuation_reason, copying valuation_snapshots.reason exactly as stored rather than writing a free-form explanation.

Evidence returns 1 row(s). First result: valuation_id=VAL-035-1-4; as_of_date=2027-02-28; price_date=2027-02-18; age_days=10; valuation_reason=stale. An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| valuation_id | as_of_date | price_date | age_days | valuation_reason |
|---|---|---|---|---|
| VAL-035-1-4 | 2027-02-28 | 2027-02-18 | 10 | stale |

## FIN-045 · intermediate

Which approval explains the exception of VAL-036-1-4?

Evidence returns 1 row(s). First result: valuation_id=VAL-036-1-4; reason=price_unapproved; price_id=PX-071-4; approval=unapproved. An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| valuation_id | reason | price_id | approval |
|---|---|---|---|
| VAL-036-1-4 | price_unapproved | PX-071-4 | unapproved |

## FIN-046 · intermediate

Does missing price VAL-037-1-4 fabricate a zero market value?

Evidence returns 1 row(s). First result: valuation_id=VAL-037-1-4; price_id=unknown (NULL); market_value_base=unknown (NULL); valuation_status=blocked; reason=missing. The absent quote produces NULL price linkage and market value; zero would fabricate evidence.

| valuation_id | price_id | market_value_base | valuation_status | reason |
|---|---|---|---|---|
| VAL-037-1-4 | NULL | NULL | blocked | missing |

## FIN-047 · intermediate

Which portfolios share the defective February price for INS-069?

Evidence returns 16 row(s). First result: portfolio_id=PF-006; valuation_id=VAL-006-7-4; reason=stale. An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| portfolio_id | valuation_id | reason |
|---|---|---|
| PF-006 | VAL-006-7-4 | stale |
| PF-018 | VAL-018-5-4 | stale |
| PF-028 | VAL-028-3-4 | stale |
| PF-035 | VAL-035-1-4 | stale |
| PF-056 | VAL-056-7-4 | stale |
| PF-068 | VAL-068-5-4 | stale |
| PF-078 | VAL-078-3-4 | stale |
| PF-085 | VAL-085-1-4 | stale |
| PF-106 | VAL-106-7-4 | stale |
| PF-118 | VAL-118-5-4 | stale |
| PF-128 | VAL-128-3-4 | stale |
| PF-135 | VAL-135-1-4 | stale |
| PF-156 | VAL-156-7-4 | stale |
| PF-168 | VAL-168-5-4 | stale |
| PF-178 | VAL-178-3-4 | stale |
| PF-185 | VAL-185-1-4 | stale |

## FIN-048 · hard_complex

Count all February valuation exceptions by reason and affected portfolios.

Evidence returns 3 row(s). First result: reason=missing; valuations=32; portfolios=32. An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| reason | valuations | portfolios |
|---|---|---|
| missing | 32 | 32 |
| price_unapproved | 32 | 32 |
| stale | 32 | 32 |

## FIN-049 · hard_complex

Which February issuer assessments must remain unknown because portfolio prices are incomplete?

Evidence returns 384 row(s). First result: portfolio_id=PF-006; assessment_id=LA-LIM-006-I1-4; assessment_status=unknown; observed_value=unknown (NULL). Any unpriced position blocks every issuer ratio for the portfolio; unknown is not within-limit.

| portfolio_id | assessment_id | assessment_status | observed_value |
|---|---|---|---|
| PF-006 | LA-LIM-006-I1-4 | unknown | NULL |
| PF-006 | LA-LIM-006-I2-4 | unknown | NULL |
| PF-006 | LA-LIM-006-I3-4 | unknown | NULL |
| PF-006 | LA-LIM-006-I4-4 | unknown | NULL |
| PF-007 | LA-LIM-007-I1-4 | unknown | NULL |
| PF-007 | LA-LIM-007-I2-4 | unknown | NULL |
| PF-007 | LA-LIM-007-I3-4 | unknown | NULL |
| PF-007 | LA-LIM-007-I4-4 | unknown | NULL |
| PF-008 | LA-LIM-008-I1-4 | unknown | NULL |
| PF-008 | LA-LIM-008-I2-4 | unknown | NULL |
| PF-008 | LA-LIM-008-I3-4 | unknown | NULL |
| PF-008 | LA-LIM-008-I4-4 | unknown | NULL |
| PF-009 | LA-LIM-009-I1-4 | unknown | NULL |
| PF-009 | LA-LIM-009-I2-4 | unknown | NULL |
| PF-009 | LA-LIM-009-I3-4 | unknown | NULL |
| PF-009 | LA-LIM-009-I4-4 | unknown | NULL |
| PF-010 | LA-LIM-010-I1-4 | unknown | NULL |
| PF-010 | LA-LIM-010-I2-4 | unknown | NULL |
| PF-010 | LA-LIM-010-I3-4 | unknown | NULL |
| PF-010 | LA-LIM-010-I4-4 | unknown | NULL |
| PF-011 | LA-LIM-011-I1-4 | unknown | NULL |
| PF-011 | LA-LIM-011-I2-4 | unknown | NULL |
| PF-011 | LA-LIM-011-I3-4 | unknown | NULL |
| PF-011 | LA-LIM-011-I4-4 | unknown | NULL |
| PF-018 | LA-LIM-018-I1-4 | unknown | NULL |
| PF-018 | LA-LIM-018-I2-4 | unknown | NULL |
| PF-018 | LA-LIM-018-I3-4 | unknown | NULL |
| PF-018 | LA-LIM-018-I4-4 | unknown | NULL |
| PF-019 | LA-LIM-019-I1-4 | unknown | NULL |
| PF-019 | LA-LIM-019-I2-4 | unknown | NULL |
| PF-019 | LA-LIM-019-I3-4 | unknown | NULL |
| PF-019 | LA-LIM-019-I4-4 | unknown | NULL |
| PF-020 | LA-LIM-020-I1-4 | unknown | NULL |
| PF-020 | LA-LIM-020-I2-4 | unknown | NULL |
| PF-020 | LA-LIM-020-I3-4 | unknown | NULL |
| PF-020 | LA-LIM-020-I4-4 | unknown | NULL |
| PF-021 | LA-LIM-021-I1-4 | unknown | NULL |
| PF-021 | LA-LIM-021-I2-4 | unknown | NULL |
| PF-021 | LA-LIM-021-I3-4 | unknown | NULL |
| PF-021 | LA-LIM-021-I4-4 | unknown | NULL |
| PF-022 | LA-LIM-022-I1-4 | unknown | NULL |
| PF-022 | LA-LIM-022-I2-4 | unknown | NULL |
| PF-022 | LA-LIM-022-I3-4 | unknown | NULL |
| PF-022 | LA-LIM-022-I4-4 | unknown | NULL |
| PF-023 | LA-LIM-023-I1-4 | unknown | NULL |
| PF-023 | LA-LIM-023-I2-4 | unknown | NULL |
| PF-023 | LA-LIM-023-I3-4 | unknown | NULL |
| PF-023 | LA-LIM-023-I4-4 | unknown | NULL |
| PF-028 | LA-LIM-028-I1-4 | unknown | NULL |
| PF-028 | LA-LIM-028-I2-4 | unknown | NULL |
| PF-028 | LA-LIM-028-I3-4 | unknown | NULL |
| PF-028 | LA-LIM-028-I4-4 | unknown | NULL |
| PF-029 | LA-LIM-029-I1-4 | unknown | NULL |
| PF-029 | LA-LIM-029-I2-4 | unknown | NULL |
| PF-029 | LA-LIM-029-I3-4 | unknown | NULL |
| PF-029 | LA-LIM-029-I4-4 | unknown | NULL |
| PF-030 | LA-LIM-030-I1-4 | unknown | NULL |
| PF-030 | LA-LIM-030-I2-4 | unknown | NULL |
| PF-030 | LA-LIM-030-I3-4 | unknown | NULL |
| PF-030 | LA-LIM-030-I4-4 | unknown | NULL |
| PF-031 | LA-LIM-031-I1-4 | unknown | NULL |
| PF-031 | LA-LIM-031-I2-4 | unknown | NULL |
| PF-031 | LA-LIM-031-I3-4 | unknown | NULL |
| PF-031 | LA-LIM-031-I4-4 | unknown | NULL |
| PF-032 | LA-LIM-032-I1-4 | unknown | NULL |
| PF-032 | LA-LIM-032-I2-4 | unknown | NULL |
| PF-032 | LA-LIM-032-I3-4 | unknown | NULL |
| PF-032 | LA-LIM-032-I4-4 | unknown | NULL |
| PF-033 | LA-LIM-033-I1-4 | unknown | NULL |
| PF-033 | LA-LIM-033-I2-4 | unknown | NULL |
| PF-033 | LA-LIM-033-I3-4 | unknown | NULL |
| PF-033 | LA-LIM-033-I4-4 | unknown | NULL |
| PF-035 | LA-LIM-035-I1-4 | unknown | NULL |
| PF-035 | LA-LIM-035-I2-4 | unknown | NULL |
| PF-035 | LA-LIM-035-I3-4 | unknown | NULL |
| PF-035 | LA-LIM-035-I4-4 | unknown | NULL |
| PF-036 | LA-LIM-036-I1-4 | unknown | NULL |
| PF-036 | LA-LIM-036-I2-4 | unknown | NULL |
| PF-036 | LA-LIM-036-I3-4 | unknown | NULL |
| PF-036 | LA-LIM-036-I4-4 | unknown | NULL |
| PF-037 | LA-LIM-037-I1-4 | unknown | NULL |
| PF-037 | LA-LIM-037-I2-4 | unknown | NULL |
| PF-037 | LA-LIM-037-I3-4 | unknown | NULL |
| PF-037 | LA-LIM-037-I4-4 | unknown | NULL |
| PF-038 | LA-LIM-038-I1-4 | unknown | NULL |
| PF-038 | LA-LIM-038-I2-4 | unknown | NULL |
| PF-038 | LA-LIM-038-I3-4 | unknown | NULL |
| PF-038 | LA-LIM-038-I4-4 | unknown | NULL |
| PF-039 | LA-LIM-039-I1-4 | unknown | NULL |
| PF-039 | LA-LIM-039-I2-4 | unknown | NULL |
| PF-039 | LA-LIM-039-I3-4 | unknown | NULL |
| PF-039 | LA-LIM-039-I4-4 | unknown | NULL |
| PF-040 | LA-LIM-040-I1-4 | unknown | NULL |
| PF-040 | LA-LIM-040-I2-4 | unknown | NULL |
| PF-040 | LA-LIM-040-I3-4 | unknown | NULL |
| PF-040 | LA-LIM-040-I4-4 | unknown | NULL |
| PF-056 | LA-LIM-056-I1-4 | unknown | NULL |
| PF-056 | LA-LIM-056-I2-4 | unknown | NULL |
| PF-056 | LA-LIM-056-I3-4 | unknown | NULL |
| PF-056 | LA-LIM-056-I4-4 | unknown | NULL |
| PF-057 | LA-LIM-057-I1-4 | unknown | NULL |
| PF-057 | LA-LIM-057-I2-4 | unknown | NULL |
| PF-057 | LA-LIM-057-I3-4 | unknown | NULL |
| PF-057 | LA-LIM-057-I4-4 | unknown | NULL |
| PF-058 | LA-LIM-058-I1-4 | unknown | NULL |
| PF-058 | LA-LIM-058-I2-4 | unknown | NULL |
| PF-058 | LA-LIM-058-I3-4 | unknown | NULL |
| PF-058 | LA-LIM-058-I4-4 | unknown | NULL |
| PF-059 | LA-LIM-059-I1-4 | unknown | NULL |
| PF-059 | LA-LIM-059-I2-4 | unknown | NULL |
| PF-059 | LA-LIM-059-I3-4 | unknown | NULL |
| PF-059 | LA-LIM-059-I4-4 | unknown | NULL |
| PF-060 | LA-LIM-060-I1-4 | unknown | NULL |
| PF-060 | LA-LIM-060-I2-4 | unknown | NULL |
| PF-060 | LA-LIM-060-I3-4 | unknown | NULL |
| PF-060 | LA-LIM-060-I4-4 | unknown | NULL |
| PF-061 | LA-LIM-061-I1-4 | unknown | NULL |
| PF-061 | LA-LIM-061-I2-4 | unknown | NULL |
| PF-061 | LA-LIM-061-I3-4 | unknown | NULL |
| PF-061 | LA-LIM-061-I4-4 | unknown | NULL |
| PF-068 | LA-LIM-068-I1-4 | unknown | NULL |
| PF-068 | LA-LIM-068-I2-4 | unknown | NULL |
| PF-068 | LA-LIM-068-I3-4 | unknown | NULL |
| PF-068 | LA-LIM-068-I4-4 | unknown | NULL |
| PF-069 | LA-LIM-069-I1-4 | unknown | NULL |
| PF-069 | LA-LIM-069-I2-4 | unknown | NULL |
| PF-069 | LA-LIM-069-I3-4 | unknown | NULL |
| PF-069 | LA-LIM-069-I4-4 | unknown | NULL |
| PF-070 | LA-LIM-070-I1-4 | unknown | NULL |
| PF-070 | LA-LIM-070-I2-4 | unknown | NULL |
| PF-070 | LA-LIM-070-I3-4 | unknown | NULL |
| PF-070 | LA-LIM-070-I4-4 | unknown | NULL |
| PF-071 | LA-LIM-071-I1-4 | unknown | NULL |
| PF-071 | LA-LIM-071-I2-4 | unknown | NULL |
| PF-071 | LA-LIM-071-I3-4 | unknown | NULL |
| PF-071 | LA-LIM-071-I4-4 | unknown | NULL |
| PF-072 | LA-LIM-072-I1-4 | unknown | NULL |
| PF-072 | LA-LIM-072-I2-4 | unknown | NULL |
| PF-072 | LA-LIM-072-I3-4 | unknown | NULL |
| PF-072 | LA-LIM-072-I4-4 | unknown | NULL |
| PF-073 | LA-LIM-073-I1-4 | unknown | NULL |
| PF-073 | LA-LIM-073-I2-4 | unknown | NULL |
| PF-073 | LA-LIM-073-I3-4 | unknown | NULL |
| PF-073 | LA-LIM-073-I4-4 | unknown | NULL |
| PF-078 | LA-LIM-078-I1-4 | unknown | NULL |
| PF-078 | LA-LIM-078-I2-4 | unknown | NULL |
| PF-078 | LA-LIM-078-I3-4 | unknown | NULL |
| PF-078 | LA-LIM-078-I4-4 | unknown | NULL |
| PF-079 | LA-LIM-079-I1-4 | unknown | NULL |
| PF-079 | LA-LIM-079-I2-4 | unknown | NULL |
| PF-079 | LA-LIM-079-I3-4 | unknown | NULL |
| PF-079 | LA-LIM-079-I4-4 | unknown | NULL |
| PF-080 | LA-LIM-080-I1-4 | unknown | NULL |
| PF-080 | LA-LIM-080-I2-4 | unknown | NULL |
| PF-080 | LA-LIM-080-I3-4 | unknown | NULL |
| PF-080 | LA-LIM-080-I4-4 | unknown | NULL |
| PF-081 | LA-LIM-081-I1-4 | unknown | NULL |
| PF-081 | LA-LIM-081-I2-4 | unknown | NULL |
| PF-081 | LA-LIM-081-I3-4 | unknown | NULL |
| PF-081 | LA-LIM-081-I4-4 | unknown | NULL |
| PF-082 | LA-LIM-082-I1-4 | unknown | NULL |
| PF-082 | LA-LIM-082-I2-4 | unknown | NULL |
| PF-082 | LA-LIM-082-I3-4 | unknown | NULL |
| PF-082 | LA-LIM-082-I4-4 | unknown | NULL |
| PF-083 | LA-LIM-083-I1-4 | unknown | NULL |
| PF-083 | LA-LIM-083-I2-4 | unknown | NULL |
| PF-083 | LA-LIM-083-I3-4 | unknown | NULL |
| PF-083 | LA-LIM-083-I4-4 | unknown | NULL |
| PF-085 | LA-LIM-085-I1-4 | unknown | NULL |
| PF-085 | LA-LIM-085-I2-4 | unknown | NULL |
| PF-085 | LA-LIM-085-I3-4 | unknown | NULL |
| PF-085 | LA-LIM-085-I4-4 | unknown | NULL |
| PF-086 | LA-LIM-086-I1-4 | unknown | NULL |
| PF-086 | LA-LIM-086-I2-4 | unknown | NULL |
| PF-086 | LA-LIM-086-I3-4 | unknown | NULL |
| PF-086 | LA-LIM-086-I4-4 | unknown | NULL |
| PF-087 | LA-LIM-087-I1-4 | unknown | NULL |
| PF-087 | LA-LIM-087-I2-4 | unknown | NULL |
| PF-087 | LA-LIM-087-I3-4 | unknown | NULL |
| PF-087 | LA-LIM-087-I4-4 | unknown | NULL |
| PF-088 | LA-LIM-088-I1-4 | unknown | NULL |
| PF-088 | LA-LIM-088-I2-4 | unknown | NULL |
| PF-088 | LA-LIM-088-I3-4 | unknown | NULL |
| PF-088 | LA-LIM-088-I4-4 | unknown | NULL |
| PF-089 | LA-LIM-089-I1-4 | unknown | NULL |
| PF-089 | LA-LIM-089-I2-4 | unknown | NULL |
| PF-089 | LA-LIM-089-I3-4 | unknown | NULL |
| PF-089 | LA-LIM-089-I4-4 | unknown | NULL |
| PF-090 | LA-LIM-090-I1-4 | unknown | NULL |
| PF-090 | LA-LIM-090-I2-4 | unknown | NULL |
| PF-090 | LA-LIM-090-I3-4 | unknown | NULL |
| PF-090 | LA-LIM-090-I4-4 | unknown | NULL |
| PF-106 | LA-LIM-106-I1-4 | unknown | NULL |
| PF-106 | LA-LIM-106-I2-4 | unknown | NULL |
| PF-106 | LA-LIM-106-I3-4 | unknown | NULL |
| PF-106 | LA-LIM-106-I4-4 | unknown | NULL |
| PF-107 | LA-LIM-107-I1-4 | unknown | NULL |
| PF-107 | LA-LIM-107-I2-4 | unknown | NULL |
| PF-107 | LA-LIM-107-I3-4 | unknown | NULL |
| PF-107 | LA-LIM-107-I4-4 | unknown | NULL |
| PF-108 | LA-LIM-108-I1-4 | unknown | NULL |
| PF-108 | LA-LIM-108-I2-4 | unknown | NULL |
| PF-108 | LA-LIM-108-I3-4 | unknown | NULL |
| PF-108 | LA-LIM-108-I4-4 | unknown | NULL |
| PF-109 | LA-LIM-109-I1-4 | unknown | NULL |
| PF-109 | LA-LIM-109-I2-4 | unknown | NULL |
| PF-109 | LA-LIM-109-I3-4 | unknown | NULL |
| PF-109 | LA-LIM-109-I4-4 | unknown | NULL |
| PF-110 | LA-LIM-110-I1-4 | unknown | NULL |
| PF-110 | LA-LIM-110-I2-4 | unknown | NULL |
| PF-110 | LA-LIM-110-I3-4 | unknown | NULL |
| PF-110 | LA-LIM-110-I4-4 | unknown | NULL |
| PF-111 | LA-LIM-111-I1-4 | unknown | NULL |
| PF-111 | LA-LIM-111-I2-4 | unknown | NULL |
| PF-111 | LA-LIM-111-I3-4 | unknown | NULL |
| PF-111 | LA-LIM-111-I4-4 | unknown | NULL |
| PF-118 | LA-LIM-118-I1-4 | unknown | NULL |
| PF-118 | LA-LIM-118-I2-4 | unknown | NULL |
| PF-118 | LA-LIM-118-I3-4 | unknown | NULL |
| PF-118 | LA-LIM-118-I4-4 | unknown | NULL |
| PF-119 | LA-LIM-119-I1-4 | unknown | NULL |
| PF-119 | LA-LIM-119-I2-4 | unknown | NULL |
| PF-119 | LA-LIM-119-I3-4 | unknown | NULL |
| PF-119 | LA-LIM-119-I4-4 | unknown | NULL |
| PF-120 | LA-LIM-120-I1-4 | unknown | NULL |
| PF-120 | LA-LIM-120-I2-4 | unknown | NULL |
| PF-120 | LA-LIM-120-I3-4 | unknown | NULL |
| PF-120 | LA-LIM-120-I4-4 | unknown | NULL |
| PF-121 | LA-LIM-121-I1-4 | unknown | NULL |
| PF-121 | LA-LIM-121-I2-4 | unknown | NULL |
| PF-121 | LA-LIM-121-I3-4 | unknown | NULL |
| PF-121 | LA-LIM-121-I4-4 | unknown | NULL |
| PF-122 | LA-LIM-122-I1-4 | unknown | NULL |
| PF-122 | LA-LIM-122-I2-4 | unknown | NULL |
| PF-122 | LA-LIM-122-I3-4 | unknown | NULL |
| PF-122 | LA-LIM-122-I4-4 | unknown | NULL |
| PF-123 | LA-LIM-123-I1-4 | unknown | NULL |
| PF-123 | LA-LIM-123-I2-4 | unknown | NULL |
| PF-123 | LA-LIM-123-I3-4 | unknown | NULL |
| PF-123 | LA-LIM-123-I4-4 | unknown | NULL |
| PF-128 | LA-LIM-128-I1-4 | unknown | NULL |
| PF-128 | LA-LIM-128-I2-4 | unknown | NULL |
| PF-128 | LA-LIM-128-I3-4 | unknown | NULL |
| PF-128 | LA-LIM-128-I4-4 | unknown | NULL |
| PF-129 | LA-LIM-129-I1-4 | unknown | NULL |
| PF-129 | LA-LIM-129-I2-4 | unknown | NULL |
| PF-129 | LA-LIM-129-I3-4 | unknown | NULL |
| PF-129 | LA-LIM-129-I4-4 | unknown | NULL |
| PF-130 | LA-LIM-130-I1-4 | unknown | NULL |
| PF-130 | LA-LIM-130-I2-4 | unknown | NULL |
| PF-130 | LA-LIM-130-I3-4 | unknown | NULL |
| PF-130 | LA-LIM-130-I4-4 | unknown | NULL |
| PF-131 | LA-LIM-131-I1-4 | unknown | NULL |
| PF-131 | LA-LIM-131-I2-4 | unknown | NULL |
| PF-131 | LA-LIM-131-I3-4 | unknown | NULL |
| PF-131 | LA-LIM-131-I4-4 | unknown | NULL |
| PF-132 | LA-LIM-132-I1-4 | unknown | NULL |
| PF-132 | LA-LIM-132-I2-4 | unknown | NULL |
| PF-132 | LA-LIM-132-I3-4 | unknown | NULL |
| PF-132 | LA-LIM-132-I4-4 | unknown | NULL |
| PF-133 | LA-LIM-133-I1-4 | unknown | NULL |
| PF-133 | LA-LIM-133-I2-4 | unknown | NULL |
| PF-133 | LA-LIM-133-I3-4 | unknown | NULL |
| PF-133 | LA-LIM-133-I4-4 | unknown | NULL |
| PF-135 | LA-LIM-135-I1-4 | unknown | NULL |
| PF-135 | LA-LIM-135-I2-4 | unknown | NULL |
| PF-135 | LA-LIM-135-I3-4 | unknown | NULL |
| PF-135 | LA-LIM-135-I4-4 | unknown | NULL |
| PF-136 | LA-LIM-136-I1-4 | unknown | NULL |
| PF-136 | LA-LIM-136-I2-4 | unknown | NULL |
| PF-136 | LA-LIM-136-I3-4 | unknown | NULL |
| PF-136 | LA-LIM-136-I4-4 | unknown | NULL |
| PF-137 | LA-LIM-137-I1-4 | unknown | NULL |
| PF-137 | LA-LIM-137-I2-4 | unknown | NULL |
| PF-137 | LA-LIM-137-I3-4 | unknown | NULL |
| PF-137 | LA-LIM-137-I4-4 | unknown | NULL |
| PF-138 | LA-LIM-138-I1-4 | unknown | NULL |
| PF-138 | LA-LIM-138-I2-4 | unknown | NULL |
| PF-138 | LA-LIM-138-I3-4 | unknown | NULL |
| PF-138 | LA-LIM-138-I4-4 | unknown | NULL |
| PF-139 | LA-LIM-139-I1-4 | unknown | NULL |
| PF-139 | LA-LIM-139-I2-4 | unknown | NULL |
| PF-139 | LA-LIM-139-I3-4 | unknown | NULL |
| PF-139 | LA-LIM-139-I4-4 | unknown | NULL |
| PF-140 | LA-LIM-140-I1-4 | unknown | NULL |
| PF-140 | LA-LIM-140-I2-4 | unknown | NULL |
| PF-140 | LA-LIM-140-I3-4 | unknown | NULL |
| PF-140 | LA-LIM-140-I4-4 | unknown | NULL |
| PF-156 | LA-LIM-156-I1-4 | unknown | NULL |
| PF-156 | LA-LIM-156-I2-4 | unknown | NULL |
| PF-156 | LA-LIM-156-I3-4 | unknown | NULL |
| PF-156 | LA-LIM-156-I4-4 | unknown | NULL |
| PF-157 | LA-LIM-157-I1-4 | unknown | NULL |
| PF-157 | LA-LIM-157-I2-4 | unknown | NULL |
| PF-157 | LA-LIM-157-I3-4 | unknown | NULL |
| PF-157 | LA-LIM-157-I4-4 | unknown | NULL |
| PF-158 | LA-LIM-158-I1-4 | unknown | NULL |
| PF-158 | LA-LIM-158-I2-4 | unknown | NULL |
| PF-158 | LA-LIM-158-I3-4 | unknown | NULL |
| PF-158 | LA-LIM-158-I4-4 | unknown | NULL |
| PF-159 | LA-LIM-159-I1-4 | unknown | NULL |
| PF-159 | LA-LIM-159-I2-4 | unknown | NULL |
| PF-159 | LA-LIM-159-I3-4 | unknown | NULL |
| PF-159 | LA-LIM-159-I4-4 | unknown | NULL |
| PF-160 | LA-LIM-160-I1-4 | unknown | NULL |
| PF-160 | LA-LIM-160-I2-4 | unknown | NULL |
| PF-160 | LA-LIM-160-I3-4 | unknown | NULL |
| PF-160 | LA-LIM-160-I4-4 | unknown | NULL |
| PF-161 | LA-LIM-161-I1-4 | unknown | NULL |
| PF-161 | LA-LIM-161-I2-4 | unknown | NULL |
| PF-161 | LA-LIM-161-I3-4 | unknown | NULL |
| PF-161 | LA-LIM-161-I4-4 | unknown | NULL |
| PF-168 | LA-LIM-168-I1-4 | unknown | NULL |
| PF-168 | LA-LIM-168-I2-4 | unknown | NULL |
| PF-168 | LA-LIM-168-I3-4 | unknown | NULL |
| PF-168 | LA-LIM-168-I4-4 | unknown | NULL |
| PF-169 | LA-LIM-169-I1-4 | unknown | NULL |
| PF-169 | LA-LIM-169-I2-4 | unknown | NULL |
| PF-169 | LA-LIM-169-I3-4 | unknown | NULL |
| PF-169 | LA-LIM-169-I4-4 | unknown | NULL |
| PF-170 | LA-LIM-170-I1-4 | unknown | NULL |
| PF-170 | LA-LIM-170-I2-4 | unknown | NULL |
| PF-170 | LA-LIM-170-I3-4 | unknown | NULL |
| PF-170 | LA-LIM-170-I4-4 | unknown | NULL |
| PF-171 | LA-LIM-171-I1-4 | unknown | NULL |
| PF-171 | LA-LIM-171-I2-4 | unknown | NULL |
| PF-171 | LA-LIM-171-I3-4 | unknown | NULL |
| PF-171 | LA-LIM-171-I4-4 | unknown | NULL |
| PF-172 | LA-LIM-172-I1-4 | unknown | NULL |
| PF-172 | LA-LIM-172-I2-4 | unknown | NULL |
| PF-172 | LA-LIM-172-I3-4 | unknown | NULL |
| PF-172 | LA-LIM-172-I4-4 | unknown | NULL |
| PF-173 | LA-LIM-173-I1-4 | unknown | NULL |
| PF-173 | LA-LIM-173-I2-4 | unknown | NULL |
| PF-173 | LA-LIM-173-I3-4 | unknown | NULL |
| PF-173 | LA-LIM-173-I4-4 | unknown | NULL |
| PF-178 | LA-LIM-178-I1-4 | unknown | NULL |
| PF-178 | LA-LIM-178-I2-4 | unknown | NULL |
| PF-178 | LA-LIM-178-I3-4 | unknown | NULL |
| PF-178 | LA-LIM-178-I4-4 | unknown | NULL |
| PF-179 | LA-LIM-179-I1-4 | unknown | NULL |
| PF-179 | LA-LIM-179-I2-4 | unknown | NULL |
| PF-179 | LA-LIM-179-I3-4 | unknown | NULL |
| PF-179 | LA-LIM-179-I4-4 | unknown | NULL |
| PF-180 | LA-LIM-180-I1-4 | unknown | NULL |
| PF-180 | LA-LIM-180-I2-4 | unknown | NULL |
| PF-180 | LA-LIM-180-I3-4 | unknown | NULL |
| PF-180 | LA-LIM-180-I4-4 | unknown | NULL |
| PF-181 | LA-LIM-181-I1-4 | unknown | NULL |
| PF-181 | LA-LIM-181-I2-4 | unknown | NULL |
| PF-181 | LA-LIM-181-I3-4 | unknown | NULL |
| PF-181 | LA-LIM-181-I4-4 | unknown | NULL |
| PF-182 | LA-LIM-182-I1-4 | unknown | NULL |
| PF-182 | LA-LIM-182-I2-4 | unknown | NULL |
| PF-182 | LA-LIM-182-I3-4 | unknown | NULL |
| PF-182 | LA-LIM-182-I4-4 | unknown | NULL |
| PF-183 | LA-LIM-183-I1-4 | unknown | NULL |
| PF-183 | LA-LIM-183-I2-4 | unknown | NULL |
| PF-183 | LA-LIM-183-I3-4 | unknown | NULL |
| PF-183 | LA-LIM-183-I4-4 | unknown | NULL |
| PF-185 | LA-LIM-185-I1-4 | unknown | NULL |
| PF-185 | LA-LIM-185-I2-4 | unknown | NULL |
| PF-185 | LA-LIM-185-I3-4 | unknown | NULL |
| PF-185 | LA-LIM-185-I4-4 | unknown | NULL |
| PF-186 | LA-LIM-186-I1-4 | unknown | NULL |
| PF-186 | LA-LIM-186-I2-4 | unknown | NULL |
| PF-186 | LA-LIM-186-I3-4 | unknown | NULL |
| PF-186 | LA-LIM-186-I4-4 | unknown | NULL |
| PF-187 | LA-LIM-187-I1-4 | unknown | NULL |
| PF-187 | LA-LIM-187-I2-4 | unknown | NULL |
| PF-187 | LA-LIM-187-I3-4 | unknown | NULL |
| PF-187 | LA-LIM-187-I4-4 | unknown | NULL |
| PF-188 | LA-LIM-188-I1-4 | unknown | NULL |
| PF-188 | LA-LIM-188-I2-4 | unknown | NULL |
| PF-188 | LA-LIM-188-I3-4 | unknown | NULL |
| PF-188 | LA-LIM-188-I4-4 | unknown | NULL |
| PF-189 | LA-LIM-189-I1-4 | unknown | NULL |
| PF-189 | LA-LIM-189-I2-4 | unknown | NULL |
| PF-189 | LA-LIM-189-I3-4 | unknown | NULL |
| PF-189 | LA-LIM-189-I4-4 | unknown | NULL |
| PF-190 | LA-LIM-190-I1-4 | unknown | NULL |
| PF-190 | LA-LIM-190-I2-4 | unknown | NULL |
| PF-190 | LA-LIM-190-I3-4 | unknown | NULL |
| PF-190 | LA-LIM-190-I4-4 | unknown | NULL |

## FIN-050 · hard_complex

Did all February price-blocked valuations also have failed settlements? Test the proposition with state evidence.

Evidence returns 3 row(s). First result: reason=missing; event_status=settled; valuations=32. An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.

| reason | event_status | valuations |
|---|---|---|
| missing | settled | 32 |
| price_unapproved | settled | 32 |
| stale | settled | 32 |

## FIN-051 · easy_basic

What USD conversion rate is FX-CNY-2027-02-28?

Evidence returns 1 row(s). First result: fx_id=FX-CNY-2027-02-28; from_currency=CNY; to_currency=USD; rate=0.1394; as_of_date=2027-02-28. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| fx_id | from_currency | to_currency | rate | as_of_date |
|---|---|---|---|---|
| FX-CNY-2027-02-28 | CNY | USD | 0.1394 | 2027-02-28 |

## FIN-052 · easy_basic

What source and target currencies does FX-EUR-2027-01-31 use?

Evidence returns 1 row(s). First result: fx_id=FX-EUR-2027-01-31; from_currency=EUR; to_currency=USD; rate=1.072. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| fx_id | from_currency | to_currency | rate |
|---|---|---|---|
| FX-EUR-2027-01-31 | EUR | USD | 1.072 |

## FIN-053 · easy_basic

What is the self-currency USD conversion rate on 2027-02-28?

Evidence returns 1 row(s). First result: fx_id=FX-USD-2027-02-28; rate=1.0. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| fx_id | rate |
|---|---|
| FX-USD-2027-02-28 | 1.0 |

## FIN-054 · intermediate

Trace VAL-001-1-4 to its exact dated FX record.

Evidence returns 1 row(s). First result: valuation_id=VAL-001-1-4; fx_id=FX-CNY-2027-02-28; as_of_date=2027-02-28; rate=0.1394; from_currency=CNY; to_currency=USD. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| valuation_id | fx_id | as_of_date | rate | from_currency | to_currency |
|---|---|---|---|---|---|
| VAL-001-1-4 | FX-CNY-2027-02-28 | 2027-02-28 | 0.1394 | CNY | USD |

## FIN-055 · intermediate

Reconstruct USD value for VAL-003-1-4 using EUR market value and rate.

Evidence returns 1 row(s). First result: valuation_id=VAL-003-1-4; market_value_local=10275.0; rate=1.073; reconstructed_base=11025.08; market_value_base=11025.08. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| valuation_id | market_value_local | rate | reconstructed_base | market_value_base |
|---|---|---|---|---|
| VAL-003-1-4 | 10275.0 | 1.073 | 11025.08 | 11025.08 |

## FIN-056 · intermediate

Do the FX dates and valuation dates match for all February valuations?

Evidence returns 1 row(s). First result: valuations=1600; date_mismatches=0. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| valuations | date_mismatches |
|---|---|
| 1600 | 0 |

## FIN-057 · intermediate

Which local currencies feed USD valuations for PF-001 and PF-003?

Evidence returns 6 row(s). First result: portfolio_id=PF-001; from_currency=CNY; to_currency=USD; rate=0.1394. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| portfolio_id | from_currency | to_currency | rate |
|---|---|---|---|
| PF-001 | CNY | USD | 0.1394 |
| PF-001 | EUR | USD | 1.073 |
| PF-001 | USD | USD | 1.0 |
| PF-003 | CNY | USD | 0.1394 |
| PF-003 | EUR | USD | 1.073 |
| PF-003 | USD | USD | 1.0 |

## FIN-058 · hard_complex

Aggregate complete February values by source currency with separate local and USD totals.

Evidence returns 3 row(s). First result: from_currency=CNY; valuations=512; local_total=44994874.48; usd_total=6272285.36. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| from_currency | valuations | local_total | usd_total |
|---|---|---|---|
| CNY | 512 | 44994874.48 | 6272285.36 |
| EUR | 480 | 5876950.06 | 6305967.36 |
| USD | 512 | 6656234.05 | 6656234.05 |

## FIN-059 · hard_complex

Compare PF-003 January and February USD values and FX rates without calling the difference trading profit.

Evidence returns 6 row(s). First result: as_of_date=2027-01-31; from_currency=CNY; rate=0.1394; usd_value=19671.93. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| as_of_date | from_currency | rate | usd_value |
|---|---|---|---|
| 2027-01-31 | CNY | 0.1394 | 19671.93 |
| 2027-01-31 | EUR | 1.072 | 19541.7 |
| 2027-01-31 | USD | 1.0 | 36645.88 |
| 2027-02-28 | CNY | 0.1394 | 18932.84 |
| 2027-02-28 | EUR | 1.073 | 19522.47 |
| 2027-02-28 | USD | 1.0 | 34916.37 |

## FIN-060 · hard_complex

Across the full complete actual valuation-snapshot history from November 2026 through February 2027, count valuations and audit whether FX source currency matches each instrument and target currency is USD. Include every actual valuation date, not only the current snapshot.

Evidence returns 1 row(s). First result: valuations=6304; currency_mismatches=0. Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.

| valuations | currency_mismatches |
|---|---|
| 6304 | 0 |

## FIN-061 · easy_basic

What method is used by VAL-001-2-4?

Evidence returns 1 row(s). First result: valuation_id=VAL-001-2-4; valuation_method=bond_dirty; valuation_status=complete. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| valuation_id | valuation_method | valuation_status |
|---|---|---|
| VAL-001-2-4 | bond_dirty | complete |

## FIN-062 · easy_basic

What USD market value and cost belong to VAL-002-1-4?

Evidence returns 1 row(s). First result: valuation_id=VAL-002-1-4; market_value_base=10355.0; cost_value_base=10893.17; currency=USD. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| valuation_id | market_value_base | cost_value_base | currency |
|---|---|---|---|
| VAL-002-1-4 | 10355.0 | 10893.17 | USD |

## FIN-063 · easy_basic

What unrealized USD P&L belongs to VAL-004-2-4?

Evidence returns 1 row(s). First result: valuation_id=VAL-004-2-4; unrealized_pnl_base=0.0; currency=USD. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| valuation_id | unrealized_pnl_base | currency |
|---|---|---|
| VAL-004-2-4 | 0.0 | USD |

## FIN-064 · intermediate

Explain the complete equity valuation equation for VAL-001-1-4.

Evidence returns 1 row(s). First result: valuation_id=VAL-001-1-4; trade_basis_quantity=3766.0; price=18.6; price_multiplier=1.0; rate=0.1394; market_value_base=9764.64. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| valuation_id | trade_basis_quantity | price | price_multiplier | rate | market_value_base |
|---|---|---|---|---|---|
| VAL-001-1-4 | 3766.0 | 18.6 | 1.0 | 0.1394 | 9764.64 |

## FIN-065 · intermediate

Explain the full-price-per-100 bond valuation equation for VAL-003-2-4.

Evidence returns 1 row(s). First result: valuation_id=VAL-003-2-4; trade_basis_quantity=7670.0; price_basis=dirty_per_100; price=103.25; price_multiplier=0.01; rate=1.073; market_value_base=8497.39. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| valuation_id | trade_basis_quantity | price_basis | price | price_multiplier | rate | market_value_base |
|---|---|---|---|---|---|---|
| VAL-003-2-4 | 7670.0 | dirty_per_100 | 103.25 | 0.01 | 1.073 | 8497.39 |

## FIN-066 · intermediate

Reconcile unrealized P&L of PF-001 from USD market value minus translated cost.

Evidence returns 8 row(s). First result: valuation_id=VAL-001-1-4; market_value_base=9764.64; cost_value_base=10949.19; unrealized_pnl_base=-1184.55; reconstructed_pnl=-1184.55. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| valuation_id | market_value_base | cost_value_base | unrealized_pnl_base | reconstructed_pnl |
|---|---|---|---|---|
| VAL-001-1-4 | 9764.64 | 10949.19 | -1184.55 | -1184.55 |
| VAL-001-2-4 | 8524.87 | 8524.87 | 0.0 | 0.0 |
| VAL-001-3-4 | 9526.0 | 9526.0 | 0.0 | 0.0 |
| VAL-001-4-4 | 8563.75 | 8500.0 | 63.75 | 63.75 |
| VAL-001-5-4 | 8557.18 | 8557.18 | 0.0 | 0.0 |
| VAL-001-6-4 | 8497.03 | 8561.9 | -64.87 | -64.87 |
| VAL-001-7-4 | 9432.31 | 8662.33 | 769.98 | 769.98 |
| VAL-001-8-4 | 8499.01 | 8561.96 | -62.95 | -62.95 |

## FIN-067 · intermediate

Why is a partial sum for PF-037 not an accepted portfolio value? Show total and complete position counts.

Evidence returns 1 row(s). First result: portfolio_id=PF-037; positions=8; complete_valuations=7; partial_usd_value=60718.01. A partial portfolio sum is displayed only for investigation. It cannot be accepted as a complete valuation or a concentration denominator.

| portfolio_id | positions | complete_valuations | partial_usd_value |
|---|---|---|---|
| PF-037 | 8 | 7 | 60718.01 |

## FIN-068 · hard_complex

By actual valuation date, reconcile fully accepted versus incomplete portfolio counts and total accepted portfolio value, excluding partial totals.

Evidence returns 4 row(s). First result: as_of_date=2026-11-30; portfolios=200; accepted_portfolios=200; incomplete_portfolios=0; accepted_usd_value=22359989.75. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| as_of_date | portfolios | accepted_portfolios | incomplete_portfolios | accepted_usd_value |
|---|---|---|---|---|
| 2026-11-30 | 200 | 200 | 0 | 22359989.75 |
| 2026-12-31 | 200 | 200 | 0 | 21624861.18 |
| 2027-01-31 | 200 | 200 | 0 | 21206090.16 |
| 2027-02-28 | 200 | 104 | 96 | 11457733.07 |

## FIN-069 · hard_complex

List each accepted February portfolio and its USD total value, accepting only portfolios whose eight positions all have complete valuation; return the complete portfolio-level list, not just a grand total.

Evidence returns 104 row(s). First result: portfolio_id=PF-001; accepted_usd_value=71364.79. Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.

| portfolio_id | accepted_usd_value |
|---|---|
| PF-001 | 71364.79 |
| PF-002 | 71229.21 |
| PF-003 | 73371.68 |
| PF-004 | 70667.49 |
| PF-005 | 72308.13 |
| PF-012 | 71217.32 |
| PF-013 | 73401.53 |
| PF-014 | 70549.95 |
| PF-015 | 72583.2 |
| PF-016 | 71584.75 |
| PF-017 | 71098.5 |
| PF-024 | 70660.53 |
| PF-025 | 72271.91 |
| PF-026 | 71673.6 |
| PF-027 | 71546.67 |
| PF-034 | 70402.78 |
| PF-041 | 136178.6 |
| PF-042 | 137928.24 |
| PF-043 | 141402.59 |
| PF-044 | 140612.5 |
| PF-045 | 143881.76 |
| PF-046 | 71107.96 |
| PF-047 | 71653.91 |
| PF-048 | 72964.05 |
| PF-049 | 70732.89 |
| PF-050 | 72062.18 |
| PF-051 | 85684.44 |
| PF-052 | 85567.87 |
| PF-053 | 88064.66 |
| PF-054 | 84704.85 |
| PF-055 | 86742.12 |
| PF-062 | 85395.74 |
| PF-063 | 87958.89 |
| PF-064 | 84751.56 |
| PF-065 | 87091.91 |
| PF-066 | 85653.91 |
| PF-067 | 85296.25 |
| PF-074 | 84684.59 |
| PF-075 | 86714.03 |
| PF-076 | 85987.5 |
| PF-077 | 85615.05 |
| PF-084 | 84454.51 |
| PF-091 | 163340.85 |
| PF-092 | 165421.11 |
| PF-093 | 169667.34 |
| PF-094 | 168685.27 |
| PF-095 | 172282.39 |
| PF-096 | 85324.62 |
| PF-097 | 85736.92 |
| PF-098 | 87533.26 |
| PF-099 | 84817.34 |
| PF-100 | 86511.03 |
| PF-101 | 99815.97 |
| PF-102 | 99791.46 |
| PF-103 | 102768.05 |
| PF-104 | 98842.26 |
| PF-105 | 101290.84 |
| PF-112 | 99594.97 |
| PF-113 | 102532.56 |
| PF-114 | 98846.23 |
| PF-115 | 101487.68 |
| PF-116 | 100057.99 |
| PF-117 | 99498.25 |
| PF-124 | 98714.06 |
| PF-125 | 101108.81 |
| PF-126 | 100212.48 |
| PF-127 | 99919.21 |
| PF-134 | 98538.29 |
| PF-141 | 190668.25 |
| PF-142 | 193039.39 |
| PF-143 | 197937.74 |
| PF-144 | 196713.13 |
| PF-145 | 201265.72 |
| PF-146 | 99531.65 |
| PF-147 | 100182.85 |
| PF-148 | 102151.21 |
| PF-149 | 98989.07 |
| PF-150 | 101108.52 |
| PF-151 | 114313.27 |
| PF-152 | 114020.57 |
| PF-153 | 117462.94 |
| PF-154 | 112826.13 |
| PF-155 | 115619.66 |
| PF-162 | 113898.03 |
| PF-163 | 117286.51 |
| PF-164 | 112972.39 |
| PF-165 | 116205.85 |
| PF-166 | 114233.62 |
| PF-167 | 113713.78 |
| PF-174 | 112855.2 |
| PF-175 | 115563.78 |
| PF-176 | 114712.44 |
| PF-177 | 114196.52 |
| PF-184 | 112603.78 |
| PF-191 | 217721.56 |
| PF-192 | 220416.86 |
| PF-193 | 226172.07 |
| PF-194 | 224792.51 |
| PF-195 | 229889.15 |
| PF-196 | 113747.5 |
| PF-197 | 114347.06 |
| PF-198 | 116832.73 |
| PF-199 | 113053.44 |
| PF-200 | 115524.35 |

## FIN-070 · hard_complex

Reconstruct the January sale P&L for OP-001-1 from opening cost plus November and December purchases; compare with its recorded realized P&L.

Evidence returns 1 row(s). First result: opening_id=OP-001-1; position_id=POS-001-1-3; opening_quantity=3426.0; prior_buy_cost=5219.0; prior_buy_quantity=255.0; sold_quantity=85.0; reconstructed_realized_pnl=-132.86. Pre-sale weighted-average unit cost = (opening cost + eligible prior buy costs)/(opening quantity + eligible prior buy quantity); multiply execution-price minus that cost by sold quantity.

| opening_id | position_id | opening_quantity | prior_buy_cost | prior_buy_quantity | sold_quantity | reconstructed_realized_pnl | realized_pnl |
|---|---|---|---|---|---|---|---|
| OP-001-1 | POS-001-1-3 | 3426.0 | 5219.0 | 255.0 | 85.0 | -132.86 | -132.86 |

## FIN-071 · easy_basic

What is the current concentration limit LIM-041-I1?

Evidence returns 1 row(s). First result: limit_id=LIM-041-I1; entity_id=ISS-008; measure=issuer_ratio; threshold=0.3; effective_from_date=2026-11-01; effective_to_date=2027-03-31. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| limit_id | entity_id | measure | threshold | effective_from_date | effective_to_date |
|---|---|---|---|---|---|
| LIM-041-I1 | ISS-008 | issuer_ratio | 0.3 | 2026-11-01 | 2027-03-31 |

## FIN-072 · easy_basic

What is the result of LA-LIM-041-I1-4?

Evidence returns 1 row(s). First result: assessment_id=LA-LIM-041-I1-4; observed_value=0.12573; assessment_status=within; excess_value=0.0. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| assessment_id | observed_value | assessment_status | excess_value |
|---|---|---|---|
| LA-LIM-041-I1-4 | 0.12573 | within | 0.0 |

## FIN-073 · easy_basic

What is the February denominator for IE-001-1-4?

Evidence returns 1 row(s). First result: exposure_id=IE-001-1-4; exposure_amount=18289.51; denominator_amount=71364.79; ratio=0.256282; currency=USD; portfolio_name=Alder Technology Core Portfolio; issuer_name=Alder Technology Holdings. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| exposure_id | exposure_amount | denominator_amount | ratio | currency | portfolio_name | issuer_name |
|---|---|---|---|---|---|---|
| IE-001-1-4 | 18289.51 | 71364.79 | 0.256282 | USD | Alder Technology Core Portfolio | Alder Technology Holdings |

## FIN-074 · intermediate

Which valuations contribute to IE-041-1-4?

Evidence returns 2 row(s). First result: contribution_id=EC-IE-041-1-4-VAL-041-5-4; valuation_id=VAL-041-5-4; contribution_amount=8558.0. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| contribution_id | valuation_id | contribution_amount |
|---|---|---|
| EC-IE-041-1-4-VAL-041-5-4 | VAL-041-5-4 | 8558.0 |
| EC-IE-041-1-4-VAL-041-6-4 | VAL-041-6-4 | 8563.75 |

## FIN-075 · intermediate

Reconcile IE-041-1-4 exposure from its two position contributions.

Evidence returns 1 row(s). First result: exposure_id=IE-041-1-4; exposure_amount=17121.75; contribution_total=17121.75; ratio=0.12573; denominator_amount=136178.6. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| exposure_id | exposure_amount | contribution_total | ratio | denominator_amount |
|---|---|---|---|---|
| IE-041-1-4 | 17121.75 | 17121.75 | 0.12573 | 136178.6 |

## FIN-076 · intermediate

Trace PF-043’s current issuer breaches to issuer names and thresholds.

Evidence returns 1 row(s). First result: portfolio_id=PF-043; name=Cedar Utilities Holdings; assessment_id=LA-LIM-043-I3-4; observed_value=0.622266; threshold=0.3; assessment_status=breach. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| portfolio_id | name | assessment_id | observed_value | threshold | assessment_status |
|---|---|---|---|---|---|
| PF-043 | Cedar Utilities Holdings | LA-LIM-043-I3-4 | 0.622266 | 0.3 | breach |

## FIN-077 · intermediate

Does PF-035 have a complete denominator for issuer concentration?

Evidence returns 4 row(s). First result: exposure_id=IE-035-1-4; exposure_status=blocked; denominator_amount=unknown (NULL); ratio=unknown (NULL). Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| exposure_id | exposure_status | denominator_amount | ratio |
|---|---|---|---|
| IE-035-1-4 | blocked | NULL | NULL |
| IE-035-2-4 | blocked | NULL | NULL |
| IE-035-3-4 | blocked | NULL | NULL |
| IE-035-4-4 | blocked | NULL | NULL |

## FIN-078 · hard_complex

List all current issuer breaches with the source issuer and excess in ratio points.

Evidence returns 20 row(s). First result: portfolio_id=PF-041; entity_id=ISS-041; observed_value=0.608018; threshold=0.3; excess_value=0.308018. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| portfolio_id | entity_id | observed_value | threshold | excess_value |
|---|---|---|---|---|
| PF-041 | ISS-041 | 0.608018 | 0.3 | 0.308018 |
| PF-042 | ISS-042 | 0.620863 | 0.3 | 0.320863 |
| PF-043 | ISS-043 | 0.622266 | 0.3 | 0.322266 |
| PF-044 | ISS-044 | 0.640044 | 0.3 | 0.340044 |
| PF-045 | ISS-045 | 0.638815 | 0.3 | 0.338815 |
| PF-091 | ISS-041 | 0.608459 | 0.3 | 0.308459 |
| PF-092 | ISS-042 | 0.620811 | 0.3 | 0.320811 |
| PF-093 | ISS-043 | 0.622339 | 0.3 | 0.322339 |
| PF-094 | ISS-044 | 0.640422 | 0.3 | 0.340422 |
| PF-095 | ISS-045 | 0.639452 | 0.3 | 0.339452 |
| PF-141 | ISS-041 | 0.608215 | 0.3 | 0.308215 |
| PF-142 | ISS-042 | 0.621069 | 0.3 | 0.321069 |
| PF-143 | ISS-043 | 0.622397 | 0.3 | 0.322397 |
| PF-144 | ISS-044 | 0.640844 | 0.3 | 0.340844 |
| PF-145 | ISS-045 | 0.638768 | 0.3 | 0.338768 |
| PF-191 | ISS-041 | 0.608826 | 0.3 | 0.308826 |
| PF-192 | ISS-042 | 0.621445 | 0.3 | 0.321445 |
| PF-193 | ISS-043 | 0.62252 | 0.3 | 0.32252 |
| PF-194 | ISS-044 | 0.64117 | 0.3 | 0.34117 |
| PF-195 | ISS-045 | 0.639411 | 0.3 | 0.339411 |

## FIN-079 · hard_complex

For every complete portfolio at 2027-02-28, report issuer count and the sum of all issuer shares; do they sum to one?

Evidence returns 104 row(s). First result: portfolio_id=PF-001; sum_ratio=1.0; issuers=4. Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.

| portfolio_id | sum_ratio | issuers |
|---|---|---|
| PF-001 | 1.0 | 4 |
| PF-002 | 1.0 | 4 |
| PF-003 | 0.999999 | 4 |
| PF-004 | 1.0 | 4 |
| PF-005 | 1.0 | 4 |
| PF-012 | 1.000001 | 4 |
| PF-013 | 1.000001 | 4 |
| PF-014 | 1.0 | 4 |
| PF-015 | 1.0 | 4 |
| PF-016 | 1.0 | 4 |
| PF-017 | 1.0 | 4 |
| PF-024 | 0.999999 | 4 |
| PF-025 | 1.0 | 4 |
| PF-026 | 0.999999 | 4 |
| PF-027 | 1.0 | 4 |
| PF-034 | 0.999999 | 4 |
| PF-041 | 1.0 | 4 |
| PF-042 | 0.999999 | 4 |
| PF-043 | 1.0 | 4 |
| PF-044 | 1.0 | 4 |
| PF-045 | 0.999999 | 4 |
| PF-046 | 1.0 | 4 |
| PF-047 | 1.0 | 4 |
| PF-048 | 1.0 | 4 |
| PF-049 | 1.0 | 4 |
| PF-050 | 1.0 | 4 |
| PF-051 | 1.0 | 4 |
| PF-052 | 0.999999 | 4 |
| PF-053 | 1.0 | 4 |
| PF-054 | 1.0 | 4 |
| PF-055 | 1.0 | 4 |
| PF-062 | 1.0 | 4 |
| PF-063 | 1.0 | 4 |
| PF-064 | 1.0 | 4 |
| PF-065 | 1.0 | 4 |
| PF-066 | 0.999999 | 4 |
| PF-067 | 1.0 | 4 |
| PF-074 | 1.0 | 4 |
| PF-075 | 1.0 | 4 |
| PF-076 | 1.000001 | 4 |
| PF-077 | 1.0 | 4 |
| PF-084 | 0.999999 | 4 |
| PF-091 | 1.0 | 4 |
| PF-092 | 1.0 | 4 |
| PF-093 | 1.0 | 4 |
| PF-094 | 1.0 | 4 |
| PF-095 | 1.000001 | 4 |
| PF-096 | 1.000001 | 4 |
| PF-097 | 1.0 | 4 |
| PF-098 | 1.0 | 4 |
| PF-099 | 1.0 | 4 |
| PF-100 | 1.0 | 4 |
| PF-101 | 1.0 | 4 |
| PF-102 | 0.999999 | 4 |
| PF-103 | 0.999999 | 4 |
| PF-104 | 1.0 | 4 |
| PF-105 | 0.999999 | 4 |
| PF-112 | 1.0 | 4 |
| PF-113 | 1.0 | 4 |
| PF-114 | 1.0 | 4 |
| PF-115 | 1.0 | 4 |
| PF-116 | 1.0 | 4 |
| PF-117 | 1.0 | 4 |
| PF-124 | 1.0 | 4 |
| PF-125 | 1.0 | 4 |
| PF-126 | 1.000001 | 4 |
| PF-127 | 1.0 | 4 |
| PF-134 | 0.999999 | 4 |
| PF-141 | 1.000001 | 4 |
| PF-142 | 0.999999 | 4 |
| PF-143 | 1.0 | 4 |
| PF-144 | 1.0 | 4 |
| PF-145 | 1.0 | 4 |
| PF-146 | 1.0 | 4 |
| PF-147 | 1.0 | 4 |
| PF-148 | 1.0 | 4 |
| PF-149 | 1.0 | 4 |
| PF-150 | 1.000001 | 4 |
| PF-151 | 1.0 | 4 |
| PF-152 | 1.0 | 4 |
| PF-153 | 1.0 | 4 |
| PF-154 | 1.0 | 4 |
| PF-155 | 1.000001 | 4 |
| PF-162 | 1.000001 | 4 |
| PF-163 | 1.0 | 4 |
| PF-164 | 1.0 | 4 |
| PF-165 | 1.0 | 4 |
| PF-166 | 1.0 | 4 |
| PF-167 | 0.999999 | 4 |
| PF-174 | 1.0 | 4 |
| PF-175 | 1.000001 | 4 |
| PF-176 | 1.000001 | 4 |
| PF-177 | 1.000001 | 4 |
| PF-184 | 0.999999 | 4 |
| PF-191 | 1.0 | 4 |
| PF-192 | 1.0 | 4 |
| PF-193 | 1.0 | 4 |
| PF-194 | 0.999999 | 4 |
| PF-195 | 1.0 | 4 |
| PF-196 | 1.0 | 4 |
| PF-197 | 1.0 | 4 |
| PF-198 | 1.0 | 4 |
| PF-199 | 1.0 | 4 |
| PF-200 | 1.000001 | 4 |

## FIN-080 · hard_complex

For current PF-041 issuer breaches, trace contributing valuations to opening balances, related current-month trades and settlement outcomes; do not attribute the whole stock exposure to those trades.

Evidence returns 2 row(s). First result: assessment_id=LA-LIM-041-I3-4; exposure_id=IE-041-3-4; issuer_id=ISS-041; valuation_id=VAL-041-1-4; position_id=POS-041-1-4; instrument_id=INS-081; opening_quantity=1957.0. Valuations contribute to the issuer numerator. Opening balances are stocks, and linked current-month fills are changes; the whole stock exposure must not be attributed to those fills.

| assessment_id | exposure_id | issuer_id | valuation_id | position_id | instrument_id | opening_quantity | trade_basis_quantity | trade_id | side | trade_quantity | instruction_id | due_date | event_status | settled_quantity | remaining_quantity | failure_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LA-LIM-041-I3-4 | IE-041-3-4 | ISS-041 | VAL-041-1-4 | POS-041-1-4 | INS-081 | 1957.0 | 2149.0 | TR-041-1-4 | buy | 96.0 | SI-041-1-4 | 2027-02-10 | settled | 96.0 | 0.0 | none |
| LA-LIM-041-I3-4 | IE-041-3-4 | ISS-041 | VAL-041-2-4 | POS-041-2-4 | INS-082 | 43689.0 | 37137.0 | TR-041-2-4 | sell | 2184.0 | SI-041-2-4 | 2027-02-12 | settled | 2184.0 | 0.0 | none |

## FIN-081 · easy_basic

What is CE-046-4’s unsettled USD receivable?

Evidence returns 1 row(s). First result: exposure_id=CE-046-4; unsettled_receivable=2002.41; currency=USD; as_of_date=2027-02-28. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| exposure_id | unsettled_receivable | currency | as_of_date |
|---|---|---|---|
| CE-046-4 | 2002.41 | USD | 2027-02-28 |

## FIN-082 · easy_basic

What is the receivable threshold for PF-046?

Evidence returns 1 row(s). First result: limit_id=LIM-046-C; threshold=500.0; currency=USD; measure=receivable_amount. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| limit_id | threshold | currency | measure |
|---|---|---|---|
| LIM-046-C | 500.0 | USD | receivable_amount |

## FIN-083 · easy_basic

Which counterparty is recorded on CE-047-4?

Evidence returns 1 row(s). First result: exposure_id=CE-047-4; counterparty_id=CP-047; counterparty_name=Grove Utilities Securities. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| exposure_id | counterparty_id | counterparty_name |
|---|---|---|
| CE-047-4 | CP-047 | Grove Utilities Securities |

## FIN-084 · intermediate

Compare PF-001’s settled receivable with PF-019’s pending receivable.

Evidence returns 2 row(s). First result: portfolio_id=PF-001; unsettled_receivable=0.0; currency=USD. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| portfolio_id | unsettled_receivable | currency |
|---|---|---|
| PF-001 | 0.0 | USD |
| PF-019 | 2000.37 | USD |

## FIN-085 · intermediate

Audit every February SELL trade for PF-046 as of 2027-02-28, including fully settled trades with open_quantity=0. Return each trade and its side, instrument currency, remaining quantity, execution price, price multiplier and stored settlement failure reason; this is the full trade audit scope.

Evidence returns 7 row(s). First result: trade_id=TR-046-2-4; side=sell; currency=CNY; open_quantity=3632.0; execution_price=99.0; price_multiplier=0.01; failure_reason=cash_mismatch. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| trade_id | side | currency | open_quantity | execution_price | price_multiplier | failure_reason |
|---|---|---|---|---|---|---|
| TR-046-2-4 | sell | CNY | 3632.0 | 99.0 | 0.01 | cash_mismatch |
| TR-046-3-4 | sell | EUR | 0.0 | 25.0 | 1.0 | none |
| TR-046-4-4 | sell | EUR | 450.0 | 103.25 | 0.01 | cash_mismatch |
| TR-046-5-4 | sell | CNY | 0.0 | 32.0 | 1.0 | none |
| TR-046-6-4 | sell | CNY | 3492.0 | 103.0 | 0.01 | cash_mismatch |
| TR-046-7-4 | sell | CNY | 0.0 | 32.4 | 1.0 | none |
| TR-046-8-4 | sell | CNY | 3632.0 | 99.0 | 0.01 | cash_mismatch |

## FIN-086 · intermediate

What assessment and excess amount explain PF-048’s current counterparty breach?

Evidence returns 1 row(s). First result: assessment_id=LA-LIM-048-C-4; counterparty_exposure_id=CE-048-4; observed_value=1997.25; threshold=500.0; excess_value=1497.25; assessment_status=breach. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| assessment_id | counterparty_exposure_id | observed_value | threshold | excess_value | assessment_status |
|---|---|---|---|---|---|
| LA-LIM-048-C-4 | CE-048-4 | 1997.25 | 500.0 | 1497.25 | breach |

## FIN-087 · intermediate

Are PF-029 and PF-046 both settlement failures but different limit outcomes?

Evidence returns 2 row(s). First result: portfolio_id=PF-029; observed_value=2007.14; threshold=1000000.0; assessment_status=within. The same settlement-failure state can be within a high receivable limit but breach a lower limit; compare amount and applicable threshold.

| portfolio_id | observed_value | threshold | assessment_status |
|---|---|---|---|
| PF-029 | 2007.14 | 1000000.0 | within |
| PF-046 | 2002.41 | 500.0 | breach |

## FIN-088 · hard_complex

Trace PF-046’s current receivable breach to each open sell instruction, cumulative settlement state and USD contribution; reconcile the total against the assessed limit. Display each USD trade_contribution rounded to 2 decimal places; sum the unrounded quantity × execution_price × price_multiplier × FX contributions first, then round reconstructed_receivable to 2 decimal places.

Evidence returns 4 row(s). First result: portfolio_id=PF-046; counterparty_id=CP-046; assessment_id=LA-LIM-046-C-4; assessment_status=breach; threshold=500.0; trade_id=TR-046-2-4; instruction_id=SI-046-2-4. Accumulate transfers before computing each open sell contribution. Sum unrounded contributions then round the aggregate, and reconcile that aggregate with the assessed receivable; display-row rounding can differ.

| portfolio_id | counterparty_id | assessment_id | assessment_status | threshold | trade_id | instruction_id | due_date | event_status | failure_reason | trade_quantity | settled_quantity | open_quantity | trade_contribution | reconstructed_receivable | unsettled_receivable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PF-046 | CP-046 | LA-LIM-046-C-4 | breach | 500.0 | TR-046-2-4 | SI-046-2-4 | 2027-02-12 | failed | cash_mismatch | 3632.0 | 0.0 | 3632.0 | 501.24 | 2002.41 | 2002.41 |
| PF-046 | CP-046 | LA-LIM-046-C-4 | breach | 500.0 | TR-046-4-4 | SI-046-4-4 | 2027-02-17 | failed | cash_mismatch | 450.0 | 0.0 | 450.0 | 498.54 | 2002.41 | 2002.41 |
| PF-046 | CP-046 | LA-LIM-046-C-4 | breach | 500.0 | TR-046-6-4 | SI-046-6-4 | 2027-02-22 | failed | cash_mismatch | 3492.0 | 0.0 | 3492.0 | 501.39 | 2002.41 | 2002.41 |
| PF-046 | CP-046 | LA-LIM-046-C-4 | breach | 500.0 | TR-046-8-4 | SI-046-8-4 | 2027-02-24 | failed | cash_mismatch | 3632.0 | 0.0 | 3632.0 | 501.24 | 2002.41 | 2002.41 |

## FIN-089 · hard_complex

Which current counterparty receivable limits breach, and what is total excess USD?

Evidence returns 12 row(s). First result: portfolio_id=PF-046; limit_id=LIM-046-C; assessment_id=LA-LIM-046-C-4; observed_value=2002.41; threshold=500.0; excess_value=1502.41; breached_limits=12. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| portfolio_id | limit_id | assessment_id | observed_value | threshold | excess_value | breached_limits | excess_usd |
|---|---|---|---|---|---|---|---|
| PF-046 | LIM-046-C | LA-LIM-046-C-4 | 2002.41 | 500.0 | 1502.41 | 12 | 25271.49 |
| PF-047 | LIM-047-C | LA-LIM-047-C-4 | 2010.15 | 500.0 | 1510.15 | 12 | 25271.49 |
| PF-048 | LIM-048-C | LA-LIM-048-C-4 | 1997.25 | 500.0 | 1497.25 | 12 | 25271.49 |
| PF-096 | LIM-096-C | LA-LIM-096-C-4 | 2403.27 | 500.0 | 1903.27 | 12 | 25271.49 |
| PF-097 | LIM-097-C | LA-LIM-097-C-4 | 2414.85 | 500.0 | 1914.85 | 12 | 25271.49 |
| PF-098 | LIM-098-C | LA-LIM-098-C-4 | 2400.98 | 500.0 | 1900.98 | 12 | 25271.49 |
| PF-146 | LIM-146-C | LA-LIM-146-C-4 | 2803.59 | 500.0 | 2303.59 | 12 | 25271.49 |
| PF-147 | LIM-147-C | LA-LIM-147-C-4 | 2815.19 | 500.0 | 2315.19 | 12 | 25271.49 |
| PF-148 | LIM-148-C | LA-LIM-148-C-4 | 2798.28 | 500.0 | 2298.28 | 12 | 25271.49 |
| PF-196 | LIM-196-C | LA-LIM-196-C-4 | 3203.9 | 500.0 | 2703.9 | 12 | 25271.49 |
| PF-197 | LIM-197-C | LA-LIM-197-C-4 | 3219.61 | 500.0 | 2719.61 | 12 | 25271.49 |
| PF-198 | LIM-198-C | LA-LIM-198-C-4 | 3202.01 | 500.0 | 2702.01 | 12 | 25271.49 |

## FIN-090 · hard_complex

Compare all seven business branches by current receivable and breached receivable limits.

Evidence returns 7 row(s). First result: branch=counterparty_breach; portfolios=12; usd_receivable=31271.49; breached_limits=12. Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.

| branch | portfolios | usd_receivable | breached_limits |
|---|---|---|---|
| counterparty_breach | 12 | 31271.49 | 12 |
| failed_settlement | 24 | 62552.71 | 0 |
| future_limit | 8 | 0.0 | 0 |
| issuer_breach | 20 | 0.0 | 0 |
| normal | 72 | 0.0 | 0 |
| pending_settlement | 40 | 78175.85 | 0 |
| price_exception | 24 | 0.0 | 0 |

## FIN-091 · easy_basic

When does the next version of PF-049 issuer limit LIM-049-I1 become effective?

Evidence returns 1 row(s). First result: limit_id=LIM-049-I1-NEXT; effective_from_date=2027-03-15; threshold=0.2; decision_date=2027-02-28. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| limit_id | effective_from_date | threshold | decision_date |
|---|---|---|---|
| LIM-049-I1-NEXT | 2027-03-15 | 0.2 | 2027-02-28 |

## FIN-092 · easy_basic

What current and planning dates exist for positions?

Evidence returns 5 row(s). First result: as_of_date=2026-11-30; view_kind=actual; positions=1600. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| as_of_date | view_kind | positions |
|---|---|---|
| 2026-11-30 | actual | 1600 |
| 2026-12-31 | actual | 1600 |
| 2027-01-31 | actual | 1600 |
| 2027-02-28 | actual | 1600 |
| 2027-03-31 | planned | 1600 |

## FIN-093 · easy_basic

Is VAL-049-1-5 a current fact or a forecast?

Evidence returns 1 row(s). First result: valuation_id=VAL-049-1-5; as_of_date=2027-03-31; view_kind=planned; known_date=2027-02-28. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| valuation_id | as_of_date | view_kind | known_date |
|---|---|---|---|
| VAL-049-1-5 | 2027-03-31 | planned | 2027-02-28 |

## FIN-094 · intermediate

Which issuer limits apply to PF-049 on 2027-02-28?

Evidence returns 4 row(s). First result: limit_id=LIM-049-I1; entity_id=ISS-006; threshold=0.8; effective_from_date=2026-11-01; effective_to_date=2027-03-14. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| limit_id | entity_id | threshold | effective_from_date | effective_to_date |
|---|---|---|---|---|
| LIM-049-I1 | ISS-006 | 0.8 | 2026-11-01 | 2027-03-14 |
| LIM-049-I2 | ISS-016 | 0.8 | 2026-11-01 | 2027-03-14 |
| LIM-049-I3 | ISS-028 | 0.8 | 2026-11-01 | 2027-03-14 |
| LIM-049-I4 | ISS-049 | 0.8 | 2026-11-01 | 2027-03-14 |

## FIN-095 · intermediate

Which issuer limits apply to PF-049’s March planning snapshot?

Evidence returns 4 row(s). First result: limit_id=LIM-049-I1-NEXT; entity_id=ISS-006; threshold=0.2; effective_from_date=2027-03-15; effective_to_date=2027-03-31. Only the version effective from 2027-03-15 applies to the March plan; it must not replace the version effective in February.

| limit_id | entity_id | threshold | effective_from_date | effective_to_date |
|---|---|---|---|---|
| LIM-049-I1-NEXT | ISS-006 | 0.2 | 2027-03-15 | 2027-03-31 |
| LIM-049-I2-NEXT | ISS-016 | 0.2 | 2027-03-15 | 2027-03-31 |
| LIM-049-I3-NEXT | ISS-028 | 0.2 | 2027-03-15 | 2027-03-31 |
| LIM-049-I4-NEXT | ISS-049 | 0.2 | 2027-03-15 | 2027-03-31 |

## FIN-096 · intermediate

Compare PF-050’s February actual and March planned issuer assessments.

Evidence returns 8 row(s). First result: as_of_date=2027-02-28; view_kind=actual; limit_id=LIM-050-I1; threshold=0.8; observed_value=0.242637; assessment_status=within. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| as_of_date | view_kind | limit_id | threshold | observed_value | assessment_status |
|---|---|---|---|---|---|
| 2027-02-28 | actual | LIM-050-I1 | 0.8 | 0.242637 | within |
| 2027-02-28 | actual | LIM-050-I2 | 0.8 | 0.231968 | within |
| 2027-02-28 | actual | LIM-050-I3 | 0.8 | 0.242454 | within |
| 2027-02-28 | actual | LIM-050-I4 | 0.8 | 0.282941 | within |
| 2027-03-31 | planned | LIM-050-I1-NEXT | 0.2 | 0.243924 | breach |
| 2027-03-31 | planned | LIM-050-I2-NEXT | 0.2 | 0.228119 | breach |
| 2027-03-31 | planned | LIM-050-I3-NEXT | 0.2 | 0.241992 | breach |
| 2027-03-31 | planned | LIM-050-I4-NEXT | 0.2 | 0.285965 | breach |

## FIN-097 · intermediate

Were all future mandate changes known by the February as-of date?

Evidence returns 32 row(s). First result: limit_id=LIM-049-I1-NEXT; decision_date=2027-02-28; effective_from_date=2027-03-15. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| limit_id | decision_date | effective_from_date |
|---|---|---|
| LIM-049-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-049-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-049-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-049-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-050-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-050-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-050-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-050-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-099-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-099-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-099-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-099-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-100-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-100-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-100-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-100-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-149-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-149-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-149-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-149-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-150-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-150-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-150-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-150-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-199-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-199-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-199-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-199-I4-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-200-I1-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-200-I2-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-200-I3-NEXT | 2027-02-28 | 2027-03-15 |
| LIM-200-I4-NEXT | 2027-02-28 | 2027-03-15 |

## FIN-098 · hard_complex

Audit whether any actual position, price, FX or trade is dated after 2027-02-28.

Evidence returns 4 row(s). First result: source=positions; future_actual_rows=0. Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.

| source | future_actual_rows |
|---|---|
| positions | 0 |
| prices | 0 |
| fx | 0 |
| trades | 0 |

## FIN-099 · hard_complex

For all portfolios in the future_limit business branch, compare current and March planned issuer assessment counts by status.

Evidence returns 2 row(s). First result: as_of_date=2027-02-28; view_kind=actual; assessment_status=within; assessments=32. The same future-limit portfolio can be within its current 80% cap and breach a planned 20% cap. The projected breach is not a current breach.

| as_of_date | view_kind | assessment_status | assessments |
|---|---|---|---|
| 2027-02-28 | actual | within | 32 |
| 2027-03-31 | planned | breach | 32 |

## FIN-100 · hard_complex

Check every assessment uses a known approved limit valid on its own date; report breaches of this rule by view.

Evidence returns 2 row(s). First result: view_kind=actual; assessments=4000; invalid_limit_uses=0. Zero invalid uses demonstrates validity/approval/knowledge alignment for these records, not that every limit assessment is within-limit.

| view_kind | assessments | invalid_limit_uses |
|---|---|---|
| actual | 4000 | 0 |
| planned | 1000 | 0 |
