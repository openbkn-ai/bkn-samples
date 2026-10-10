# OpenBKN Sample Development Guide

This guide defines the small, reviewable contract for adding and updating a sample in `bkn-samples`.

## Layout

Each sample lives under `samples/<sample-id>/` and must contain `sample.yaml`, release notes, and the files needed by its declared hooks. Use `kn/` for an OpenBKN BKN directory or KN JSON, `data/` for embedded locked data, `tools/` for functions, and `skills/` for skills.

## Contract

Keep `sample.yaml` aligned with the OpenBKN sample schema. Declare the platform range, required capabilities, components, data mode, knowledge-network entrypoint, and installation hooks. Do not add sample-specific branches to Studio or the shared installer.

## Versions and release notes

Use semantic versions. Every version gets `releases/<version>/release-notes.en-US.md` and/or `release-notes.zh-CN.md`. Describe changes, compatibility, data or network changes, and known limits. Installed version and release notes are shown by Studio.

## Build and validate

Build a review package without executing sample code:

```bash
python3 tools/publication/build_candidate.py samples/<sample-id> \
  --version <version> --output /tmp/sample-candidate
```

The package contains only tracked allowlisted files. Fixed data must be checked by a lock file. Validate native BKN with `openbkn bkn validate <sample>/kn` before publication.

## Release and catalog

After PR review and installation acceptance, publish the immutable package and data image. Add `sample.json` and `verification.json` under the release directory, then update the root `catalog.json` with immutable URLs and SHA256 digests. Catalog changes also go through PR review.

## Updating a sample

Create a new semantic version for data, BKN structure, functions, metrics, or skills. Do not overwrite an existing release. Update release notes, rebuild the package, run installation and smoke verification, and record the new installed version. Studio treats the catalog as the source for online updates and accepts the package directly for offline import.

## Pull request checklist

- schema and capability declarations match the files;
- release notes and version are present;
- package and data image digests are fixed;
- no secrets or unreviewed executable downloads are included;
- native BKN validation passes;
- fresh installation and smoke verification are recorded;
- `catalog.json` points to the exact immutable commit and assets.
