# Financial Portfolio Operations (FIBO reference, EN)

A fictional asset manager’s securities post-trade control sample: instrument, legal entity and portfolio → order and execution → settlement → position → price and valuation → issuer concentration and unsettled-receivable limits.

## Published package

Fixed [0.2.5 Release](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.5) contains the immutable package, acceptance evidence and checksums. Requires **OpenBKN >=0.2.1 <0.3.0**. Offline import uses that package; official online discovery follows the merged catalog. [Release acceptance and limits](../../docs/financial-fibo-release-0.2.5.zh-CN.md) distinguish original EN/ZH 96/100 financial-field scores, the four-path **4/4 (100%)** post-fix tool regression and fresh-package technical checks. No full-bank 100% claim.

Version 0.2.5 corrects publication notes and execution requirements only. Business data, ontology, functions, metrics, Skill and evaluation banks are byte-identical to 0.2.4. Historical 0.2.4 assets remain unchanged; only versions registered in the merged official catalog are available online.

## Start here

1. [Business PRD](docs/PRD.md): stakeholder concerns, P0 decisions and boundaries.
2. [BKN model and calculation rules](docs/bkn-modeling-spec.md): 20 object types, 29 relations, 3 groups and all financial formulas.
3. [FIBO semantic mapping](docs/fibo-operational-mapping.md): pinned sources, mapping decisions and explicit operational extensions.
4. [Dataset and business branches](docs/dataset-scenarios.md): record counts, relationships and shared-price effects.
5. [100 questions and full answers](bkn-eval/answers.md): 10 acceptance scenarios; 30 easy/basic, 40 intermediate, 30 hard/complex.

The observation date is **2027-02-28**. November 2026 through February 2027 are actual views; 2027-03-31 is a planned view known at the observation date. All business facts use dates. Each table has at least 50 records; the largest exceeds 16,000. There are **78,356 records per language** in this revision. English and Chinese share business keys, numeric facts and semantics; human-facing names, states, reasons, questions and answers are localized.

## Current validation status

This 0.2.5 release provides the reviewed source and fixed package, with 3 functions, 2 recorded-snapshot metrics and 1 investigation Skill. [Results and limits](../../docs/financial-fibo-183-readiness.zh-CN.md) separate the original EN/ZH 96/100 run from the four-path post-fix regression. Source PR #183 is merged. Online discovery follows the official catalog; offline import uses the fixed Release assets.

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

This is a fixed package requiring **OpenBKN >=0.2.1 <0.3.0**. [Offline installation](docs/offline-installation.md) uses the standard Studio import/install flow and the shared MariaDB database. The package includes `sample.yaml`, typed database loading/verification hooks and native BKN resource-binding hooks. The official catalog controls online discovery; use the fixed Release assets for offline import. SQL replay validates frozen answers; it does not measure model accuracy. Live question-only model transcripts and scoring are separate acceptance artifacts. Installs 2 recorded-snapshot metrics, 3 atomic reconstruction functions and 1 read-only investigation Skill. See the [capability contract](docs/business-capability-contract.md). Public 100-question regression is not blind accuracy.


## This capability revision

The public 100-question difficulty split is unchanged. An additional [30 complex capability cases](bkn-eval/capability-questions.json) and [development references](bkn-eval/capability-expected.json) cover cross-date comparison, atomic reconstruction and cache differences. These references are implementation-generated development regressions, not independent correctness evidence. Independent holdout/perturbation answers are excluded from installation packages. Fixed 0.2.5 assets are published. The historical single public run scored 96/100 financial fields per language; no new question-bank run was made for 0.2.5; the four specified post-fix tool paths passed separately. Historical 0.2.2 records remain unchanged and are not rescored. Neither result is independent blind accuracy.

[Public response contracts](bkn-eval/response-contracts.json) define field types and meanings without expected values or record counts. The original100-question gold stays unchanged. Declared SQL0/1 Boolean and source-category alias equivalences are documented by the scorer; raw legacy-contract scores are also retained.

The English and Chinese packages are independent samples, each with its own database, network and installation receipts. The 0.2.4 source added component-completeness semantics and bounded observation requests to the existing three functions; the recorded native preflight checks specific platform inputs and output bounds without guaranteeing all maximum-size requests. Business requirements start in the [PRD](docs/PRD.md), interface details in the [capability contract](docs/business-capability-contract.md). This selected post-trade scope does not represent all FIBO, official NAV or regulatory risk.

Multi-observation requests allow at most 20 portfolios and 12 observations including the base; scalar requests retain the 200-portfolio input bound. The guard measures the complete compact JSON serialization as UTF-8 bytes and rejects results above 3 MiB. Native platform preflight observed a 4 MiB result quota; the 3 MiB application guard leaves transport headroom. These input-count bounds do not guarantee that every maximum-size input succeeds: result size depends on records and evidence. On a limit failure reduce portfolios or observations; never truncate required rows or evidence. The original native preflight and the single public 100-question pass per language are recorded in the [validation report](../../docs/financial-fibo-183-readiness.zh-CN.md). Input bounds are not universal runtime guarantees. The four specified post-fix tool paths passed separately; the fixed package is available from the Release.
