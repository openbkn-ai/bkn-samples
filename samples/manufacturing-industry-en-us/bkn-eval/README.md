# Evaluation suite

`scenarios.md` defines 17 acceptance questions, including the forecast-to-shipment fulfillment chain. `questions.json` contains the bilingual 100-question bank: 30 easy/basic, 40 intermediate, and 30 hard/complex questions. Every question has a stable ID and deterministic expected answer. `expected-results.json` contains the 17 acceptance baselines. Run `python3 bkn-eval/run.py` from the sample root after `python3 tools/verify_industry_links.py` and `python3 iof-reference/tools/verify_reference_instances.py`.

The suite is source-controlled and local. It validates the CSV/BKN model before a future platform resource binding is added.
