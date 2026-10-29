# Original official020 supply compatibility release

This maintenance release targets the unchanged original OpenBKN0.2.0 Sample service. It does not target the later shared-database patch described in [offline-installation.md](offline-installation.md). The same numeric platform version can therefore have different installation capabilities; inspect the actual service before choosing an artifact.

## Artifact contract

- Chinese supply0.1.16: URL-only `samples.openbkn.ai/offline.v1`, `>=0.2.0 <0.2.1`, per-sample database image fixed by digest.
- The image is not contained in `package.tar.gz`; provision it in the cluster before importing the archive in a disconnected environment.
- The later shared installer rejects this legacy protocol. Use its own shared `offline-package.tar.gz` release, not this original020 compatibility artifact. The default maintenance builder is unchanged.

## Reproducible build

Review and commit the source, including all new files, before a final build. Keep the old Git object3a0b4ab5a09a42cd43953a38466e762aadfcc0ab available (`git fetch` it if the checkout is shallow). Run:

```sh
python3 tools/publication/build_candidate_020.py samples/supply_ontology_hand \
  --version 0.1.16 --output /absolute/path/outside/repository \
  --data-image-ref ghcr.io/openbkn-ai/bkn-samples@sha256:<verified-digest>
```

The explicit compatibility entry loads the original reviewed builder from a full commit, verifies its SHA256, and only narrows the original platform constraint. It packages the current clean source through the Git index, excludes evaluation/experience material, and records source commit, builder commit/hash, transformed code hash, wrapper hash, Python/PyYAML versions and package digest in build.json. It does not rewrite a tar by hand or execute sample hooks. `--allow-dirty` marks a preliminary candidate only; it is not a release build.

## Acceptance and evidence

After all blind answers are frozen, install the exact final archive on original official020; verify12 business tables, ontology,14 source bundles, object-array schema, metrics/Skills and54 deterministic business calls. Uninstall and reinstall it, retaining fresh installation identities.

A newer source baseline can change documentation and packaging without changing business computation. Preserve both package SHAs and prove all data/model/function/schema/Skill payloads byte-identical before reusing a prior model trial as supporting evidence. Label this “original blind-tested package plus final-package equivalence regression”; never claim the final archive participated in a model trial it did not run. Historical answers and trials stay in maintenance records, outside current runtime and agent input archives.

The ordinary source review, human merge decision, fixed Release asset verification and catalog metadata gates still apply.
