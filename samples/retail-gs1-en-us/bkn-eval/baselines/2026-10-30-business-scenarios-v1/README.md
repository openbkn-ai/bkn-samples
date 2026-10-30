# Business-scenario test set v1

Written from the scenarios and business rules in the [business PRD](../../../docs/PRD.en-US.md): 50 questions, 12 basic, 20 medium and 18 complex, asked from the viewpoints of the quality lead, the warehouse and distribution lead, and the store manager. Questions use business language and state no calculation rule.

- `question-set-v1.yaml`: questions, scenario, difficulty, role and expected output. The agent under test sees only this file.
- `answer-set-v1.yaml`: machine-readable expected values. The agent under test must not read it.
- `oracle.py`: reads only this package's delivered CSV files under `data/`; inventory replay, order allocation, replenishment and recall closure use the evaluator-only reference `tools/retail_eval/oracle.py`, which applies the PRD rules to source facts and does not import the sample's functions. The Chinese and English packages share the same script; their data differ only in text, so expected values match apart from names.

```sh
python3 samples/retail-gs1-en-us/bkn-eval/baselines/2026-10-30-business-scenarios-v1/oracle.py
```

## Scenarios and questions

| Scenario | Questions | Basic/medium/complex |
|---|---|---|
| S01 Products and locations | Q-01, Q-02, Q-03 | 3/0/0 |
| S02 Receipt and inspection | Q-05, Q-06, Q-07, Q-08 | 2/2/0 |
| S03 Lot flow | Q-04, Q-48, Q-49, Q-50 | 0/4/0 |
| S04 Stock and in transit | Q-09, Q-10, Q-11, Q-12, Q-13 | 2/2/1 |
| S05 Expiry | Q-14, Q-15, Q-16 | 1/2/0 |
| S06 Order fulfilment | Q-17, Q-18, Q-19, Q-20, Q-21, Q-22 | 1/0/5 |
| S07 Replenishment | Q-23, Q-24, Q-25, Q-26, Q-27 | 1/0/4 |
| S08 Recall reach | Q-28, Q-29, Q-30, Q-31, Q-32, Q-33 | 1/3/2 |
| S09 Recall control | Q-34, Q-35, Q-36, Q-37, Q-38, Q-39, Q-40 | 1/4/2 |
| S10 Data trust and look-back | Q-41, Q-42, Q-43, Q-44, Q-45, Q-46, Q-47 | 0/3/4 |

## Exceptions in the data

On the business date there are 400 lot-location positions: the stock of 4 cannot be determined (conflicting event copies, an arrival without dispatch leading to negative stock, negative stock), 157 carry quarantine, 189 are blocked by recalls and 100 hold expired stock. 4 lots failed inspection and 3 are awaiting it. Allocating current stock to the 100 open order lines covers 47 in full, 45 in part and 8 not at all; all 50 product-warehouse pairs need March replenishment. 49 recalls are open and REC-050 is closed; REC-048 reaches another product through a transformation. There is also one event recorded twice, one reversed sale and one sale recorded only on March 2. Inventory and recall coverage on the business date have recorded snapshots; other dates, what was known on a day, allocation, replenishment and recall closure need calculation from the source events.
