# Self-contained offline sample installation

Offline installation must not contact GitHub, GHCR, a mirror, or any other external service. Calls to the already installed OpenBKN APIs and Kubernetes remain necessary. Online catalog installation is a separate path.

## Package and preparation

Use **offline-package.tar.gz**, format `samples.openbkn.ai/offline.v2`. It contains the sample data, native knowledge network, declared function/metric/Skill assets, release notes, every OCI image manifest/config/layer for its declared architectures, and a Python standard-library preparation tool. A URL or image digest alone is not an offline artifact. URL-only `offline.v1` packages are rejected; previously published bytes are not rewritten.

The OpenBKN product and its infrastructure must already be installed. This package supplies the additional sample runtime, not a second platform installation.

1. Transfer the package into the disconnected environment and extract it.
2. On **each schedulable Kubernetes node**, use the node's existing containerd CLI and Python 3 to import the bundled image:

   ```sh
   python3 runtime/prepare_offline.py
   # If the node uses k3s:
   python3 runtime/prepare_offline.py --ctr 'k3s ctr'
   # Or specify the existing containerd socket:
   python3 runtime/prepare_offline.py --address /run/containerd/containerd.sock
   ```

   Run with the administrator permissions required by the installed runtime. The tool validates the exact image and every blob, streams a local OCI import into namespace `k8s.io`, and verifies the pinned image name. It never invokes pull, builds an image, contacts a registry, changes permissions, or installs a privileged service. Currently containerd is the supported node preparation path; other runtimes are not claimed.
3. In Studio → Home → One-click experience → **Import offline package**, select the original `offline-package.tar.gz`, then click **Install**.

Node preparation is an explicit administrator step. Uploading a package to the application does not grant it host container-runtime access. Copy/import the image on every eligible node so rescheduling remains offline.

## Installation and retry

Both paths use only the imported package and set the sample database's `imagePullPolicy: Never`. Missing local images fail with `offline_image_missing` and instructions to import from the package. Retry preserves the same package/image identity, revalidates its local contents, and never falls back to online installation or another registry. Importing the image locally after a missing-image failure allows the normal retry action to continue.

The upload limit is 1 GiB and expanded contents are bounded at 2 GiB. Image hashes are streamed, not loaded entirely into service memory. The offline cache is bounded at 3 GiB; allow space for temporary extraction and staging as well. Size the existing state volume for the packages you retain (for three maximum-size packages, allow at least 6 GiB free during import). Existing PVCs are not silently resized. The bundled OCI tool also needs local temporary disk space for an uncompressed OCI transport archive.

## Building on the connected publisher machine

```sh
# Resolve and review IMAGE_REF as an immutable registry/repository@sha256 reference.
skopeo copy --all --preserve-digests "docker://$IMAGE_REF" oci:/tmp/sample-oci:sample
PYTHONPATH=. python3 tools/publication/build_candidate.py samples/world-cup-en \
  --version 0.1.0 --output /tmp/offline-candidate \
  --data-image-ref "$IMAGE_REF" --image-layout /tmp/sample-oci
```

The builder verifies the complete blob closure and derives supported Linux architectures from the bundled image. It produces `offline-package.tar.gz`. Build the lean online `package.tar.gz` separately without either image flag; its existing catalog URL, digest and size limits remain unchanged. Publish the complete offline asset as an additional release attachment after actual disconnected acceptance. Do not replace existing release assets or alter immutable historical proofs.

## Required acceptance

Begin with the sample image absent from the target runtime and block external traffic at the node and application boundaries. Verify that installation fails locally without pulling. Import the image from the same package, retry successfully, verify actual data/network and declared capabilities, uninstall, and reinstall while external traffic stays blocked. Inspect pull policies, task history, old resource absence, and traffic evidence. A warm-cache installation, mocked networking, or an unreachable URL alone does not establish offline acceptance.
