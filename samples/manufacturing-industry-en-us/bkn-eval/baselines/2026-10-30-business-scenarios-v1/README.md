# Business-scenario test set v1

Written from the scenarios and rules of the [business PRD](../../../docs/PRD.md): 50 questions, 12 basic, 20 medium and 18 complex, asked as an order fulfilment manager, production lead, quality manager or purchasing and materials manager. Questions use business language and never state calculation rules.

- `question-set-v1.yaml`: questions, scenarios, difficulty, role and output contract. The evaluated agent sees only this file.
- `answer-set-v1.yaml`: machine-readable expected values. The evaluated agent must not read it.
- `oracle.py` and `mfg_calc.py`: read only this package's delivered CSV files under `data/` and compute the PRD rules independently, without importing the data generator. Both language packages use the same scripts; their data differ only in translated text, so expected values match except for names.

```sh
python3 samples/manufacturing-industry-en-us/bkn-eval/baselines/2026-10-30-business-scenarios-v1/oracle.py
```

## Scenarios and questions

| Scenario | Questions | Basic/medium/complex |
|---|---|---|
| S01 Products and capacity | Q-01, Q-02, Q-03, Q-04, Q-05 | 3/2/0 |
| S02 Orders and delivery | Q-06, Q-07, Q-08, Q-09, Q-10, Q-11 | 1/2/3 |
| S03 Forecast and plan | Q-12, Q-13, Q-14, Q-15 | 1/2/1 |
| S04 Material availability | Q-16, Q-17, Q-18, Q-19, Q-20 | 1/1/3 |
| S05 Purchasing and receipts | Q-21, Q-22, Q-23, Q-24, Q-25 | 0/3/2 |
| S06 Progress and output | Q-26, Q-27, Q-28, Q-29, Q-30 | 1/3/1 |
| S07 Execution compliance | Q-31, Q-32, Q-33, Q-34, Q-35, Q-36 | 1/2/3 |
| S08 Quality release | Q-37, Q-38, Q-39, Q-40, Q-41, Q-42 | 1/3/2 |
| S09 Maintenance | Q-43, Q-44, Q-45, Q-46 | 2/1/1 |
| S10 End-to-end trace | Q-47, Q-48, Q-49, Q-50 | 1/1/2 |

## Exceptions in the data

Of 55 work orders (one a replacement), 43 are completed, 2 in production, 4 blocked and 6 released for March. WO-2611-08 failed its bore check and was remade by WO-2612-R1, 12 days late; WO-2701-10 and WO-2702-10 were rejected and not yet remade; WO-2612-10 was recorded as pass with flatness out of limit and shipped (a quality escape). Four work orders had scrap, leaving three order lines 2 to 5 units short. Eight executions are non-compliant: 2 on a machine whose capability is suspended, 3 by an operator with an expired or in-training qualification, 1 on a service day, and 2 with the operator assigned to another work centre or not scheduled. WO-2612-09 was issued material from a receipt still in inspection; three Baolian Special Steel purchases are short and a South China Foundry casting receipt was rejected; WO-2702-03, WO-2703-04 and WO-2703-06 are blocked by material and WO-2703-02 by a draft BOM. Three maintenance orders are overdue and 5-axis Mill 3 is under repair. The PH100 critical bore specification tightened from 2027-01-01.
