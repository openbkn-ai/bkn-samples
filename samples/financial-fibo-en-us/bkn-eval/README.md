# Local acceptance bank

100 distinct questions span 10 business acceptance scenarios. `questions.json` includes question, level, scenario ID, relation paths and read-only SQL evidence. `expected-results.json` freezes all rows; `answers.md` is the readable counterpart. Preserve row order, fields and null semantics; numeric comparison uses the explicit tolerance.

`run.py` checks digests and BKN mappings, reconstructs financial facts with independent Decimal logic, then replays queries in in-memory SQLite. The query connection is read-only; evaluation neither imports the generator nor regenerates gold. Actual agent/MCP evaluation requires a separate question-only run with persisted answers, tool traces and post-answer scoring.
