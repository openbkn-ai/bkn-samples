# 0.1.6 — OpenBKN 0.2.1 candidate

Load all 142 model-declared integer columns as BIGINT and preserve strings, including IDs. Validate explicit type maps and reject malformed integers before promoting loaded tables. Both language datasets pass 50/50 frozen SQL cases on isolated MariaDB 11.4.13; numeric score filtering matches the CSV oracle (326). OpenBKN query-engine and declared-function acceptance remains pending.

Self-contained package for download and offline import into OpenBKN 0.2.1 with the shared sample database. Candidate only: local validation is not platform acceptance. Not added to an official catalog. Existing installations must be uninstalled before installing this new version; no in-place migration. Historical packages are unchanged.
