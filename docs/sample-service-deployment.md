# Deploying the one-click sample service

Install this service in the existing OpenBKN cluster. Studio uses the same gateway at `/api/studio`; no second platform instance is required. Use the published Chart and service image from the same main build or release, and pin the image digest. The service currently supports one replica with `Recreate`.

The standard Foundry product composition already includes this Chart. The paired installer change derives the 0.2 platform version and capabilities from that composition, while the publication workflow stamps the built service image digest into the Chart. After both changes are merged and published, normal product installation does not require users to fill those fields manually. The following standalone configuration remains useful for administrators and acceptance.

## Configuration and installation

Create a values file using the addresses and capabilities of the actual platform:

```yaml
image:
  repository: ghcr.io/openbkn-ai/bkn-sample-studio
  digest: sha256:<service-image-digest>
safeURL: http://bkn-safe:3000
baseURL: http://<existing-platform-gateway>
platform:
  version: "0.2.0"
  capabilities:
    - vega.catalog
    - knowledge-network.import.kn-json
    - knowledge-network.import.bkn-directory
    - execution.function
    - execution.skill
ingress:
  ingressClass: class-443
persistence:
  existingClaim: ""
```

Declare only capabilities supported by the platform. The example list is not automatic capability discovery. Leave `catalogURL` empty to scan official main when the administrator clicks **Refresh samples**. A page GET reads the existing cache; it does not scan GitHub on every request. A new environment has no remote cache. Network failure preserves an existing cache and installed records; a new environment can use the built-in entries or import a compatible offline package, with its data image available to the cluster.

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

This is the standalone published deployment entry point. Bundling it into a Foundry distribution requires changes in that distribution's deployment repository and its own acceptance; installing this Chart does not prove that integration.
