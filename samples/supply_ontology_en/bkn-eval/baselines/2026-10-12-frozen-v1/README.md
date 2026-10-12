# Frozen Fixture Baseline

`dataset.lock` pins all 12 CSV files by row count and SHA-256. The fixture includes three future forecast scenarios. Business date: `2026-08-25`.

The core has 50 deterministic questions. `gold-evidence/recalculate.py` reads the CSVs using Decimal and does not import or call evaluated functions. `capability-basis.json` identifies the published capabilities used for each question; it does not calculate expected results.

The formal datasets mirror `question-set-v1.yaml` and `answer-set-v1.yaml`. Release acceptance requires standard package installation and independent live MCP evaluation of the exact candidate. Offline oracle checks alone do not establish a live score. Keep execution records locally outside the sample.
