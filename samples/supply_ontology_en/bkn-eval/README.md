# BKN-Eval

The core contains 50 questions in `datasets/sample-question-set-v1.yaml`; expected answers are in `datasets/sample-answer-set-v1.yaml`. Four calendar-month checks are versioned separately. The business date is `2026-08-25`.

The frozen baseline pins the delivered CSV files and deterministic business rules. Its independent Decimal oracle calculates expected outputs directly from these files without importing or calling the evaluated functions.

Use separate agents: blind A reads questions and published MCP metadata/Skills only; judge C compares actual calls and answers against the expected outputs. A must not access CSVs, answer sets, implementation source or direct databases. Unknown or partial answers do not count as a pass on these fully specified cases.

Keep evaluation receipts, logs, answers and judgments in a local workspace outside the committed sample. Record exact source/data/package hashes and standard installation results. Scores do not carry across rebuilt packages. Core acceptance requires 50/50 exact matches; calendar checks require 4/4 separately. Evaluation assets are excluded from the installed package.
