#!/usr/bin/env bash
# OpenBKN Samples one-command installer.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=installer/lib/common.sh
source "$ROOT_DIR/installer/lib/common.sh"
# shellcheck source=installer/lib/sample.sh
source "$ROOT_DIR/installer/lib/sample.sh"
# shellcheck source=installer/lib/openbkn.sh
source "$ROOT_DIR/installer/lib/openbkn.sh"
# shellcheck source=installer/lib/platform.sh
source "$ROOT_DIR/installer/lib/platform.sh"
# shellcheck source=installer/lib/runtime_docker.sh
source "$ROOT_DIR/installer/lib/runtime_docker.sh"
# shellcheck source=installer/lib/runtime_k8s.sh
source "$ROOT_DIR/installer/lib/runtime_k8s.sh"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh list
  ./install.sh <sample> [options]

Options:
  --runtime auto|k8s|docker  Data runtime (default: auto)
  --catalog-host HOST        Docker mode: database host visible to OpenBKN
  --catalog-port PORT        Docker mode: database port visible to OpenBKN (default: 3306)
  --namespace NAME           Kubernetes namespace (default: openbkn-samples)
  --base-url URL             OpenBKN URL used when login is needed
  --upgrade                  Permit an installer-managed sample upgrade
  --dry-run                  Print the plan without external writes
  -h, --help                 Show this help
EOF
}

main() {
  local sample="" runtime="auto" catalog_host="" catalog_port=""
  local namespace="openbkn-samples" base_url="" upgrade=0 dry_run=0

  if [[ "${1:-}" == "list" ]]; then
    shift
    [[ $# -eq 0 ]] || die "list does not accept options"
    list_samples "$ROOT_DIR"
    return 0
  fi
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -eq 0 ]]; then
    usage
    return 0
  fi

  sample="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --runtime) runtime="${2:?--runtime requires a value}"; shift 2 ;;
      --catalog-host) catalog_host="${2:?--catalog-host requires a value}"; shift 2 ;;
      --catalog-port) catalog_port="${2:?--catalog-port requires a value}"; shift 2 ;;
      --namespace) namespace="${2:?--namespace requires a value}"; shift 2 ;;
      --base-url) base_url="${2:?--base-url requires a value}"; shift 2 ;;
      --upgrade) upgrade=1; shift ;;
      --dry-run) dry_run=1; shift ;;
      -h|--help) usage; return 0 ;;
      *) die "unknown option: $1" ;;
    esac
  done

  validate_runtime "$runtime"
  validate_k8s_name "$namespace" "namespace"
  load_sample "$ROOT_DIR" "$sample"
  catalog_port="${catalog_port:-$SAMPLE_DOCKER_PORT}"
  validate_port "$catalog_port"

  if (( dry_run )); then
    print_install_plan "$runtime" "$catalog_host" "$catalog_port" "$namespace" "$upgrade"
    return 0
  fi

  require_python_311
  require_command curl
  require_command jq
  ensure_openbkn_login "$base_url"
  require_openbkn_safe_connector_input
  prepare_python_env "$ROOT_DIR"

  runtime="$(resolve_runtime "$runtime" "$catalog_host")"
  case "$runtime" in
    docker)
      [[ -n "$catalog_host" ]] || die "--catalog-host is required in Docker mode"
      prepare_docker_runtime "$ROOT_DIR" "$catalog_host" "$catalog_port" "$upgrade"
      ;;
    k8s)
      prepare_k8s_runtime "$ROOT_DIR" "$namespace" "$upgrade"
      ;;
    *) die "internal error: unsupported runtime $runtime" ;;
  esac
  bootstrap_platform "$runtime" "$catalog_host" "$catalog_port" "$namespace"
}

main "$@"
