# Business-scenario test set v1

Written from the scenarios and business rules in the [business PRD](../../../docs/PRD.md): 50 questions, 12 basic, 20 medium and 18 complex, asked from the viewpoints of the aggregator operations lead, the site energy manager, the response duty officer and the settlement clerk. Questions use business language and state no calculation rule.

- `question-set-v1.yaml`: questions, scenario, difficulty, role and expected output. The agent under test sees only this file.
- `answer-set-v1.yaml`: machine-readable expected values. The agent under test must not read it.
- `oracle.py` and `energy_calc.py`: read only this package's delivered CSV files under `data/` and compute eligible capacity, dispatch and settlement from the business contract without importing the sample's functions. During development they were compared with the sample's functions event by event for four business-date and knowledge-cutoff combinations, with identical results. The Chinese and English packages share the same scripts; their data differ only in text, so expected values match apart from names.

```sh
python3 samples/energy-saref4ener-en-us/bkn-eval/baselines/2026-10-30-business-scenarios-v1/oracle.py
```

## Scenarios and questions

| Scenario | Questions | Basic/medium/complex |
|---|---|---|
| S01 Assets | Q-01, Q-02, Q-03, Q-04, Q-49 | 4/1/0 |
| S02 Forecasts and plan | Q-05, Q-06, Q-07, Q-08 | 2/2/0 |
| S03 Eligible capacity | Q-09, Q-10, Q-11, Q-12, Q-13, Q-47 | 0/4/2 |
| S04 Site caps | Q-14, Q-15 | 1/0/1 |
| S05 Shared resources | Q-16, Q-17, Q-18, Q-19 | 0/1/3 |
| S06 Cost-ordered scheduling | Q-20, Q-21, Q-22 | 0/2/1 |
| S07 Execution and delivery | Q-23, Q-24, Q-25, Q-26, Q-27 | 1/2/2 |
| S08 Corrections and look-back | Q-28, Q-29, Q-30, Q-31, Q-32 | 0/3/2 |
| S09 Settlement and ledger | Q-33, Q-34, Q-35, Q-36, Q-37, Q-38, Q-39, Q-48 | 1/3/4 |
| S10 Plan and snapshots | Q-40, Q-41, Q-42, Q-43, Q-44, Q-45, Q-46, Q-50 | 3/2/3 |

## Exceptions in the data

Of 100 events, 60 have happened (2 cancelled) and 40 are in March (1 cancelled). Among past events, 19 fall below their minimum delivery ratio and run at a net loss; EVT-021, EVT-029 and EVT-033 cannot be settled because of a baseline conflict, a missing reading and a missing receipt; EVT-005 has no commitment. EVT-025's recomputed revenue is 5 CNY below the ledger, and EVT-041 has two conflicting postings on one day. Capacity for EVT-013, EVT-053 and EVT-054 is undeterminable because the latest forecast is invalid or a cap has no value; one allocation in the 2027-02-24 block exceeds a device limit. 7 capacity snapshots are invalid and 3 disagree with recomputation; 1 settlement snapshot's revenue disagrees. DEV-136 also has a late reading correction and a duplicate submission, DEV-061's baseline was restated on March 3, and an EVT-073 offer was withdrawn on March 5.
