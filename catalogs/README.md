# Product catalogs

Each `<product-version>/catalog.json` is an independent official directory for that
OpenBKN product version, with its own revision and sequence. Its entries reference
fixed sample versions and packages. `metadata.productVersion` must match its path.

See [directory selection and publication](../docs/product-version-catalogs.md).

Current retained releases and the protected Manufacturing/Energy 021 acceptance
and promotion plan are listed in [release retention](../docs/release-retention-20261030.md).
The 021 supply releases require `sample.experience-set`; their recorded acceptance
covers fixed arm64 mainline builds, not a formally released vanilla 021 platform.
Withdrawn historical entries retain metadata for cache compatibility, while their
superseded GitHub Release assets may be removed after local archival.
