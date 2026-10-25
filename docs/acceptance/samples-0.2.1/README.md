# OpenBKN 0.2.1 sample candidates: local evidence

Source inventory: **11 standard samples**. This batch contains **9 candidates**;
`manufacturing-industry-en-us` and `manufacturing-industry-zh-cn` still need unified
packages and local/target acceptance. The batch is not complete product coverage.

These candidates are intended for download and offline import into a later fixed
OpenBKN 0.2.1 test environment. They have not passed product installation, real
MCP/Agent, upgrade or uninstall acceptance. No official catalog entry or successful
platform verification receipt is created by this work.

Local checks:

- Installer: 315 tests, one existing skip (run with Python 3.11 and Helm).
- Supply tools: 236 tests per language, including frozen data/function business rules.
- World Cup: 10 baseline tests across both languages.
- World Cup isolated MariaDB: 27 tables and 81,200 rows per language, 142 physical
  BIGINT columns per language, all 50 frozen SQL answers per language; the score
  range query and an independent CSV oracle both give 326.
- FIBO capability reconstruction: 21 local tests.
- GS1 structural audit: 2,911 source rows per language, bilingual fact identity.
- Metric fixtures: upstream MCP request schemas, date literal types, immutable
  definitions, exact numeric display, warning/partial/no-data handling, opaque
  cursor/bucket handling, completeness, independent CSV query expectations.
- Both product catalogs and the legacy root catalog pass metadata validation.

The SQL evidence records the actual cached MariaDB 11.4.13 image ID; it is not a
claim about product MariaDB 11.4.7 or OpenBKN query pushdown. The harness uses loader
DDL and value conversion with direct SQL, then compares locked gold answers. The
existing `AS rows` alias is quoted for MariaDB portability without changing the
frozen query's business semantics or expected answers. Run:

```sh
python tools/acceptance/worldcup_mariadb.py --image mariadb:11.4 --output /tmp/worldcup-evidence.json
```

The harness creates a unique temporary container without networking or exposed
ports and removes it afterwards. It uses a locally cached image (`--pull=never`).

Source function and Skill behavior is preserved. The 0.2.0 branch PR #184 is not
merged wholesale: it resets supply data and removes Skills. Managed-context,
function execution and existing-sample replacement remain explicit target-runtime
checks. The metric inventory documents 30 unchanged version-1 definitions; no
sample is converted into a live or cross-date metric just to expand the demo.

Candidate publication must retain package digests and exact source commit. Failed
or changed candidates get a new version; stable catalogs accept only the same
bytes that later pass the target-platform checks.
