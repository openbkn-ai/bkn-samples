# Offline candidate installation / 离线候选包安装

Requires OpenBKN >=0.2.1 <0.3.0 with sample offline.v2 and database.shared support.

1. Build the candidate using `python3 -m tools.publication.build_candidate samples/SAMPLE --version VERSION --output /absolute/output --shared-database` from the source repository. The Git index is the explicit file allowlist; candidate bytes come from the working tree. No commit, push or catalogue update is required for local acceptance.
2. In Studio, import the resulting `package.tar.gz` as an offline sample. The corresponding API is `POST /api/studio/samples/import` with raw gzip bytes and an authorized local session.
3. Install the imported version from its sample card. The installer creates an owned shared-MariaDB database, discovers 20 table resources, imports the BKN directory and binds all 20 objects. It also installs and verifies 2 recorded metrics, 3 native functions and 1 Skill with owned execution-resource receipts. It checks all 78,356 typed records against locked CSV contents, model counts, bindings and live queries for every object type.
4. Wait until all five stages succeed. A partial install is not acceptance. For removal use the sample card's uninstall operation, which uses installer ownership receipts; do not delete shared databases or unrelated networks manually.
5. After package freeze, execute the approved question-only acceptance workflow for each language. Keep public regression, independent evaluation and perturbation evidence separate; preserve failures and tool/lifecycle errors in their denominators. Use references only after saving responses. Deterministic SQL replay does not measure model business accuracy.

两个语言是独立样例，具有独立数据库、知识网络和安装回执。不得把本地候选包加入线上发布列表。原始问答记录、模型与工具调用、评分、包摘要保存在独立验收目录，避免混入数据源。

Candidate **0.2.4** is unpublished; this PR contributes source and recorded validation only. After source merge, build and validate a fixed candidate from that commit, then publish immutable assets and register them in a separate catalog PR. Historical package verification cannot be relabeled for this version. See [actual results and limits](../../../docs/financial-fibo-183-readiness.zh-CN.md).
