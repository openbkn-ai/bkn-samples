# Business-scenario test set v1

Written from the scenarios and business rules in the [business PRD](../../../docs/PRD.md): 50 questions, 12 basic, 20 medium and 18 complex, asked from the viewpoints of middle office, fund accounting, risk and compliance, and the portfolio manager. Questions use business language and state no calculation rule.

- `question-set-v1.yaml`: questions, scenario, difficulty, role and expected output. The agent under test sees only this file.
- `answer-set-v1.yaml`: machine-readable expected values. The agent under test must not read it.
- `oracle.py`: reads only this package's delivered CSV files under `data/` and `model-contract.json`, computes every answer independently with Decimal and writes the two files above. It does not import or call the sample's functions and does not read earlier answers. The Chinese and English packages share the same script; their data differ only in text, so expected values match apart from names and status labels.

```sh
python3 samples/financial-fibo-en-us/bkn-eval/baselines/2026-10-30-business-scenarios-v1/oracle.py
```

## Scenarios and questions

| Scenario | Questions | Basic/medium/complex |
|---|---|---|
| S01 Reference data and portfolios | Q-01, Q-02, Q-03, Q-04 | 4/0/0 |
| S02 Trades and settlement | Q-05, Q-06, Q-07, Q-08, Q-09, Q-10, Q-11, Q-12 | 3/5/0 |
| S03 Prices and valuation | Q-13, Q-14, Q-15, Q-16, Q-17, Q-18, Q-19, Q-20, Q-21, Q-49 | 3/6/1 |
| S04 Positions, cost and month end | Q-22, Q-23, Q-24, Q-47 | 0/2/2 |
| S05 Issuer concentration | Q-25, Q-26, Q-27, Q-28, Q-29 | 0/3/2 |
| S06 Counterparty receivables | Q-30, Q-31, Q-32, Q-33, Q-48 | 1/2/2 |
| S07 Limits and plan | Q-34, Q-35, Q-36, Q-37, Q-38, Q-39, Q-50 | 1/2/4 |
| S08 Look-back and trace | Q-40, Q-41, Q-42, Q-43, Q-44, Q-45, Q-46 | 0/0/7 |

## Exceptions in the data

As of the business date, 304 instructions are not fully settled: 144 failed and 80 partially settled (all overdue), and 80 pending (due March 2). At the end of February, 96 valuations are blocked by stale, unapproved or missing prices, so issuer concentration cannot be judged for 96 portfolios. At the end of February, 20 portfolios breach an issuer concentration limit and 12 breach a counterparty receivable limit. New limits take effect on March 15 for 8 portfolios, which newly breach under the March plan. Month-end questions can read the recorded valuation, exposure and limit-assessment snapshots directly; questions about a non-month-end date or about what was known on a day need recomputation from the original trades and settlement events.

## Runs

| Agent | Result | Record |
|---|---|---|
| External MCP agent (can call the sample functions), one round | 50/50 | [runs/2026-10-30-mcp-agent-r1](runs/2026-10-30-mcp-agent-r1/README.md) |
