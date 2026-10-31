# Product version catalogs

The product version selects `catalogs/<product-version>/catalog.json`. The directory
lists independently versioned samples with fixed manifest, package and verification
digests. The service image version does not select the directory. Package-level
platform, architecture, capability and executor checks still apply, including offline
imports. The legacy root `catalog.json` remains unchanged for released 0.2.0 clients.

The service reads the product version from the public Backend health endpoint;
`platform.version` remains an explicit deployment override. On refresh it resolves the
trusted main reference to one commit, then fetches the version-specific catalog at
that commit. Unknown/unpublished versions never fall back to another directory.
A service restart can load its bundled product directory without network access.
Installed receipts and imported offline packages remain available independently.

`catalogURL` can pin the official repository URL at a full SHA, for example
`https://raw.githubusercontent.com/openbkn-ai/bkn-samples/<40-character-SHA>/catalogs/0.2.1/catalog.json`.
The path and `metadata.productVersion` must match the detected product. An existing
pin to the legacy root directory must be changed when deploying this service.
Product versions have separate caches and monotonically increasing sequences;
switching between them does not delete another version's cache or installation history.

The initial 0.2.0 directory preserves its existing sample entries. The initial 0.2.1
directory contains the already published bilingual FIBO/GS1 releases declaring
0.2.1 compatibility. The twelve samples offered on 0.2.1 are tracked by
tools/publication/candidates-0.2.1.json (Order Basics is excluded) and added to stable
directories only after fixed-candidate platform acceptance.

Release tags and titles carry the product version, for example the tag
`openbkn-0.2.1-world-cup-v0.1.7` titled `[OpenBKN 0.2.1] 世界杯 0.1.7`, so a release
list shows which product each package targets. `prepare_shared_release.py` writes this
tag into the manifest's download location and rebuilds the manifest from `sample.yaml`. Missing entries are not replaced with an
unverified bundled development sample in the online listing.

## Publish and verify

Build candidates from reviewed fixed source using `tools/publication/prepare_shared_release.py`.
A downloadable prerelease candidate may be imported and tested before OpenBKN 0.2.1
is released. Uploading a candidate does not claim acceptance and does not add it to
the official directory. Never fabricate `verification.json` to admit a candidate.

After acceptance, add the same package and its genuine proof to the product catalog.
A package verified for more than one product may be referenced by multiple catalogs.
Each catalog's sequence and history advance independently; preserve historical
entries and immutable metadata. To validate a product directory:

```sh
python tools/publication/validate.py . --official --catalog catalogs/0.2.1/catalog.json
```

Use `--baseline-catalog` with the previous version of that same product directory
for immutability checks. The contract workflow checks all product directories.
The root directory retains its existing validation and publication lifecycle.

A fixed catalog pin that does not match the detected product directory is rejected
with HTTP 409 / `catalog_configuration_invalid`, including legacy root pins after
a product upgrade. Update the pin to `catalogs/<actual-version>/catalog.json` at
a trusted immutable commit. The service does not fetch or fall back to another
product directory in this case.
