# Demand Response Operations: Capacity, Dispatch and Settlement PRD

## Goals and users

The fictional aggregator manages controllable HVAC, cold-chain refrigeration and EV-charging loads for 50 enterprises, organizing load reduction when the grid announces events, verifying delivery and settling. Business users want to ask in plain business language how much can be committed, which devices can take part, how competing events share resources, how much was actually delivered, and whether revenue and customer compensation are right, and see the events, devices, allocations, readings and dates behind every conclusion.

| User | Concern | Expected conclusion |
|---|---|---|
| Aggregator operations lead | Whether a request can be accepted, whether commitments crowd out other events, how to schedule by cost | eligible capacity, committed, new, shortfall and estimated cost, and why something cannot be determined |
| Site energy manager | Reductions must keep minimum service load; devices under maintenance or withdrawn must stay out | device and site limits, barred devices and withdrawn offers, affected events |
| Response duty officer | Whether allocations were really executed and metering is reliable | execution receipts, verified energy, delivery ratio, missing or corrected readings |
| Settlement clerk | Whether threshold, revenue and compensation follow one rule and match the ledger | revenue, compensation, net, difference from posted amounts and why something cannot be reconciled |

Success means users get conclusions that follow the business rules below without stating any calculation rule, together with the records behind them. An answer that is only right when the rule is spelled out in the question, and wrong when it is phrased differently, does not count.

## Decision scope

In scope: customers, sites, devices and meters; response events; load forecasts and approved baselines; device offers; device constraints (blocks and caps); dispatch allocations and execution receipts; meter readings; the settlement ledger; capacity and settlement snapshots.

Out of scope: sending real instructions, controlling devices or paying; generation, storage optimization and power flow; second-level control and intra-block ramps; statutory electricity-market settlement. Every conclusion is advice only.

## Business rules

These are the default rules; users do not need to repeat them. When a user states a different condition, the user's condition wins.

1. **Business date**: 2027-02-28; "now" and "today" mean this date. November to February events have happened; March events are announced plans. Block peak_a lasts 2 hours and peak_b 3 hours; events on the same date and block overlap completely, different blocks do not.
2. **As of a day**: count only events announced and records known by that day; a correction learned later does not count when looking at earlier knowledge.
3. **Versions**: forecasts, baselines and readings take the latest version visible that day per device (meter), date and block; offers per event and device; receipts per allocation. A duplicate submission with the same content counts once; conflicting content in the same version makes the result undeterminable. When the latest version is invalid, never fall back to an older valid one.
4. **Units and precision**: power in kW, energy in kWh = kW × block hours, prices in CNY/kWh. Sum exact values, then round half up: quantities and ratios to 6 decimals, money to 2.
5. **Unknown is not zero**: a missing required forecast, baseline, reading or receipt, or conflicting content, makes the related result undeterminable, never zero; a ratio with a zero denominator is empty.
6. **Eligible capacity**: per device, the minimum of the offered kW, the device's maximum reduction, the lower of forecast and baseline minus minimum service load (not below zero), and any active cap that day. An inactive device, a device barred that day, or an offer withdrawn or out of validity counts zero; a cap without a value is undeterminable. Each site's total is limited to its response cap, and the event's capacity is the sum over sites. Each device has one meter, never added to a site meter.
7. **Dispatch plan**: active events on the same date and block share device and site reduction limits. Existing commitments take their share first; new allocation goes by event priority, then by offer cost from lowest, within the event target, device eligibility and remaining limits. If any event in the block has undeterminable capacity, or a commitment exceeds a device limit or its current eligibility, the block's new plan cannot be given in full. The estimated cost covers both existing and new allocations.
8. **Delivery verification**: only allocations with a completed receipt count as delivered; failed or customer-declined ones count zero; a missing receipt is undeterminable. Measured reduction = latest approved baseline × hours − latest valid reading, not below zero; when one device in one block is committed to several events, it is shared in proportion to committed energy and never exceeds the measured reduction. Delivery ratio = verified energy ÷ committed energy, empty when nothing was committed.
9. **Revenue and compensation**: revenue = verified energy × the event reward rate when the delivery ratio meets the minimum (equal counts), otherwise zero; customer compensation = each device's shared energy × its offer cost rate, paid whether or not the threshold is met; revenue and compensation are each rounded to the cent and net = revenue − compensation, which may be negative. Future events cannot be settled yet; cancelled events are not settled.
10. **Ledger reconciliation**: compare recomputed revenue with the latest posted settlement dated on or before the day; no posting means empty, not zero; two conflicting postings on the same date cannot be reconciled.
11. **Snapshots**: capacity and settlement snapshots record results for 2027-02-28; invalid ones cannot be used, and valid ones still have to be checked against recomputation from the source records, with any difference explained.

## Business scenarios

| Scenario | User question | Expected conclusion |
|---|---|---|
| S01 Assets | Which customers, sites and devices, what limits and meters | counts, site caps, device reduction and service load, inactive devices |
| S02 Forecasts and plan | Which events are in March, can the forecast be used | event schedule, targets, whether the latest forecast is valid |
| S03 Eligible capacity | How much can be committed, which devices cannot take part, why something is undeterminable | event capacity, barred devices and withdrawn offers, missing caps or invalid forecasts |
| S04 Site caps | How much the site cap removes, whether metering is double counted | sites over the cap, meter uniqueness |
| S05 Shared resources | How events in one block share resources, whether anything is over-committed | shared commitments, over-reserved devices, new allocation and shortfall by priority |
| S06 Cost-ordered scheduling | Which devices to add, at what cost, whether the target is reached | added devices and kW, estimated cost, shortfall |
| S07 Execution and delivery | Whether instructions were executed, how much was delivered | receipts, verified energy, delivery ratio, events below threshold |
| S08 Corrections and look-back | How late corrections, conflicts and duplicates change results | verified energy and revenue by knowledge date, affected events |
| S09 Settlement and ledger | Revenue, compensation and net, whether they match the ledger | revenue, compensation, net, ledger difference and why reconciliation fails |
| S10 Plan and snapshots | Whether future events can be settled, whether snapshots can be trusted | invalid and mismatched snapshots, plan completeness, what blocks settlement |

## Acceptance

1. 50 questions per language covering the 10 scenarios: 12 basic, 20 medium, 18 complex. All asked in the business language of operations, energy management, duty or settlement staff, with no calculation rule in the question.
2. Complex questions involve at least two business rules, or reasoning across three or more record types.
3. Reference answers are computed independently of the capability under test, and the tested agent never sees them.
4. One round per language, with a 100% accuracy target.
