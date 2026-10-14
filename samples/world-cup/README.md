# World Cup

Explore a Chinese-language ontology over public World Cup history through object queries, joins, rankings and cross-tournament analysis. Install through standard one-click onboarding, then let an external agent read facts through MCP and perform the analysis.

[中文文档](README_cn.md)

## Data and model

The locked snapshot contains **27 CSV tables and 81,200 rows**: 22 men's editions through 2022 and eight women's editions through 2019. Detail coverage varies by table. Names and historical identities retain their source spelling.

- Sample ID: `world-cup`
- Knowledge network: `worldcup_vega_catalog_bkn`
- Database: `worldcup`
- Model: 27 object types, 29 relationships and four concept groups
- [Model overview](bkn-network-structure.html)

## One-click onboarding

1. Open **Studio → One-click onboarding** and refresh the sample catalog.
2. Select World Cup, check its version and release notes, and select **Install**.
3. Wait for installation and verification to complete, then open the knowledge network.
4. Connect an external agent through MCP to inspect object definitions, retrieve complete instance pages and perform joins and calculations.
5. Use **Uninstall** to remove the sample. Reinstall after cleanup completes; installation history is retained.

If the catalog is unreachable, download this sample’s `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases) and use **Import offline package**, then install it. Its referenced data image must also be reachable or preloaded in the target cluster. See the [development and publication guide](../../docs/SAMPLE_DEVELOPMENT_GUIDE.md). The [official catalog](../../catalog.json) determines installable versions; new source-controlled evaluation material does not replace an existing release package.

## Questions to try

- Which awards did Lionel Messi receive in WC-2014 and WC-2022?
- Which players were in Argentina's WC-2022 squad, and how many appearances and goals did each record?
- Which players share a top-five scorer rank at WC-2022?
- How do Argentina's WC-2022 match goals and shootout records reconcile?
- How many matches, squad entries, goals and player appearances are recorded for WC-1999?

## Chinese scenario evaluation

The suite provides **50 Chinese questions, reference answers, recalculation and grading scripts**:

| Category | Questions |
| --- | ---: |
| Basic queries and statistics | 10 |
| Multi-table joins | 12 |
| Rankings and cross-tournament comparisons | 14 |
| Combined analysis | 14 |

- [Evaluation guide and business semantics](https://github.com/openbkn-ai/bkn-samples/blob/main/samples/world-cup/bkn-eval/README.md)
- [Question set](https://github.com/openbkn-ai/bkn-samples/blob/main/samples/world-cup/bkn-eval/datasets/question-set-v1.yaml)
- [Reference answers](https://github.com/openbkn-ai/bkn-samples/blob/main/samples/world-cup/bkn-eval/gold/answer-set-v1.yaml)

An independent external agent answers through MCP without seeing the reference answers. Check its required fields, ordering and business values after completion. Evaluation uses standard object queries rather than a runtime SQL endpoint, an internal Vega query interface or the platform-internal agent.

The evaluation scripts are maintained on `main`; follow the linked evaluation guide from a main-branch source checkout.


Evaluation suites and tests remain in source control and are excluded from runtime packages by the current packaging rules. Execution records and temporary calculation files remain local.

## Query semantics

Count matches from `matches` or distinct `match_id`. A team appearance represents one team in one match, so each match has two team records. Exclude own goals from individual scoring; include them for the credited team. Shootout kicks are separate from match-score goals. Booking flags may overlap and must be counted as requested.

The current model omits ten CSV display fields each from matches and team appearances. Resolve labels and stages through declared team, referee-appearance, goal or manager-appearance objects. Convert numeric text before capacity comparisons, row-key ordering or calculations, and retrieve every required page.

## Development and publication

[sample.yaml](sample.yaml) declares the installed components and hooks. Installation hooks call `run.sh` internally; users install through one-click onboarding or offline package import. Historical SQL tool registration is not the query path described here.

Follow the [Sample Development Guide](../../docs/SAMPLE_DEVELOPMENT_GUIDE.md) to build a fixed candidate, validate installation and business scenarios, and publish a new immutable version when changing data or models.

## Data source and license

Data: [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup), commit `35a8667f518b07469182ae16d35574dd0e7a00fb`. [dataset.lock](dataset.lock) records checksums for all 27 CSV files.

© 2023 Joshua C. Fjelstul, Ph.D. Data is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Preserve attribution and share-alike requirements when sharing data or adaptations.
