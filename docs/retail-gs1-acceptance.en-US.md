# GS1 retail samples: scope and actual acceptance

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
