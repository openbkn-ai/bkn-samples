# GS1 retail samples: scope and actual acceptance

Publication update: source PR #186 is merged. The English and Chinese 0.1.0 immutable Release assets have passed exact-archive fresh-install verification and are published. The follow-up catalog PR remains unmerged; use offline import on OpenBKN 0.2.1 or later. The sections below retain the original evaluation history; fixed-release evidence is summarized at the end.

Source-release candidate 0.1.0, requiring **OpenBKN 0.2.1 or later** within the current manifest range `>=0.2.1 <0.3.0`. This PR prepares two independent English/Chinese samples for review; immutable Release assets and catalog registration follow source approval. No claim of full-bank 100% accuracy is made.

Each sample has15 populated object types/tables,30 relations,3 concept groups and2,911 fictional records; every table has at least50 rows. Three generic functions cover dated inventory, shared-stock order/replenishment planning and recall assessment, with two dated snapshot metrics and one investigation Skill. The10 PRD scenarios map to100 questions per language:30 basic,40 medium,30 complex. Actual/planned and business/knowledge dates are explicit; plans extend through March31,2027. See each sample's PRD, ontology, public business contract and GS1 source/license documentation. GS1 WebVoc is a conceptual reference, not a claim to implement its complete ontology or an EPCIS server.

## Original full pass

Two fresh isolated AI answerers used live 8081 MCP tools. They did not receive localCSV, runtime sources, old answers or gold. Source, public questions and evaluator were frozen; each question has one first terminal. All200 questions ended before scoring. Reference calculations were independently implemented from source records, without importing runtime calculations.

| Language | Basic | Medium | Complex | Original total |
|---|---:|---:|---:|---:|
| English |29/30|37/40|30/30|**96/100**|
| Chinese |29/30|37/40|29/30|**95/100**|

Both languages had100 completed executions and no business-tool exceptions. At finish, English evidence was25 complete/75 assembling; Chinese21 complete/79 assembling. Assembling is asynchronous and does not prove failure or complete capture. These are frozen-contract exact-match results; question/reference defects prevent treating them as a dispute-free business accuracy estimate.

## Findings and repair

| Cases | Cause | Change |
|---|---|---|
| Q018, both | Gold implicitly filtered positive returns; wording did not explicitly exclude zero rows | State returned>0 explicitly; no quantity facts changed |
| Q033, both | Gold implicitly filtered positive quarantine; wording did not explicitly exclude zero rows | State quarantined>0 explicitly |
| Q027, both | CSV gold used empty strings where native absent endpoints were null; original comparator also ignored requested event order | Normalize nullable source fields; generic order contract checks date, numeric sequence and event ID |
| Q028, Chinese | Upstream-only wording conflicted with full connected-component gold | Both languages now request the complete upstream/downstream undirected component, including sibling edges; include LINK-048 provenance |
| Q094, both | Runtime deduplication compared SDK record/display metadata as business payload | Compare explicit business fields; normalize dates and Decimal values; retain genuine conflicts |

EV-00875's two rows differed only in physical record identity, knowledge date and SDK metadata. On the old installed engine, LOT-042-C/STORE-017 therefore became unknown. The repaired engine ignores the duplicate and returns on-hand28, sold12, returned3, available23. This is a sample adapter defect, with no evidence that a platform query defect caused it.

## Authorized targeted retest

After explicit user authorization, both repaired candidates were installed via the standard uninstall/cache-delete/import/install flow. All five stages passed. Six registered function definitions were read without execution and matched the repaired archive engine exactly. English initially returned503 Proxy.SyncPending; standard installation retry recovered, with the failed record retained. No platform code changes were made.

New isolated answerers then ran **only English Q018/Q027/Q033/Q094 and Chinese Q018/Q027/Q028/Q033/Q094**, once each. All nine ended before strict scoring: **English 4/4, Chinese 5/5**. All nine execution states were completed and evidence states complete, with no business-tool errors. Q027 satisfied the strengthened ordering contract; Q028 included all three connected edges; Q094 returned the expected28/12/3/23 quantities and DUPLICATE_EVENT_IGNORED.

Q094 confirms the runtime repair. The other cases confirm clarified questions and output contracts, rather than proving a model capability gain. Original96/95 scores remain unchanged. The revised full banks were not rerun; do not combine batches into “100/100 in each language.”

The tested repaired package digests are English `f1274fc96dfcc7b6aab66d904b2f09bc3af2a07802979860a7deaa1b9ca921a1` and Chinese `34391f05c2c07587f1df1f5edd97e2d5853a1927332862d8d226a102160f6edd`. These identify the exact local test archives, not future publication builds after source review.

## Evidence and limits

[Recorded answers, scores and installation summaries](retail-gs1-evidence/README.md) support offline reproduction using the original/revised comparator separately. The original bank is retained in source, and corrected bank metadata explains its relation to the original freeze. Development checks included179 core invariants,760 independent source/negative controls,106 source-calculation comparisons and104 offline checks replaying the captured native representation. These are not additional AI acceptance rounds.

This is a synthetic operational sample and an isolated AI evaluation, not professional certification or a production guarantee. It does not execute procurement/payments, dispatch or recall notifications, train forecasts or optimize routes. Returns stay quarantined; generic release/redistribution is outside scope. Snapshot metrics are not live recomputation. Release publication must bind the exact reviewed commit and verified package; this source PR does not create catalog entries or official successful verification receipts.

## Immutable publication after source review

Both 0.1.0 packages were built from clean merged source `5a03b975aa9a1dda0df126b0e8bce8f30a00162f`. Exact published digests are EN `d1bbf2b8d6d19a85eb3659f141a60f66a309002ace0b7ba224ba064f0ccd09c2`, ZH `7313ddec87edf4d90eb3510441e8fe6d13d17f86a30791b363a6be7b459f4e83`. Compared with the prior targeted archives, runtime and data bytes are identical; only README, release notes and the offline descriptor differ.

Each exact publication archive passed standard uninstall/cache removal/import/fresh-install on 8081, all five stages,15 live table counts totaling2911 rows, all15 bindings,3 actual functions,2 metrics and mounted Skill/business contract. Other nine sample cards/identities were unchanged. Both fixed technical interactions completed execution; evidence was assembling at finish. This is bounded publication verification using packaged deterministic output parity, not a new independent model evaluation or a claim of final trace closure. Architecture tested is arm64; no cluster-wide outbound isolation was imposed.

[English Release](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-en-us-v0.1.0) and [Chinese Release](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-zh-cn-v0.1.0) contain package.tar.gz, acceptance.json and SHA256SUMS. All three assets were downloaded and compared byte-for-byte before publication. The standard public client subsequently fetched actual pinned metadata and public release assets, validated archive/evidence digests, safely extracted native BKN and all15 declared bindings, rejected 0.2.0 before downloading metadata and accepted 0.2.1. See [client verification](retail-gs1-evidence/publication-client-verification.json) and [package parity](retail-gs1-evidence/publication-package-parity.json).

Metadata is retained at `1533b268e1e37421671e02fb57499be03c0e8f45` through tag `samples-retail-gs1-metadata-20261020`. The proposed catalog adds only the two releases, preserves all12 previous entries and advances sequence13 to14. No legacy 020 bundled index changed. Official main-catalog refresh/online-install verification awaits the catalog PR merge; it is not claimed here. Original EN96/ZH95 and targeted EN4/4,ZH5/5 remain historical scores at their original digests; no question bank was rerun for publication.
