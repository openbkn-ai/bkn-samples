#!/usr/bin/env bash
# Dedicated, disposable Linux CI runners only. Never use a business Docker daemon.
set -euo pipefail
umask 077
: "${EXPECTED_ARCH:?}"
: "${SERVICE_DIGEST:?}" "${DATA_DIGEST:?}" "${CANDIDATE_VERSION:?}"
registry=swr.cn-east-3.myhuaweicloud.com
evidence="$PWD/cold-pull-evidence"
mkdir -p "$evidence"
case "$(uname -m)" in x86_64) native=amd64;; aarch64) native=arm64;; *) exit 1;; esac
test "$native" = "$EXPECTED_ARCH"
printf 'native=%s\nversion=%s\nsource=%s\n' "$native" "$CANDIDATE_VERSION" "$(git rev-parse HEAD)" > "$evidence/runner.txt"

# The harness image is fetched before creating the target image store. No host
# image/layer mounts are passed to the nested daemon. Each target gets a new volume.
docker pull docker:27.5.1-dind > "$evidence/harness-pull.log" 2>&1
docker image inspect docker:27.5.1-dind --format '{{json .RepoDigests}}' > "$evidence/harness-digests.json"
getent ahostsv4 "$registry" | awk '{print $1}' | sort -u > "$evidence/allowed-registry-ipv4.txt"
test -s "$evidence/allowed-registry-ipv4.txt"

container= volume= network= chain= ip= pull_log=
cleanup() {
  local failed=0
  if [[ -n "$chain" ]]; then
    sudo iptables -nvL "$chain" > "$evidence/${image:-setup}-egress-counters.txt" 2>/dev/null || true
    [[ -z "$ip" ]] || sudo iptables -D DOCKER-USER -s "$ip" -j "$chain" || failed=1
    sudo iptables -F "$chain" || failed=1
    sudo iptables -X "$chain" || failed=1
  fi
  [[ -z "$container" ]] || docker rm -fv "$container" >/dev/null || failed=1
  [[ -z "$volume" ]] || docker volume rm "$volume" >/dev/null || failed=1
  [[ -z "$network" ]] || docker network rm "$network" >/dev/null || failed=1
  [[ -z "$pull_log" ]] || rm -f "$pull_log" || failed=1
  container= volume= network= chain= ip= pull_log=
  return "$failed"
}
trap 'status=$?; cleanup || status=1; exit "$status"' EXIT

for image in bkn-sample-studio bkn-samples; do
  if [[ "$image" = bkn-sample-studio ]]; then digest="$SERVICE_DIGEST"; else digest="$DATA_DIGEST"; fi
  [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
  directory="$evidence/$image"
  mkdir -p "$directory"
  suffix="${GITHUB_RUN_ID:-local}-${RANDOM}"
  network="swr-cold-$suffix"
  volume="swr-cold-$suffix"
  container="swr-cold-$suffix"
  docker network create "$network" >/dev/null
  docker volume create "$volume" >/dev/null
  docker run -d --privileged --entrypoint dockerd --name "$container" --network "$network" \
    -e DOCKER_TLS_CERTDIR= -v "$volume:/var/lib/docker" \
    docker:27.5.1-dind --host=unix:///var/run/docker.sock \
    --feature=containerd-snapshotter=true --iptables=false --bridge=none >/dev/null
  for _ in $(seq 1 60); do
    if docker exec "$container" docker info >/dev/null 2>&1; then break; fi
    sleep 1
  done
  docker exec "$container" docker info --format '{{json .}}' > "$directory/daemon-before.json"
  docker exec "$container" docker image ls -aq > "$directory/images-before.txt"
  test ! -s "$directory/images-before.txt"
  docker exec "$container" sh -c 'find /var/lib/docker -path "*/blobs/sha256/*" -type f' > "$directory/blobs-before.txt"
  test ! -s "$directory/blobs-before.txt"

  ip="$(docker inspect "$container" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
  [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
  chain="SWRCOLD${RANDOM}"
  sudo iptables -N "$chain"
  # No unrestricted established-connection rule: every packet must match the
  # SWR IPv4 allowlist. Redirects to unlisted blob/CDN hosts fail closed.
  while read -r address; do
    sudo iptables -A "$chain" -d "$address" -p tcp --dport 443 -j ACCEPT
  done < "$evidence/allowed-registry-ipv4.txt"
  sudo iptables -A "$chain" -p udp --dport 53 -j ACCEPT
  sudo iptables -A "$chain" -p tcp --dport 53 -j ACCEPT
  sudo iptables -A "$chain" -j REJECT
  sudo iptables -I DOCKER-USER 1 -s "$ip" -j "$chain"
  sudo iptables -S "$chain" > "$directory/egress-policy.txt"
  docker exec "$container" cat /proc/net/if_inet6 > "$directory/ipv6-addresses.txt"
  # Docker bridge IPv6 must remain disabled; IPv6 cannot bypass the IPv4 policy.
  test "$(docker network inspect "$network" --format '{{.EnableIPv6}}')" = false
  if timeout 20 docker exec "$container" wget -T 10 -S -O /dev/null https://ghcr.io/v2/ > "$directory/ghcr-denied.log" 2>&1; then
    echo 'GHCR unexpectedly reachable' >&2; exit 1
  fi
  # Failed HTTP authorization would not prove the firewall worked: require the
  # reject rule to have actually rejected packets from the harness.
  sudo iptables -nvL "$chain" > "$directory/ghcr-denied-counters.txt"
  awk '$3 == "REJECT" && $1 > 0 { found=1 } END { exit !found }' "$directory/ghcr-denied-counters.txt"

  # Anonymous by design: standard Chart defaults have no imagePullSecrets.
  test "$(docker exec "$container" sh -c 'test ! -e /root/.docker/config.json && echo absent')" = absent
  reference="$registry/openbkn-ai/$image@$digest"
  printf '%s\n' "$reference" > "$directory/reference.txt"
  pull_log="$(mktemp)"
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  started_epoch="$(date +%s)"
  pull_status=0
  timeout 900 docker exec "$container" docker pull --platform "linux/$native" "$reference" > "$pull_log" 2>&1 || pull_status=$?
  ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  elapsed="$(( $(date +%s) - started_epoch ))"
  printf 'start=%s\nend=%s\nelapsed_seconds=%s\nexit_status=%s\nauth=anonymous\n' "$started_at" "$ended_at" "$elapsed" "$pull_status" > "$directory/timing.txt"
  # Registry errors can contain signed redirect URLs. Never archive URL queries.
  python3 - "$pull_log" "$directory/pull.log" <<'PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(errors="replace")
text = re.sub(r'(https?://[^?\s"<>]+)\?[^\s"<>]+', r'\1?[redacted]', text)
pathlib.Path(sys.argv[2]).write_text(text)
PY
  rm -f "$pull_log"
  pull_log=
  test "$pull_status" = 0
  docker exec "$container" docker image inspect "$reference" > "$directory/image-inspect.json"
  docker exec "$container" sh -c 'find /var/lib/docker -path "*/blobs/sha256/*" -type f -exec sha256sum {} \;' > "$directory/blob-hashes.txt"
  python3 installer/ci/verify_cold_store.py "$container" "$directory" "$digest" "$native"
  cleanup
done
