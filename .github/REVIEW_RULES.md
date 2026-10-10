# bkn-samples PR review rules

Review every changed file for concrete problems that could make a sample unsafe or unusable. Existing BKN and KN JSON formats are valid; do not require format conversion or future protocol work.

## Check

1. **Install and try:** references to models, data, functions, and Skills resolve; initialization and verification describe the actual sample; retries do not duplicate or overwrite resources unexpectedly.
2. **Source safety:** no real secrets or unauthorized sensitive data; new code and dependencies do not exfiltrate data, download and execute untrusted code, delete unrelated data, or grant unnecessary access.
3. **Release truth:** released files are immutable; version and release notes match the change; installed and verified versions are stated accurately.
4. **Loose coupling:** a sample does not add `sampleId` branches to Studio or the shared installer; required capabilities and compatibility limits are explicit.

## Decision

- **Blocker:** a changed file contains a concrete, reachable failure or security problem with file and line evidence. Uncertain concerns are advisory.
- **Advisory:** at most two items on the first review and one new item on re-review. Do not report style preferences, old issues, or broad architecture ideas.
- Re-review each carried blocker against the current commit. Close it only with evidence that it is fixed or false; otherwise mark the review incomplete.
- The summary is at most two sentences. Put unreviewed source in `not_covered`; disclose fixed-digest Release or OCI artifacts in `external_not_covered` without blocking when fresh installation evidence binds them.

Do not run PR code, install dependencies, read credentials, modify the repository, or post comments. The workflow reads these rules from the default branch and uses `plan -> review -> verify -> verdict`; merging remains a human decision.
