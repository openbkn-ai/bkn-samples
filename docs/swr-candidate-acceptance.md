# Immutable SWR candidate acceptance

The sample service publishing workflow also accepts a reviewed commit pushed to
`validation/66-swr-*`. Ordinary pull-request branches do not publish. This path
uses `VERSION-rc.66.<run_id>.<run_attempt>`; it never updates `latest`, a stable
version, or a main/release build tag. A rerun gets a new candidate version.

This publishes service and sample-data architecture tags and manifest lists to
the existing SWR and GHCR repositories, followed by a matching OCI Chart in
`ghcr.io/openbkn-ai/charts`. It uses the existing repository publishing secrets.
It does not deploy a release or alter a cluster. Candidate images/Charts remain
available for review; this workflow does not delete registry artifacts.

After publication, native GitHub-hosted `ubuntu-24.04` (amd64) and
`ubuntu-24.04-arm` (arm64) jobs run `installer/ci/verify_swr_cold_pull.sh`.
Builds retain the normal workflow's QEMU support; **cold-pull verification is
native, not emulated**. The script refuses a mismatched host architecture.

Each of the two images gets a separate privileged Docker-in-Docker harness,
network, and empty named volume on a disposable CI runner. The harness uses
containerd's image store, with no host image/content mounts. Evidence records
empty image and blob listings before the target pull. The harness image itself
is downloaded before this isolation and is not a target-layer cache.

The runner firewall allows the harness only HTTPS to the recorded SWR IPv4
addresses, the exact observed OBS blob host
`op-svc-swr-b051-10-147-7-14-3az.obs.cn-east-3.myhuaweicloud.com`, and DNS.
Host-to-IP mappings are retained. This OBS redirect was first observed (and
blocked as intended) by both native jobs of run `39938478419`. The bridge has IPv6 disabled. A GHCR request must fail and
increment the reject counter before the SWR pull begins. Unlisted SWR blob
redirect/CDN destinations fail closed; do not loosen the firewall to all HTTPS
to make a failed run pass. If a redirect is required, review the actual endpoint
and add a narrow explicit policy in a follow-up change before rerunning.

Both pulls use the independently verified SWR index digest from publication.
Evidence includes the exact index, native child manifest, image config, image
inspection, every compressed layer's measured SHA256 and size, pull progress,
and firewall rules/counters. The verifier fails on missing content, mismatched
hashes/sizes, or a non-native image config. Signed URL query strings in pull
errors are redacted. Pulls are anonymous, matching the standard Chart without imagePullSecrets.
No registry credentials are passed to cold-pull jobs; the script verifies no
Docker login configuration exists. Start/end/elapsed timing is recorded for each pull. Cleanup removes the harness, network, volume,
and firewall chain on success or failure. Evidence artifacts are kept 14 days.

A successful run establishes fresh native pulls of these exact candidate
digests under the recorded egress policy. It does not establish production
rollout, future-node prewarming, or application behavior. Earlier local kind
acceptance used cached arm64 layers and cannot substitute for these CI results.

## Retesting the same published content

`retest-swr-candidate.yml` accepts only `validation/66-cold-*` branch pushes.
This pattern does not trigger publication. Its reviewed environment pins the
original version, publication run, source commit, and both SWR index digests from
run `39938478419`; it accepts no arbitrary tag input. Evidence distinguishes the
image source commit from the updated harness commit. Each rerun still creates
new empty stores, so fixing an allowlist cannot inherit partially downloaded
content from an earlier failed run. Updating the pinned tuple requires a normal
reviewed code change tied to new publication evidence.
