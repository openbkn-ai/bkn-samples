# v4 business-scenario test set

Written from the scenarios and business rules in the [supply chain PRD](../../../docs/PRD.en-US.md): 50 questions, 12 basic, 20 medium and 18 complex; 33 from the PMC planner's view and 17 from purchasing. Questions use business language and state no calculation rule.

- `question-set-v4.yaml`: questions, scenario, difficulty, role and expected output. The agent under test sees only this file.
- `answer-set-v4.yaml`: machine-readable expected values. The agent under test must not read it.
- `oracle.py`: reads only the delivered CSV files under `data/` and computes every answer independently with Decimal, then writes the two files above. It does not import or call the sample's functions and does not read earlier answers.

```sh
python3 samples/supply_ontology_en/bkn-eval/baselines/2026-10-30-business-scenarios-v4/oracle.py
```

The English data is a row-by-row translation of the Chinese sample's data, with the same codes, quantities and dates. This set therefore matches the Chinese v4 set question by question, and the expected values are identical apart from names.

## Scenarios and questions

| Scenario | Questions | Basic/medium/complex |
|---|---|---|
| S01 Products and materials | Q-01, Q-02, Q-36 | 3/0/0 |
| S02 Backlog | Q-05, Q-09, Q-10, Q-23, Q-24, Q-37, Q-39, Q-42, Q-43 | 3/4/2 |
| S03 Forecasts and preparation | Q-06, Q-18, Q-30, Q-45 | 1/2/1 |
| S04 BOM and common parts | Q-03, Q-14, Q-15, Q-32 | 1/2/1 |
| S05 Stock | Q-04, Q-16, Q-38 | 2/1/0 |
| S06 Order acceptance | Q-21, Q-22, Q-25, Q-28, Q-29, Q-49 | 0/2/4 |
| S07 Backlog filling and competing orders | Q-27, Q-31, Q-47 | 0/0/3 |
| S08 Purchase follow-up | Q-07, Q-11, Q-12, Q-13, Q-19, Q-26, Q-40, Q-41, Q-44, Q-50 | 1/7/2 |
| S09 Lead time and dated supply | Q-20, Q-33, Q-46, Q-48 | 0/1/3 |
| S10 Plan execution and trace | Q-08, Q-17, Q-34, Q-35 | 1/1/2 |

## Open purchases in the data

There are 517 open purchase lines, 483 of them overdue. Only 34 are due on or after the business date, and none of those changes any product's buildable quantity. If overdue lines could be chased in, U00-000080 and the P61 series could build noticeably more. The questions test the difference between on-schedule and chase-dependent supply without inventing extra purchase data.

## Runs

| Agent | Result | Record |
|---|---|---|
| External MCP agent (can call the sample functions), acceptance target | 50/50, one round | [runs/2026-10-30-mcp-agent-r1](runs/2026-10-30-mcp-agent-r1/README.md) |
