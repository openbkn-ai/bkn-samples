# Recorded GS1 retail evaluation evidence

`first-pass/` preserves the original 100-question scores and structured submitted rows for each language. `targeted/` preserves only the explicitly authorized four English and five Chinese retests, their scores and installation/registered-code summaries. Each answer includes the digest of its full raw tool trace, retained by the local verifier; full traces and authentication/session state are not distributed here. These are historical local 8081 observations, not newly executed CI questions or official release verification receipts.

The original bank and original comparator are retained under each sample's `bkn-eval/original/`. Current bank corrections have separate revision metadata. Replay each batch against its own bank and comparator; do not substitute the revised gold into the original results or combine the batches into a full-bank 100% claim.

```sh
python3 tools/retail_eval/replay_recorded.py
```

This command audits saved answers offline. It neither contacts 8081 nor calls a model. Source/candidate review still precedes building and verifying an immutable publication package. The live-tested repaired package digests are recorded in `targeted/*-installation.json`; changes to README/release notes during source review do not retrospectively verify a newly built archive.
