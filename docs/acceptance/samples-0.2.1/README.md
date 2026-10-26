# Complete OpenBKN 0.2.1 sample candidates: local evidence

All **13 standard source samples** are covered by the same
[machine-readable plan](../../../tools/publication/candidates-0.2.1.json): Order Basics
and bilingual Supply Chain, World Cup, Manufacturing, Financial FIBO, Retail GS1 and
Energy SAREF4ENER. Missing, duplicate or unregistered identities fail the batch build.
Manufacturing is **0.1.3** per language and Energy is **0.1.5** per language.

The complete set is built from clean committed source. Archive digests, offline
inspection and declared architecture compatibility are checked for every sample.
Those checks do not execute installation hooks or prove amd64/arm64 native runtime
support. The 0.2.0 product floor rejects these 0.2.1 candidates. No successful
platform verification receipt is created and no new candidate is added to stable
catalogs by this work. Prior package assets and the 0.2.0 root catalog remain intact.

## Current local checks

- Installer: 321 tests, OK with one existing skip, including complete-plan, ownership, data/type, references,
  schemas and consumer checks.
- Manufacturing: each language passes 71 relationship checks, material/BOM and
  shipment gates, 112 IOF reference-instance/link checks, 18 deterministic scenarios
  and the structural 100-question bank checks. No new Agent bank is run.
- Energy: 12 independent hand-built engine boundaries and 4 managed adapter tests;
  100 historical structured-projection cases per language replayed locally with
  explicit source-record SHA-256 provenance and question output contracts. This
  regression is not a new model-accuracy score. The lost original independent oracle
  is not represented as restored; see the [recovery record](energy-recovery.json).
- Real database hooks for the four Manufacturing/Energy samples: init, full typed
  row verification, repeat init and verify on an isolated temporary MariaDB. Each
  manufacturing language has 40 tables/2,700 records; each energy language has
  15 tables/14,787 records. Column types are separately inspected through
  information_schema. The report is [industry-energy-database.json](industry-energy-database.json).
- Supply tools: 236 tests per language; World Cup baseline suites: 10 tests.
- Eight metric-bearing samples / 34 definitions: request schemas, typed dates,
  immutable definitions, exact display/units, states, complete paging, opaque
  cursor/bucket handling and CSV-based example expectations. No metrics are forced
  into manufacturing or the other non-metric samples.
- Legacy root and both product catalogs pass metadata validation; Helm rendering,
  lint and documentation links are checked.

## Reproduction

```sh
python -m unittest discover -s installer/tests
python -m unittest tools.energy_saref4ener.test_engine tools.energy_saref4ener.test_adapter
python tools/energy_saref4ener/verify.py --sample en-us
python tools/energy_saref4ener/verify.py --sample zh-cn
python tools/acceptance/industry_energy_database.py --output /tmp/four-database-evidence.json
python -m tools.publication.build_candidate_set --output /absolute/path/outside/repository
```

The database harness needs the existing Python database dependencies, Docker and a
locally cached MariaDB image (`--pull=never`). It creates an isolated temporary
bridge and exposes a random port only on 127.0.0.1, then deletes its own container
and network. The actual report uses MariaDB **11.4.13**, not a claim about product
MariaDB 11.4.7 or OpenBKN query pushdown. The separate [World Cup report](worldcup-mariadb.json)
retains 50/50 SQL gold cases per language and CSV-independent score count 326;
its original `AS rows` alias is quoted for MariaDB SQL portability.

## Remaining target-product acceptance

Real fixed OpenBKN 0.2.1 install, bounded failure retry, uninstall, replacement,
CLI/API/MCP, metric create/publish/query/drill, functions/Skills and query-engine
behavior remain pending under the user's requested scope. Source function/Skill
behavior is retained; the 0.2.0 PR #184 is not merged wholesale. Candidate publication
is not stable catalog admission, migration support or proof of target runtime success.

## Interrupted binding recovery

Manufacturing 0.1.3 and Energy 0.1.5 add a local regression for an interrupted
owned-network import: a retry preserves existing matching resource bindings and
fills only unbound objects. All object bindings are inspected before the first
update, so a foreign binding aborts without changing any object. Verify refuses
missing bindings and performs no writes. The test covers all four sample hooks;
this does not replace target-product install/retry acceptance. Previous package
versions and their assets remain immutable.
