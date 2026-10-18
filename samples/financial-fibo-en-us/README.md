# Financial Portfolio Operations (FIBO reference, EN)

A fictional asset manager’s securities post-trade control sample: instrument, legal entity and portfolio → order and execution → settlement → position → price and valuation → issuer concentration and unsettled-receivable limits.

## Start here

1. [Business PRD](docs/PRD.md): stakeholder concerns, P0 decisions and boundaries.
2. [BKN model and calculation rules](docs/bkn-modeling-spec.md): 20 object types, 29 relations, 3 groups and all financial formulas.
3. [FIBO semantic mapping](docs/fibo-operational-mapping.md): pinned sources, mapping decisions and explicit operational extensions.
4. [Dataset and business branches](docs/dataset-scenarios.md): record counts, relationships and shared-price effects.
5. [100 questions and full answers](bkn-eval/answers.md): 10 acceptance scenarios; 30 easy/basic, 40 intermediate, 30 hard/complex.

The observation date is **2027-02-28**. November 2026 through February 2027 are actual views; 2027-03-31 is a planned view known at the observation date. All business facts use dates. Each table has at least 50 records; the largest exceeds 16,000. There are **78,356 records per language** in this revision. English and Chinese share business keys, numeric facts and semantics; human-facing names, states, reasons, questions and answers are localized.

## Local validation

From this directory, use Python 3.9+ and its standard library. Validation needs no platform credentials or downloaded dependencies:

```bash
openbkn bkn validate kn
python3 tools/verify.py
python3 bkn-eval/run.py
```

Native BKN validation requires an installed OpenBKN CLI. Scripts independently reconstruct 8,000 positions, 8,000 valuations and 5,000 limit assessments, then replay all 100 frozen answers. From the repository root, `python3 tools/financial_fibo/test_financial_fibo.py` runs bilingual-equivalence, negative-injection and regression controls.

`data/` contains locked CSVs; `dataset.lock` binds digests and counts. `kn/network.bkn` is the sole model entry point. `model-contract.json` describes fields and FK relationships. `bkn-eval/` contains questions, complete structured answers, read-only evidence SQL and the replayer. Source-checkout `verification/` holds local evidence; it is not part of the install archive.

## Review evidence

[Initial findings, resolution and independent recheck](docs/expert-review-resolution.zh-CN.md) record the 55 financial/bilingual controls and full review evidence.

## Sources and delivery boundary

Source: [official EDM Council FIBO repository](https://github.com/edmcouncil/fibo), pinned revision `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`, MIT license. Six original RDFs, the original license, SHA-256 digests and named class/property inventories are in [fibo-reference/](fibo-reference/README.md). These are selected business-scope modules, not all FIBO or its transitive import closure.

This is a local offline candidate requiring **OpenBKN >=0.2.1 <0.3.0**. [Offline installation](docs/offline-installation.md) uses the standard Studio import/install flow and the shared MariaDB database. The package includes `sample.yaml`, typed database loading/verification hooks and native BKN resource-binding hooks. No official catalog entry or online release is created. SQL replay validates frozen answers; it does not measure model accuracy. Live question-only model transcripts and scoring are separate acceptance artifacts. Valuation snapshots and SQL are data and offline acceptance tools; no runtime metric, function or Skill is installed.
