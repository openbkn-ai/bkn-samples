# BKN-Eval

The current acceptance set is the [v4 business-scenario test set](baselines/2026-10-30-business-scenarios-v4/README.md). The material below describes the earlier frozen baseline and is kept as history.

The candidate paper contains only 50 question IDs and business questions in `datasets/sample-question-set-v1.yaml`. Before the exam, give both candidates only the common time statement in `exam-time-reference.txt`. Expected answers and rule evidence in `datasets/sample-answer-set-v1.yaml` are judge-only. Four calendar-month checks are versioned separately.

The frozen baseline pins the delivered CSV files and deterministic business rules. Its independent Decimal oracle calculates expected outputs directly from these files without importing or calling the evaluated functions.

Use separate agents: blind A reads questions and published MCP metadata/Skills only; judge C compares actual calls and answers against the expected outputs. A must not access CSVs, answer sets, implementation source or direct databases. Unknown or partial answers do not count as a pass on these fully specified cases.

Keep evaluation receipts, logs, answers and judgments in a local workspace outside the committed sample. Record exact source/data/package hashes and standard installation results. Scores do not carry across rebuilt packages. Core acceptance requires 50/50 exact matches; calendar checks require 4/4 separately. Evaluation assets are excluded from the installed package.

## Classification and lead-time supporting facts (MF-01)

The [question](datasets/material-field-questions-v1.yaml) and [gold answer](datasets/material-field-answers-v1.yaml)
form one regression separate from the frozen core 50. The evaluated agent may read only the question and installed BKN/MCP metadata, not gold, CSVs or implementation source.
All requested facts must be correct; a correct one-day lead time does not excuse swapped category labels.
Local tests establish metadata, import-payload and CSV-gold consistency, not a model score or live MCP acceptance. Record and judge the actual caller answer separately.
