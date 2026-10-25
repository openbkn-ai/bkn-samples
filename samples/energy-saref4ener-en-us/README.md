# Energy demand-response operations (SAREF4ENER reference, English)

Fixed-source candidate sample 0.1.4 targeting OpenBKN **>=0.2.1 <0.3.0**. A fictional load aggregator connects eligibility, commitment readiness, competing-event allocation, execution/metering and settlement investigation. Start with the [business PRD](docs/PRD.md); exact rules are defined once in the [calculation contract](docs/business-capability-contract.md).

Each language provides 15 linked tables and 14,787 records (at least 50 per table), 15 native BKN object types, 15 relations and 3 concept groups. Default observation date 2027-02-28; history starts November 2026 and announced plans/forecasts extend through 2027-03-31. Dates are day-only; named response blocks carry explicit duration hours. Business names and displays are localized; stable IDs/codes/units remain equivalent across languages.

## Contents

| Business artifact | Location |
|---|---|
| Stakeholder concerns, 10 acceptance scenarios and question mapping | [PRD](docs/PRD.md) |
| Native ontology, semantic references and operational extensions | [BKN specification](docs/bkn-modeling-spec.md), [network](kn/network.bkn) |
| Connected instances, typed dictionary and locked hashes | [data](data/), [model-contract](model-contract.json), [dataset.lock](dataset.lock) |
| Differences, intentional anomalies and exact source IDs | [dataset scenarios](docs/dataset-scenarios.md) |
| 3 functions: eligibility, dispatch proposal, delivery/settlement | [engine](tools/energy.py), [contract](docs/business-capability-contract.md) |
| 2 atomic recorded-snapshot metrics: eligible kW and delivery ratio | [metric definitions](tools/assets/metrics-create.json) |
| 1 read-only investigation Skill with physically included references | [Skill](skills/energy-response-investigation-en-us/SKILL.md) |
| 100 questions, concrete answers/evidence and scenario mapping | [questions](bkn-eval/questions.json), [answers](bkn-eval/answers.md), [gold](bkn-eval/expected-results.json) |

## Sources and modeling scope

Official [SAREF4ENER 2.1.1](https://saref.etsi.org/saref4ener/v2.1.1/) and its direct import [SAREF Core 4.1.1](https://saref.etsi.org/core/v4.1.1/) supply semantic references. Downloaded Turtle, BSD-3-Clause license text, SHA256 and complete named-class/property inventories are in [saref-reference](saref-reference/README.md). SAREF4ENER has 80 explicit named classes (76 in its own namespace); Core has 32 (29 own). The complete source inventory and 15 operational business objects document their respective coverage.

Customer/site records, settlement formulas and dispatch proposals are explicit local extensions. Native BKN 2.x-compatible structure is validated locally; full OWL axioms, ETSI certification, complete grid dispatch and global optimization are not claimed. All business data are fictional, with no real controls/payments.

## Local verification from the repository

Use Python 3.11+, the installed openbkn CLI and local dependencies:

```sh
python3 tools/energy_saref4ener/verify.py --sample en-us
python3 -m unittest tools.energy_saref4ener.test_engine tools.energy_saref4ener.test_adapter -v
```

Alternatively run `python3 bkn-eval/run.py` inside this sample. Replay invokes the shipped implementation against recovered historical projections; independent hand-built boundaries and managed adapters check calculations, relational queries and snapshot comparisons. The 100-question bank has 30 easy/basic, 40 medium and 30 hard/complex questions, 10 per scenario; Business and knowledge cutoffs are explicit; contracts carrying reference_scope compare both views. Source recovery and this update are documented in the [integration report](../../docs/energy-saref4ener-readiness.md). Structured projection success is not natural-language model accuracy.

## Installation preparation and current boundaries

Includes sample.yaml, shared-MariaDB initialization/verification, native resource binding, capability registration and ownership hooks. Installation consumes local delivered data, without creator tools or hidden evaluation answers. Stable catalog admission requires actual platform acceptance of the exact candidate bytes.

This fixed-source 0.1.4 candidate is not registered in the official catalog. The integration report distinguishes current local checks from historical platform evidence. Fixed-package platform installation, runtime capability checks and actual question answering require separate receipts bound to the exact package; this README is not proof of runtime success. Snapshot metrics are recorded values, not replacements for reconstruction; incomplete facts preserve null/evidence. Upstream license notices are retained; custom code and synthetic data use the repository MIT license.
