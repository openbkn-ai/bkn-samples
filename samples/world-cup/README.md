# World Cup (Chinese network)

This package installs the Chinese knowledge network; [中文说明](README_cn.md). Query tournaments, teams, players, matches and events such as goals, cards, substitutions and shootouts from Joshua C. Fjelstul's open World Cup history data. Includes 27 data tables, the ontology and 1 business Skill. Business needs and rules are in the [PRD](docs/PRD.md).

## Install and try

1. Sign in to OpenBKN and open **Quick start** on the home page.
2. Refresh the official catalog, choose **世界杯** and click **Install**; it needs **OpenBKN >=0.2.1 <0.3.0**.
3. Wait for installation and verification to finish, then open the World Cup knowledge network.
4. Try the experience cards in smart Q&A, data query and graph exploration, or connect an external agent over MCP to query objects and use the Skill.

Without access to the official catalog, download this sample's `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases) and install it with **Import offline package** in Quick start.

The locked snapshot contains **27 CSV tables and 81,200 rows**: 22 men's World Cups through 2022 and 8 women's through 2019. Detail records cover different editions; names of people, teams and awards keep the source spelling.

## Capabilities

Every question can be answered with Cypher, so the sample ships no functions and no metrics, and the Community edition can use all of it.

- **Cypher queries**: tournaments and hosts, teams and confederations, squads and players, managers and referees, stadiums, matches and scores, goals, cards, substitutions, shootouts, group tables and final standings, awards.
- **Skill**: "World Cup history analysis" for sports editors, team analysts and tournament data stewards, stating the business rules, Cypher patterns and how to answer.

## Experience cards

15 experience cards are taken from the test set, covering editions, the 2022 tournament, the final and its shootout, goals and cards, Messi's awards and goals, a co-hosted tournament, the 1950 format and the two Müllers. The cards' data-query and graph Cypher are checked online after installation with `tools/acceptance/experience_set.py`.

## Acceptance and maintenance

The test set is the [business-scenario test set v1](bkn-eval/baselines/2026-10-31-business-scenarios-v1/README.md); reference answers are computed by reference SQL directly from the locked CSV files and are not shipped in the package. After installation, an agent that has not seen the answers runs every question once; below 100%, record why it failed and change the ontology description or the Skill first, never the questions or answers.

The installation hooks call `run.sh` and register the Skill; users never run scripts by hand. To upgrade, uninstall the old sample before installing the new version.

## Data and attribution

Data: [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup), commit `35a8667f518b07469182ae16d35574dd0e7a00fb`; the CSV hashes are recorded in [dataset.lock](dataset.lock).

© 2023 Joshua C. Fjelstul, Ph.D. Data is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Retain the attribution and license when sharing data or adaptations.
