# OpenBKN Sample Development Guide

This guide defines the small, reviewable contract for adding and updating a sample in `bkn-samples`.

See the [Chinese development and version guide](SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md) for the supply-chain update workflow.

## Layout

Each sample lives under `samples/<sample-id>/` and must contain `sample.yaml`, release notes, and the files needed by its declared hooks. Use `kn/` for an OpenBKN BKN directory or KN JSON, `data/` for embedded locked data, `tools/` for functions, and `skills/` for skills. An optional `experience/experience-set.yaml` offers question-and-answer cases taken from `bkn-eval/`; see [Sample experience sets](experience-set.md).

## Contract

Keep `sample.yaml` aligned with the OpenBKN sample schema. Declare the platform range, required capabilities, components, data mode, knowledge-network entrypoint, and installation hooks. Do not add sample-specific branches to Studio or the shared installer. Required capability names identify standard API adapters implemented by the installer; they do not grant authorization or assert that an API is enabled on every deployment. Installation uses the existing OpenBKN APIs and records actual API failures. The target backend version is read through its standard health endpoint by default.

## Online delivery is a separate release step

Merging sample source or updating the installer does not publish an online sample. `sample.yaml` declares package identity; the root `catalog.json` registers downloadable releases. The refresh action reads that catalog, not arbitrary sample directories in Git. Do not add sample-name branches to Studio or the installer.

A release is complete only when all of these have been verified:

- The exact reviewed package were installed and tested.
- The package is available from an immutable official Release asset, with a fixed digest.
- `sample.json` and `verification.json` bind those exact artifacts and genuine acceptance evidence.
- A catalog entry references the metadata at a full official commit SHA and the catalog sequence increases.
- With the sample uninstalled and its offline cache removed, **Refresh samples** discovers the online version. Install from that online card, query the declared capabilities, uninstall, and verify resources and history.

Do not mark source merge, offline import, or installer deployment as online-release acceptance. Updating the installer does not replace cached packages. If a card disappears after removing its offline package, first check the catalog registration and refresh status.

## Versions and release notes

Use semantic versions. Every version gets `releases/<version>/release-notes.en-US.md` and/or `release-notes.zh-CN.md`. Describe changes, compatibility, data or network changes, and known limits. Installed version and release notes are shown by Studio.

## Build and validate

Build a review package without executing sample code:

```bash
PYTHONPATH=. python3 tools/publication/build_candidate.py samples/<sample-id> \
  --version <version> --output /tmp/sample-candidate
```

The package contains only tracked allowlisted files. Fixed data must be checked by a lock file. Validate native BKN directories with `openbkn bkn validate <sample>/kn` before publication. KN JSON uses the existing standard import API and actual object-query acceptance; the directory validator does not accept a JSON file path. Installation imports packaged content and does not invoke creator or generative Skills.

Add new sample files to the Git index before building; untracked hooks and models are excluded. Build the final candidate from the reviewed, clean commit and keep `build.json` with the package digest. Candidate construction does not execute hooks or prove that installation works. Never overwrite a published version; choose a new version and a new output directory.

For both online and offline content archives plus a candidate manifest:

```bash
PYTHONPATH=. python3 tools/publication/prepare_shared_release.py samples/<sample-directory> \
  --version <new-version> --output /absolute/path/to/candidates
```

The offline archive contains all sample content and no OCI image. The product-provisioned shared sample database is already running; uploading the package requires no node preparation. See [offline installation](offline-installation.md).

## Release and catalog

After PR review and installation acceptance, publish the immutable online and offline packages. Add `sample.json` and `verification.json` under the release directory, then update the root `catalog.json` with immutable URLs and SHA256 digests. Catalog changes also go through PR review.

Use an existing release as the small reference: [World Cup 0.1.1](../samples/world-cup/releases/0.1.1/sample.json). Keep its protocol and installation profile, replacing sample identity, content, requirements and fixed artifacts. Reference release metadata at a full official repository commit, increase the catalog sequence, and preserve existing releases. Validate against the trusted PR base:

```bash
git show origin/main:catalog.json > /tmp/baseline-catalog.json
python3 tools/publication/validate.py . --official \
  --baseline-catalog /tmp/baseline-catalog.json
```

Record fresh installation and actual database, knowledge, capability and scenario checks for the exact package in `verification.json`. A passing schema check or AI approval is not an installation result. Publish catalog references only after those fixed artifacts pass acceptance. See [candidate publication](candidate-publication.md) for the build boundary and [service deployment](sample-service-deployment.md) for deployment and recovery.

For bundled `v1alpha1` samples, declare the independent sample version in `sample.yaml` as `metadata.version`. Legacy manifests without it retain their original `0.1.0` identity, never the service `VERSION`. Online and offline packages use their fixed release version. The index top-level version and shared data-image tag remain service artifact versions.

## Updating a sample

Create a new semantic version for data, BKN structure, functions, metrics, or skills. Do not overwrite an existing release. Update release notes, rebuild the package, run installation and smoke verification, and record the new installed version. Studio treats the catalog as the source for online updates and accepts the package directly for offline import.

Version the sample as a whole; do not independently replace one file in an installed release. Include sample-declared interfaces and bindings in this rule:

| Change | Files to update and acceptance to record |
| --- | --- |
| Data | Update embedded data and its lock, then verify tables and representative values. |
| Knowledge network | Update the existing BKN / KN JSON model and bindings, validate and import it, verify objects and relations. |
| Functions | Update packaged code and registration, invoke the changed function with a representative input and check the result. |
| Metrics | Update Object Metrics V1 definitions, verify their owning object types, published versions and actual calculated results. |
| Skills | Update skill content and referenced functions/interfaces, verify discovery and the changed scenario. |
| Interfaces | Update sample-declared tool/API contracts and bindings, verify arguments, results and compatibility; declare a new platform requirement if the sample needs a different platform API. |

For each changed category, explain the change and compatibility in the new release notes. Unchanged content can remain identical, but the new package and verification must all refer to the same sample version. For supply-chain metrics, update `tools/assets/metrics-create.json`, `logic-properties.json` and `metrics-query-examples.json`. The installation hook must create, validate and publish each explicit metric version. The supply-chain metrics aggregate object sets and must not be bound as instance logical properties; `logic-properties.json` now summarizes their ownership. Verification must query actual published values against the locked CSV snapshot. Filters must use properties declared by the published metric. Merely keeping metric files in the archive does not install them. No separate metric or interface plugin protocol is required. Keep sample versions independent from the OpenBKN platform version.

Publishing a new version does not upgrade an installed sample. In-place upgrades, data migrations, and merging user changes remain unsupported. With updated installation hooks and ownership receipts, uninstall the old sample before installing another version. Uninstall clears sample data and user edits while preserving attempt history. Legacy installations without ownership receipts cannot be automatically uninstalled. See [uninstall and reinstall](sample-uninstall.md) for the implementation and validation boundary. Online and offline installation use the same fixed `package.tar.gz` with embedded data and resources. Samples share the product-provided sample database and do not require a sample image or node import. The package must pass disconnected installation, retry, uninstall and reinstall acceptance.

Each accepted installation or retry receives an `attemptId` and its own start time. Terminal records are archived separately, so retrying the same version preserves the earlier failure. Legacy records remain readable, but previously overwritten records cannot be reconstructed; Studio marks that history as incomplete. Requests rejected during preflight do not create attempts.

## Replacing an installed version

1. Publish the new version through the reviewed candidate and catalog flow above.
2. In Studio, uninstall the installed sample and confirm that its data and user edits will be removed. The five cleanup stages appear above the release notes; installation history remains available.
3. Wait until cleanup completes. If it stops, use **Continue uninstall**; do not start another installation until the card returns to **Not installed**.
4. Refresh the catalog and select the new version, or remove the old cached offline package and import the new fixed package. Removing a cached package does not uninstall platform resources.
5. Click **Install** on the card. Verify the new installed version and its database, objects/relations, declared functions, metrics and Skills. The old installation and uninstall attempts must remain in history.

The new package must include its managed installation hooks and ownership receipt helper. Legacy published packages without receipts remain immutable and cannot gain uninstall support merely by updating Studio. The current knowledge-network API allows five tags; these managed samples reserve three for ownership, leaving two for provenance. Validate the rendered model against platform constraints as well as the BKN syntax.

## Pull request checklist

- schema and capability declarations match the files;
- release notes and version are present;
- package and data image digests are fixed;
- no secrets or unreviewed executable downloads are included;
- native BKN validation passes;
- fresh installation and smoke verification are recorded;
- `catalog.json` points to the exact immutable commit and assets.

## Shared database patch and offline publication

The 0.2.0 shared database patch uses one product-provisioned sample MariaDB server, separate databases and accounts per sample. Existing `spec.database`, `dbInit` and `dbVerify` hooks remain applicable. Loaders use the installer-provided `MYSQL_*` connection settings, not a local socket, root account or image startup. Current loaders use `<database>_loading` for staging; privileges are limited to the owned target and staging schemas.

Offline delivery requires embedded data and all declared model/execution resources without runtime dependency downloads. See [offline delivery](offline-installation.md). `prepare_shared_release.py` prepares one self-contained `package.tar.gz` for both online download and offline import and a candidate manifest requiring `database.shared`; its database dependency references the archive, not an OCI image. Verify each new version and retain immutable historical artifacts.

Declare the sample content language with optional `metadata.language` (for example, `zh-CN` or `en-US`) in `sample.yaml`. This field is carried into new packages and the Studio catalog; it is independent of the release-note language. Published catalog entries may also declare `language`. Older packages without it can reuse a known catalog language; otherwise they remain visible under **All languages**. Do not rewrite published packages or fixed release manifests just to add this field.
