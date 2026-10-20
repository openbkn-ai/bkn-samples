# Independent retail acceptance oracle

This directory belongs to the evaluator, not the runtime package. The oracle reads source CSVs and the public business contract; it must never import production inventory, fulfillment or recall functions. Question-bank authoring and deterministic checks are preparation, not a formal agent answer run.

Each language has exactly 100 public questions, with S01–S10 coverage and 30 basic / 40 medium / 30 complex. The independent expected rows and evidence live under source `bkn-eval/` and must be excluded from installable artifacts. Formal answerers receive question text and output contracts only, discover installed capabilities and query the installed network, and never read this directory or expected answers.

Do not use production results to create, repair or normalize expected results. Resolve ambiguity against the PRD before freezing the bank. A disagreement after freeze is recorded with the original result; no silent gold edits or unrequested repeated passes. The explicitly authorized nine-case retest has separate records and does not replace the original full-pass scores.

Count unanswered and tool-failed questions in the fixed denominator. Report exact business-field agreement and evidence/lifecycle status independently; an accepted asynchronous trace state does not imply evidence loss, nor complete capture.
