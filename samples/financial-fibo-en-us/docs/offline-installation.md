# Offline candidate installation / 离线候选包安装

Requires OpenBKN >=0.2.1 <0.3.0 with sample offline.v2 and database.shared support.

1. Build the candidate using `python3 -m tools.publication.build_candidate samples/SAMPLE --version VERSION --output /absolute/output --shared-database` from the source repository. The Git index is the explicit file allowlist; candidate bytes come from the working tree. No commit, push or catalogue update is required for local acceptance.
2. In Studio, import the resulting `package.tar.gz` as an offline sample. The corresponding API is `POST /api/studio/samples/import` with raw gzip bytes and an authorized local session.
3. Install the imported version from its sample card. The installer creates an owned shared-MariaDB database, discovers 20 table resources, imports the BKN directory and binds all 20 objects. It also installs and verifies 3 native functions and 2 Skills with owned execution-resource receipts. It checks all 78,356 typed records against locked CSV contents, model counts, bindings and live queries for every object type.
4. Wait until all five stages succeed. A partial install is not acceptance. For removal use the sample card's uninstall operation, which uses installer ownership receipts; do not delete shared databases or unrelated networks manually.
5. Run the [business-scenario test set v1](../bkn-eval/baselines/2026-10-30-business-scenarios-v1/README.md) once per question through MCP with an agent that has not read the answers. The model gets only the questions and the installed capabilities; score with the reference answers only after saving responses, and keep failures and tool or session errors.

The two languages are independent samples with their own database, knowledge network and installation receipt. Keep raw answers, model and tool calls, scores and package digests in a separate acceptance directory, never mixed into the data sources.
