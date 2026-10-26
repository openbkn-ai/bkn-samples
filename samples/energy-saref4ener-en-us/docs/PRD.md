# Demand-response operations: business requirements

## Business problem and intended decisions

A fictional load aggregator, ClearSpring Flex, manages HVAC, refrigeration and EV charging for enterprise customers. After a response event is announced, the team must decide how much it can safely commit, which devices may participate, how competing events share scarce resources, and what was actually delivered and should be settled. Nameplate power, offers, approved baselines, forecasts, proposals, commitments, execution receipts and meter readings have different meanings and cannot be added indiscriminately.

The required operating loop is: announced event -> customer/asset checks -> commitment readiness -> preservation of existing commitments and proposed allocation -> execution and measurement verification -> settlement reconciliation and exception investigation. All records and commercial terms are fictional. The scope is customer-side load reduction.

## Stakeholders and business concerns

| Stakeholder | Decision | Required evidence |
|---|---|---|
| Aggregator operations | Accept demand without using resources promised elsewhere | Eligible capacity, existing commitments, incremental allocations, shortage and uncertainty |
| Site energy manager | Maintain service and honor maintenance/opt-out restrictions | Device eligibility, service floor, site cap, exclusion reasons and affected events |
| Response duty team | Establish whether a planned dispatch was executed | Commitments versus receipts, missing/failed execution, reading quality and unresolved evidence |
| Settlement analyst | Apply threshold/payment and customer compensation consistently | Verified energy, delivery ratio, revenue, customer cost, net and posted-ledger difference |

Success is a consistent, unit-correct, traceable basis for these decisions. Incomplete sources must produce explicit uncertainty and evidence, never a plausible fabricated zero.

## Scope and dates

Default observation date2027-02-28; historical facts span November2026 through February2027 and announced plans/forecasts extend to2027-03-31. Separate business as-of and knowledge-cutoff dates support reconstruction of what was known and later corrections. The English and Chinese samples have equivalent IDs/facts/numbers with localized business names and displays.

Dates use YYYY-MM-DD only. Named response blocks peak_a and peak_b last2 and3hours. Events on the same date/block overlap completely. This model supports average power and block energy; it does not certify instantaneous control, intra-block ramps or hour-by-hour safety. Load forecasts are supplied synthetic inputs, not an ML forecasting product.

Generation, battery SOC optimization, network power flow, real control commands, actual payments, taxes and jurisdictional market compliance are out of scope. Each device has one nonoverlapping meter; site meters are not added again. Customer compensation and market payment follow different rules, so net results can be negative.

## P0 requirements and acceptance scenarios

| Scenario / requirement | Business concern and acceptance | Questions |
|---|---|---|
| S01 / R01 Ownership and metering | Resolve customer/site/device and unique meter, types and units; nameplate is not eligible power | ENE-001--010 |
| S02 / R02 Forecasts and planning visibility | Latest known forecast, revision versus target date; March planning never becomes an actual reading | ENE-011--020 |
| S03 / R03 Eligibility | Offers, service floors, equipment caps, maintenance, opt-out and validity; known zero differs from missing source | ENE-021--030 |
| S04 / R04 Site and measurement boundaries | Site total respects cap, meter energy is not duplicated, aggregate contributions trace to devices | ENE-031--040 |
| S05 / R05 Competing commitments | Preserve commitments, include unrequested overlapping events, never allocate shared power twice | ENE-041--050 |
| S06 / R06 Allocation and cost | Honor event priority/commitments, rank incremental compensation cost deterministically, expose shortages without global-optimality claims | ENE-051--060 |
| S07 / R07 Delivery verification | Attribute completed commitments only, use approved baseline and measured energy, convert kW/kWh, show failed receipts | ENE-061--070 |
| S08 / R08 Missing/late/corrected sources | Reconstruct knowledge cutoff, do not fall back from latest bad quality, disclose conflicting revisions | ENE-071--080 |
| S09 / R09 Settlement and ledger | Inclusive threshold, separate customer cost, Decimal rounding, ledger variance; missing ledger is not zero | ENE-081--090 |
| S10 / R10 Future/snapshots/investigation | Future events are planning only, compare equivalent snapshot scopes, return evidence and next action for exceptions | ENE-091--100 |

Each scenario has10questions:3easy/basic,4medium and3hard/complex, totaling30/40/30 per language. Complex questions combine competition, knowledge cutoffs, uncertainty propagation, attribution and reconciliation; merely changing IDs is insufficient.

## Shared business rules

Power is kW, energy kWh and price CNY/kWh. Convert using block hours before Decimal half-up cent rounding. Unknown values, zero denominators and true zero remain distinct. Readiness honors offers, equipment/service limits, forecast/baseline and site capacity. Explicit maintenance/opt-out/expiry yields an explained exclusion; potentially eligible missing data yields uncertainty.

Proposals are not commitments and commitments are not execution. Overlapping events share device/site budgets, including commitments outside the requested event subset. Only approved baselines and valid actual readings establish delivered reduction. Allocate a shared meter's measured reduction pro-rata across completed commitments, capped by total measured reduction and commitment.

Market payment requires delivery_ratio >= minimum_ratio. Customer compensation for verified delivery still occurs if the aggregator misses its market threshold. Support zero revenue, negative net and unknown amounts. Respect knowledge cutoffs and corrections. Snapshot metrics retain their as-of/knowledge scope and do not replace reconstruction.

Exact formulas/version selection/API/errors are defined once in the [business calculation contract](business-capability-contract.md), rather than duplicated in another scenario requirements file. Semantic mapping is in the [BKN modeling specification](bkn-modeling-spec.md).

## Minimal capabilities and acceptance

Exactly3reusable functions: flexibility assessment, dispatch proposal and delivery/settlement assessment;2recorded snapshot metrics: eligible flexibility and delivery ratio;1read-only exception investigation Skill. Do not add a function for each question or device type.

Local deliverables include bilingual PRDs/native BKN, connected data for every object, data locks, source/licensing, executable functions, metrics, physically included Skill references and100questions with concrete answers/evidence per language. An independent subagent validates business semantics, coverage, localization, dates and important differences. Passing deterministic checks does not prove platform installation or100%model accuracy. Fixed-package platform installation and actual QA require separate recorded acceptance before publication.
