# Diagnostics sample release acceptance — 2026-10-31

Status: **all twelve fixed packages accepted and published; product 0.2.1 catalog sequence 6**.

PR #237 is merged. Native package acceptance found the English counterpart of #217: the 0.1.12 candidate retained an unbound Skills object. PR #238 removes only that object and prepares 0.1.13. The failed 0.1.12 draft and archive are retained and must not be published. The other eleven package digests are unchanged.

| Sample | Version | Business tables | Objects | Native functions called | Mounted Skills read | Cypher queries / graph patterns |
| --- | --- | --- | --- | --- | --- | --- |
| supply-chain | 0.1.18 | 12 | 11 | 2 | 2 | 7 / 3 |
| supply-chain-en | 0.1.13 | 12 | 11 | 2 | 2 | 7 / 3 |
| world-cup | 0.1.8 | 27 | 27 | 0 | 1 | 7 / 3 |
| world-cup-en | 0.1.4 | 27 | 27 | 0 | 1 | 7 / 3 |
| manufacturing-industry-en-us | 0.1.6 | 40 | 40 | 0 | 2 | 6 / 4 |
| manufacturing-industry-zh-cn | 0.1.6 | 40 | 40 | 0 | 2 | 6 / 4 |
| financial-fibo-en-us | 0.2.8 | 20 | 20 | 3 | 2 | 6 / 4 |
| financial-fibo-zh-cn | 0.2.8 | 20 | 20 | 3 | 2 | 6 / 4 |
| retail-gs1-en-us | 0.1.3 | 15 | 15 | 3 | 2 | 5 / 4 |
| retail-gs1-zh-cn | 0.1.3 | 15 | 15 | 3 | 2 | 5 / 4 |
| energy-saref4ener-en-us | 0.1.7 | 15 | 15 | 3 | 2 | 7 / 4 |
| energy-saref4ener-zh-cn | 0.1.7 | 15 | 15 | 3 | 2 | 7 / 4 |

Every fixed archive passed import, a bounded internal-dependency failure, retry with the same archive and executor, uninstall with its active package cache absent and external HTTP unavailable, and fresh reinstallation. A retained unrelated sample remained queryable before and after each cleanup. Every object returned a live row through its resource binding. Declared native functions executed, and mounted Skill contents and file inventories matched the source. The dated financial snapshot checks matched source CSV without cross-date aggregation.

Each release directory contains its immutable manifest, verification metadata and a public acceptance summary. Detailed runtime receipts, environment/resource identities, raw responses, logs and credentials remain private; the public summaries contain only package/source identities and the check results needed to assess the release. This is a publisher acceptance summary, not a raw runtime export.

The environment was Linux arm64 on an OpenBKN 0.2.1 main build; this does not certify an unpatched 0.2.1 release or native amd64 execution. Only the listed reference Cypher queries and graph patterns were checked. Cards without a direct reference check were not exercised as full questions; no browser UI or model-question benchmark was run for these artifacts. All samples declare metrics disabled. Paid-license transitions and the original invalid-metric publication chain are outside this acceptance.

Publication follows the [fixed-package standard](candidate-publication.md): preserve historical assets, publish the accepted archive and public proof unchanged, then register metadata pinned to a retained commit with a higher catalog sequence. Product 0.2.0 catalogs remain unchanged. After registration, refresh the product directory and verify the same packages through online installation.

The directory pins release metadata to `02ce10305a8f476497efad8acde5b5bbd5fc891d`. Prior published manifests and proofs are unchanged. Supply Chain 0.1.17 and Supply Chain EN 0.1.11 remain as withdrawn directory entries, with their Release assets retained; the failed EN 0.1.12 remains an unpublished draft. The 0.2.0 directories remain unchanged.

Online-delivery receipts are added separately as `online-acceptance.json` Release attachments after product-catalog installation; they do not replace the fixed prepublication proof.
