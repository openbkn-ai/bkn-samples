# World Cup

Explore tournament editions, teams, players, stadiums and match events through an English knowledge network and the standard MCP object-query tools.

The locked snapshot contains **27 CSV tables and 81,200 rows**: 22 men’s editions through 2022 and eight women’s editions through 2019. Detail coverage varies by table. Names, accents and historical identities retain their source spelling.

## Contents

- 27 object types with all 410 CSV fields, 29 relationships and four concept groups.
- 50 evaluation questions, deterministic reference answers and a CSV-based recalculation script.
- Managed installation and verification hooks, with a separate database and knowledge network named `worldcup_en`.

No custom functions, metrics or executable business Skills are declared in this release. Independent external agents query the published object model through MCP and compute the requested results.

## Installation

Open **Studio → One-click onboarding**, refresh the official catalog, select **World Cup (EN)** and click **Install**. Wait for installation and verification to complete, then open the knowledge network.

If the catalog is unreachable, download this sample’s `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases), choose **Import offline package**, then install it. The referenced data image must be reachable or preloaded in the target cluster.

See [the import guide](docs/import-guide.en-US.md), [model semantics](kn/README.md) and the repository’s [evaluation suite](https://github.com/openbkn-ai/bkn-samples/tree/main/samples/world-cup-en/bkn-eval). The evaluation suite is maintained in source control and is excluded from the runtime installation package. To remove an installed sample, use **Uninstall** and wait for cleanup to finish before reinstalling. Installation history is retained.

## Questions to try

- Which awards did Lionel Messi receive in WC-2014 and WC-2022?
- Who won the 2014, 2018 and 2022 men’s tournaments?
- Which players share a top-five scorer rank at WC-2022, excluding own goals?
- How do Argentina’s match results, credited goals and shootout outcomes reconcile at WC-2022?

## Data and attribution

Data: [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup), commit `35a8667f518b07469182ae16d35574dd0e7a00fb`. The CSV hashes are recorded in `dataset.lock`.

© 2023 Joshua C. Fjelstul, Ph.D. Data is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Retain the attribution and license when sharing data or adaptations.
