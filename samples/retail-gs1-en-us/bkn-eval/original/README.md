# Retail business acceptance bank

Exactly 100 questions map to the ten PRD scenarios: Q001–010/S01 through Q091–100/S10. Each language contains 30 basic, 40 medium and 30 complex questions. Requirements and scene descriptions live in the PRD, not a second competing requirements file.

`questions.json` contains natural-language questions and output contracts, with no oracle recipe or answer. `expected-results.json` and `answers.md` contain evaluator-only reference rows and source provenance; `oracle-recipes.json` records how the independent evaluator computed those rows. These evaluator assets must not be installed into the live sample or exposed to answerers. `freeze.json` records bank digests; the official acceptance freeze additionally binds source, package and evaluator hashes.

The independent source-fact implementation is `tools/retail_eval/oracle.py`. It does not import the production capability functions or derive expected answers from their output. It separately reconstructs event deduplication/reversal, bitemporal stock, explicit return/hold overlap, reservations, FEFO shared allocation, dated replenishment and directed recall scope. Recorded metric questions explicitly compare recorded sources with independent reconstruction.

Five intentional empty-list answers test clean responsibility/split/integrity audits, an unannounced recall and a closed recall. The remaining 95 have source-derived rows. Unknown quantitative values remain null; an empty result is not a substitute for failed execution or missing evidence.

Developer preparation (not formal question answering):

```sh
python3 tools/retail_eval/validate_bank.py
```

The source-only check verifies all frozen answers, cross-language numeric facts, source evidence IDs, manual business controls and comparator negative controls. It does not claim agent accuracy. `build_bank.py --write` is an authoring/regeneration operation and must not be called after formal freeze.

Formal acceptance uses fresh isolated agents against the installed 8081 networks, one attempt per question and only one round per language. Agents receive public questions and live schema/skills; they cannot read this oracle, gold, local CSVs or previous answers. Every first answer/tool failure must be retained. Only after all 100 questions terminate may the evaluator open gold and grade using the unchanged strict comparator.

```sh
python3 tools/retail_eval/grade.py --sample samples/retail-gs1-en-us --results /path/to/terminal-results --output /path/to/new-score.json
```

The fixed denominator is 100, including failures and unanswered records. Exact Decimal equality accepts equivalent decimal spellings, and midnight DATE transport normalization only; missing fields, omitted rows, duplicate IDs, null/zero substitution and wrong controlled values fail. Evidence/lifecycle status is reported separately from business-field correctness. No question-specific exceptions or retries are allowed to manufacture a perfect score.
