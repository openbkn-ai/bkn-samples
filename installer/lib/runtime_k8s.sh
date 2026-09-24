#!/usr/bin/env bash

prepare_k8s_runtime() {
  local root="$1" namespace="$2" upgrade="$3"
  local attempt password image state_dir
  require_command kubectl
  if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
    kubectl auth can-i create namespaces | grep -qx yes || die \
      "namespace $namespace does not exist and kubectl cannot create namespaces"
    kubectl create namespace "$namespace"
  fi
  local resource verb
  for resource in statefulsets secrets services persistentvolumeclaims; do
    for verb in create patch; do
      kubectl auth can-i "$verb" "$resource" -n "$namespace" | grep -qx yes || die \
        "kubectl lacks permission to $verb $resource in namespace $namespace"
    done
  done

  state_dir="$(state_root)/runtime/$SAMPLE_ID"
  mkdir -p "$state_dir"
  chmod 700 "$(state_root)" "$(state_root)/runtime" "$state_dir"
  password="$(random_secret)"
  (umask 077; printf '%s\n' "$password" >"$state_dir/database-password")
  attempt="$(random_secret)"
  image="swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples:$(<"$root/VERSION")"

  apply_k8s_sample_manifest "$root" "$namespace" "$image" "$attempt" "$password"
  if ! kubectl rollout status "statefulset/bkn-sample-$SAMPLE_ID" -n "$namespace" --timeout=5m; then
    if ! k8s_image_pull_failed "$namespace"; then
      die "sample StatefulSet did not become ready"
    fi
    image="ghcr.io/openbkn-ai/bkn-samples:$(<"$root/VERSION")"
    printf 'warning: SWR image could not be pulled; retrying StatefulSet from GHCR\n' >&2
    apply_k8s_sample_manifest "$root" "$namespace" "$image" "$attempt" "$password"
    kubectl rollout status "statefulset/bkn-sample-$SAMPLE_ID" -n "$namespace" --timeout=5m || die \
      "sample StatefulSet did not become ready after GHCR fallback"
  fi
  printf 'runtime: Kubernetes resources applied for %s in namespace %s\n' "$SAMPLE_ID" "$namespace"
  if (( upgrade )); then
    printf 'note: --upgrade was requested; upgrade hook execution is pending platform bootstrap support\n'
  fi
}

apply_k8s_sample_manifest() {
  local root="$1" namespace="$2" image="$3" attempt="$4" password="$5"
  python3 - "$root/installer/manifests/k8s/sample.yaml" "$SAMPLE_ID" "$SAMPLE_DATABASE" \
    "$SAMPLE_VERSION" "$SAMPLE_DATA_VERSION" "$attempt" "$image" "$namespace" 3<<<"$password" <<'PY' | kubectl apply -f -
import os
import pathlib
import sys

template = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
values = {
    "BKN_SAMPLE_ID": sys.argv[2],
    "BKN_DATABASE": sys.argv[3],
    "BKN_SAMPLE_VERSION": sys.argv[4],
    "BKN_DATA_VERSION": sys.argv[5],
    "BKN_INIT_ATTEMPT": sys.argv[6],
    "BKN_SAMPLES_IMAGE": sys.argv[7],
    "BKN_NAMESPACE": sys.argv[8],
    "BKN_DATABASE_PASSWORD": os.fdopen(3).read().rstrip("\n"),
}
for key, value in values.items():
    template = template.replace("${" + key + "}", value)
sys.stdout.write(template)
PY
}

k8s_image_pull_failed() {
  local namespace="$1" reason
  reason="$(kubectl get pods -n "$namespace" -l "app.kubernetes.io/instance=$SAMPLE_ID" \
    -o jsonpath='{range .items[*].status.containerStatuses[*]}{.state.waiting.reason}{"\\n"}{end}' 2>/dev/null || true)"
  grep -Eq '(^|[[:space:]])(ErrImagePull|ImagePullBackOff)($|[[:space:]])' <<<"$reason"
}
