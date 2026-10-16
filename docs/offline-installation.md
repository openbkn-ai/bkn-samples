# Offline sample installation

The shared sample database patch for OpenBKN 0.2.0 separates the database server from sample content. Online and offline installations use one product-provisioned sample MariaDB server. Each sample has its own database and account; OpenBKN system databases are separate.

## User flow

1. Install or upgrade OpenBKN with the sample service Chart containing the shared sample database. Product offline delivery must include its runtime images, including MariaDB.
2. Download the desired version's **package.tar.gz** Release attachment on a connected machine and transfer it to the offline environment.
3. In Studio → Home → One-click experience, import the package and click **Install**.

No node command, image import, registry connection, or dependency download is required by sample installation. The package includes data, native knowledge network, declared functions/metrics/Skills, installation scripts, release notes, and a complete file digest inventory. Existing OpenBKN services and the sample database must be available inside the environment.

## Installation, retry and uninstall

The installer executes the manifest's existing `dbInit` and `dbVerify` hooks against the sample's scoped account, then uses the standard platform import and verification flow. Shared runtime packages require embedded data. Missing or damaged content fails locally; it must never fall back to downloading data or a sample image.

Retry uses the original local package and ownership receipt. Uninstall uses recorded resource IDs and database ownership, independently of the package and official catalog. It removes only the sample's databases, account and platform resources; other samples, the database server and installation history remain. Internal service failures have bounded waits and leave a retryable failure.

Old per-sample database installations retain their original uninstall path. Uninstall them before installing a new shared-runtime version; no automatic migration is performed. Historical Release attachments are immutable. Old image-bearing offline.v2 packages remain inspectable, but the patched installer loads their embedded content into the shared runtime without running the bundled image or node tool. URL-only offline.v1 packages remain unsupported.

## Publisher flow

Add release notes for a new version, then prepare the single delivery archive and candidate manifest:

```sh
PYTHONPATH=. python3 tools/publication/prepare_shared_release.py \
  samples/world-cup-en --version NEW_VERSION --output /absolute/path/to/candidates
```

The command produces one self-contained `package.tar.gz` and a candidate `sample.json`. Online installation downloads this archive; offline installation imports the exact same bytes and digest. The unified archive uses the existing online compressed-size limit of 128 MiB; oversized candidates are rejected during construction. The online manifest declares `database.shared` and points its data dependency to the archive. No sample image is required. Older sample services reject the new required capability rather than attempting an incompatible installation.

These outputs are candidates, not acceptance evidence. Verify the exact package digests, submit release metadata and real verification receipts through PR review, publish new Release attachments, and update the pinned official catalog. Never overwrite existing version assets or fabricate successful verification.

## Required acceptance

With the product already running, remove all sample-specific image caches and block external access. Import, install, retry, uninstall, and reinstall every sample. Verify actual data, knowledge networks and declared functions/metrics/Skills. Keep another sample installed while uninstalling one and verify that its data and resources remain usable. Delete the offline package and make the official catalog unavailable, then verify uninstall still works. Simulate unavailable internal services and ensure operations finish with a retryable failure instead of remaining in progress indefinitely.
