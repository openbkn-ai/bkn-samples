# Deploying the one-click sample service

Install this service in the existing OpenBKN cluster. Studio uses the same gateway at `/api/studio`; no second platform instance is required. Use the published Chart and service image from the same main build or release, and pin the image digest. The service currently supports one replica with `Recreate`.

The standard product deployment entry in `openbkn-ai/openbkn-deploy` includes this Chart. The sample service uses the existing internal ingress-nginx HTTP entrypoint by default, independently of the public HTTPS address. It does not create another gateway or change public Ingress/TLS settings. The publication workflow stamps the built service image digest into the Chart. Default installation no longer needs manually filled platform version or API capability values.

The service reads `GET /api/bkn-backend/v1/health`, the same version endpoint used by the SDK, when listing releases, accepting a selected installation, importing an offline package or retrying. Missing or malformed version information keeps fixed-package installation unavailable. It does not infer a version from a Chart tag.

`requires.capabilities` identifies the standard API adapters needed by a sample. The installer rejects names it does not implement. This is not a claim that the target deployment has every API enabled: actual API calls enforce availability, authorization and licensing, with failures recorded in the installation stages. `GET /api/safe/v1/capabilities` describes licensing and paid extensions and is not used as the sample API inventory.

Explicit `platform.version` and nonempty `platform.capabilities` values remain supported for existing deployments and operator restrictions. A version override is an operator declaration rather than a health check; use the empty defaults for automatic version reading. These overrides do not bypass platform API authorization.

The repository `VERSION` is the product service and image base version, aligned with OpenBKN 0.2.0. Both `bkn-sample-studio` and `bkn-samples` images, and the service Chart, use this base version; main builds append `-main.<UTC timestamp>.sha<commit>`. Individual sample packages retain their own independently published versions and immutable artifact references.

For a release candidate, open GitHub Actions → **Publish sample catalog service** → **Run workflow** on the default branch, then enter `release/X.Y.Z` in **source_branch**. The workflow checks out that branch and publishes both images and the service Chart as `X.Y.Z-release.<UTC timestamp>.sha<commit>`; the branch version must match `VERSION`. A normal `main` push still creates a main build. A final `vX.Y.Z` tag uses the separate release-tag publication path.

## Configuration and installation

Create a values file using the actual platform addresses. Leave the optional platform overrides empty:

```yaml
image:
  repository: ghcr.io/openbkn-ai/bkn-sample-studio
  digest: sha256:<service-image-digest>
safeURL: http://bkn-safe:3000
# Default internal gateway; no manual value is needed in the standard product topology.
baseURL: http://ingress-nginx-controller.ingress-nginx.svc.cluster.local
# Optional: version detection only; business operations still use baseURL.
backendURL: ""
platform:
  version: ""
  capabilities: []
ingress:
  ingressClass: class-443
persistence:
  existingClaim: ""
```

Leave `catalogURL` empty to scan official main when the administrator clicks **Refresh samples**. A page GET reads the existing cache; it does not scan GitHub on every request. A new environment has no remote cache. Network failure preserves an existing cache and installed records; a new environment can use the built-in entries or import a compatible offline package, with its data image available to the cluster.

```bash
helm upgrade --install bkn-sample-studio \
  oci://ghcr.io/openbkn-ai/charts/bkn-sample-studio \
  --version <published-chart-version> -n openbkn -f sample-service-values.yaml
kubectl -n openbkn rollout status deployment/bkn-sample-studio
```

Use **Import offline package** on Studio's one-click tab for local `package.tar.gz` files. Administrator authentication is required. Online and offline installation share the installer, fixed version and artifact checks; offline import does not need an online catalog.

## Existing deployment and state

Before migration, stop accepting installations, wait for running tasks to finish, and back up `/var/lib/bkn-samples` to a protected location. It can contain database credentials; do not commit it. Preserve both the state PVC and the sample database resources. Set `persistence.existingClaim` to the original state PVC when adopting an existing deployment. An emptyDir deployment requires explicitly copying its state to a PVC before replacing the Pod; Helm does not copy it automatically.

For resources originally created outside Helm, inspect ownership before adopting them. Helm 4 supports `--take-ownership`; apply it only to this service's resources. A deployment previously changed with `kubectl set image` may also need `--force-conflicts` to return image-field ownership to Helm. These flags are migration tools, not required on a clean installation.

After deployment, compare installed versions, timestamps, network links and history with the backup, then restart the Pod and compare again. Legacy history remains incomplete; migration must not invent missing attempts.

## Rollback and uninstall

Keep the same PVC during rollback. Use `helm history bkn-sample-studio -n openbkn` to select the actual prior revision, then `helm rollback bkn-sample-studio <revision> -n openbkn`. Check history and network links after rollback, and return to the current build when acceptance is complete. Older services may not display newer attempt records correctly; do not create installations during a compatibility rollback check. State backup remains necessary.

The state PVC and `openbkn-samples` namespace are retained by the Chart's `helm.sh/resource-policy: keep` annotations. Removing the service must not remove installed databases. Charts before the namespace-retention fix lack that protection: do not uninstall those releases with sample data present. A later deliberate cleanup must separately inspect and remove sample resources and retained volumes.

Product integration is maintained in [openbkn-deploy](https://github.com/openbkn-ai/openbkn-deploy). Use its standard installation entry and the official sample service Chart. Runtime state uses a PVC and a single-replica Recreate deployment. Service restart preserves installed records and history; interrupted tasks require an explicit retry.

`baseURL` must reach the unified OpenBKN gateway, including Backend, Vega and capability APIs. A Backend-only service will pass version detection but fail sample installation with a Vega 404. For deployments whose public gateway uses a private CA, trust that CA for business API calls; optionally set `backendURL` to the in-cluster Backend service for unauthenticated version detection. Do not disable TLS verification or replace `baseURL` with that service. An empty `backendURL` preserves gateway-based version detection.

For an existing deployment that recorded a Backend-only or untrusted external `baseURL`, correct that stored override during upgrade. Helm upgrades that reuse prior values may preserve it; updating the image alone does not correct it. Keep the existing PVC and fixed data/executor images. A different internal topology may require an operator override. Before using that override, verify Backend health, authenticated Vega/knowledge-network/capability APIs, Host matching and the absence of an unwanted HTTPS redirect.

For a direct Chart upgrade of an affected deployment in the standard product topology, the following command corrects the stored addresses while preserving other Helm values, including the PVC and pinned images:

```bash
helm upgrade bkn-sample-studio \
  oci://ghcr.io/openbkn-ai/charts/bkn-sample-studio \
  --version <published-chart-version> -n openbkn --reuse-values \
  --set-string baseURL=http://ingress-nginx-controller.ingress-nginx.svc.cluster.local \
  --set-string backendURL=
```

Use a published Chart/image pair compatible with the current platform version. This routing-only correction does not require reversioning samples or replacing their data images. The standard product installer performs the same address correction, including when the Chart version has not changed. Use the operator-approved gateway instead for a nonstandard topology; do not disable TLS or SDK version checks.
