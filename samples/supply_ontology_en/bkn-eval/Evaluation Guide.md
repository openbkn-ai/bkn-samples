# BKN-Eval

The candidate paper is `datasets/sample-question-set-v1.yaml`: exactly 50 question IDs and business questions. Give the same file to both candidates. Before opening the paper, read only `exam-time-reference.txt` as the common time reference. Do not attach this guide, answer files, baseline metadata, calculation rules, field mappings, tool recommendations or algorithm instructions to either candidate's paper.

Expected answers and their business-rule basis are in `datasets/sample-answer-set-v1.yaml`, for the independent judge only. Four calendar-month checks are versioned separately and are outside the core 50-question exam.

The frozen baseline pins the delivered CSV files and deterministic business rules. Its independent Decimal oracle calculates expected outputs directly from these files without importing or calling the evaluated functions.

Use separate agents: blind A reads questions and published MCP metadata/Skills only; judge C compares actual calls and answers against the expected outputs. A must not access CSVs, answer sets, implementation source or direct databases. Unknown or partial answers do not count as a pass on these fully specified cases.

For a BKN versus direct-database comparison, use fresh workspaces and sessions with the same model configuration and the same data snapshot. The BKN candidate may use its normally published knowledge-network capabilities; the database candidate may inspect its database and write its own local program. Keep the judge's answer files and implementation sources inaccessible to both. Send the paper once; do not provide intermediate corrections, substitute queries, hints or follow-up coaching. Record execution errors and rule violations separately from factual scores. An unexpected execution failure pauses the run for diagnosis; any later approved restart is a new attempt, never a continuation with corrected answers.

The frozen baseline retains the historical rule-explicit paper for audit. It is not the candidate paper for a blind comparison. Preserve prior submissions, recordings and judgments when replacing the paper; do not retroactively apply a new paper to old scores. Record the question-file hash for every attempt. Clarify an ambiguous business acceptance definition with the judge before a future exam, rather than adding algorithm hints or coaching a candidate during it.

Keep evaluation receipts, logs, answers and judgments in a local workspace outside the committed sample. Record exact source/data/package hashes and standard installation results. Scores do not carry across rebuilt packages. Core acceptance requires 50/50 exact matches; calendar checks require 4/4 separately. Evaluation assets are excluded from the installed package.
